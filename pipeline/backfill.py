"""一次性回溯：按每个交易日当时已经公布的数据，重算近 30 个交易日的板块、个股打分，写入 data/snapshots/scores.json。
用法：
  python3 -I pipeline/backfill.py <项目根目录> stocks
  python3 -I pipeline/backfill.py <项目根目录> boardfetch <BK代码>   # 先补抓回溯需要的数据（较慢，每个板块单独跑）
  python3 -I pipeline/backfill.py <项目根目录> boards
不能回溯的维度：个股 E（机构一致预期没有历史）、板块 B（人工打分），这两项从开始记录那天起才有。
"""
import json, os, sys, copy, io, contextlib

ROOT, MODE = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
N_DAYS = 30


def load_ctx():
    sys.argv = [sys.argv[0], ROOT]
    import runpy
    with contextlib.redirect_stdout(io.StringIO()):
        return runpy.run_path(os.path.join(ROOT, "pipeline", "build.py"))


def save(kind, key, date, scores):
    import scorecard
    scorecard.record(ROOT, kind, key, date, scores)


if MODE == "stocks":
    ctx = load_ctx()
    import stockpage
    dates = ctx["D"].dates[-N_DAYS:]
    cfgs = json.load(open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))["stocks"]
    only = sys.argv[3:]
    for cfg in cfgs:
        if only and cfg["code"] not in only:
            continue
        raw = json.load(open(os.path.join(ROOT, "data", "raw", "stocks", cfg["code"] + ".json"), encoding="utf-8"))
        for d in dates[:-1]:
            r = copy.deepcopy(raw)
            r["kline"]["rows"] = [x for x in r["kline"]["rows"] if x["date"] <= d]
            r["board"]["rows"] = [x for x in r["board"]["rows"] if x["date"] <= d]
            r["val"] = [x for x in r["val"] if x["TRADE_DATE"][:10] <= d]
            r["fin"] = [x for x in r["fin"] if x["NOTICE_DATE"][:10] <= d]
            r["margin"] = [x for x in r["margin"] if x["DATE"][:10] <= d]
            r["notices"] = [x for x in r["notices"] if x["date"] <= d]
            r["consensus"] = []
            a = stockpage.analyze_stock(cfg, r, ctx)
            sc = {k: v for k, v in a["scores"].items() if k != "E"}
            save("stocks", cfg["code"], d, sc)
        print(cfg["name"], "ok", flush=True)

elif MODE == "boardfetch":
    from fetch import dc
    from boards import batch
    slug = sys.argv[3]
    idx_dates = [r["date"] for r in json.load(open(os.path.join(ROOT, "data", "raw", "idx_all.json")))["rows"]][-N_DAYS:]
    p = os.path.join(ROOT, "data", "raw", "boards", slug + ".json")
    raw = json.load(open(p, encoding="utf-8"))
    codes = [c["f12"] for c in raw["cons"]]
    per = raw["periods"]
    out = {"notice": {}, "fin": {}, "val": {}}
    # 各报告期的公告日期，以及上一年同期需要的 Q1
    for k in ("cur", "prev"):
        rows = batch("RPT_LICO_FN_CPD", "SECURITY_CODE,NOTICE_DATE", codes, f"(REPORTDATE='{per[k]}')")
        out["notice"][k] = {r["SECURITY_CODE"]: r["NOTICE_DATE"][:10] for r in rows}
    ly_q1 = f"{int(per['prev_ly'][:4])}-03-31"
    out["fin"]["prev_ly_q1"] = batch("RPT_LICO_FN_CPD", "SECURITY_CODE,PARENT_NETPROFIT,TOTAL_OPERATE_INCOME,XSMLL", codes, f"(REPORTDATE='{ly_q1}')")
    done = os.path.join(ROOT, "data", "raw", "boards", slug + "_bf.json")
    if os.path.exists(done):
        old = json.load(open(done, encoding="utf-8"))
        out["val"] = old.get("val", {})
    for d in idx_dates[:-1]:
        if d in out["val"]:
            continue
        out["val"][d] = batch("RPT_VALUEANALYSIS_DET", "SECURITY_CODE,PE_TTM,TOTAL_MARKET_CAP", codes, f"(TRADE_DATE='{d}')")
        json.dump(out, open(done, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(out, open(done, "w", encoding="utf-8"), ensure_ascii=False)
    print(slug, "ok", len(out["val"]), flush=True)

elif MODE == "boards":
    ctx = load_ctx()
    import boardpage
    dates = ctx["D"].dates[-N_DAYS:]
    cfgs = json.load(open(os.path.join(ROOT, "data", "boards.json"), encoding="utf-8"))["boards"]
    for cfg in cfgs:
        p = os.path.join(ROOT, "data", "raw", "boards", cfg["slug"] + ".json")
        bf = os.path.join(ROOT, "data", "raw", "boards", cfg["slug"] + "_bf.json")
        if not os.path.exists(bf):
            print(cfg["name"], "skip: 先运行 boardfetch"); continue
        raw = json.load(open(p, encoding="utf-8")); extra = json.load(open(bf, encoding="utf-8"))
        n_all = len(raw["cons"])
        for d in dates[:-1]:
            r = copy.deepcopy(raw)
            published = sum(1 for v in extra["notice"]["cur"].values() if v <= d)
            if published < 0.5 * n_all:
                # 当时最新的是上一个报告期：整体往前挪一个季度
                zero = [{"SECURITY_CODE": c["f12"], "PARENT_NETPROFIT": 0, "TOTAL_OPERATE_INCOME": 0, "XSMLL": None} for c in raw["cons"]]
                r["fin"] = {"cur": raw["fin"]["prev"], "prev": raw["fin"]["prev2"], "cur_ly": raw["fin"]["prev_ly"],
                            "prev_ly": extra["fin"]["prev_ly_q1"], "prev2": zero}
                r["periods"] = dict(raw["periods"], cur=raw["periods"]["prev"])
            r["val_now"] = extra["val"].get(d) or raw["val_now"]
            r["kline"]["rows"] = [x for x in r["kline"]["rows"] if x["date"] <= d]
            a = boardpage.analyze_board(cfg, r, ctx)
            save("boards", cfg["slug"], d, {k: v for k, v in a["scores"].items() if k not in ("D", "B")})
        print(cfg["name"], "ok", flush=True)
