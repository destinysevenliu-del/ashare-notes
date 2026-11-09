"""板块：抓成分股、聚合财务、估值和板块行情。
用法：python3 -I pipeline/boards.py <项目根目录>
"""
import json, os, sys, time, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import get_json, kline, dc  # noqa: E402


def constituents(bk):
    out, pn = [], 1
    while True:
        u = (f"https://push2.eastmoney.com/api/qt/clist/get?fs=b:{bk}&fields=f12,f13,f14,f2,f3,f20,f9,f23,f24,f25"
             f"&fid=f20&po=1&pn={pn}&pz=100&fltt=2&invt=2")
        d = get_json(u)["data"]
        diff = d["diff"]
        diff = list(diff.values()) if isinstance(diff, dict) else diff
        out += diff
        if len(out) >= d["total"] or not diff:
            return out
        pn += 1


def in_filter(codes):
    return '(SECURITY_CODE in ("' + '","'.join(codes) + '"))'


def batch(report, cols, codes, extra):
    rows = []
    for i in range(0, len(codes), 80):
        rows += dc(report, "SECURITY_CODE", cols, 500, 1, in_filter(codes[i:i + 80]) + extra)
        time.sleep(0.3)
    return rows


def fetch_board(b, idx_dates):
    cons = [c for c in constituents(b["slug"]) if c.get("f20") not in (None, "-")]
    codes = [c["f12"] for c in cons]
    today = datetime.date.fromisoformat(idx_dates[-1])
    y = today.year if today.month > 10 else today.year - 1  # 最近一个已披露完的季度：这里按三季报
    # 找最近已披露的季报期：取成分股中披露最多的报告期
    periods = []
    for yy in (today.year, today.year - 1):
        for md in ("12-31", "09-30", "06-30", "03-31"):
            periods.append(f"{yy}-{md}")
    periods = [p for p in periods if p < today.isoformat()]
    latest = None
    for p in periods:
        r = dc("RPT_LICO_FN_CPD", "SECURITY_CODE", "SECURITY_CODE", 500, 1, in_filter(codes[:80]) + f"(REPORTDATE='{p}')")
        if len(r) >= 0.6 * min(len(codes), 80):
            latest = p
            break
    ly, lmd = int(latest[:4]), latest[5:]
    prev_md = {"03-31": None, "06-30": "03-31", "09-30": "06-30", "12-31": "09-30"}[lmd]
    want = {"cur": latest, "cur_ly": f"{ly - 1}-{lmd}"}
    if prev_md:
        want["prev"] = f"{ly}-{prev_md}"; want["prev_ly"] = f"{ly - 1}-{prev_md}"
        pp = {"06-30": "03-31", "09-30": "06-30", "12-31": "09-30"}.get(prev_md)
        if pp:
            want["prev2"] = f"{ly}-{pp}"
    fin = {}
    for k, p in want.items():
        fin[k] = batch("RPT_LICO_FN_CPD", "SECURITY_CODE,PARENT_NETPROFIT,TOTAL_OPERATE_INCOME,XSMLL", codes, f"(REPORTDATE='{p}')")
    # 估值：今天和约一年前
    d_now = idx_dates[-1]
    one_y = (today - datetime.timedelta(days=365)).isoformat()
    d_1y = [d for d in idx_dates if d >= one_y][0]
    val_now = batch("RPT_VALUEANALYSIS_DET", "SECURITY_CODE,PE_TTM,TOTAL_MARKET_CAP", codes, f"(TRADE_DATE='{d_now}')")
    if not val_now:  # 当天估值还没更新时退一天
        d_now = idx_dates[-2]
        val_now = batch("RPT_VALUEANALYSIS_DET", "SECURITY_CODE,PE_TTM,TOTAL_MARKET_CAP", codes, f"(TRADE_DATE='{d_now}')")
    val_1y = batch("RPT_VALUEANALYSIS_DET", "SECURITY_CODE,PE_TTM,TOTAL_MARKET_CAP", codes, f"(TRADE_DATE='{d_1y}')")
    return {"cons": cons, "periods": want, "fin": fin, "val_now": val_now, "val_1y": val_1y, "d_now": d_now, "d_1y": d_1y,
            "kline": kline(b["secid"], 300)}


if __name__ == "__main__":
    root = sys.argv[1]
    cfg = json.load(open(os.path.join(root, "data", "boards.json"), encoding="utf-8"))["boards"]
    idx_dates = [r["date"] for r in json.load(open(os.path.join(root, "data", "raw", "idx_all.json")))["rows"]]
    d = os.path.join(root, "data", "raw", "boards")
    os.makedirs(d, exist_ok=True)
    only = sys.argv[2:]  # 可指定只抓某几个板块
    for b in cfg:
        if only and b["slug"] not in only:
            continue
        try:
            json.dump(fetch_board(b, idx_dates), open(os.path.join(d, b["slug"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
            print(b["name"], "ok", flush=True)
        except Exception as e:
            print(b["name"], "error", str(e)[:200], flush=True)
