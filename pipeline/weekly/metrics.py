"""每周价格更新：取数与指标计算（Python 主通道）。
计算口径与 metrics.js 的 compute() 必须逐字段一致；test_weekly.py 用 node 同时跑两边核对。
字段口径：
  close/pxdate  最近交易日收盘价（未复权）与日期
  pos52         近365天复权收盘价区间位置 (c-lo)/(hi-lo)，复权序列由 CHANGE_RATE 从最新收盘价倒推
  dd            复权价距近365天最高点 %
  ret60         复权价60个交易日涨跌 %
  vsMA60        复权价相对最近60个交易日均值 %
  marginPct     融资余额占流通市值 %（东方财富 RZYEZB）
  margin20      融资余额相对20个交易日前变化 %
  holdersChg    最近一期（公告日≤截止日）股东户数较上期变化 %；hdate 为该期报告期
  focus/top10free 筹码集中度标签 / 前十大流通股东合计持股 %
  lift6m        截止日后182天内解禁股占总股本 %
"""
import json, time, datetime, urllib.request, urllib.parse

DC = "https://datacenter-web.eastmoney.com/api/data/v1/get?"
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}

def _get(q, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(DC + urllib.parse.urlencode(q), headers=H), timeout=25) as r:
                return (json.loads(r.read().decode("utf-8", "ignore")).get("result") or {"data": [], "pages": 1})
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError("东方财富取数失败：%s :: %s" % (q.get("reportName"), last))

def _all(report, sort, flt):
    out, p = [], 1
    while True:
        r = _get({"reportName": report, "columns": "ALL", "pageSize": 500, "pageNumber": p, "sortColumns": sort, "sortTypes": -1, "filter": flt})
        out += r.get("data") or []
        if p >= (r.get("pages") or 1): return out
        p += 1

def shift(d, n):
    return (datetime.date.fromisoformat(d) + datetime.timedelta(days=n)).isoformat()

def fetch_raw(codes, asof):
    raw = {}
    new = lambda c: raw.setdefault(c, {"px": [], "mg": [], "hd": [], "lf": []})
    for i in range(0, len(codes), 10):
        inn = "(" + ",".join('"%s"' % c for c in codes[i:i + 10]) + ")"
        for x in _all("RPT_VALUEANALYSIS_DET", "TRADE_DATE", "(SECURITY_CODE in %s)(TRADE_DATE>='%s')(TRADE_DATE<='%s')" % (inn, shift(asof, -400), asof)):
            new(x["SECURITY_CODE"])["px"].append([x["TRADE_DATE"][:10], x["CLOSE_PRICE"], x["CHANGE_RATE"]])
        for x in _all("RPTA_WEB_RZRQ_GGMX", "DATE", "(SCODE in %s)(DATE>='%s')(DATE<='%s')" % (inn, shift(asof, -60), asof)):
            new(x["SCODE"])["mg"].append([x["DATE"][:10], x["RZYE"], x["RZYEZB"]])
        for x in _all("RPT_F10_EH_HOLDERNUM", "END_DATE", "(SECURITY_CODE in %s)(END_DATE>='%s')" % (inn, shift(asof, -400))):
            new(x["SECURITY_CODE"])["hd"].append([x["END_DATE"][:10], x["TOTAL_NUM_RATIO"], x["HOLD_FOCUS"], x["FREEHOLD_RATIO_TOTAL"], (x.get("NOTICE_DATE") or x["END_DATE"])[:10]])
        for x in _all("RPT_LIFT_STAGE", "FREE_DATE", "(SECURITY_CODE in %s)(FREE_DATE>'%s')(FREE_DATE<='%s')" % (inn, asof, shift(asof, 182))):
            new(x["SECURITY_CODE"])["lf"].append([x["FREE_DATE"][:10], x["TOTAL_RATIO"]])
    return raw

def fetch_cn10y(asof):
    r = _get({"reportName": "RPTA_WEB_TREASURYYIELD", "columns": "SOLAR_DATE,EMM00166466", "pageSize": 5, "sortColumns": "SOLAR_DATE", "sortTypes": -1, "filter": "(SOLAR_DATE<='%s')" % asof})
    rows = [x for x in r.get("data") or [] if x.get("EMM00166466") is not None]
    return {"date": rows[0]["SOLAR_DATE"][:10], "value": rows[0]["EMM00166466"]} if rows else None

def fetch_csi_all(asof):
    s = asof.replace("-", ""); st = str(int(s[:4]) - 1) + s[4:]
    u = "https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=000985&startDate=%s&endDate=%s" % (st, s)
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25) as r:
        return csi_rows(json.loads(r.read().decode("utf-8")))

def csi_rows(d):
    rows = []
    for x in d["data"]:
        dt = x["tradeDate"]; dt = dt[:4] + "-" + dt[4:6] + "-" + dt[6:]
        if datetime.date.fromisoformat(dt).weekday() >= 5: continue
        if rows and rows[-1]["close"] == x["close"] and rows[-1]["vol"] == x["tradingVol"]: continue
        rows.append({"date": dt, "close": x["close"], "vol": x["tradingVol"]})
    return [{"date": r["date"], "close": r["close"]} for r in rows]

def compute(r, asof, y1):
    jsr = lambda v, n: None if v is None else __import__("math").floor(v * 10 ** n + 0.5) / 10 ** n   # 等同 JS Math.round
    r2 = lambda v: jsr(v, 2); r1 = lambda v: jsr(v, 1)
    px = sorted([x for x in r["px"] if x[1] is not None], key=lambda x: x[0])
    out = {}
    if px:
        n = len(px); adj = [0.0] * n; adj[-1] = px[-1][1]
        for i in range(n - 1, 0, -1): adj[i - 1] = adj[i] / (1 + (px[i][2] or 0) / 100)
        c = adj[-1]; win = [a for a, x in zip(adj, px) if x[0] > y1]; hi, lo = max(win), min(win)
        last60 = adj[-60:]; ma = sum(last60) / len(last60)
        out.update(close=px[-1][1], pxdate=px[-1][0], pos52=r2((c - lo) / (hi - lo)) if hi > lo else None, dd=r1((c / hi - 1) * 100),
                   ret60=r1((c / adj[n - 61] - 1) * 100) if n > 60 else None, vsMA60=r1((c / ma - 1) * 100))
    mg = sorted([x for x in r["mg"] if x[1] is not None], key=lambda x: x[0])
    if mg:
        m = len(mg); out.update(marginPct=r2(mg[-1][2]), margin20=r1((mg[-1][1] / mg[m - 21][1] - 1) * 100) if m > 20 and mg[m - 21][1] else None)
    hd = sorted([x for x in r["hd"] if x[4] <= asof], key=lambda x: x[0])
    if hd:
        h = hd[-1]; out.update(holdersChg=r1(h[1]), hdate=h[0], focus=h[2], top10free=None if h[3] is None else jsr(h[3], 0))
    out["lift6m"] = r1(sum((x[1] or 0) for x in r["lf"]) * 100)
    for k in ("top10free",):
        if out.get(k) is not None: out[k] = int(out[k])
    return out

def metrics(codes, asof):
    raw = fetch_raw(codes, asof); y1 = shift(asof, -365)
    return {"asof": asof, "via": "python", "cn10y": fetch_cn10y(asof), "metrics": {c: compute(raw.get(c, {"px": [], "mg": [], "hd": [], "lf": []}), asof, y1) for c in codes}}
