"""抓取全球环境序列（FRED 公共 CSV）：广义美元、VIX、美国高收益信用利差、SOFR。
写入 data/raw/global.json，供 A 股 A 节点与港股 A／D 节点使用。
用 curl 子进程下载，避开本机 Python 的证书链问题。
"""
import csv, datetime, io, json, os, subprocess

SERIES = {
    "vix": ("VIXCLS", "标普 500 隐含波动率 VIX", "点"),
    "usd_broad": ("DTWEXBGS", "美联储广义美元指数", "2006-01=100"),
    "us_hy_oas": ("BAMLH0A0HYM2", "美国高收益信用利差 OAS", "%"),
    "sofr": ("SOFR", "有担保隔夜融资利率 SOFR", "%"),
}


def fetch_series(key, days=400):
    code, name, unit = SERIES[key]
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd={start}&coed={end}"
    r = subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "25", url],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr or "curl failed")[:160])
    rows = []
    for rec in csv.DictReader(io.StringIO(r.stdout)):
        date = rec.get("observation_date") or rec.get("DATE")
        value = rec.get(code)
        if date and date <= end.isoformat() and value not in (None, "", "."):
            rows.append({"date": date, "value": float(value)})
    if not rows:
        raise ValueError(f"no observations for {code}")
    return {"name": name, "unit": unit, "code": code, "rows": rows,
            "source": f"https://fred.stlouisfed.org/series/{code}"}


def fetch(root):
    target = os.path.join(root, "data", "raw", "global.json")
    data = json.load(open(target, encoding="utf-8")) if os.path.exists(target) else {"series": {}}
    status = {}
    for key in SERIES:
        try:
            data["series"][key] = fetch_series(key)
            status[key] = "ok"
        except Exception as e:
            status[key] = "error: " + str(e)[:120]
    data["observed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data["status"] = status
    os.makedirs(os.path.dirname(target), exist_ok=True)
    json.dump(data, open(target, "w", encoding="utf-8"), ensure_ascii=False)
    return status


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(fetch(root))
