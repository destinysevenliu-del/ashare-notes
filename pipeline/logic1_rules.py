"""Logic 1: stock candidates inside selected sectors. Rules are explicit and sector-specific.
Inputs: company Q3 single-quarter financials (data/raw/screen/fin_*), valuation snapshot, browser-fetched PB/dividend (data/raw/stock_pick/val_extra.json)."""
import json
from pathlib import Path

ACC=lambda x:(x['np_yoy'] or 0)-(x['h1_yoy'] or 0)
F={'np':('单季利润同比',lambda x:x['np_yoy'] or 0),'acc':('较上半年加速',ACC),'rev':('营收同比',lambda x:x['rev_yoy'] or 0),'cheap':('估值低（PE）',lambda x:-(x['pe'] or 999)),'dy':('股息率',lambda x:x.get('dy') or 0),'qual':('利润增长有营收支撑',lambda x:-max(0,(x['np_yoy'] or 0)-3*max(x['rev_yoy'] or 0,10)))}
RULES={
 'a-bank':{'gate':'市值≥1000亿；三季度单季利润同比≥0','factors':['dy','np'],'n':5,'filter':lambda x:x['mc']>=1000 and (x['np_yoy'] or -1)>=0},
 'a-coal':{'gate':'市值≥100亿；三季度单季利润≥3亿且同比为正；PE 0—20','factors':['np','acc','dy','cheap','qual'],'n':4,'filter':lambda x:x['mc']>=100 and x['q_np']>=3 and (x['np_yoy'] or -1)>0 and 0<(x['pe'] or 99)<=20},
 'a-oil':{'gate':'一体化油企（油价弹性来自上游，板块其余为炼化）','factors':['np','dy'],'n':2,'filter':lambda x:x['code'] in ('601857','600028')},
 'a-tanker':{'gate':'只保留纯油运公司（板块含港口与集运）；三季度单季利润同比为正','factors':['np','cheap'],'n':3,'filter':lambda x:x['code'] in ('601872','600026','601975') and (x['np_yoy'] or -1)>0},
 'a-semiconductor':{'gate':'市值≥300亿；三季度单季利润≥3亿且同比≥30%；PE 0—60','factors':['np','acc','rev','cheap','qual'],'n':5,'filter':lambda x:x['mc']>=300 and x['q_np']>=3 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 999)<=60},
 'a-computing':{'gate':'市值≥300亿；三季度单季利润≥3亿且同比≥30%；PE 0—40','factors':['np','acc','rev','cheap','qual'],'n':5,'filter':lambda x:x['mc']>=300 and x['q_np']>=3 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 999)<=40},
 'a-pharma':{'gate':'市值≥200亿；三季度单季利润≥2亿且同比≥30%；PE 0—70','factors':['np','acc','rev','cheap','qual'],'n':4,'filter':lambda x:x['mc']>=200 and x['q_np']>=2 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 999)<=70},
 'a-grid':{'gate':'市值≥200亿；三季度单季利润同比>0且营收同比≥15%（没有被成本挤压的）','factors':['rev','np','cheap'],'n':4,'filter':lambda x:x['mc']>=200 and (x['np_yoy'] or -1)>0 and (x['rev_yoy'] or 0)>=15},
 'a-chemical':{'gate':'市值≥150亿；三季度单季利润≥3亿且同比≥30%；PE 0—15','factors':['np','acc','rev','cheap','qual'],'n':4,'filter':lambda x:x['mc']>=150 and x['q_np']>=3 and (x['np_yoy'] or 0)>=30 and 0<(x['pe'] or 99)<=15},
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

def flag(x):
    n,r=x['np_yoy'],x['rev_yoy']
    if n is not None and r is not None and n>=100 and n>3*max(r,10):return '利润增速远超营收：可能来自价格周期或低基数，需看持续性'
    if x['q_np']<5:return '利润规模小，增速易受基数影响'
    return ''

def select(root,sectors):
    res={}
    for s in sectors:
        if s['id'] not in RULES:continue
        R=RULES[s['id']];pool=rows(root,s['bks']);ok=[x for x in pool if R['filter'](x)]
        for k in R['factors']:
            vals=sorted(F[k][1](x) for x in ok)
            for x in ok:x['pct_'+k]=(sum(v<F[k][1](x) for v in vals)+0.5*sum(v==F[k][1](x) for v in vals))/len(vals)
        for x in ok:x['score']=round(sum(x['pct_'+k] for k in R['factors'])/len(R['factors']),2);x['flag']=flag(x)
        res[s['id']]={'gate':R['gate'],'rank':'综合排名＝以下各项在通过门槛的公司中的百分位平均：'+'、'.join(F[k][0] for k in R['factors'])+'。市值只用作门槛，不参与排名。','pool':len(pool),'passed':len(ok),'picks':sorted(ok,key=lambda x:-x['score'])[:R['n']]}
    return res

# ---------- 2026-11-15：按板块类型看三层（基本面 / 位置 / 筹码） ----------
TYPE={'a-bank':'crowded','a-coal':'upstream','a-oil':'upstream','a-tanker':'upstream','a-semiconductor':'growth','a-computing':'growth','a-pharma':'growth','a-grid':'cost','a-chemical':'cost'}
LENS={
 'crowded':{'name':'顺风但拥挤','fund':'股息率（2025年度）、单季利润同比、PB、ROE：分红能不能持续','pos':'近一年位置：拥挤板块不追高，位置≤0.6为好，>0.85为差','chip':'股东户数变化（户数大增＝散户追入）、融资余额20日变化（快速上升＝杠杆追入）'},
 'upstream':{'name':'看价格水平','fund':'单季利润同比、股息率、经营现金流/利润（≥1说明利润是真金白银）、毛利率变化','pos':'距一年高点回撤：已回撤20%以上说明部分风险已反映；回撤不足10%为差','chip':'融资余额20日变化与股东户数变化：资金是否还在追'},
 'growth':{'name':'等开关','fund':'利润加速、营收增速、毛利率变化、经营现金流/利润：盈利路径（开关②）靠这些兑现','pos':'是否已出现价格确认：站上60日均线且60日涨幅为正＝好（开关②的价格条件）；仍在均线下方＝差','chip':'融资余额是否已出清、股东户数是否减少（筹码集中）、未来6个月解禁比例（≥5%为差）'},
 'cost':{'name':'看成本与价差','fund':'毛利率同比变化（成本压力或价差修复的直接证据）、单季利润与营收','pos':'近一年位置：≤0.5为好，>0.8为差','chip':'股东户数变化、融资余额20日变化、未来6个月解禁比例'},
}

def _layers(t,x):
    e=x.get('en') or {}
    # 位置
    p=e.get('pos52');dd=e.get('dd');ma=e.get('vsMA60');r60=e.get('ret60')
    if t=='crowded':pos='好' if p is not None and p<=.6 else '差' if p is not None and p>.85 else '中'
    elif t=='upstream':pos='好' if dd is not None and dd<=-20 else '差' if dd is not None and dd>-10 else '中'
    elif t=='growth':pos='好' if ma is not None and ma>0 and (r60 or 0)>0 else '差' if ma is not None and ma<-5 else '中'
    else:pos='好' if p is not None and p<=.5 else '差' if p is not None and p>.8 else '中'
    # 筹码
    bad=[];good=[]
    hc=e.get('holdersChg');m20=e.get('margin20');lf=e.get('lift6m') or 0
    if hc is not None and hc>=10:bad.append('股东户数+'+format(hc,'.0f')+'%')
    if hc is not None and hc<=-5:good.append('股东户数'+format(hc,'.0f')+'%')
    if m20 is not None and m20>=15:bad.append('融资20日+'+format(m20,'.0f')+'%')
    if t=='growth' and m20 is not None and m20<=-10:good.append('融资已出清'+format(m20,'.0f')+'%')
    if lf>=5:bad.append('6个月解禁'+format(lf,'.1f')+'%')
    chip='差' if bad else '好' if good else '中'
    # 基本面（板块特有的硬检查）
    fb=[]
    if t=='upstream' and e.get('cashEps') is not None and e['cashEps']<1:fb.append('经营现金流低于利润')
    if t=='cost' and e.get('gmChg') is not None and e['gmChg']<0:fb.append('毛利率同比下降'+format(e['gmChg'],'.1f')+'个百分点')
    if t=='growth' and e.get('cashEps') is not None and e['cashEps']<0.5:fb.append('经营现金流明显低于利润')
    if t=='cost' and e.get('cashEps') is not None and e['cashEps']<0:fb.append('经营现金流为负')
    fund='差' if fb else '好' if x.get('score',0)>=0.6 else '中'
    return {'fund':fund,'pos':pos,'chip':chip,'notes':fb+bad+good}

def select_v2(root,sectors):
    import json
    p=Path(root)/'data/raw/stock_pick/l1_enrich.json';en=json.loads(p.read_text()) if p.exists() else {}
    base=select_all(root,sectors);out={}
    V={'好':1,'中':.5,'差':0}
    for sid,r in base.items():
        t=TYPE[sid];rows=[]
        for x in r['all']:
            x['en']=en.get(x['code'],{});L=_layers(t,x);x.update(L)
            x['total']=round((x['score']+V[L['pos']]+V[L['chip']])/3*(0.5 if L['fund']=='差' else 1),2)
            rows.append(x)
        rows.sort(key=lambda x:-x['total'])
        out[sid]={**{k:v for k,v in r.items() if k!='all'},'type':t,'lens':LENS[t],'picks':rows[:R_N.get(sid,5)]}
    return out

R_N={'a-bank':5,'a-coal':4,'a-oil':2,'a-tanker':2,'a-semiconductor':5,'a-computing':5,'a-pharma':4,'a-grid':4,'a-chemical':4}

def select_all(root,sectors):
    res=select(root,sectors)
    for s in sectors:
        if s['id'] not in RULES:continue
        R=RULES[s['id']];pool=rows(root,s['bks']);ok=[x for x in pool if R['filter'](x)]
        for k in R['factors']:
            vals=sorted(F[k][1](x) for x in ok)
            for x in ok:x['pct_'+k]=(sum(v<F[k][1](x) for v in vals)+0.5*sum(v==F[k][1](x) for v in vals))/len(vals)
        for x in ok:x['score']=round(sum(x['pct_'+k] for k in R['factors'])/len(R['factors']),2);x['flag']=flag(x)
        res[s['id']]['all']=ok
    return res
