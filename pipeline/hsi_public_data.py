"""Read public HSI report directories and UTF-16 daily index CSVs."""
import concurrent.futures
import csv
import datetime
import io
import json
import ssl
import urllib.parse
import urllib.request

BASE = 'https://www.hsi.com.hk/api/wsit-hsi-ddoc-ea-public-website-proxy/v1/'
NAMES = {'hsi': 'Hang Seng Index', 'hscei': 'Hang Seng China Enterprises Index', 'hstech': 'Hang Seng TECH Index'}

def get_bytes(url):
    context = ssl.create_default_context()
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, context=context, timeout=25) as response:
        return response.read()

def download_url(resource):
    return BASE + 'content/gcs/download?' + urllib.parse.urlencode({'resource': resource})

def parse_daily(content, code, source):
    # The first row is Chinese headings. The second row has the stable English headings.
    text = content.decode('utf-16') if content.startswith((b'\xff\xfe', b'\xfe\xff')) else content.decode('utf-8-sig')
    lines = list(csv.reader(io.StringIO(text), delimiter='\t'))
    headers = lines[1]
    records = [dict(zip(headers, row)) for row in lines[2:] if row and row[0]]
    record = next(row for row in records if row['Index'].startswith(NAMES[code]) and row.get('Index Currency') == 'HKD')
    day = datetime.datetime.strptime(record['Trade Date'], '%Y%m%d').date().isoformat()
    def value(key):
        item = record.get(key)
        return float(item.replace(',', '')) if item else None
    close = value('Index Close')
    pe = value('PE Ratio (times)')
    return {
        'date': day, 'close': close, 'pe_ratio': pe,
        'dividend_yield_pct': value('Dividend Yield (%)'),
        'index_turnover_million_hkd': value('Index Turnover (Mn)'),
        'market_turnover_million_hkd': value('Market Turnover (Mn)'),
        'earnings_proxy': close / pe if pe else None,
        'source': source,
    }

def report_items(code):
    url = BASE + 'product-data/pub/series/metadata/v2?' + urllib.parse.urlencode({'data': 'dailyReport', 'seriesCode': code})
    data = json.loads(get_bytes(url))
    series = next(item for item in data if item['seriesCode'] == code)
    return next(item['reportDate'] for item in series['reportList'] if item['reportType'] == 'idx')

def fetch_recent(codes=('hsi', 'hscei', 'hstech'), asof=None, cached=None):
    """Keep all publicly listed dates, with missing fields as None, never zero-filled."""
    asof = asof or datetime.date.today().isoformat()
    result = {'indices': {}, 'errors': {}, 'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    cached = cached or {'indices': {}}
    jobs = []
    for code in codes:
        result['indices'][code] = list(cached.get('indices', {}).get(code, []))
        existing = {row['date'] for row in result['indices'][code]}
        items = [item for item in report_items(code) if item['date'] <= asof]
        latest = max((item['date'] for item in items), default='')
        for item in items:
            if item['date'] not in existing or item['date'] == latest:
                jobs.append((code, item))
    def fetch_one(job):
        code, item = job
        url = download_url(item['url'])
        row = parse_daily(get_bytes(url), code, url)
        if row['date'] != item['date']:
            raise ValueError('Report date differs from directory date')
        return code, row
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_one, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            code, item = futures[future]
            try:
                _, row = future.result()
                result['indices'][code] = [old for old in result['indices'][code] if old['date'] != row['date']] + [row]
            except Exception as exc:
                result['errors'][code + ':' + item['date']] = str(exc)
    for rows in result['indices'].values():
        rows.sort(key=lambda row: row['date'])
    return result


def refresh(root, asof):
    from pathlib import Path
    path = Path(root) / 'data/raw/hk/valuations.json'
    cached = json.loads(path.read_text()) if path.exists() else {'indices': {}}
    try:
        result = fetch_recent(asof=asof, cached=cached)
    except Exception as exc:
        result = cached
        result['refresh_error'] = str(exc)[:200]
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
