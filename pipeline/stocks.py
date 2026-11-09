"""候选个股：抓数据（fetch）和计算（analyze_stock）。
抓数据：python3 -I pipeline/stocks.py <项目根目录>
"""
import json, os, sys, time, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import get_json, kline, dc  # noqa: E402


def load_cfg(root):
    return json.load(open(os.path.join(root, "data", "stocks.json"), encoding="utf-8"))["stocks"]


def fetch_stock(s):
    code = s["code"]
    flt = f'(SECURITY_CODE="{code}")'
    out = {"kline": kline(s["secid"], 800), "board": kline(s["board"]["secid"], 300)}
    out["val"] = dc("RPT_VALUEANALYSIS_DET", "TRADE_DATE", "TRADE_DATE,CLOSE_PRICE,PE_TTM,PB_MRQ,TOTAL_MARKET_CAP", 500, 2, flt)
    out["fin"] = dc("RPT_LICO_FN_CPD", "REPORTDATE", "REPORTDATE,DATATYPE,NOTICE_DATE,BASIC_EPS,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,XSMLL,MGJYXJJE,WEIGHTAVG_ROE,YSTZ,SJLTZ", 16, 1, flt)
    out["margin"] = dc("RPTA_WEB_RZRQ_GGMX", "DATE", "DATE,SPJ,RZYE,RZJME,RZYEZB", 120, 1, f'(SCODE="{code}")')
    try:
        out["consensus"] = dc("RPT_WEB_RESPREDICT", "RATING_ORG_NUM", "ALL", 1, 1, flt)
    except Exception:
        out["consensus"] = []
    try:
        out["holders"] = dc("RPT_HOLDERNUMLATEST", "END_DATE", "END_DATE,HOLDER_NUM,PRE_HOLDER_NUM,HOLDER_NUM_RATIO", 1, 1, flt)
    except Exception:
        out["holders"] = []
    u = ("https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=30&page_index=1"
         f"&ann_type=A&client_source=web&stock_list={code}")
    try:
        out["notices"] = [{"date": x["notice_date"][:10], "title": x["title"], "art": x["art_code"]}
                          for x in get_json(u)["data"]["list"]]
    except Exception:
        out["notices"] = []
    return out


if __name__ == "__main__":
    root = sys.argv[1]
    d = os.path.join(root, "data", "raw", "stocks")
    os.makedirs(d, exist_ok=True)
    only = sys.argv[2:]  # 可指定只抓某几只（股票代码）
    for s in load_cfg(root):
        if only and s["code"] not in only:
            continue
        try:
            data = fetch_stock(s)
            json.dump(data, open(os.path.join(d, s["code"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
            print(s["name"], "ok", flush=True)
        except Exception as e:
            print(s["name"], "error", str(e)[:200], flush=True)
        time.sleep(1)
