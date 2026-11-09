"""抓取大盘层所需的全部原始数据，保存到 data/raw/*.json。
用法：python3 -I pipeline/fetch.py <项目根目录>
"""
import json, sys, time, urllib.request, urllib.parse, datetime, os

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
DC = "https://datacenter-web.eastmoney.com/api/data/v1/get?"


def get_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:  # 东方财富偶尔超时，重试
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"fetch failed: {url[:120]} :: {last}")


def dc(report, sort, columns="ALL", page_size=500, pages=1, flt=None):
    rows = []
    for p in range(1, pages + 1):
        q = {"reportName": report, "columns": columns, "pageSize": page_size, "pageNumber": p,
             "sortColumns": sort, "sortTypes": -1}
        if flt:
            q["filter"] = flt
        d = get_json(DC + urllib.parse.urlencode(q))
        res = d.get("result") or {}
        rows += res.get("data") or []
        if p >= (res.get("pages") or 1):
            break
    return rows


def kline(secid, lmt=800):
    u = ("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=%s&fields1=f1,f2,f3"
         "&fields2=f51,f52,f53,f54,f55,f57&klt=101&fqt=1&lmt=%d&end=20500101" % (secid, lmt))
    d = get_json(u)["data"]
    out = []
    for k in d["klines"]:
        dt, o, c, h, l, amt = k.split(",")
        out.append({"date": dt, "open": float(o), "close": float(c), "high": float(h), "low": float(l), "amount": float(amt)})
    return {"code": d["code"], "name": d.get("name"), "rows": out}


def csindex_pe(code, start_year=2019):
    rows = []
    today = datetime.date.today()
    for y in range(start_year, today.year + 1):
        s, e = f"{y}0101", f"{y}1231"
        u = f"https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode={code}&startDate={s}&endDate={e}"
        d = get_json(u)
        for r in d.get("data") or []:
            if r.get("peg"):
                rows.append({"date": f"{r['tradeDate'][:4]}-{r['tradeDate'][4:6]}-{r['tradeDate'][6:]}",
                             "pe": float(r["peg"]), "close": r.get("close")})
        time.sleep(0.5)
    rows.sort(key=lambda r: r["date"])
    # 中证官网周末也会返回上一交易日的重复行，去重
    dedup = []
    for r in rows:
        if dedup and r["close"] == dedup[-1]["close"] and r["pe"] == dedup[-1]["pe"]:
            continue
        dedup.append(r)
    return dedup


def save(name, obj):
    with open(os.path.join(RAW, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


JOBS = {
    # H 市场走势 / G 成交额
    "idx_sh": lambda: kline("1.000001"),
    "idx_hs300": lambda: kline("1.000300"),
    "idx_cyb": lambda: kline("0.399006"),
    "idx_kc50": lambda: kline("1.000688"),
    "idx_all": lambda: kline("1.000985"),
    # D 利率 / 汇率
    "usdcnh": lambda: kline("133.USDCNH"),
    "bond": lambda: dc("RPTA_WEB_TREASURYYIELD", "SOLAR_DATE", "SOLAR_DATE,EMM00166466,EMG00001310", 500, 5),
    "lpr": lambda: dc("RPTA_WEB_RATE", "TRADE_DATE", "ALL", 24),
    "money": lambda: dc("RPT_ECONOMY_CURRENCY_SUPPLY", "REPORT_DATE", "ALL", 36),
    # G 两融
    "margin": lambda: dc("RPTA_RZRQ_LSHJ", "DIM_DATE", "DIM_DATE,RZRQYE,RZYE,RZJME,RZYEZB,LTSZ", 500, 2),
    # A 经济
    "pmi": lambda: dc("RPT_ECONOMY_PMI", "REPORT_DATE", "ALL", 36),
    "cpi": lambda: dc("RPT_ECONOMY_CPI", "REPORT_DATE", "ALL", 36),
    "ppi": lambda: dc("RPT_ECONOMY_PPI", "REPORT_DATE", "ALL", 36),
    "exports": lambda: dc("RPT_ECONOMY_CUSTOMS", "REPORT_DATE", "ALL", 36),
    "indus": lambda: dc("RPT_ECONOMY_INDUS_GROW", "REPORT_DATE", "ALL", 36),
    "retail": lambda: dc("RPT_ECONOMY_TOTAL_RETAIL", "REPORT_DATE", "ALL", 36),
    "gdp": lambda: dc("RPT_ECONOMY_GDP", "REPORT_DATE", "ALL", 12),
    # F 估值
    "pe_all": lambda: csindex_pe("000985", 2019),
    "pe_hs300": lambda: csindex_pe("000300", 2016),
}

if __name__ == "__main__":
    status = {}
    for name, fn in JOBS.items():
        try:
            save(name, fn())
            status[name] = "ok"
        except Exception as e:
            status[name] = "error: " + str(e)[:200]
        print(name, status[name], flush=True)
    status["_fetched_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    save("_status", status)
