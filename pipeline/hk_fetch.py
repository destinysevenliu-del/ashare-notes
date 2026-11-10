"""Fetch public HK daily data; keep source dates and last-good cache on failure."""
import concurrent.futures,datetime,json,ssl,sys,urllib.request,urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo

LIQ_URL='https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity'
INDEX_IDS={'hsi':'100.HSI','hscei':'100.HSCEI','hstech':'124.HSTECH'}
TZ=ZoneInfo('Asia/Shanghai')

def get_text(url):
    ctx=ssl.create_default_context()
    try:
        import certifi
        ctx=ssl.create_default_context(cafile=certifi.where())
    except ImportError: pass
    headers={'User-Agent':'Mozilla/5.0'}
    if 'eastmoney.com' in url:headers['Referer']='https://data.eastmoney.com/'
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,context=ctx,timeout=25) as response:return response.read().decode('utf-8-sig')

def index(code):
    url=f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={code}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f57&klt=101&fqt=1&lmt=800&end=20500101'
    data=json.loads(get_text(url))['data'];rows=[]
    for item in data['klines']:
        day,o,c,h,l,amount=item.split(',')
        rows.append(dict(date=day,open=float(o),close=float(c),high=float(h),low=float(l)))
    if len(rows)<21:raise ValueError('Insufficient index history')
    return {'name':data['name'],'code':data['code'],'rows':rows,'source':url,'observed_at':datetime.datetime.now(TZ).isoformat()}

def liquidity():
    data=json.loads(get_text(LIQ_URL))
    if not data['header']['success']:raise ValueError('HKMA unsuccessful')
    rows=sorted(data['result']['records'],key=lambda r:r['end_of_date'])
    if not rows:raise ValueError('HKMA empty')
    return {'rows':rows,'source':LIQ_URL,'observed_at':datetime.datetime.now(TZ).isoformat()}

def parse_connect(text,date):
    # Data is a JSON assignment; never execute JavaScript from the source.
    records=json.loads(text[text.index('['):].strip().rstrip(';'))
    south=[r for r in records if r.get('market') in ('SSE Southbound','SZSE Southbound')]
    if len(south)!=2 or any(r['date']!=date or r.get('tradingDay')!=1 for r in south):raise ValueError('Both southbound links must be available on the same day')
    totals={'buy':0,'sell':0}
    for record in south:
        table=next(c['table'] for c in record['content'] if c.get('table',{}).get('classname')=='tradingTable')
        fields=dict(zip(table['schema'][0],[r['td'][0][0] for r in table['tr']]))
        for key,label in [('buy','Buy Turnover'),('sell','Sell Turnover')]:
            value=float(fields[label].replace(',',''))
            if value<0:raise ValueError('Invalid turnover')
            totals[key]+=value/100 # HKEX summary tables: HK$ million -> 亿港元
    return dict(date=date,**totals,net=totals['buy']-totals['sell'],source=f'https://www.hkex.com.hk/eng/csm/DailyStat/data_tab_daily_{date.replace("-","")}e.js')

def completed_rows(data, now):
    # Conservatively wait until 17:00 local time before treating today's daily bar as close.
    today=now.date().isoformat()
    observed=datetime.datetime.fromisoformat(data['observed_at']) if data.get('observed_at') else now
    observed_day=observed.date().isoformat()
    return [r for r in data['rows'] if r['date']<=today and r['date']<=observed_day
            and not (r['date']==today and now.hour<17)
            and not (r['date']==observed_day and observed.hour<17)]

def fetch(root):
    target=Path(root)/'data/raw/hk';target.mkdir(parents=True,exist_ok=True)
    status={};jobs={**{k:(lambda v=v:index(v)) for k,v in INDEX_IDS.items()},'liquidity':liquidity}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(fn):name for name,fn in jobs.items()}
        for future in concurrent.futures.as_completed(pending):
            name=pending[future]
            try:
                data=future.result();(target/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False));status[name]='ok'
            except Exception as exc:status[name]='error: '+str(exc)[:180]
    if (target/'hsi.json').exists():
        dates=[r['date'] for r in completed_rows(json.loads((target/'hsi.json').read_text()),datetime.datetime.now(TZ))][-35:]
        path=target/'southbound.json';old=json.loads(path.read_text()) if path.exists() else {'rows':[]}
        cached={r['date']:r for r in old['rows']};errors={}
        def one(date):
            url=f'https://www.hkex.com.hk/eng/csm/DailyStat/data_tab_daily_{date.replace("-","")}e.js'
            try:
                result=parse_connect(get_text(url),date)
            except (ValueError, urllib.error.URLError):
                url+='?lang=en'
                result=parse_connect(get_text(url),date)
            result['source']=url
            return result
        need=[d for d in dates if d not in cached or d==dates[-1]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures={pool.submit(one,d):d for d in need}
            for future in concurrent.futures.as_completed(futures):
                date=futures[future]
                try:cached[date]=future.result()
                except Exception as exc:errors[date]=str(exc)[:120]
        rows=[cached[d] for d in sorted(cached)]
        path.write_text(json.dumps({'rows':rows,'observed_at':datetime.datetime.now(TZ).isoformat(),'unavailable_dates':errors,'unit':'亿港元','source':'https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily?sc_lang=en'},ensure_ascii=False))
        status['southbound']='ok' if rows and rows[-1]['date']==dates[-1] else 'partial: latest complete southbound data unavailable'
    status['observed_at']=datetime.datetime.now(TZ).isoformat()
    (target/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
    print(json.dumps(status,ensure_ascii=False))
    if not all((target/(k+'.json')).exists() for k in INDEX_IDS):raise SystemExit('Missing essential HK index data')
if __name__=='__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    fetch(sys.argv[1])
    from hk_context import fetch as fetch_context
    fetch_context(sys.argv[1])
    from hsi_public_data import refresh
    hsi = json.loads((Path(sys.argv[1])/'data/raw/hk/hsi.json').read_text())
    complete = completed_rows(hsi, datetime.datetime.now(TZ))
    if complete:
        result = refresh(sys.argv[1], complete[-1]['date'])
        print('HK official valuations', {key:len(rows) for key,rows in result.get('indices',{}).items()})
