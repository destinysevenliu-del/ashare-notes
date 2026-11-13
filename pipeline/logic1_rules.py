"""Logic 1: stock candidates inside selected sectors. Rules are explicit and sector-specific.
Inputs: company Q3 single-quarter financials (data/raw/screen/fin_*), valuation snapshot, browser-fetched PB/dividend (data/raw/stock_pick/val_extra.json)."""
import json
from pathlib import Path

RULES={
 'a-bank':{'gate':'市值≥1000亿（国家队与险资主要买大盘银行）；三季度单季利润同比≥0','rank':'近12个月股息率从高到低','n':5,'filter':lambda x:x['mc']>=1000 and (x['np_yoy'] or -1)>=0,'key':lambda x:-(x.get('dy') or 0)},
 'a-coal':{'gate':'市值≥100亿；三季度单季利润≥5亿且同比≥20%；PE 0—20','rank':'三季度单季利润规模（避免低基数造成的超高增速）','n':4,'filter':lambda x:x['mc']>=100 and x['q_np']>=5 and (x['np_yoy'] or -1)>=20 and 0<(x['pe'] or 99)<=20,'key':lambda x:-x['q_np']},
 'a-oil':{'gate':'市值≥1000亿的一体化油企（油价弹性来自上游）','rank':'市值','n':2,'filter':lambda x:x['mc']>=1000 and x['code'] in ('601857','600028'),'key':lambda x:-x['mc']},
 'a-tanker':{'gate':'只保留纯油运公司（板块含港口与集运）；三季度单季利润同比为正','rank':'三季度单季利润同比','n':3,'filter':lambda x:x['code'] in ('601872','600026','601975') and (x['np_yoy'] or -1)>0,'key':lambda x:-(x['np_yoy'] or 0)},
 'a-semiconductor':{'gate':'市值≥800亿；三季度单季利润≥8亿且同比≥30%；PE 0—60','rank':'三季度单季利润规模（开关打开时资金先回到盈利最厚的龙头）','n':5,'filter':lambda x:x['mc']>=800 and x['q_np']>=8 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 999)<=60,'key':lambda x:-x['q_np']},
 'a-computing':{'gate':'市值≥800亿；三季度单季利润≥15亿且同比≥50%；PE 0—40','rank':'三季度单季利润规模','n':5,'filter':lambda x:x['mc']>=800 and x['q_np']>=15 and (x['np_yoy'] or 0)>=50 and 0<(x['pe'] or 999)<=40,'key':lambda x:-x['q_np']},
 'a-pharma':{'gate':'市值≥200亿；三季度单季利润≥2亿且同比≥30%；PE 0—70','rank':'三季度单季利润同比','n':4,'filter':lambda x:x['mc']>=200 and x['q_np']>=2 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 999)<=70,'key':lambda x:-(x['np_yoy'] or 0)},
 'a-grid':{'gate':'市值≥200亿；三季度单季利润同比>0且营收同比≥15%（没有被成本挤压的）','rank':'营收同比','n':4,'filter':lambda x:x['mc']>=200 and (x['np_yoy'] or -1)>0 and (x['rev_yoy'] or 0)>=15,'key':lambda x:-(x['rev_yoy'] or 0)},
 'a-chemical':{'gate':'市值≥150亿；三季度单季利润≥5亿且同比≥30%；PE 0—15','rank':'三季度单季利润同比','n':4,'filter':lambda x:x['mc']>=150 and x['q_np']>=5 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 99)<=15,'key':lambda x:-(x['np_yoy'] or 0)},
}

def rows(root,bks):
    L=lambda f:{r['SECURITY_CODE']:r for r in json.load(open(Path(root)/'data/raw/screen'/f))}
    F={k:L('fin_'+k+'.json') for k in ['2026-09-30','2026-06-30','2025-09-30','2025-06-30']};V=L('val_2026-11-09.json')
    ex={};p=Path(root)/'data/raw/stock_pick/val_extra.json'
    if p.exists():ex=json.loads(p.read_text())
    g=lambda a,b:(a/b-1)*100 if b and b>0 and a is not None else None
    out=[]
    for c,r in F['2026-09-30'].items():
        if r['BOARD_CODE'] not in bks or not all(c in F[k] for k in F) or 'ST' in r['SECURITY_NAME_ABBR']:continue
        n=lambda k,f:F[k][c][f] or 0
        q=n('2026-09-30','PARENT_NETPROFIT')-n('2026-06-30','PARENT_NETPROFIT');ql=n('2025-09-30','PARENT_NETPROFIT')-n('2025-06-30','PARENT_NETPROFIT')
        rv=n('2026-09-30','TOTAL_OPERATE_INCOME')-n('2026-06-30','TOTAL_OPERATE_INCOME');rvl=n('2025-09-30','TOTAL_OPERATE_INCOME')-n('2025-06-30','TOTAL_OPERATE_INCOME')
        v=V.get(c,{});e=ex.get(c,{})
        out.append({'code':c,'name':r['SECURITY_NAME_ABBR'],'industry':r['BOARD_NAME'],'q_np':round(q/1e8,1),'np_yoy':g(q,ql),'rev_yoy':g(rv,rvl),'h1_yoy':g(n('2026-06-30','PARENT_NETPROFIT'),n('2025-06-30','PARENT_NETPROFIT')),'pe':v.get('PE_TTM'),'mc':round((v.get('TOTAL_MARKET_CAP') or 0)/1e8),'pb':e.get('pb'),'dy':e.get('dy'),'close':e.get('close')})
    return out

def select(root,sectors):
    res={}
    for s in sectors:
        if s['id'] not in RULES:continue
        R=RULES[s['id']];pool=rows(root,s['bks']);ok=[x for x in pool if R['filter'](x)]
        res[s['id']]={'gate':R['gate'],'rank':R['rank'],'pool':len(pool),'passed':len(ok),'picks':sorted(ok,key=R['key'])[:R['n']]}
    return res
