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
 'a-rare-earth':{'gate':'稀土冶炼分离公司（稀土业务为主，按分产品毛利确认；市值≥150亿）','factors':['np','cheap','qual'],'n':4,'filter':lambda x:x['code'] in ('600111','000831','600259','600392')},
 'a-magnet':{'gate':'钕铁硼占主营毛利≥70%、市值≥100亿','factors':['np','rev','cheap','qual'],'n':4,'filter':lambda x:x['code'] in ('300748','300224','600366','000970')},
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
TYPE={'a-bank':'crowded','a-coal':'upstream','a-oil':'upstream','a-tanker':'upstream','a-semiconductor':'growth','a-computing':'growth','a-pharma':'growth','a-grid':'cost','a-chemical':'cost','a-rare-earth':'upstream','a-magnet':'cost'}
LENS={
 'crowded':{'name':'顺风但拥挤','fund':'股息率（2025年度）、单季利润同比、PB、ROE：分红能不能持续','pos':'近一年位置：拥挤板块不追高，位置≤0.6为好，>0.85为差','chip':'股东户数变化（户数大增＝散户追入）、融资余额20日变化（快速上升＝杠杆追入）'},
 'upstream':{'name':'看价格水平','fund':'单季利润同比（只作初筛，同时看利润绝对额和比较基数）、股息率、经营现金流覆盖倍数（经营现金流÷净利润；≥1只说明当期利润有现金覆盖，不证明分红安全）、毛利率变化','pos':'距一年高点回撤：回撤≥20%＝回撤条件达标（只说明价格离高点较远，不代表风险已充分反映）；回撤不足10%为未达标','chip':'融资余额20日变化与股东户数变化：资金是否还在追'},
 'growth':{'name':'等开关','fund':'利润加速、营收增速、毛利率变化、经营现金流覆盖倍数：盈利路径（开关②）靠这些兑现','pos':'是否已出现价格确认：站上60日均线且60日涨幅为正＝好（开关②的价格条件）；仍在均线下方＝差','chip':'融资余额是否已出清、股东户数是否减少（筹码集中）、未来6个月解禁比例（≥5%为差）'},
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
    if t=='upstream' and e.get('cashEps') is not None and e['cashEps']<1:fb.append('经营现金流覆盖不足1倍')
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
    sp=Path(root)/'data/stock_pick.json';fixed=(json.loads(sp.read_text()).get('logic1_list') or {}).get('sectors',{}) if sp.exists() else {}
    for sid,r in base.items():
        t=TYPE[sid];rows=[]
        for x in r['all']:
            x['en']=en.get(x['code'],{});L=_layers(t,x);x.update(L)
            x['total']=round((x['score']+V[L['pos']]+V[L['chip']])/3*(0.5 if L['fund']=='差' else 1),2)
            rows.append(x)
        rows.sort(key=lambda x:-x['total'])
        # 名单季度固定（stock_pick.json 的 logic1_list）；没有固定名单时按三层总分取前N
        picks=[x for x in rows if x['code'] in fixed[sid]] if fixed.get(sid) else rows[:R_N.get(sid,5)]
        out[sid]={**{k:v for k,v in r.items() if k!='all'},'type':t,'lens':LENS[t],'picks':picks}
    return out

R_N={'a-bank':5,'a-coal':4,'a-oil':2,'a-tanker':2,'a-semiconductor':5,'a-computing':5,'a-pharma':4,'a-grid':4,'a-chemical':4,'a-rare-earth':4,'a-magnet':4}

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

# ---------- 2026-11-16：参考买入价、卖出价与止损价（研究规则，未回测） ----------
CN10Y=1.59
def cn10y(root):
    """银行买卖价用的10年国债收益率：每周更新写在 data/raw/weekly/state.json；没有时用建档值1.59%。"""
    p=Path(root)/'data/raw/weekly/state.json'
    if p.exists():
        v=json.loads(p.read_text()).get('cn10y')
        if v and v.get('value'):return {'value':round(v['value'],2),'date':v['date']}
    return {'value':1.59,'date':'2026-11-13'}
PRICE_RULES={
 'crowded':{'buy':'股息率达到“10年国债+2.5个百分点”对应的价格及以下（每股分红÷(10年国债+2.5%)）','sell':'股息率降到“10年国债+2.0个百分点”对应的价格（与板块降级线一致）','stop':'不设价格止损；分红下调或10年国债持续高于1.85%时退出'},
 'upstream':{'buy':'一年区间下部：区间位置0.2—0.4（且不高于60日均线）','sell':'接近一年高点：区间位置0.9（价格纪律：不把创新高作为基准情形）','stop':'跌破一年低点5%'},
 'growth':{'buy':'开关打开、且价格先站上60日均线后：60日均线至均线上方5%','sell':'第一目标取“一年区间中位”与“两倍风险距离”中较高者，第二目标为一年高点下方5%','stop':'买入价下方12%与一年低点下方5%中较高者'},
 'cost':{'buy':'一年区间下部：区间位置0.15—0.35','sell':'一年区间位置0.8','stop':'跌破一年低点5%'},
}

def _range(e):
    c=e.get('close');dd=e.get('dd');p=e.get('pos52');ma=e.get('vsMA60')
    if c is None or dd is None or p is None:return None
    hi=c/(1+dd/100)
    lo=c if p>=0.999 else (c-p*hi)/(1-p)
    if p>=0.999:lo=None
    return {'c':c,'hi':hi,'lo':lo,'ma60':c/(1+ma/100) if ma is not None else None}

def price_levels(t,x):
    e=x.get('en') or {};R=_range(e)
    if not R:return None
    c,hi,lo,ma=R['c'],R['hi'],R['lo'],R['ma60']
    out={'close':c,'note':''}
    if t=='crowded':
        dy=e.get('dy') or x.get('dy');dps=(dy or 0)*c/100
        if not dps:return None
        b=dps/((CN10Y+2.5)/100);s=dps/((CN10Y+2.0)/100)
        out.update(buy=(round(b*0.97,2),round(b,2)),sell=round(s,2),stop=None,dps=round(dps,3))
    elif lo is None:
        return None
    elif t=='upstream':
        b1=lo+0.2*(hi-lo);b2=lo+0.4*(hi-lo)
        if ma:b2=min(b2,ma)
        b2=max(b2,b1)
        out.update(buy=(round(b1,2),round(b2,2)),sell=round(lo+0.9*(hi-lo),2),stop=round(lo*0.95,2))
    elif t=='growth':
        if not ma:return None
        b1,b2=ma,ma*1.05;mid=(b1+b2)/2
        st=max(mid*0.88,lo*0.95);out.update(buy=(round(b1,2),round(b2,2)),sell=round(max(lo+0.5*(hi-lo),mid+2*(mid-st)),2),sell2=round(max(hi*0.95,mid+2*(mid-st)),2),stop=round(st,2))
    else:
        out.update(buy=(round(lo+0.15*(hi-lo),2),round(lo+0.35*(hi-lo),2)),sell=round(lo+0.8*(hi-lo),2),stop=round(lo*0.95,2))
    b1,b2=out['buy'];mid=(b1+b2)/2
    out['rr']=round((out['sell']-mid)/(mid-out['stop']),1) if out.get('stop') and mid>out['stop'] else None
    out['rr_now']=round((out['sell']-c)/(c-out['stop']),1) if out.get('stop') and max(out['stop'],out['buy'][0])<=c<out['sell'] else None  # 低于买入区时规则是观察，不计算现价盈亏比
    out['where']='在买入区' if b1<=c<=b2 else ('高于买入区'+format((c/b2-1)*100,'.0f')+'%' if c>b2 else '低于买入区'+format((1-c/b1)*100,'.0f')+'%')
    if t=='crowded':
        out['where']='已在卖出区（股息率不足）' if c>=out['sell'] else ('在买入区（股息率达标）' if c<=b2 else '等待：高于买入价'+format((c/b2-1)*100,'.0f')+'%')
    if t=='growth':
        out['where']='价格已确认，'+('在买入区' if b1<=c<=b2 else '高于买入区'+format((c/b2-1)*100,'.0f')+'%') if c>=b1 else '未确认：需先站上60日均线（约'+format(b1,'.2f')+'）'
    if t in ('upstream','cost') and c<b1:out['where']='低于买入区'+format((1-c/b1)*100,'.0f')+'%（接近一年低点，靠近止损）'
    if t!='growth' and out.get('stop') and c<=out['stop']:out['where']='已跌破止损价（按规则退出，不接）'
    return out

def box_levels(x):
    c,p,W=x['close'],x['pos'],x['W']
    L=c/(1+p*W);H=L*(1+W)
    b=(round(L,2),round(L+0.25*(H-L),2));s=round(H-0.2*(H-L),2);st=round(L*0.85,2);mid=sum(b)/2
    return {'close':c,'buy':b,'sell':s,'stop':st,'rr':round((s-mid)/(mid-st),1),'rr_now':round((s-c)/(c-st),1) if st<c<s else None,'where':'已跌破止损价（箱体失效）' if c<=st else ('到达卖出区' if c>=s else ('在买入区' if b[0]<=c<=b[1] else ('高于买入区' if c>b[1] else '低于箱底')))}


# ---------- 价格规则说明（网页“价格规则”区块的唯一来源；改规则时同时改这里） ----------
PRICE_DOC={
 'inputs':[
  ('现价','每周更新时最近一个交易日的收盘价，未复权；页面顶部写明截止日。'),
  ('一年高点','近365天复权收盘价最高点（复权序列由每日涨跌幅从最新收盘价倒推，等于前复权），即现价÷(1+距一年高点回撤)。'),
  ('一年低点','由“一年区间位置”反推：低点＝(现价−位置×高点)÷(1−位置)。现价就是一年高点时无法反推，该股不给价格。'),
  ('区间位置','(价格−一年低点)÷(一年高点−一年低点)，0＝一年最低，1＝一年最高。'),
  ('60日均线','现价÷(1+相对60日线偏离)。'),
  ('每股分红','2025年度每股分红（与板块页股息率同口径，不用滚动12个月）。'),
  ('10年国债','每周更新时取最新一期中国10年期国债收益率（东方财富数据中心 RPTA_WEB_TREASURYYIELD）；建档值1.59%。'),
 ],
 'types':[
  {'t':'crowded','name':'顺风但拥挤','sectors':'银行','buy':'每股分红÷(10年国债+2.5%)，向下留3%作为区间','sell':'每股分红÷(10年国债+2.0%)','stop':'不设价格止损；分红下调、或10年国债持续高于1.85%时退出','why':'买银行买的是分红，价格高低只体现在“股息率比国债高多少”。卖出线2.0个百分点与板块页的降级线是同一条线，个股和板块用同一把尺子。银行波动小，价格止损容易被噪音打掉，所以改用基本面退出条件。'},
  {'t':'upstream','name':'看价格水平（前半段）','sectors':'煤炭、石油、油运','buy':'一年区间位置0.2—0.4，且上沿不高于60日均线','sell':'区间位置0.9（接近一年高点）','stop':'一年低点下方5%','why':'这是价格纪律，不是对行业见顶的判断：上游利润跟着商品价格水平走，板块估值分位已高，所以在一年区间里低买高卖，不把创新高当作基准情形；买点放在区间下部、不追到均线上方；跌破一年低点说明价格水平的判断可能错了。同比回落和2027年2—4月的PPI数据只是复核节点，不触发卖出。只有个股核验与估值通过后，价格规则才用于执行。'},
  {'t':'growth','name':'等开关','sectors':'半导体、算力硬件、创新药','buy':'开关打开、且价格先站上60日均线之后：60日均线至均线上方5%','sell':'第一目标取“一年区间中位”与“买入区中点+2倍风险距离”中较高者；第二目标为一年高点下方5%','stop':'买入区中点下方12%与一年低点下方5%中较高者','why':'开关打开前不买，价格在区间里再低也不买。站上60日均线是开关②的价格条件，买点限定在均线上方5%以内，防止追高。目标至少是风险的两倍，否则这笔交易不值得做。'},
  {'t':'cost','name':'看成本与价差','sectors':'电网设备、化工','buy':'一年区间位置0.15—0.35','sell':'区间位置0.8','stop':'一年低点下方5%','why':'逻辑是成本下降或价差修复带来的毛利改善，兑现慢、没有强催化，所以买得比上游更低、卖得比上游更早。'},
 ],
 'common':[
  ('使用顺序','板块层（业务是否适用）→ 个股初筛（进入候选）→ 个股核验（业务受益、盈利持续性、资本开支后现金与分红覆盖）→ 估值（价格是否已充分反映）→ 价格（入场、兑现、止损）→ 筹码（只提示拥挤与交易风险）。价格只决定“什么价格做”，不改变“做不做”：核验或估值没有通过时，进入买入区也只显示“价格到位·待核”；估值否决、核验未通过或到了卖出价，显示“不买”；等开关板块任何价格都不买。'),
  ('盈亏比','计划盈亏比＝(卖出参考价−买入区中点)÷(买入区中点−止损价)，衡量按计划价位买入的性价比；现价盈亏比＝(卖出参考价−现价)÷(现价−止损价)，衡量现在买的性价比，现价低于买入区（规则要求先观察）或已到卖出价时不计算。低于2说明赚的空间不足亏的两倍；这是研究信号，不是硬规则。'),
  ('现价状态','“在买入区”＝可以按计划执行；“高于买入区X%”＝等回落；“低于买入区（靠近止损）”＝区间可能正在失效，先观察不接；“未确认”＝等开关板块尚未站上60日均线；“已在卖出区”＝持有者兑现，新资金不买；“已跌破止损价”＝持有者按规则退出，新资金不接。'),
  ('什么时候重算','每周按“更新流程.md”跑一次 weekly_update.py，全部价格自动重算并存快照；银行公布新分红时，先改分红数据再跑；板块档位变化时，该板块换用新档位对应的规则。规则本身只在复盘时改，改了要写版本和原因。'),
  ('规则性质','景气顺势的价格规则是研究规则，尚未回测，阈值（0.2、0.4、0.9、12%等）是按板块逻辑设定的初始值，回测后可能调整。国资箱体的买卖规则就是组合回测里用的那一套。'),
 ],
 'box':{'inputs':'箱底＝近两年前复权收盘价的10%分位，箱顶＝90%分位；箱体位置＝(价格−箱底)÷(箱顶−箱底)。','buy':'箱体位置0—0.25，即箱底到箱底+25%箱宽','sell':'箱体位置≥0.8；或单次脉冲上涨≥30%时直接兑现','stop':'收盘跌破箱底15%（箱底×0.85），视为箱体失效','pause':'中证全指收盘低于4,700时不开新仓（托底失效）','why':'这类股票赚的是箱体往返和事件脉冲的钱，不是盈利增长，所以价格完全由箱体决定。这几个数和组合回测用的规则完全一致，回测结果见本页“回测”。'},
}
