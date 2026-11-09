"""候选个股页面：四层信号汇总、因子影响地图、个股 A–H、股价层、关注条件、公告、操作记录。
由 build.py 调用：stockpage.build(ctx)，ctx 是 build.py 的 globals()。
"""
import json, os, datetime, html

E = html.escape
POS_KW = ["回购", "增持"]
NEG_KW = ["减持", "解禁", "处罚", "立案", "问询函", "监管工作函", "质押", "警示"]
KEY_KW = POS_KW + NEG_KW + ["业绩预告", "季度报告", "年度报告", "半年度报告", "重大合同", "中标", "激励"]


def st(x):
    return "up" if x > 0 else ("down" if x < 0 else "flat")


def rnd(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def clip(x):
    return max(-2, min(2, x))


def pct_rank(vals, x):
    return 100.0 * sum(1 for v in vals if v < x) / len(vals)


def quantile(vals, q):
    v = sorted(vals)
    return v[min(len(v) - 1, int(len(v) * q))]


def fmt2(x, n=3):
    return "—" if x is None else f"{x:.{n}f}"


def yi(x):
    return f"{x / 1e8:,.1f} 亿"


# ---------------- 计算 ----------------
def analyze_stock(cfg, raw, ctx):
    R, D = ctx["R"], ctx["D"]
    k = raw["kline"]["rows"]
    c = [r["close"] for r in k]
    dts = [r["date"] for r in k]
    amt = [r["amount"] for r in k]
    ma = lambda n, off=0: sum(c[len(c) - n - off:len(c) - off]) / n
    t = {"close": c[-1], "date": dts[-1], "d1": (c[-1] / c[-2] - 1) * 100, "d5": (c[-1] / c[-6] - 1) * 100,
         "d20": (c[-1] / c[-21] - 1) * 100, "d60": (c[-1] / c[-61] - 1) * 100}
    y0 = [r["close"] for r in k if r["date"] < dts[-1][:4] + "-01-01"]
    t["ytd"] = (c[-1] / y0[-1] - 1) * 100 if y0 else None
    for n in (20, 60, 120, 250):
        t[f"ma{n}"] = ma(n)
        t[f"ma{n}_dir"] = "向上" if ma(n) > ma(n, 5) else "向下"
    t["hi250"], t["lo250"] = max(c[-250:]), min(c[-250:])
    t["hi_date"] = dts[len(c) - 250 + c[-250:].index(t["hi250"])]
    t["dd"] = (c[-1] / t["hi250"] - 1) * 100
    t["from_lo"] = (c[-1] / t["lo250"] - 1) * 100
    t["amt_ratio"] = amt[-1] / (sum(amt[-21:-1]) / 20)
    t["lo20"], t["hi20"] = min(c[-20:]), max(c[-20:])
    # 近 5 日是否穿越 120 / 250 日线
    cross = []
    for n in (120, 250):
        above_now = c[-1] > ma(n)
        above_5 = c[-6] > ma(n, 5)
        if above_now != above_5:
            cross.append(f"{'站上' if above_now else '跌破'} {n} 日线")
    t["cross"] = cross

    # 估值
    val = sorted(raw["val"], key=lambda r: r["TRADE_DATE"])
    v3 = val[-730:]
    pe_now = val[-1]["PE_TTM"]
    pos = [r["PE_TTM"] for r in v3 if r["PE_TTM"] and r["PE_TTM"] > 0]
    v = {"pe": pe_now, "pb": val[-1]["PB_MRQ"], "mcap": val[-1]["TOTAL_MARKET_CAP"], "date": val[-1]["TRADE_DATE"][:10],
         "series": [(r["TRADE_DATE"][:10], r["PE_TTM"]) for r in v3 if r["PE_TTM"] and r["PE_TTM"] > 0]}
    if pe_now and pe_now > 0 and len(pos) > 100:
        v["pct"] = pct_rank(pos, pe_now)
        eps_ttm = val[-1]["CLOSE_PRICE"] / pe_now
        v["eps_ttm"] = eps_ttm
        v["q"] = {q: quantile(pos, q) for q in (0.2, 0.5, 0.8)}
        v["channel"] = {q: eps_ttm * pe for q, pe in v["q"].items()}
        v["pe_3y_ago"] = pos[0]
    else:
        v["pct"] = None

    # 财务：累计值拆成单季
    fin = sorted(raw["fin"], key=lambda r: r["REPORTDATE"])
    cum = {r["REPORTDATE"][:10]: r for r in fin}
    qs = []
    for r in fin:
        d = r["REPORTDATE"][:10]
        y, m = d[:4], int(d[5:7])
        prev = cum.get(f"{y}-{m - 3:02d}-{30 if m - 3 in (6, 9) else 31}") if m > 3 else None
        if m > 3 and prev is None:
            continue
        npq = r["PARENT_NETPROFIT"] - (prev["PARENT_NETPROFIT"] if prev else 0)
        revq = r["TOTAL_OPERATE_INCOME"] - (prev["TOTAL_OPERATE_INCOME"] if prev else 0)
        qs.append({"label": f"{y[2:]}Q{m // 3}", "end": d, "np": npq, "rev": revq})
    for i, q in enumerate(qs):
        q["qoq"] = (q["np"] / qs[i - 1]["np"] - 1) * 100 if i > 0 and qs[i - 1]["np"] > 0 else None
        same = [x for x in qs if x["label"] == f"{int(q['label'][:2]) - 1}{q['label'][2:]}"]
        q["yoy"] = (q["np"] / same[0]["np"] - 1) * 100 if same and same[0]["np"] > 0 else None
        q["rev_yoy"] = (q["rev"] / same[0]["rev"] - 1) * 100 if same and same[0]["rev"] > 0 else None
    last = fin[-1]
    f = {"qs": qs, "type": last["DATATYPE"], "notice": last["NOTICE_DATE"][:10], "gm": last["XSMLL"], "roe": last["WEIGHTAVG_ROE"],
         "eps": last["BASIC_EPS"], "cfps": last["MGJYXJJE"],
         "cash_ratio": (last["MGJYXJJE"] / last["BASIC_EPS"]) if last["BASIC_EPS"] and last["BASIC_EPS"] > 0 and last["MGJYXJJE"] is not None else None}
    prev_gm = [r for r in fin if r["REPORTDATE"][5:] == last["REPORTDATE"][5:] and r["REPORTDATE"][:4] == str(int(last["REPORTDATE"][:4]) - 1)]
    f["gm_prev"] = prev_gm[0]["XSMLL"] if prev_gm else None

    # 一致预期
    cs = raw["consensus"][0] if raw["consensus"] else None
    e = None
    if cs:
        ys = [(cs.get(f"YEAR{i}"), cs.get(f"YEAR_MARK{i}"), cs.get(f"EPS{i}")) for i in range(1, 5)]
        est = [(y, eps) for y, mk, eps in ys if mk == "E" and eps]
        act = [(y, eps) for y, mk, eps in ys if mk == "A" and eps]
        if len(est) >= 2:
            (y1, e1), (y2, e2) = est[0], est[1]
            e = {"y1": y1, "e1": e1, "y2": y2, "e2": e2, "g": (e2 / e1 - 1) * 100 if e1 > 0 else None,
                 "fpe1": c[-1] / e1 if e1 > 0 else None, "fpe2": c[-1] / e2 if e2 > 0 else None,
                 "orgs": cs.get("RATING_ORG_NUM"), "buy": (cs.get("RATING_BUY_NUM") or 0) + (cs.get("RATING_ADD_NUM") or 0),
                 "act": act[-1] if act else None}

    # 融资
    mg = sorted(raw["margin"], key=lambda r: r["DATE"])
    m = {"date": mg[-1]["DATE"][:10], "rz": mg[-1]["RZYE"], "lev": mg[-1]["RZYEZB"],
         "m10": (mg[-1]["RZYE"] / mg[-11]["RZYE"] - 1) * 100, "p10": (mg[-1]["SPJ"] / mg[-11]["SPJ"] - 1) * 100,
         "series": [(r["DATE"][:10], r["RZYE"], r["SPJ"]) for r in mg]}
    hd = raw["holders"][0] if raw["holders"] else None

    # 公告
    cutoff = (datetime.date.fromisoformat(dts[-1]) - datetime.timedelta(days=30)).isoformat()
    recent = [n for n in raw["notices"] if n["date"] >= cutoff]
    key = [n for n in recent if any(w in n["title"] for w in KEY_KW)]
    pos_n = [n for n in recent if any(w in n["title"] for w in POS_KW)]
    neg_n = [n for n in recent if any(w in n["title"] for w in NEG_KW) and not any(w in n["title"] for w in ["回购"])]

    # 板块
    b = raw["board"]["rows"]
    bc = [r["close"] for r in b]
    hs = [r["close"] for r in D.idx["idx_hs300"]["rows"]]
    bd = {"name": cfg["board"]["name"], "close": bc[-1], "d20": (bc[-1] / bc[-21] - 1) * 100, "d60": (bc[-1] / bc[-61] - 1) * 100,
          "rs20": (bc[-1] / bc[-21] - hs[-1] / hs[-21]) * 100, "rs60": (bc[-1] / bc[-61] - hs[-1] / hs[-61]) * 100,
          "ma60": bc[-1] > sum(bc[-60:]) / 60, "rows": b}

    # ---- 个股 A–G 判定 ----
    nodes = {}
    lq = qs[-1]
    h = []
    ry = lq.get("rev_yoy")
    if ry is not None:
        if ry >= 30: h.append((f"{lq['label']} 单季营收同比 {ry:+.0f}%，订单旺盛", 1))
        elif ry >= 10: h.append((f"{lq['label']} 单季营收同比 {ry:+.0f}%", 0.5))
        elif ry < 0: h.append((f"{lq['label']} 单季营收同比 {ry:+.0f}%，需求在收缩", -1))
        else: h.append((f"{lq['label']} 单季营收同比 {ry:+.0f}%，增长平缓", 0))
    nodes["A"] = h
    h = []
    if pos_n: h.append(("近 30 天有" + "、".join(sorted({w for n in pos_n for w in POS_KW if w in n["title"]})) + "公告", 0.5))
    if neg_n: h.append(("近 30 天有" + "、".join(sorted({w for n in neg_n for w in NEG_KW if w in n["title"]})) + "相关公告", -1))
    if not h: h.append(("近 30 天没有回购、增减持、解禁等重要事项公告", 0))
    nodes["B"] = h
    h = []
    if lq["yoy"] is not None:
        if lq["yoy"] >= 20: h.append((f"{lq['label']} 单季净利润同比 {lq['yoy']:+.0f}%", 1))
        elif lq["yoy"] >= 0: h.append((f"{lq['label']} 单季净利润同比 {lq['yoy']:+.0f}%", 0.5))
        else: h.append((f"{lq['label']} 单季净利润同比 {lq['yoy']:+.0f}%，利润在下滑", -1))
    if lq["qoq"] is not None:
        if lq["qoq"] >= 5: h.append((f"环比上季度 {lq['qoq']:+.0f}%，二阶导向上", 0.5))
        elif lq["qoq"] <= -5: h.append((f"环比上季度 {lq['qoq']:+.0f}%，二阶导向下", -0.5))
        else: h.append((f"环比上季度 {lq['qoq']:+.0f}%，基本持平", 0))
    if lq["np"] <= 0: h.append((f"{lq['label']} 单季亏损", -1))
    nodes["C"] = h
    h = []
    cr = f["cash_ratio"]
    if f["eps"] is not None and f["eps"] <= 0:
        if f["cfps"] is not None and f["cfps"] < 0:
            h.append((f"本年仍亏损（每股收益 {f['eps']:.3f}），经营现金流也为负（每股 {f['cfps']:.3f}），在持续失血", -1))
        else:
            h.append((f"本年仍亏损（每股收益 {f['eps']:.3f}），但经营现金流为正", 0))
    if cr is not None:
        if cr >= 0.9: h.append((f"每股经营现金流是每股收益的 {cr:.2f} 倍，利润有现金支撑", 0.5))
        elif cr < 0.5: h.append((f"每股经营现金流只有每股收益的 {cr:.2f} 倍，利润含金量偏低", -1))
        else: h.append((f"每股经营现金流是每股收益的 {cr:.2f} 倍，尚可", 0))
    if f["gm_prev"] is not None and f["gm"] is not None:
        dg = f["gm"] - f["gm_prev"]
        if dg >= 2: h.append((f"毛利率 {f['gm']:.1f}%，比去年同期高 {dg:.1f} 个点", 0.5))
        elif dg <= -2: h.append((f"毛利率 {f['gm']:.1f}%，比去年同期低 {abs(dg):.1f} 个点", -0.5))
    nodes["D"] = h
    h = []
    if e and e["g"] is not None:
        if e["g"] >= 30: h.append((f"机构预期 {e['y2']} 年每股收益比 {e['y1']} 年增长 {e['g']:.0f}%", 1))
        elif e["g"] >= 10: h.append((f"机构预期 {e['y2']} 年每股收益增长 {e['g']:.0f}%", 0.5))
        elif e["g"] < 0: h.append((f"机构预期 {e['y2']} 年每股收益下降 {abs(e['g']):.0f}%", -1))
        else: h.append((f"机构预期 {e['y2']} 年每股收益增长 {e['g']:.0f}%，偏慢", 0))
    nodes["E"] = h
    h = []
    if v["pct"] is not None:
        if v["pct"] < 20: h.append((f"PE-TTM {pe_now:.1f} 倍，近 3 年 {v['pct']:.0f}% 分位，偏低", 1))
        elif v["pct"] > 80: h.append((f"PE-TTM {pe_now:.1f} 倍，近 3 年 {v['pct']:.0f}% 分位，偏高", -1))
        else: h.append((f"PE-TTM {pe_now:.1f} 倍，近 3 年 {v['pct']:.0f}% 分位，中间位置", 0))
    nodes["F"] = h
    h = []
    if m["m10"] >= 5: h.append((f"融资余额 10 日增加 {m['m10']:.1f}%（股价同期 {m['p10']:+.1f}%）", 0.5))
    elif m["m10"] <= -5: h.append((f"融资余额 10 日减少 {abs(m['m10']):.1f}%（股价同期 {m['p10']:+.1f}%），杠杆资金在撤", -0.5))
    else: h.append((f"融资余额 10 日变化 {m['m10']:+.1f}%，基本稳定", 0))
    if m["lev"] >= 4: h.append((f"融资余额占流通市值 {m['lev']:.2f}%，杠杆偏重", -0.5))
    nodes["G"] = h
    scores = {k2: clip(rnd(sum(p for _, p in hh))) if hh else None for k2, hh in nodes.items()}

    # ---- 四层汇总 ----
    stock_sum = sum(s for s in scores.values() if s is not None)
    layers = [
        {"name": "大盘", "state": st(R["total"]), "text": f"六项合计 {R['total']:+d}。" + ctx["summary"]().split("。", 1)[1], "link": "../index.html"},
        {"name": "板块", "state": "up" if bd["rs20"] >= 5 else ("down" if bd["rs20"] <= -5 else "flat"),
         "text": f"{bd['name']}近 20 日 {bd['d20']:+.1f}%，相对沪深 300 {bd['rs20']:+.1f} 个点；近 60 日相对 {bd['rs60']:+.1f} 个点；{'在' if bd['ma60'] else '跌破'} 60 日线{'上方' if bd['ma60'] else ''}。", "link": None},
        {"name": "个股", "state": st(stock_sum), "text": f"A–G 合计 {stock_sum:+d}。" + "；".join(
            f"{k2} {s:+d}" for k2, s in scores.items() if s), "link": "#nodes"},
    ]
    vtxt = (f"PE {pe_now:.1f} 倍，近 3 年 {v['pct']:.0f}% 分位" if v["pct"] is not None else f"PE {pe_now:.1f} 倍（无法计算分位）")
    ttxt = f"股价在 120 日线{'上方' if c[-1] > t['ma120'] else '下方'}、250 日线{'上方' if c[-1] > t['ma250'] else '下方'}，距一年高点 {t['dd']:.0f}%"
    pstate = "flat" if v["pct"] is None else ("up" if v["pct"] < 20 else ("down" if v["pct"] > 80 else "flat"))
    layers.append({"name": "股价", "state": pstate, "text": vtxt + "；" + ttxt + "。", "link": "#price"})

    # ---- 关注条件 ----
    conds = []
    if v["pct"] is not None:
        conds.append(("PE-TTM 跌破近 3 年 20% 分位，或升破 80% 分位", v["pct"] < 20 or v["pct"] > 80, f"{v['pct']:.0f}% 分位"))
    conds.append(("近 5 日股价站上或跌破 120 日、250 日线", bool(cross), "；".join(cross) if cross else
                  f"在 120 日线{'上方' if c[-1] > t['ma120'] else '下方'}，250 日线{'上方' if c[-1] > t['ma250'] else '下方'}"))
    conds.append(("距近 250 日高点回撤超过 30%", t["dd"] <= -30, f"{t['dd']:.1f}%（高点 {t['hi250']:.2f}，{t['hi_date']}）"))
    diverge = (m["m10"] > 0) != (m["p10"] > 0)
    conds.append(("融资余额和股价近 10 个交易日反向", diverge, f"融资 {m['m10']:+.1f}%，股价 {m['p10']:+.1f}%（截至 {m['date'][5:]}）"))
    conds.append(("成交额超过 20 日均值的 2 倍", t["amt_ratio"] >= 2, f"{t['amt_ratio']:.2f} 倍"))
    if len(qs) >= 2 and qs[-1]["qoq"] is not None and qs[-2]["qoq"] is not None:
        flip = (qs[-1]["qoq"] > 0) != (qs[-2]["qoq"] > 0)
        conds.append(("单季利润环比由正转负，或由负转正", flip, f"{qs[-2]['label']} {qs[-2]['qoq']:+.0f}% → {qs[-1]['label']} {qs[-1]['qoq']:+.0f}%"))
    conds.append(("机构一致预期 1 个月内上调或下调超过 5%", False, "从今天开始记录，满 1 个月后可以判断"))
    k5 = [n for n in raw["notices"] if n["date"] >= dts[-6] and any(w in n["title"] for w in POS_KW + NEG_KW)]
    conds.append(("近 5 个交易日有回购、增减持、解禁等公告", bool(k5), "；".join(n["title"].split(":", 1)[-1] for n in k5[:2]) or "无"))
    conds.append(("持仓触发了操作记录里写下的计划条件", False, "还没有这只股票的操作记录"))

    return {"cfg": cfg, "t": t, "v": v, "f": f, "e": e, "m": m, "hd": hd, "bd": bd, "nodes": nodes, "scores": scores,
            "layers": layers, "conds": conds, "key_notices": key, "notices": raw["notices"], "dates": dts, "closes": c}


# ---------------- 因子地图：当前状态 ----------------
def factor_now(name, ctx, a):
    R, D, manual = ctx["R"], ctx["D"], ctx["manual"]
    sr = {r["key"]: r for r in R["score_rows"]}
    us = D.us10[-1][1]
    sg = lambda x: f"{x:+d}" if x else "0"
    if "重组" in name or "资产处置" in name:
        hits = [n for n in a["notices"] if any(w in n["title"] for w in ["收购", "转让", "出售", "重组", "股权"])]
        if hits:
            return f"近期相关公告 {len(hits)} 条，最新：{hits[0]['date'][5:]} {hits[0]['title'].split(':', 1)[-1][:30]}", "flat"
        return "近期没有相关公告", "flat"
    if "利率" in name:
        return f"美国 10 年国债 {us:.2f}%；大盘「利率与流动性」{sg(sr['liq']['score'])}", "down" if us >= 4.5 else "flat"
    if "汇率" in name:
        x = D.cnh[-1][1]; x20 = D.cnh[-21][1]
        return f"离岸人民币 {x:.4f}，近 20 日{'升值' if x < x20 else '贬值'} {abs(x / x20 - 1) * 100:.1f}%（升值对出口型公司不利）", "down" if x < x20 else "up"
    if "两融" in name or "情绪" in name:
        return f"本股融资余额 10 日 {a['m']['m10']:+.1f}%；大盘「资金」{sg(sr['funds']['score'])}", st(sr["funds"]["score"])
    if any(w in name for w in ["出口限制", "关税", "管制", "对华"]):
        return f"大盘「外部环境」{manual['external']['score']:+d}（人工判定）", st(manual["external"]["score"])
    if "国内经济" in name or "消费" in name:
        return f"大盘「国内经济」{sg(sr['econ']['score'])}：PMI {D.pmi[-1]['v']}，社零同比 {D.retail[-1]['v']}%", st(sr["econ"]["score"])
    if "政策" in name or "医保" in name:
        return f"大盘「政策」{manual['policy']['score']:+d}（人工判定）；行业政策待整理", "flat"
    if "资本开支" in name or "订单" in name:
        q = a["f"]["qs"][-1]
        return f"用公司收入代替观察：{q['label']} 单季营收同比 {q['rev_yoy']:+.0f}%" if q.get("rev_yoy") is not None else "待整理", st(q.get("rev_yoy") or 0)
    return "待整理（需要行业数据或人工跟踪）", "na"


# ---------------- 渲染 ----------------
NODE_NAMES = {"A": "客户与订单", "B": "公司事件：减持 / 回购 / 解禁", "C": "营收 × 毛利率 → 净利润", "D": "利润质量：现金流与毛利率",
              "E": "盈利预测：今年 → 明年", "F": "个股估值（PE）", "G": "筹码：融资 / 股东", "H": "股价"}


def render(a, ctx):
    spark, line_chart, verdict, rules = ctx["spark"], ctx["line_chart"], ctx["verdict"], ctx["rules"]
    cfg, t, v, f, e, m, bd = a["cfg"], a["t"], a["v"], a["f"], a["e"], a["m"], a["bd"]
    sc = a["scores"]

    def node_state(k):
        if k == "H": return "price"
        s = sc.get(k)
        return "na" if s is None else st(s)

    # 四层汇总
    lrows = ""
    for L in a["layers"]:
        lab = {"up": "利好", "down": "利空", "flat": "中性"}[L["state"]]
        if L["name"] == "股价":
            lab = {"up": "估值偏低", "down": "估值偏高", "flat": "估值居中"}[L["state"]]
        link = f' <a href="{L["link"]}">展开</a>' if L["link"] else ' <span class="soon2">板块页第二期</span>'
        lrows += f'<tr><th scope="row">{L["name"]}</th><td><span class="tag {L["state"]}">{lab}</span></td><td>{E(L["text"])}{link}</td></tr>'
    layers = f'<div class="tblwrap"><table class="mt lay"><tbody>{lrows}</tbody></table></div>'

    # 因子地图
    frows = ""
    for name, level, why in cfg["factor_map"]:
        now, s2 = factor_now(name, ctx, a)
        lv = {"高": "hi", "中": "mid", "低": "lo"}[level]
        frows += (f'<tr><th scope="row">{E(name)}</th><td><span class="lv {lv}">{level}</span></td><td class="why">{E(why)}</td>'
                  f'<td class="now {s2}">{E(now)}</td></tr>')
    fmap = ('<div class="tblwrap"><table class="mt fm"><thead><tr><th>因素</th><th>影响</th><th>为什么</th><th>现在的状态</th></tr></thead>'
            f'<tbody>{frows}</tbody></table></div>')

    # 个股 A–H 图
    P = {"A": (20, 20), "B": (370, 20), "C": (35, 120), "D": (370, 120), "E": (50, 220), "F": (370, 220), "G": (700, 220), "H": (640, 330)}
    NW, NH = 290, 62

    def sub(k):
        if k == "H": return f"{t['close']:.2f}，今日 {t['d1']:+.2f}%，距一年高点 {t['dd']:.0f}%"
        s = sc.get(k)
        if s is None: return "暂缺"
        return {"up": "利好", "down": "利空", "flat": "中性"}[st(s)] + (f" {s:+d}" if s else " 0")
    o = ['<svg class="fw" viewBox="0 0 1000 410" role="img" aria-label="个股层传导图">',
         '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9AA2AF"/></marker>'
         '<marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#D88B1F"/></marker></defs>']
    for ed in [f"M{P['A'][0] + 90},{P['A'][1] + NH} V{P['C'][1]}",
               f"M{P['B'][0] + 90},{P['B'][1] + NH} V{P['B'][1] + NH + 18} H{P['C'][0] + 200} V{P['C'][1]}",
               f"M{P['B'][0] + 160},{P['B'][1] + NH} V{P['D'][1]}",
               f"M{P['C'][0] + 90},{P['C'][1] + NH} V{P['E'][1]}",
               f"M{P['D'][0] + 110},{P['D'][1] + NH} V{P['F'][1]}",
               f"M{P['E'][0] + 90},{P['E'][1] + NH} V{P['H'][1] - 14} H{P['H'][0] + 30} V{P['H'][1]}",
               f"M{P['F'][0] + 150},{P['F'][1] + NH} V{P['H'][1] - 26} H{P['H'][0] + 70} V{P['H'][1]}",
               f"M{P['G'][0] + 70},{P['G'][1] + NH} V{P['H'][1]}"]:
        o.append(f'<path d="{ed}" class="edge" marker-end="url(#ar)"/>')
    o.append(f'<path d="M{P["H"][0] + 160},{P["H"][1]} V{P["H"][1] - 24} H{P["G"][0] + 170} V{P["G"][1] + NH}" class="edge fb" marker-end="url(#ar2)"/>')
    for k, (x, y) in P.items():
        s2 = node_state(k)
        w = NW if k != "H" else 330
        href = "#price" if k == "H" else f"#n-{k}"
        o.append(f'<a href="{href}" class="node {s2}"><rect x="{x}" y="{y}" width="{w}" height="{NH}" rx="10"/>'
                 f'<circle cx="{x + 22}" cy="{y + 31}" r="12" class="lc"/><text x="{x + 22}" y="{y + 36}" class="lt" text-anchor="middle">{k}</text>'
                 f'<text x="{x + 44}" y="{y + 27}" class="n">{E(NODE_NAMES[k])}</text><text x="{x + 44}" y="{y + 48}" class="s">{E(sub(k))}</text></a>')
    o.append("</svg>")
    chips = "".join(f'<a href="{"#price" if k == "H" else "#n-" + k}" class="chip {node_state(k)}"><b>{k}</b>{E(NODE_NAMES[k])}<span>{E(sub(k))}</span></a>' for k in "ABCDEFGH")
    diagram = f'<div class="fwbox">{"".join(o)}</div><div class="chips">{chips}</div>'

    # 节点展开
    qs = f["qs"][-8:]
    pf = lambda x: "" if x is None else f"{x:+.0f}%"
    qrows = "".join(
        f'<tr><th scope="row">{q["label"]}</th><td>{yi(q["rev"])}</td><td class="{st(q["rev_yoy"] or 0)}">{pf(q["rev_yoy"])}</td>'
        f'<td>{yi(q["np"])}</td><td class="{st(q["yoy"] or 0)}">{pf(q["yoy"])}</td>'
        f'<td class="{st(q["qoq"] or 0)}">{pf(q["qoq"])}</td></tr>' for q in qs)
    qtable = ('<div class="tblwrap"><table class="mt"><thead><tr><th>季度</th><th>单季营收</th><th>营收同比</th><th>单季净利润</th><th>利润同比</th><th>利润环比</th></tr></thead>'
              f'<tbody>{qrows}</tbody></table></div>')
    np_spark = spark([q["np"] for q in qs], 160, 36)

    def sec(k, title, q, body):
        hits = a["nodes"].get(k) or []
        s = sc.get(k)
        vd = verdict(node_state(k), s, hits) if hits else '<div class="verdict na"><div class="vh"><span class="tag na">暂缺</span></div></div>'
        return (f'<section class="nd" id="n-{k}"><div class="ndh"><span class="lc2 {node_state(k)}">{k}</span><div><h3>{E(title)}</h3>'
                f'<p class="q">{E(q)}</p></div></div>{vd}{body}</section>')

    ann = "".join(f'<li><span class="evd">{n["date"]}</span><a href="https://data.eastmoney.com/notices/detail/{cfg["code"]}/{n["art"]}.html" rel="noopener">{E(n["title"].split(":", 1)[-1])}</a></li>'
                  for n in a["notices"][:10])
    estr = ""
    if e:
        estr = ('<div class="tblwrap"><table class="mt"><thead><tr><th>年份</th><th>每股收益</th><th>对应 PE（按现价）</th></tr></thead><tbody>'
                + (f'<tr><th scope="row">{e["act"][0]} 实际</th><td>{e["act"][1]:.2f}</td><td>{t["close"] / e["act"][1]:.1f} 倍</td></tr>' if e["act"] and e["act"][1] > 0 else "")
                + f'<tr><th scope="row">{e["y1"]} 预测</th><td>{e["e1"]:.2f}</td><td>{e["fpe1"]:.1f} 倍</td></tr>'
                + f'<tr><th scope="row">{e["y2"]} 预测</th><td>{e["e2"]:.2f}</td><td>{e["fpe2"]:.1f} 倍</td></tr></tbody></table></div>'
                + f'<p class="note">{e["orgs"]} 家机构给出预测，其中 {e["buy"]} 家评级为买入或增持。预测的上调、下调从今天开始逐日记录。</p>')
    hd = a["hd"]
    hdtxt = (f'<p class="note">股东户数 {hd["HOLDER_NUM"]:,} 户（截至 {hd["END_DATE"][:10]}），比上一期变化 {hd["HOLDER_NUM_RATIO"]:+.1f}%。户数增加通常意味着筹码在分散。</p>' if hd else "")

    nodes_html = (
        sec("A", "客户与订单", "谁在买它的产品，买得多不多？", f'<p class="note">{E(cfg["customer_note"])}</p>'
            + rules("单季营收同比 ≥ 30% 加 1，10–30% 加 0.5，0–10% 为 0，负增长减 1。订单和客户的具体变化需要人工跟踪。"))
        + sec("B", "公司事件", "最近有没有回购、增减持、解禁、监管问询？", f'<h4>最近公告</h4><ul class="ann">{ann}</ul>'
              + rules("近 30 天有回购、增持公告加 0.5；有减持、解禁、处罚、立案、问询函、质押、警示等公告减 1。按标题关键词判断，需要点开原文确认。"))
        + sec("C", "营收 × 毛利率 → 净利润", "公司还在多赚钱吗？增速在加快还是放缓？", qtable
              + f'<p class="note">最新报告：{E(f["type"])}，{f["notice"]} 公布。单季数据由累计值相减得到。近 8 个季度单季净利润走势：{np_spark}</p>'
              + rules("最新单季净利润同比 ≥ 20% 加 1，0–20% 加 0.5，负增长减 1；环比 ≥ +5% 加 0.5，≤ −5% 减 0.5；单季亏损减 1。"))
        + sec("D", "利润质量", "赚的是真金白银吗？毛利率守得住吗？",
              f'<p class="note">本年累计：每股收益 {fmt2(f["eps"])}，每股经营现金流 {fmt2(f["cfps"])}，毛利率 {fmt2(f["gm"], 1)}%，ROE {fmt2(f["roe"], 1)}%。存货和扣非利润暂未接入。</p>'
              + rules("亏损且经营现金流为负减 1；每股经营现金流 ÷ 每股收益 ≥ 0.9 加 0.5，< 0.5 减 1；毛利率比去年同期高 2 个点以上加 0.5，低 2 个点以上减 0.5。"))
        + sec("E", "盈利预测", "机构预期明年比今年多赚多少？", estr
              + rules("明年每股收益比今年预测增长 ≥ 30% 加 1，10–30% 加 0.5，负增长减 1。"))
        + sec("F", "个股估值", "市场现在愿意给它多少倍市盈率？", '<p class="note">估值的细节在下面的「股价层」。</p>'
              + rules("PE-TTM 在近 3 年分位低于 20% 加 1，高于 80% 减 1。亏损或 PE 为负时不判定。"))
        + sec("G", "筹码", "谁在买、谁在卖？杠杆资金在进还是在出？",
              f'<p class="note">融资余额 {yi(m["rz"])}，占流通市值 {m["lev"]:.2f}%（截至 {m["date"]}）。</p>{hdtxt}'
              + rules("融资余额 10 日增加 ≥ 5% 加 0.5，减少 ≥ 5% 减 0.5；融资余额占流通市值 ≥ 4% 减 0.5。"))
    )

    # 股价层
    pe_chart = ""
    ch = ""
    if v["pct"] is not None:
        pe_chart = line_chart([("PE-TTM（倍）", "#27408B", v["series"])],
                              bands=[(v["q"][0.2], "20% 分位"), (v["q"][0.8], "80% 分位")], ylabel="近 3 年 PE-TTM")
        ch = ('<div class="tblwrap"><table class="mt"><thead><tr><th>PE 通道</th><th>PE</th><th>对应股价</th><th>和现价比</th></tr></thead><tbody>'
              + "".join(f'<tr><th scope="row">近 3 年 {int(q * 100)}% 分位</th><td>{v["q"][q]:.1f} 倍</td><td>{v["channel"][q]:.2f}</td>'
                        f'<td class="{st(v["channel"][q] - t["close"])}">{(v["channel"][q] / t["close"] - 1) * 100:+.0f}%</td></tr>' for q in (0.2, 0.5, 0.8))
              + '</tbody></table></div><p class="note">PE 通道 = 当前滚动每股收益 × 历史 PE 分位，回答“按现在的利润，便宜时和贵时分别是什么价”。利润变化后通道会跟着移动。</p>'
              + (f'<p class="mnote">注意：3 年前 PE 约 {v["pe_3y_ago"]:.0f} 倍，现在 {v["pe"]:.0f} 倍。利润大幅增长或下滑时，PE 会被动大幅变化，历史分位的参考意义会下降，要结合 C、E 两环一起看。</p>' if v["pe_3y_ago"] > v["pe"] * 2.5 or v["pe_3y_ago"] < v["pe"] / 2.5 else ""))
    n = 250
    ds = a["dates"][-n:]; cs = a["closes"][-n:]
    allc = a["closes"]
    ma_s = lambda w: [(a["dates"][i], sum(allc[i - w + 1:i + 1]) / w) for i in range(len(allc) - n, len(allc))]
    price_chart = line_chart([("收盘价", "#18202B", list(zip(ds, cs))), ("60 日线", "#D88B1F", ma_s(60)), ("250 日线", "#C8312B", ma_s(250))],
                             ylabel="近一年股价和均线", fmt="{:.0f}")
    ms = m["series"]
    mg_chart = line_chart([("融资余额（期初 = 100）", "#C8312B", [(d, rz / ms[0][1] * 100) for d, rz, _ in ms]),
                           ("股价（期初 = 100）", "#18202B", [(d, p / ms[0][2] * 100) for d, _, p in ms])],
                          ylabel="融资余额和股价", fmt="{:.0f}")
    tech_rows = "".join(f'<tr><th scope="row">{n2} 日线</th><td>{t[f"ma{n2}"]:.2f}</td><td class="{st(t["close"] - t[f"ma{n2}"])}">{"上方" if t["close"] > t[f"ma{n2}"] else "下方"} {(t["close"] / t[f"ma{n2}"] - 1) * 100:+.1f}%</td><td>{t[f"ma{n2}_dir"]}</td></tr>'
                        for n2 in (20, 60, 120, 250))
    tech = ('<div class="tblwrap"><table class="mt"><thead><tr><th>均线</th><th>数值</th><th>股价位置</th><th>均线方向</th></tr></thead><tbody>' + tech_rows + '</tbody></table></div>'
            f'<p class="note">近一年最高 {t["hi250"]:.2f}（{t["hi_date"]}），现价距高点 {t["dd"]:.1f}%；近一年最低 {t["lo250"]:.2f}，现价距低点 {t["from_lo"]:+.1f}%。'
            f'近 20 日区间 {t["lo20"]:.2f}–{t["hi20"]:.2f}，可作为短期支撑和压力参考。今日成交额是 20 日均值的 {t["amt_ratio"]:.2f} 倍。</p>')
    price_sec = (f'<section class="block" id="price"><h2>股价层：现在这个价格处在什么位置</h2><p class="sub">只呈现位置，不下结论。估值回答“贵不贵”，技术面回答“趋势在哪”，筹码回答“谁在推”。</p>'
                 f'<div class="nd"><h3 class="h3s">估值位置</h3><p class="note">PE-TTM {v["pe"]:.1f} 倍{"，近 3 年 " + format(v["pct"], ".0f") + "% 分位" if v["pct"] is not None else ""}；PB {v["pb"]:.2f} 倍；总市值 {yi(v["mcap"])}'
                 + (f'；按 {e["y2"]} 年预测利润算的前瞻 PE {e["fpe2"]:.1f} 倍' if e and e["fpe2"] else "") + f'（截至 {v["date"]}）。</p>{ch}{pe_chart}</div>'
                 f'<div class="nd"><h3 class="h3s">技术位置</h3>{tech}{price_chart}</div>'
                 f'<div class="nd"><h3 class="h3s">筹码：融资余额和股价是否同向</h3><p class="note">同向下跌是去杠杆；股价跌而融资增加是有人借钱抄底；股价涨而融资减少说明上涨不靠杠杆。</p>{mg_chart}</div></section>')

    conds = "".join(f'<li class="{"hit" if h else "ok"}"><span class="cs">{"触发中" if h else "未触发"}</span><b>{E(nm)}</b><span class="cn">{E(now)}</span></li>' for nm, h, now in a["conds"])

    trades = [x for x in ctx["trades"] if x.get("code") == cfg["code"]]
    tr_html = ('<p class="note">还没有这只股票的操作记录。买卖时在对话里告诉 Claude 即可。</p>' if not trades else
               "<ul class='ev'>" + "".join(f"<li><b>{E(x['date'])} {E(x['side'])} {E(str(x['price']))}</b><p>{E(x.get('reason', ''))}</p></li>" for x in trades) + "</ul>")

    pr = cfg["prior"]
    body = f"""
<div class="crumb"><a href="index.html">个股</a> ／ 候选 ／ {E(cfg['name'])}</div>
<div class="hero shero"><div><h1>{E(cfg['name'])}<small>{cfg['code']}</small></h1>
<div class="tags2"><span class="drv">{E(cfg['driver'])}</span><span>{E(cfg['industry'])}</span><span class="cand">候选，未正式入池</span></div></div>
<div class="px"><b>{t['close']:.2f}</b><span class="{st(t['d1'])}">{t['d1']:+.2f}%</span><small>{t['date']} 收盘</small></div></div>

<section class="block" id="layers"><h2>四层信号</h2><p class="sub">从大盘到股价，每一层现在是利好、利空还是中性。不加总，也不给买卖结论。</p>{layers}</section>

<section class="block"><h2>{E(pr.get('label', '之前的结论'))}：{E(pr['title'])}</h2><p class="prior">{E(pr['text'])}<span class="src">来源：{E(pr['source'])}</span></p></section>

<section class="block" id="fmap"><h2>因子影响地图</h2><p class="sub">框架里哪些因素对这只股票影响大。“现在的状态”取自大盘页和本页的实时数据。这张表是初稿，等你确认后按季度更新。</p>{fmap}</section>

<section class="block" id="nodes"><h2>个股层传导图</h2><p class="sub">和大盘页同一套 A–H 骨架，换成了这只股票自己的变量。</p>{diagram}<div class="ndlist">{nodes_html}</div></section>
{price_sec}
<section class="block" id="conds"><h2>关注条件</h2><p class="sub">触发只是提醒你去看一眼，不是买卖信号。</p><ul class="conds">{conds}</ul></section>

<section class="block" id="trades"><h2>我的操作</h2>{tr_html}</section>
"""
    return body


def stock_index(analyses, ctx):
    rows = ""
    for a in analyses:
        cfg, t, v = a["cfg"], a["t"], a["v"]
        tags = "".join(f'<span class="tag {L["state"]}" title="{L["name"]}">{L["name"]}</span>' for L in a["layers"])
        rows += (f'<a class="srow" href="{cfg["slug"]}.html"><span class="nm">{E(cfg["name"])}<small>{cfg["code"]} {E(cfg["industry"])}</small></span>'
                 f'<span class="px2"><b>{t["close"]:.2f}</b><span class="{st(t["d1"])}">{t["d1"]:+.2f}%</span></span>'
                 f'<span class="kv">年内 <b class="{st(t["ytd"] or 0)}">{(t["ytd"] or 0):+.0f}%</b></span>'
                 f'<span class="kv">距高点 <b class="down">{t["dd"]:.0f}%</b></span>'
                 f'<span class="kv">PE 分位 <b>{"—" if v["pct"] is None else format(v["pct"], ".0f") + "%"}</b></span>'
                 f'<span class="lys">{tags}</span></a>')
    return f"""<div class="hero"><h1>个股</h1><p class="sum">正式的 20 只追踪股还没选。下面先放进来的都是候选，用来熟悉个股页的结构。</p>
<p class="stamp">四个色块依次是大盘、板块、个股、股价四层的状态：红色利好，绿色利空，灰色中性。</p></div>
<section class="block"><div class="slist">{rows}</div></section>
<section class="block"><h2>正式股票池怎么定</h2><p class="note">按需求文档的流程：先根据大盘判断定 6–8 个板块，每个板块挑 3–5 只候选，逐只初筛后一起讨论，定下约 20 只。这 5 只也要经过同样的筛选，不会自动入选。</p></section>"""


def build(ctx):
    root = ctx["ROOT"]
    cfgs = json.load(open(os.path.join(root, "data", "stocks.json"), encoding="utf-8"))["stocks"]
    out = os.path.join(ctx["SITE"], "stocks")
    os.makedirs(out, exist_ok=True)
    analyses = []
    for cfg in cfgs:
        p = os.path.join(root, "data", "raw", "stocks", cfg["code"] + ".json")
        if not os.path.exists(p):
            continue
        raw = json.load(open(p, encoding="utf-8"))
        a = analyze_stock(cfg, raw, ctx)
        analyses.append(a)
        html_ = ctx["page"](f"{cfg['name']} | A 股框架笔记", "gg", render(a, ctx), "../")
        open(os.path.join(out, cfg["slug"] + ".html"), "w", encoding="utf-8").write(html_)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(ctx["page"]("个股 | A 股框架笔记", "gg", stock_index(analyses, ctx), "../"))
    return analyses
