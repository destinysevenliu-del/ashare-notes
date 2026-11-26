"""每周价格更新（固定流程，任何模型或人都按这个跑）。

用法：
  python3 -I pipeline/weekly_update.py <项目根目录> [--asof YYYY-MM-DD] [--metrics 文件] [--csi 文件] [--no-build] [--snapshot-only]
步骤（每一步失败都会停下并打印原因，不会写半截数据）：
  1. 取数：默认 Python 直连东方财富数据中心与中证指数公司；连不上时改用浏览器通道
     （pipeline/weekly/metrics.js，见 更新流程.md），把结果用 --metrics / --csi 传进来。
  2. 写入：只覆盖价格与筹码字段（l1_enrich.json、val_extra.json 的现价/股息率/PB、逻辑二候选的现价与箱体位置、
     10年国债、中证全指），基本面字段和候选名单不动（那是季度更新的事）。
  3. 快照：按当前规则算出每只股票的买入区、卖出价、止损价和状态，存 data/snapshots/prices/<日期>.json。
  4. 对比：和上一份快照比，列出状态变化（进入买入区、到达卖出价、跌破止损、价格确认等），写 data/weekly_changes.json，
     个股页顶部“本周变化”读这个文件。
  5. 生成网页并跑测试。发布另行执行 publish_api.py（需要令牌，由用户本机执行或授权后执行）。
"""
import json, sys, datetime, subprocess, os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weekly import metrics as M

ROOT = Path(sys.argv[1]); ARGS = sys.argv[2:]
def arg(k):
    return ARGS[ARGS.index(k) + 1] if k in ARGS else None
def rj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def wj(p, o):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp"); tmp.write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(p)

BJ = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
ASOF = arg("--asof") or BJ.date().isoformat()
EN_P = ROOT / "data/raw/stock_pick/l1_enrich.json"; VX_P = ROOT / "data/raw/stock_pick/val_extra.json"
SP_P = ROOT / "data/stock_pick.json"; ST_P = ROOT / "data/raw/weekly/state.json"
SNAP = ROOT / "data/snapshots/prices"; CH_P = ROOT / "data/weekly_changes.json"
RULES_VERSION = "2026-11-19 箱体加股东户数条件"  # 规则版本变化时，本周变化不比较结论（避免把改规则当成市场变化）
PRICE_FIELDS = ["close", "pxdate", "pos52", "dd", "ret60", "vsMA60", "marginPct", "margin20", "holdersChg", "hdate", "focus", "top10free", "lift6m"]

def codes():
    en = rj(EN_P); L2 = rj(SP_P)["logic2"]
    c = [k for k in en if k != "_meta"] + [x["code"] for x in L2["top"]] + [L2["reference"]["code"]]
    return list(dict.fromkeys(c))

def step_fetch():
    cs = codes()
    if arg("--metrics"):
        m = rj(arg("--metrics"))
    else:
        try:
            m = M.metrics(cs, ASOF)
        except Exception as e:
            wj(ROOT / "data/raw/weekly/codes.json", cs)
            sys.exit("取数失败：%s\n改用浏览器通道：股票代码已写到 data/raw/weekly/codes.json，按 更新流程.md 第二节操作后用 --metrics 传入。" % e)
    if arg("--csi"):
        csi = M.csi_rows(rj(arg("--csi"))) if isinstance(rj(arg("--csi")), dict) else rj(arg("--csi"))
    else:
        try: csi = M.fetch_csi_all(ASOF)
        except Exception as e: sys.exit("中证全指取数失败：%s\n改用浏览器通道 csiAll()，结果用 --csi 传入。" % e)
    miss = [c for c in cs if not (m["metrics"].get(c) or {}).get("close")]
    if len(miss) > len(cs) * 0.1: sys.exit("缺价格的股票过多（%d只：%s），停止，不写入。" % (len(miss), ",".join(miss[:10])))
    dates = sorted({v["pxdate"] for v in m["metrics"].values() if v.get("pxdate")})
    return m, csi, miss, dates[-1]

def step_write(m, csi, miss, asof):
    en = rj(EN_P); vx = rj(VX_P); sp = rj(SP_P); mt = m["metrics"]
    for c, v in mt.items():
        if not v.get("close"): continue
        if c in en:
            old = en[c].get("close"); en[c].update({k: v[k] for k in PRICE_FIELDS if v.get(k) is not None})  # 新值为空时保留旧值（如最新一期户数未披露前十大流通股东）
            if c in vx and vx[c].get("dps") is not None:
                if vx[c].get("pb") and vx[c].get("close"): vx[c]["pb"] = round(vx[c]["pb"] * v["close"] / vx[c]["close"], 2)
                vx[c]["close"] = v["close"]; vx[c]["dy"] = round(vx[c]["dps"] / v["close"] * 100, 2); en[c]["dy"] = vx[c]["dy"]
            elif en[c].get("dy") and old: en[c]["dy"] = round(en[c]["dy"] * old / v["close"], 2)
    en["_meta"]["as_of"] = asof
    en["_meta"]["weekly"] = "价格与筹码字段由 pipeline/weekly_update.py 每周覆盖；基本面字段（gm、gmChg、roe、cashEps）季度更新。最近一次：%s，缺价格：%s" % (asof, "、".join(miss) or "无")
    L2 = sp["logic2"]
    for x in L2["top"] + [L2["reference"]]:
        if "boxL" not in x:  # 首次运行：由建档时的现价、位置、宽度反推箱底箱顶并固定，季度重算
            x["boxL"] = round(x["close"] / (1 + x["pos"] * x["W"]), 3); x["boxH"] = round(x["boxL"] * (1 + x["W"]), 3); x["box_asof"] = L2.get("box_asof", "2026-11-13")
        v = mt.get(x["code"]) or {}
        if v.get("close"):
            x["en"] = {**(x.get("en") or {}), **{k: v[k] for k in ("holdersChg", "hdate", "margin20", "marginPct", "lift6m", "top10free", "focus") if v.get(k) is not None}}
            x["close"] = v["close"]; x["pos"] = round((v["close"] - x["boxL"]) / (x["boxH"] - x["boxL"]), 2)
    L2["px_asof"] = asof
    st = rj(ST_P) if ST_P.exists() else {}
    if m.get("cn10y"): st["cn10y"] = m["cn10y"]
    if m.get("bond_rows"):  # 中美10年期写回 bond.json（首页跟踪单读这里），按日期合并、不覆盖已有行
        bp = ROOT / "data/raw/bond.json"; b = rj(bp); have = {r["SOLAR_DATE"] for r in b}
        b = sorted([r for r in m["bond_rows"] if r["SOLAR_DATE"] not in have] + b, key=lambda r: r["SOLAR_DATE"], reverse=True); wj(bp, b)
    if csi: st["csi_all"] = csi[-1]; st["csi_all_rows"] = csi[-260:]
    st["asof"] = asof; st["via"] = m.get("via")
    wj(EN_P, en); wj(VX_P, vx); wj(SP_P, sp); wj(ST_P, st)

def cat(p):
    """把每只股票的状态归成几类，便于周与周比较。"""
    if not p: return "无价格"
    w = p["where"]; c = p["close"]
    if "未确认" in w: return "未确认"   # 等开关板块还没有买点，计划中的止损价不适用
    if p.get("stop") and c <= p["stop"]: return "跌破止损"
    if "卖出区" in w or c >= p["sell"]: return "到达卖出价"
    if "未确认" in w: return "未确认"
    if "在买入区" in w: return "在买入区"
    if "低于" in w: return "低于买入区"
    return "高于买入区"

def step_snapshot(asof):
    import importlib, logic1_rules, stockpick
    importlib.reload(logic1_rules); importlib.reload(stockpick)
    S = rj(ROOT / "data/sector_selection.json"); sec = {s["id"]: s for s in S["sectors"]}
    L1 = stockpick.logic1_data(ROOT, S); L2 = rj(SP_P)["logic2"]; sw = stockpick.switch_state(ROOT)
    out = {"asof": asof, "rules": RULES_VERSION, "cn10y": logic1_rules.cn10y(ROOT), "switch": sw, "logic1": {}, "logic2": {}}
    for sid, r in L1.items():
        for i, x in enumerate(r["picks"]):
            p = x.get("pl"); v, _ = stockpick.view_of(sec[sid]["rating"], sid, x, i)
            out["logic1"][x["code"]] = {"name": x["name"], "sector": sec[sid]["title"], "rating": sec[sid]["rating"], "type": r["type"], "view": v, "cat": cat(p), **({k: p.get(k) for k in ("close", "buy", "sell", "sell2", "stop", "rr", "where")} if p else {})}
    import logic2_box; F2 = stockpick.l2_fund(ROOT)
    for x in L2["top"]:
        b = logic1_rules.box_levels(x); J = logic2_box.judge(x, F2.get(x["code"]), x.get("en"), sw["on"])
        out["logic2"][x["code"]] = {"name": x["name"], "view": J["view"], "layers": [J["fund"], J["pos"], J["chip"], J["box"]], "cat": "跌破止损" if b["close"] <= b["stop"] else ("到达卖出价" if b["close"] >= b["sell"] else ("在买入区" if b["where"] == "在买入区" else b["where"])), **b}
    wj(SNAP / (asof + ".json"), out)
    return out

def step_changes(cur):
    prev = sorted(p for p in SNAP.glob("*.json") if p.stem < cur["asof"])
    items = []; P = rj(prev[-1]) if prev else None
    same_rules = bool(P) and P.get("rules") == cur.get("rules")
    def cmp(part, label):
        for c, x in cur[part].items():
            o = (P or {}).get(part, {}).get(c)
            if o is None: items.append({"logic": label, "code": c, "name": x["name"], "from": "新增候选", "to": x["cat"], "close": x.get("close")}); continue
            if o["cat"] != x["cat"]: items.append({"logic": label, "code": c, "name": x["name"], "from": o["cat"], "to": x["cat"], "close": x.get("close")})
            elif same_rules and o.get("view") and x.get("view") and o["view"] != x["view"]: items.append({"logic": label, "code": c, "name": x["name"], "from": o["view"], "to": x["view"], "close": x.get("close")})
        for c, o in ((P or {}).get(part) or {}).items():
            if c not in cur[part]: items.append({"logic": label, "code": c, "name": o["name"], "from": o["cat"], "to": "移出候选", "close": None})
    if P: cmp("logic1", "逻辑一"); cmp("logic2", "逻辑二")
    alerts = [] if (not P or same_rules) else ["规则已更新（%s）：本周起结论按判断链重排，结论变化不计入本周变化，详见筛选规则页" % cur.get("rules")]
    ty = cur["cn10y"]
    if ty["value"] > 1.85: alerts.append("10年国债%.2f%%高于1.85%%：银行按规则退出条件需要复核" % ty["value"])
    if P and abs(ty["value"] - P["cn10y"]["value"]) >= 0.10: alerts.append("10年国债较上周变化%.2f个百分点：银行买卖价已按新收益率重算" % (ty["value"] - P["cn10y"]["value"]))
    if P and P["switch"]["on"] != cur["switch"]["on"]: alerts.append("中证全指%s4,700：逻辑二%s" % ("回到" if cur["switch"]["on"] else "跌破", "恢复开新仓" if cur["switch"]["on"] else "暂停开新仓"))
    order = {"跌破止损": 0, "到达卖出价": 1, "在买入区": 2}
    items.sort(key=lambda x: (order.get(x["to"], 9), x["logic"]))
    summ = {}
    for part in ("logic1", "logic2"):
        for x in cur[part].values(): summ[x["cat"]] = summ.get(x["cat"], 0) + 1
    ch = {"asof": cur["asof"], "prev": P["asof"] if P else None, "items": items, "alerts": alerts, "summary": summ}
    wj(CH_P, ch); return ch

def run(script, *a):
    r = subprocess.run([sys.executable, "-I", str(ROOT / "pipeline" / script), str(ROOT), *a], capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    if r.returncode: sys.exit("失败：%s\n%s" % (script, (r.stdout + r.stderr)[-2000:]))
    return tail[0]

if __name__ == "__main__":
    if "--snapshot-only" in ARGS:  # 不取数，只按现有数据建快照（第一次建立基准时用）
        asof = rj(EN_P)["_meta"]["as_of"]
    else:
        m, csi, miss, asof = step_fetch()
        step_write(m, csi, miss, asof)
    cur = step_snapshot(asof); ch = step_changes(cur)
    print("截止日：%s（上次：%s）  10年国债：%.2f%%  中证全指：%s" % (asof, ch["prev"], cur["cn10y"]["value"], cur["switch"]["close"]))
    print("状态分布：" + "，".join("%s %d" % kv for kv in ch["summary"].items()))
    for a in ch["alerts"]: print("提醒：" + a)
    for x in ch["items"]: print("变化：[%s] %s %s：%s → %s（现价 %s）" % (x["logic"], x["name"], x["code"], x["from"], x["to"], x["close"]))
    if "--no-build" not in ARGS:
        run("build.py")
        for t in ("test_stock_pick.py", "test_chain.py", "test_weekly.py", "test_sector_selection.py", "test_macro_regime.py", "test_hk.py", "test_newslog.py", "test_hk_pick.py"):
            print(t, run(t))
    print("完成。发布：python3 -I pipeline/publish_api.py <根目录> \"每周价格更新 %s\"" % asof)
