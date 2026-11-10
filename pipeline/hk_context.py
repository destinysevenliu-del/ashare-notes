"""Collect dated global risk inputs from FRED's public CSV export."""
import concurrent.futures
import csv
import datetime
import io
import json
import subprocess
from pathlib import Path

SERIES = {
    'us10': ('DGS10', '美国 10 年国债收益率', '%'),
    'usd_broad': ('DTWEXBGS', '美联储广义美元指数', '2006-01=100'),
    'vix': ('VIXCLS', '标普 500 隐含波动率 VIX', '点'),
    'us_hy_oas': ('BAMLH0A0HYM2', '美国高收益信用利差 OAS', '%'),
}


def fetch_series(key):
    code, name, unit = SERIES[key]
    end = datetime.date.today()
    start = end - datetime.timedelta(days=400)
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd={start}&coed={end}'
    response = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error', '--max-time', '25', url], capture_output=True, text=True, check=True)
    records = csv.DictReader(io.StringIO(response.stdout))
    rows = []
    for record in records:
        date = record.get('observation_date') or record.get('DATE')
        value = record.get(code)
        if date and date <= end.isoformat() and value not in (None, '', '.'):
            rows.append({'date': date, 'value': float(value)})
    if not rows:
        raise ValueError(f'No observations for {code}')
    return {'name': name, 'unit': unit, 'code': code, 'rows': rows,
            'source': f'https://fred.stlouisfed.org/series/{code}', 'download_url': url,
            'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}


def fetch(root):
    target = Path(root) / 'data/raw/hk/context.json'
    data = json.loads(target.read_text()) if target.exists() else {'series': {}}
    status = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_series, key): key for key in SERIES}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                data['series'][key] = future.result()
                status[key] = 'ok'
            except Exception as exc:
                status[key] = str(exc)[:180]
    data['status'] = status
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print('HK context', json.dumps(status, ensure_ascii=False))
    return data


if __name__ == '__main__':
    import sys
    fetch(sys.argv[1])
