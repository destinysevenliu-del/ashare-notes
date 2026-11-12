"""Three stock decisions, one financial pack per issuer, no A-H additive score.
Review schema: issuers[id].financial_pack owns normalized TTM metrics and checks;
securities[market:code].gate owns A/B/C facts; .pricing owns F bands/H confirmation.
No absent evidence is converted into a pass. D/G never enter this module's evaluators.
"""
import json, math
from pathlib import Path
from html import escape as E

ALIASES={'hk:01088':'cn:601088','hk:01898':'cn:601898','hk:01171':'cn:600188','hk:01138':'cn:600026','hk:00981':'cn:688981','hk:06160':'cn:688235'}
CHECK_METRICS={'现金覆盖':'cash_coverage','毛利变化':'gross_margin_delta_pp','应收周转':'receivable_days_delta','库存周转':'inventory_days_delta'}


def read(root,name):return json.loads((Path(root)/'data'/name).read_text())
def num(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def fmt(x,suffix=''):return f'{x:,.2f}{suffix}' if num(x) else '待核'
def issuer_id(key):return ALIASES.get(key,('cn:'+key[2:] if key.startswith('a:') else key))
def violation(value,op,limit):
    if not num(value) or not num(limit):return None
    if op not in ('gt','ge','lt','le'):raise ValueError('Unknown threshold operation')
    return {'gt':value>limit,'ge':value>=limit,'lt':value<limit,'le':value<=limit}[op]


def validate(policy,reviews):
    pools=policy['subpools'];ids=[p['id'] for p in pools]
    assert len(ids)==len(set(ids))
    assert sum(p['slots'] for p in pools)+policy['convergence']['reserved_slots']<=policy['convergence']['max_issuers']
    assert all(isinstance(p['slots'],int) and p['slots']>=0 for p in pools)
    assert all(p['primary_valuation'] in ['PB','PS','正常化PE'] for p in pools)
    assert all(p['primary_rank'] in ['normalized_profit_growth','normalized_fcf_growth'] for p in pools)
    # A document may be shared; an individual fact cannot get multiple decision owners.
    owners={}
    def register(eids,owner):
        for eid in eids:
            assert isinstance(eid,str) and eid
            assert eid not in owners or owners[eid]==owner,'Duplicate evidence ownership: '+eid
            owners[eid]=owner
    for key,s in reviews['securities'].items():
        gate=s.get('gate',{})
        for k in 'ABC':
            g=gate.get(k,{})
            assert g.get('status') in (None,'yes','no','pending')
            register(g.get('evidence_ids',[]),'gate')
        register(s.get('pricing',{}).get('evidence_ids',[]),'price')
    for key,r in reviews['issuers'].items():
        register(r.get('financial_pack',{}).get('evidence_ids',[]),'quality')


def gate_decision(pool,review):
    if pool is None:return {'status':'no','label':'否 · 未匹配当前理由','why':'历史资料保留；须先指定当前半年接受的方向与唯一入池理由。'}
    g=review.get('gate',{})
    if g.get('reason') and g['reason']!=pool['reason']:
        return {'status':'no','label':'否 · 理由不匹配','why':'不得用另一个理由进入此子池；需要另建子池。'}
    fails=[k for k in 'ABC' if g.get(k,{}).get('status')=='no']
    if fails:return {'status':'no','label':'否 · 未通过入池门','why':'；'.join(k+'：'+g[k].get('note','条件不满足') for k in fails)}
    complete=g.get('reason')==pool['reason'] and all(g.get(k,{}).get('status')=='yes' and g[k].get('evidence_ids') and g[k].get('source') and g[k].get('date') for k in 'ABC')
    if complete:return {'status':'yes','label':'是 · 入池门通过','why':'A/B/C业务和订单事实逐项有日期与来源；不计分。'}
    return {'status':'pending','label':'待核 · 尚未入池','why':'旧候选身份、龙头身份和资料入口不视为A/B/C通过；补齐公司层证据后只判是或否。'}


def quality_decision(pool,pack,gate):
    out={'status':'pending','label':'待统一财务口径','value':None,'rank':None,'why':'需一套经核验的合并TTM财务包，含正常化调整、现金、毛利、应收和库存。','checks':[]}
    if pool is None or gate['status']!='yes':
        out['label']='未进入排序';out['why']='先通过赛道归属；已有财务仅作留档，不可绕过入池门。';return out
    required=['id','period','basis','currency','source','normalization_notes','evidence_ids']
    if not pack.get('reviewed') or not all(pack.get(k) for k in required):return out
    if pack['period']!=pool['peer_period'] or pack['basis']!=pool['financial_basis']:
        out['why']='财务期间或口径与本子池不一致，禁止混排。';return out
    metrics=pack.get('metrics',{});kind='normalized_profit' if pool['primary_rank']=='normalized_profit_growth' else 'normalized_fcf'
    current,previous=metrics.get(kind),metrics.get(kind+'_previous')
    if not num(current) or not num(previous):return out
    if previous<=0:
        out['why']='同比基数非正，不能与正基数增长率混排；需另建扭亏理由子池。';return out
    out['value']=(current/previous-1)*100
    if current<=0:
        out.update(status='downgraded',label='降级 · 主兑现指标非正',why='正常化利润或自由现金流非正，不能靠估值或题材补回。');return out
    for name,metric in CHECK_METRICS.items():
        rule=pack.get('checks',{}).get(name,{})
        if not rule.get('source') or not rule.get('rationale') or rule.get('op') not in ('gt','ge','lt','le'):
            out['why']='质量否决阈值、依据未登记：'+name;return out
        bad=violation(metrics.get(metric),rule['op'],rule.get('limit'))
        out['checks'].append({'name':name,'value':metrics.get(metric),'limit':rule.get('limit'),'op':rule['op'],'bad':bad,'rationale':rule['rationale']})
        if bad is None:out['why']='缺少同口径指标：'+name;return out
    failures=[x['name'] for x in out['checks'] if x['bad']]
    # E is a downgrade check on the same target year, never another positive weight.
    er=pack.get('earnings_revision',{})
    if er.get('verified'):
        if er.get('target_year')!=2027 or not er.get('same_institutions') or not er.get('source'):
            out['why']='E修订口径不一致：只接受固定2027年度、同机构样本。';return out
        bad=violation(er.get('change_pct'),'lt',er.get('downgrade_below_pct'))
        if bad is None:out['why']='E降级阈值尚未登记。';return out
        if bad:failures.append('2027盈利修订')
    out['comparison_key']=[pool['id'],pack['period'],pack['basis'],pack['currency']]
    if failures:out.update(status='downgraded',label='降级 · 兑现未通过',why='触发质量否决：'+'、'.join(failures)+'；不与主指标的增长相抵。')
    else:out.update(status='ready',label='可作池内比较',why='只按'+pool['primary_rank_label']+'排序。质量检查通过不加分；E缺失不冒充上修。')
    return out


def price_decision(pool,pricing,gate,quality,as_of="2026-11-13"):
    out={'status':'wait','label':'等','main_value':None,'why':'唯一主估值指标的数值、适用区间或时点尚未核齐。','vetoes':[]}
    if pool is None or gate['status']=='no':out.update(status='avoid',label='不追',why='入池门未通过；估值低不能抵消理由不匹配。');return out
    if gate['status']!='yes' or quality['status']=='pending':out['why']='先核入池与兑现；历史价格不构成现在追的依据。'
    if quality['status']=='downgraded':out.update(status='avoid',label='不追',why='兑现质量触发否决，低估值不能救回。');return out
    if not pricing.get('reviewed') or pricing.get('metric')!=pool['primary_valuation']:return out
    required=['date','source','basis','range_source','range_date','evidence_ids','financial_pack_id','valid_until']
    if not all(pricing.get(k) for k in required):return out
    if not pricing['range_date']<=pricing['date']<=as_of<=pricing['valid_until']:
        out['why']='价格判断不在登记的有效期内，等待新行情复核。';return out
    value,low,high=pricing.get('value'),pricing.get('pursue_max'),pricing.get('avoid_above')
    if num(value) and value<=0 and pool['primary_valuation']=='PB':
        out.update(status='avoid',label='不追',why='PB分母不支持正净资产估值；不得当成低估值。');return out
    if not all(num(v) for v in (value,low,high)) or value<=0 or not 0<low<=high:return out
    out['main_value']=value
    # Secondary indicators only exercise a veto; they never influence quality rank.
    vetoes=pricing.get('secondary_vetoes',[])
    if {v.get('metric') for v in vetoes}!={pool['secondary_valuation']} or len(vetoes)!=1:
        out['why']='必须完成本板块唯一辅助估值否决检查，不得用另一指标替代。';return out
    for v in vetoes:
        if v.get('metric')==pool['primary_valuation']:raise ValueError('Main valuation must not be counted twice')
        if v.get('kind')!='historical_percentile' or v.get('op')!='gt' or v.get('limit')!=95:
            out['why']='辅助估值仅按已登记的95%历史分位阈值否决，不作排序。';return out
        bad=violation(v.get('value'),v.get('op'),v.get('limit')) if v.get('op') in ('gt','ge','lt','le') else None
        if not v.get('source') or not v.get('basis') or not v.get('date') or v['date']>pricing['date']:bad=None
        if 'percentile' in v.get('kind','') and (v.get('observations',0)<250 or not v.get('window')):bad=None
        out['vetoes'].append(dict(v,bad=bad))
    if any(v['bad'] is True for v in out['vetoes']):out.update(status='avoid',label='不追',why='辅助估值超预先登记的否决阈值；只降级，不参与并列排序。');return out
    if value>high:out.update(status='avoid',label='不追',why='唯一主估值指标高于预先登记的价格上限。');return out
    if gate['status']!='yes' or quality['status']!='ready':return out
    if not pricing.get('secondary_review_complete') or any(v['bad'] is None for v in out['vetoes']):out['why']='辅助估值否决检查未完成，缺数据不能视作通过。';return out
    if value<=low and pricing.get('execution_confirmed') is True:
        out.update(status='pursue',label='追 · 价格门通过',why='主估值落在已核区间、辅助否决未触发，H执行条件已验证；组合D/G仍单独约束节奏。')
    else:out['why']='主估值尚未进入追的区间，或H执行条件未确认；保持兑现排名，等待时机。'
    return out


def rank_and_select(records,policy,reviews):
    # No global score. Different financial bases/currencies form incomparable cohorts.
    selected=[];conflicts=[]
    eligible=[r for r in records if r['gate']['status']=='yes' and r['quality']['status']=='ready']
    issuer_pools={}
    for r in eligible:issuer_pools.setdefault(r['issuer_id'],set()).add(r['pool_id'])
    for pool in policy['subpools']:
        items=[r for r in eligible if r['pool_id']==pool['id']]
        cohorts={tuple(r['quality']['comparison_key']) for r in items}
        if len(cohorts)>1:
            for r in items:r['quality'].update(rank=None,label='口径分组待统一')
            continue
        items.sort(key=lambda r:-r['quality']['value'])
        for r in items:r['quality']['rank']=1+sum(x['quality']['value']>r['quality']['value'] for x in items)
        shortlist=[]
        for r in items:
            assignment=reviews['issuers'].get(r['issuer_id'],{}).get('primary_subpool')
            if len(issuer_pools[r['issuer_id']])>1 and assignment!=pool['id']:
                conflicts.append(r['key']);continue
            if r['price']['status']=='avoid':continue
            if r['issuer_id'] not in {x['issuer_id'] for x in shortlist}:shortlist.append(r)
        cap=pool['slots']
        for i,r in enumerate(shortlist[:cap]):
            if len(shortlist)>cap and r['quality']['value']==shortlist[cap]['quality']['value']:continue
            if r['issuer_id'] not in {x['issuer_id'] for x in selected}:
                selected.append(r);r['shortlisted']=True
    assert len(selected)<=policy['convergence']['max_issuers']
    return selected,sorted(set(conflicts))


def archived_financials(root,code):
    p=Path(root)/'data/raw/stocks'/f'{code}.json'
    if not p.exists():return {}
    raw=json.loads(p.read_text());rows=sorted(raw.get('fin',[]),key=lambda x:x['REPORTDATE'])
    v=sorted(raw.get('val',[]),key=lambda x:x['TRADE_DATE'])
    if not rows:return {}
    now=rows[-1];prev=next((x for x in rows if x['REPORTDATE'][:4]==str(int(now['REPORTDATE'][:4])-1) and x['REPORTDATE'][4:10]==now['REPORTDATE'][4:10]),None)
    profit=now.get('PARENT_NETPROFIT');base=prev.get('PARENT_NETPROFIT') if prev else None
    return dict(period=now['REPORTDATE'][:10],notice=now['NOTICE_DATE'][:10],basis='合并累计报告值；接口留档，未经正常化审核，不进入排序',revenue=now.get('TOTAL_OPERATE_INCOME'),profit=profit,reported_profit_yoy=(profit/base-1)*100 if num(base) and base>0 and num(profit) else None,gross_margin=now.get('XSMLL'),cash_per_share=now.get('MGJYXJJE'),value_date=v[-1]['TRADE_DATE'][:10] if v else None,pb=v[-1].get('PB_MRQ') if v else None,price=v[-1].get('CLOSE_PRICE') if v else None,source='https://data.eastmoney.com/stockdata/'+code+'.html')


def prepare(root):
    policy=read(root,'stock_selection_policy.json');reviews=read(root,'stock_decision_reviews.json');validate(policy,reviews)
    original=read(root,'sector_research.json');old=read(root,'stocks.json')['stocks'];pools={p['id']:p for p in policy['subpools']}
    records=[];seen=set()
    for s in original['sectors']:
        for c in s['candidates']:
            key=s['market']+':'+c['code'];assert key not in seen,'Multiple reasons need explicit assignment: '+key
            seen.add(key);leader=next((x for x in s['stocks'] if x['code']==c['code']),None)
            records.append(dict(key=key,issuer_id=issuer_id(key),code=c['code'],name=c['name'],market=s['market'],pool_id=s['id'],legacy=False,business=c['segment'],hypothesis=c['logic'],verify=c['verify'],risk=c['risk'],source=original['sources'][c['source']],observation=leader.get('observation') if leader else None,leader=bool(leader)))
    for c in old:
        key='a:'+c['code']
        if key in seen:continue
        seen.add(key);records.append(dict(key=key,issuer_id=issuer_id(key),code=c['code'],name=c['name'],market='a',pool_id=None,legacy=True,business=c['industry'],hypothesis=c.get('customer_note',''),verify='先核对是否符合当前半年的理由合同。',risk='历史名单不自动进入新研究池。',source='https://data.eastmoney.com/stockdata/'+c['code']+'.html',observation=None,leader=False))
    # One canonical financial pack per issuer, shared by A/H listings.
    packs={}
    for r in records:
        iid=r['issuer_id']
        if iid not in packs:
            code=iid[3:] if iid.startswith('cn:') else r['code']
            packs[iid]={'review':reviews['issuers'].get(iid,{}).get('financial_pack',{}),'archive':archived_financials(root,code)}
    for r in records:
        p=pools.get(r['pool_id']);review=reviews['securities'].get(r['key'],{});pack=packs[r['issuer_id']]['review']
        r['gate']=gate_decision(p,review);r['quality']=quality_decision(p,pack,r['gate'])
        pricing=review.get('pricing',{})
        if pricing.get('reviewed') and pricing.get('financial_pack_id')!=pack.get('id'):
            pricing={}  # Never mix valuation denominator from another financial pack.
        r['price']=price_decision(p,pricing,r['gate'],r['quality'],policy['as_of']);r['shortlisted']=False
    selected,conflicts=rank_and_select(records,policy,reviews)
    return dict(policy=policy,reviews=reviews,packs=packs,records=records,selected=selected,conflicts=conflicts)


def roles(policy):
    out='<details class="sd-roles"><summary>A–H职能标签与去重规则</summary><p>'+E(policy['evidence_rule'])+'</p><div class="sd-table-wrap"><table class="sd-table"><thead><tr><th>节点</th><th>唯一职能</th><th>使用规则</th></tr></thead><tbody>'
    for x in policy['node_roles']:out+='<tr><th>'+x['node']+'</th><td>'+E(x['role'])+'</td><td>'+E(x['text'])+'</td></tr>'
    return out+'</tbody></table></div><p>'+E(policy['logic2'])+'</p></details>'


def nav():return '<nav class="sd-nav"><a href="index.html">← 个股筛选</a><details><summary>规则与组合约束</summary><a href="portfolio.html">D/G详情</a><a href="selection-rules.html">筛选规则</a></details></nav>'
def top(title,subtitle):return '<div class="stock-decisions">'+nav()+'<div class="hero"><h1>'+E(title)+'</h1><p class="sum">'+E(subtitle)+'</p></div>'
def end():return '</div>'
def badge(s):return '<span class="sd-badge">'+E(s)+'</span>'
def flow():return '<div class="sd-flow"><div><b>01 · 赛道归属</b><span>A/B/C 入池门：是 / 否</span></div><i>→</i><div><b>02 · 兑现质量</b><span>C→E：同理由、同口径排序</span></div><i>→</i><div><b>03 · 价格反映</b><span>F主指标 / H验证：追 / 等 / 不追</span></div></div><p class="sd-note">D/G已移至<a href="portfolio.html">组合层</a>。同一数据不在多节点重复加权；个股不再有A–H总分。</p>'
def source_link(r):return '<a href="'+E(r['source'],quote=True)+'">原始资料 / 核验入口</a>'

def table(records,model):
    poolmap={p['id']:p for p in model['policy']['subpools']}
    out='<div class="sd-table-wrap"><table class="sd-table sd-comp"><thead><tr><th>公司 / 唯一理由</th><th>赛道归属 · 入池门</th><th>兑现质量 · 排序</th><th>价格反映 · 时机</th></tr></thead><tbody>'
    for r in records:
        p=poolmap.get(r['pool_id']);q=r['quality'];ar=model['packs'][r['issuer_id']]['archive']
        out+='<tr><th><a href="'+r['code']+'.html">'+E(r['name'])+'</a><small>'+('A股' if r['market']=='a' else '港股')+' '+r['code']+'</small><p>'+E(p['reason'] if p else '历史记录 · 未匹配')+'</p></th><td>'+badge(r['gate']['label'])+'<p>'+E(r['verify'])+'</p></td><td>'+badge(('池内第'+str(q['rank'])+'位') if q['rank'] else q['label'])+'<p>'+E(p['primary_rank_label'] if p else '不进入当前排序')+'：'+fmt(q['value'],'%')+'</p>'
        if ar:out+='<small>留档 '+ar['period']+' 累计归母利润 '+fmt(ar['profit']/1e8 if num(ar['profit']) else None,'亿元')+'；未正常化，不作排名。</small>'
        out+='</td><td>'+badge(r['price']['label'])+'<p>主指标：'+E(p['primary_valuation'] if p else '未指定')+' '+fmt(r['price']['main_value'],'倍')+'</p><small>'+E(r['price']['why'])+'</small></td></tr>'
    return out+'</tbody></table></div>'


def index(model):
    p=model['policy'];records=model['records'];out=top('个股筛选 · 三个决策','先确定接受哪一种理由，再比较兑现质量，最后判断当前价格。候选记录不等于已入池或已选定。')+flow()
    out+='<p class="sd-summary-line">候选资料 '+str(len([r for r in records if not r['legacy']]))+' 条 · 新入池门通过 '+str(sum(r['gate']['status']=='yes' for r in records))+' 条 · 研究短名单 '+str(len(model['selected']))+' / 10 家。原候选保留，未经新规则审核不自动入选。</p>'
    out+='<details class="sd-panel"><summary>如何收敛到10家：同理由排序，少于10家不凑数</summary><p>'+E(p['convergence']['description'])+'</p><ol>'+''.join('<li>'+E(x)+'</li>' for x in p['convergence']['rules'])+'</ol><a href="selection-rules.html#seats">查看子池规则与席位 →</a></details>'
    if model['selected']:out+='<section class="sd-panel"><h2>当前研究短名单 · 按子池展示</h2>'+table(model['selected'],model)+'</section>'
    for market,label in [('a','A股'),('hk','港股')]:
        out+='<section><h2>'+label+' · 选择一个理由子池</h2><div class="sd-table-wrap"><table class="sd-table"><thead><tr><th>方向</th><th>本半年接受的理由</th><th>唯一主排序 / 主估值</th><th>候选 / 研究席位</th></tr></thead><tbody>'
        for pool in p['subpools']:
            if pool['market']!=market:continue
            subset=[r for r in records if r['pool_id']==pool['id']]
            out+='<tr><th><a href="pool-'+pool['id']+'.html">'+E(pool['title'])+'</a></th><td>'+E(pool['reason'])+'</td><td>'+E(pool['primary_rank_label'])+'<small>主估值：'+E(pool['primary_valuation'])+'</small></td><td>'+str(len(subset))+' 条 / '+str(pool['slots'])+' 席</td></tr>'
        out+='</tbody></table></div></section>'
    legacy=[r for r in records if r['legacy']]
    if legacy:out+='<details class="sd-panel"><summary>历史资料 · 未匹配当前理由（'+str(len(legacy))+'条）</summary>'+table(legacy,model)+'</details>'
    return out+roles(p)+end()


def pool_page(model,pool):
    records=[r for r in model['records'] if r['pool_id']==pool['id']]
    out=top(pool['title']+' · '+pool['reason'],'只在本理由子池内比较，不与其他理由合并排序。')+flow()
    out+='<section class="sd-panel"><h2>这个半年只接受哪一类理由</h2><p class="sd-lead">'+E(pool['admission'])+'</p><div class="sd-contract"><p><b>主排序理由</b><br>'+E(pool['reason'])+' → '+E(pool['primary_rank_label'])+'</p><p><b>统一财务口径</b><br>'+E(pool['financial_basis'])+'</p><p><b>唯一主估值</b><br>'+E(pool['primary_valuation'])+' · '+E(pool['valuation_note'])+'</p></div><p>研究席位上限 '+str(pool['slots'])+'；'+('当前为观察方向，核验记录保留，未分配短名单席位。' if pool['slots']==0 else '只有入池与兑现通过的公司参与席位比较。')+' <a href="../boards/'+pool['id']+'.html">返回板块依据 →</a></p></section>'
    eligible=[r for r in records if r['gate']['status']=='yes'];pending=[r for r in records if r['gate']['status']!='yes']
    out+='<section id="candidates"><h2>已入池 · 同口径排序</h2>'+(table(eligible,model) if eligible else '<p class="sd-note">尚无经过新入池合同审核的记录；以下保留原候选及资料，不把历史映射当作已通过。</p>')+'</section>'
    out+='<section><h2>待核与未通过 · 不参与排名</h2>'+table(pending,model)+'</section>'
    out+='<details class="sd-panel" id="leaders"><summary>龙头观察资料 · 不提供额外分数</summary>'
    for r in records:
        if not r['leader']:continue
        ob=r['observation'] or {}
        out+='<p><b><a href="'+r['code']+'.html">'+E(r['name'])+'</a></b>：'+E(ob.get('text',r['business']))+' <small>'+E(ob.get('date','资料日期待核'))+'</small> '+source_link(r)+'</p>'
    return out+'</details>'+roles(model['policy'])+end()


def detail(model,r):
    policy=model['policy'];pool=next((x for x in policy['subpools'] if x['id']==r['pool_id']),None);review=model['reviews']['securities'].get(r['key'],{});pack=model['packs'][r['issuer_id']];q=r['quality'];price=r['price'];archive=pack['archive']
    out=top(r['name']+' · '+r['code'],('A股' if r['market']=='a' else '港股')+'｜同一公司一套财务口径；同一证券一个主排序理由。')+flow()
    out+='<div class="sd-three"><a href="#admission"><b>赛道归属</b>'+badge(r['gate']['label'])+'</a><a href="#quality"><b>兑现质量</b>'+badge('池内第'+str(q['rank'])+'位' if q['rank'] else q['label'])+'</a><a href="#timing"><b>价格反映</b>'+badge(price['label'])+'</a></div>'
    out+='<section class="sd-panel" id="admission"><h2>1．赛道归属 · A/B/C只做入池门</h2><p><b>本半年接受的唯一理由：</b>'+E(pool['reason'] if pool else '尚未匹配当前方向')+'</p><p>'+E(pool['admission'] if pool else r['gate']['why'])+'</p><p><b>已有业务映射：</b>'+E(r['business'])+' '+source_link(r)+'</p><p><b>原研究假设：</b>'+E(r['hypothesis'])+'</p><div class="sd-contract">'
    for k,label in [('A','需求是否落到本公司业务'),('B','政策/准入是否适用且不存在排除'),('C','订单或商业化业务是否有事实')]:
        g=review.get('gate',{}).get(k,{})
        out+='<div><b>'+k+' · '+label+'</b><p>'+E({'yes':'是','no':'否','pending':'待核'}.get(g.get('status'),'待核'))+'</p><small>'+E(g.get('note','需核正文、日期及事实；资料入口不等于审核完成。'))+'</small></div>'
    out+='</div><p>'+E(r['gate']['why'])+'</p></section>'
    out+='<section class="sd-panel" id="quality"><h2>2．兑现质量 · C→E决定池内顺序</h2><p><b>唯一主排序指标：</b>'+E(pool['primary_rank_label'] if pool else '先指定理由')+' '+fmt(q['value'],'%')+'</p><p>'+E(q['why'])+'</p><p><b>口径合同：</b>'+E(pool['financial_basis'] if pool else '尚未指定')+'</p><p class="sd-note">利润、现金、毛利、应收及库存全部属于这一财务包。C入池只证明业务存在，不重复用收入/利润增速给A、C、E加分。正基数与扭亏分开；固定2027盈利修订只验证或降级，不再加一遍分。</p>'
    reviewed=pack['review']
    if reviewed:out+='<p><b>财务包：</b>'+E(str(reviewed.get('id','待编号')))+' · '+E(str(reviewed.get('period','待核')))+'</p>'
    if q['checks']:
        out+='<ul>'+''.join('<li>'+E(x['name'])+'：'+fmt(x['value'])+'；否决阈值 '+E(x['op'])+' '+fmt(x['limit'])+'；'+('触发' if x['bad'] else '未触发')+'。'+E(x['rationale'])+'</li>' for x in q['checks'])+'</ul>'
    if archive:
        out+='<details class="sd-archive"><summary>已有财务留档 · 尚未正常化，不混入排名</summary><p>'+E(archive['basis'])+'；报告期 '+archive['period']+'，披露 '+archive['notice']+'。</p><div class="sd-contract"><p>累计营业收入<br><b>'+fmt(archive['revenue']/1e8 if num(archive['revenue']) else None,'亿元')+'</b></p><p>累计归母净利润<br><b>'+fmt(archive['profit']/1e8 if num(archive['profit']) else None,'亿元')+'</b></p><p>累计毛利率<br><b>'+fmt(archive['gross_margin'],'%')+'</b></p></div><p>每股经营现金流 '+fmt(archive['cash_per_share'],'元')+'；未用每股现金流÷EPS冒充现金/利润总额比。缺少应收、库存和正常化调整时，不能自动认定兑现质量通过。</p></details>'
    else:out+='<p class="sd-note">目前只有业务/资料线索，尚无可供比较的完整财务包；不从行业总量或其他公司填补。</p>'
    out+='</section><section class="sd-panel" id="timing"><h2>3．价格反映 · F主估值，H只验证执行</h2><p class="sd-lead">'+badge(price['label'])+' '+E(price['why'])+'</p><div class="sd-contract"><p><b>唯一主指标</b><br>'+E(pool['primary_valuation'] if pool else '未指定')+' '+fmt(price['main_value'],'倍')+'</p><p><b>追 / 等 / 不追区间</b><br>'+E(('追≤'+str(review['pricing']['pursue_max'])+'；不追>'+str(review['pricing']['avoid_above'])) if num(price['main_value']) else '待登记主指标区间、来源和有效日期')+'</p><p><b>H执行验证</b><br>'+('已确认' if review.get('pricing',{}).get('execution_confirmed') else '待验证；价格上涨不增加兑现排名')+'</p></div>'
    if archive and pool and pool['primary_valuation']=='PB':out+='<p>历史PB留档 '+fmt(archive['pb'],'倍')+'，日期 '+E(str(archive['value_date']))+'；仅是旧截面，未完成区间标定，不据此给目标价。</p>'
    else:out+='<p>不以报告PE替代正常化PE，也不把PB、PS、PE并排选最低的一项；缺主指标时保持“等”，不据此给目标价。</p>'
    out+='<details><summary>辅助估值 · 只作否决条件</summary><p>'+E(policy['valuation']['rule_note'])+'</p>'
    for v in price['vetoes']:out+='<p>'+E(v['metric'])+'：'+fmt(v.get('value'))+'；阈值 '+E(v.get('op',''))+' '+fmt(v.get('limit'))+' · '+('触发' if v['bad'] else '未触发' if v['bad'] is False else '缺数据')+'</p>'
    if not price['vetoes']:out+='<p>尚未完成辅助估值检查。未记录不能当作“没有否决”。</p>'
    out+='</details></section><section class="sd-panel"><h2>下一步只补会改变决策的证据</h2><p><b>入池待核：</b>'+E(r['verify'])+'</p><p><b>退回条件：</b>'+E(r['risk'])+'</p><p><a href="portfolio.html">D/G组合约束 →</a>　利率、资金和拥挤度不在本页加减分。</p></section>'
    if r['observation']:out+='<details class="sd-panel"><summary>已有龙头观察资料（不是额外排序理由）</summary><p>'+E(r['observation']['date']+'：'+r['observation']['text'])+' '+source_link(r)+'</p></details>'
    return out+roles(policy)+end()


def rules_page(model):
    p=model['policy'];out=top('个股筛选规则','职能分离、一个理由、一套口径、一个主估值。规则更新 '+p['as_of'])+flow()+roles(p)
    out+='<section class="sd-panel" id="seats"><h2>子池合同与研究席位</h2><p>'+E(p['convergence']['description'])+'</p><p>这是首版研究容量设置，可在研究源中调整；不是已选名单或资金配置。不同理由新增独立子池，不给原公司叠加第二个主排序理由。</p><div class="sd-table-wrap"><table class="sd-table"><thead><tr><th>子池</th><th>只接受的理由</th><th>唯一主排序</th><th>唯一主估值</th><th>席位</th></tr></thead><tbody>'
    for pool in p['subpools']:out+='<tr><th><a href="pool-'+pool['id']+'.html">'+E(pool['title'])+'</a></th><td>'+E(pool['reason'])+'</td><td>'+E(pool['primary_rank_label'])+'</td><td>'+E(pool['primary_valuation'])+'</td><td>'+str(pool['slots'])+'</td></tr>'
    out+='</tbody></table></div><ol>'+''.join('<li>'+E(x)+'</li>' for x in p['convergence']['rules'])+'</ol></section><section class="sd-panel"><h2>质量与价格：否决不能被加分抵消</h2><p>现金覆盖、毛利、应收和库存的阈值，必须在同一财务包登记指标值、阈值、比较方向和依据；未填阈值或缺指标时不进入自动排名。不统一套用任意行业阈值。E仅在同机构、固定2027目标年的序列可用时参与降级。</p><p>'+E(p['valuation']['bands_note'])+'</p><p>'+E(p['valuation']['rule_note'])+'</p><p>“低估值修复”若另行研究，应单独建池，写明价值如何兑现及其主财务排序指标；不得把低PB拿到需求兑现池中与订单清晰竞争。</p></section>'
    return out+'<p><a href="../data/stock_decisions.json">下载结构化规则与决策结果</a></p>'+end()


def portfolio(root,model):
    d=read(root,'market_thesis.json');out=top('组合层 · D/G约束','利率与资金只影响整体仓位和执行节奏，不改变个股入池、兑现排名或主估值。')
    out+='<section class="sd-panel"><h2>使用顺序</h2><p>先得到各子池的研究短名单，再检查利率、市场流动性、拥挤度与共同风险。当前没有获授权的目标仓位或个股配置，本页不推算比例；不把市场约束平均拆成每只股票的扣分。</p><p>即使F标为“追”，也只表示价格门通过；组合约束可以要求延后执行，但不能把低质量公司改成高优先级。</p></section><div class="sd-pools">'
    for market,m in d['markets'].items():
        out+='<article class="sd-panel"><h2>'+m['label']+' · 组合环境</h2><p class="sd-note">研究复核 '+d['as_of']+'；各原始数据日期见大盘资料。</p>'
        for k in 'DG':
            n=next(n for n in m['nodes'] if n['key']==k)
            out+='<h3>'+k+' · '+E(n['title'])+'</h3><p>'+E(n['note'])+'</p><p>'+E(n['judgment'])+'</p>'
        out+='<p><b>当前节奏：</b>'+E(m['macro_overview']['constraint']['title'])+'。'+E(m['macro_overview']['constraint']['text'])+'</p><a href="'+('../index.html' if market=='a' else '../hk/index.html')+'#thesis-D">查看市场证据与来源 →</a></article>'
    out+='</div><section class="sd-panel"><h2>集中度与容量</h2><p>最多10家发行人；同一公司A/H经营证据共用，不能算两个独立风险。另检查不同子池是否共同暴露于AI资本开支、油价或同一政策；共同标签仅作组合风险提示，不回流到个股分数。</p><p>研究席位不是仓位权重，未用席位不强制补满。涉及同一发行人跨池时，须明确唯一主子池后才能占用席位。</p></section>'
    return out+end()


def build(ctx):
    root=Path(ctx['ROOT']);model=prepare(root);out=Path(ctx['SITE'])/'stocks';out.mkdir(exist_ok=True)
    def write(name,title,body):(out/name).write_text(ctx['page'](title+' | 个股研究','gg',body,'../'))
    write('index.html','个股三维筛选',index(model));write('sector-pools.html','理由子池',index(model))
    write('portfolio.html','D/G组合约束',portfolio(root,model));write('selection-rules.html','筛选规则',rules_page(model))
    for p in model['policy']['subpools']:write('pool-'+p['id']+'.html',p['title'],pool_page(model,p))
    for r in model['records']:write(r['code']+'.html',r['name'],detail(model,r))
    public={'policy':model['policy'],'records':model['records'],'financial_packs':model['packs'],'selected':[r['key'] for r in model['selected']],'issuer_conflicts':model['conflicts']}
    (Path(ctx['SITE'])/'data/stock_decisions.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
    return model['records']
