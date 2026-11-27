"""Single issuer shortlist after macro sustainability and sector comparison. No scoring."""
import json,re
from pathlib import Path
from html import escape as E
import stockcards as SC
import stockpick as SP
import logic1_rules as LR
import hk_pick as HK

def load(root):
    root=Path(root);d=json.loads((root/'data/research_shortlist.json').read_text());s=json.loads((root/'data/sector_selection.json').read_text());sec={x['id']:x for x in s['sectors']}
    validate(d,sec)
    return d,sec

def validate(d,sec):
    xs=d['companies'];ids=[x['issuer_id'] for x in xs]
    if d['max_issuers']!=10 or len(xs)>10 or len(ids)!=len(set(ids)):raise ValueError('Shortlist must contain at most 10 unique issuers')
    codes=[v for x in xs for v in [x['code'],x.get('refcode')] if v]
    if len(codes)!=len(set(codes)):raise ValueError('A/H aliases must belong to one issuer only')
    choices={x['sector_id']:x for x in d['sector_decisions']}
    if len(choices)!=len(d['sector_decisions']) or set(choices)!=set(sec):raise ValueError('Every researched sector needs an explicit keep or defer decision')
    for x in xs:
        parent=sec[x['sector_id']]
        if parent['market']!=x['market'] or parent['rating'] not in ('顺风','前半段') or choices[x['sector_id']]['status']!='重点':raise ValueError('Review shortlist after parent sector changes: '+x['name'])
        for sid in x.get('related_sectors',[]):
            if sid not in sec or choices[sid]['status']!='重点':raise ValueError('Invalid related sector: '+sid)
        for key in ['reason','why_selected','peer_decision','trigger','drop','sections']:
            if not x.get(key):raise ValueError('Missing shortlist rationale: '+key)

def links(d,keys):
    return '<p class="src">'+ ' · '.join('<a href="'+E(d['sources'][k]['url'],quote=True)+'">'+E(d['sources'][k]['title'])+'</a>' for k in keys)+'</p>'

def nav(market=None):
    return '<nav class="lp-mkt"><a href="index.html"'+(' aria-current="page"' if market is None else '')+'><b>两市重点名单</b><span>A/H同公司合并，合计最多10家</span></a><a href="hk.html"'+(' aria-current="page"' if market=='hk' else '')+'><b>港股视图</b><span>同一名单，独立检验港股价格与资金</span></a></nav>'

def sustain(root,market,prefix='../'):
    d,_=load(root);x=d['market_sustainability'][market]
    return '<section class="mp-upstream" id="sustainability"><h2>先验收可持续性，再分配研究精力</h2><p><b>'+E(x['conclusion'])+'</b></p><div class="mp-grid">'+''.join('<article><b>'+name+'</b><p>'+E(x[key])+'</p></article>' for key,name in [('policy','政策力度'),('duration','持续多久、依赖什么'),('next','下一次验收')])+'</div><p><a href="'+prefix+'stocks/index.html">查看两市最多10家的收敛结果 →</a></p></section>'

def plans(root,x):
    root=Path(root)
    if x['market']=='a':
        en=json.loads((root/'data/raw/stock_pick/l1_enrich.json').read_text())[x['code']]
        return LR.price_levels('upstream',{'en':en})
    d=HK.load(root);row=next(z for z in HK.rows(d) if z['code']==x['code'])
    if x['issuer_id']=='icbc':
        import dividend
        L=dividend.load(root,'hk_dividend.json');c=next(z for z in L['cand'] if z[0]==x['code']);return dividend.levels(L,c)
    return HK.hk_levels('upstream',row,HK.load_trend(root))

def action(root,x):
    t=json.loads((Path(root)/'data/market_thesis.json').read_text())['macro_regime']['markets']
    if x['market']=='a' and t['a'].get('defense',{}).get('on'):return '暂停新增：A股恢复条件未完成'
    # Explicit reviewed decision; do not infer recovery from a single quote or stale prose.
    return '等待：港股恢复与公司价格条件' if x['market']=='hk' else '等待：复核兑现与价格条件'

def card(root,d,s,x):
    p=plans(root,x);v=action(root,x)
    steps=[('赛道','通过',x['reason']),('兑现','支撑',x['why_selected']),('价格','等待',x['trigger'])]
    chain=SP.chain_html({'steps':steps}).replace('<dl class="ch-d"></dl>','<dl class="ch-d">'+''.join('<div><dt>'+E(a)+'</dt><dd>'+E(tx)+'</dd></div>' for a,_,tx in steps)+'</dl>')
    layers=[('同业取舍','中',E(x['peer_decision']),{'中':'比较'})]
    out=SC.card('s-'+x['code'],x['name'],('A股 · ' if x['market']=='a' else '港股 · ')+x['code']+' · '+s[x['sector_id']]['title'],v,'wait',p,layers,bar_html=SC.bar(None,None,p['buy'],p['sell'],p.get('stop'),p['close']),note=x['thesis'],chain=chain).replace('<em>买入</em>','<em>参考入场</em>').replace('<span>卖出 ','<span>参考上沿 ').replace('<span>买入 ','<span>参考下沿 ')
    if x['market']=='hk':
        out=out.replace('现价 <b>'+SC.money(p['close'])+'</b>','现价 <b>'+format(p['close'],'.3f')+'</b>')
    if p.get('trend') is False:
        out=out.replace('<em>止损</em>','<em>入场后失效线</em>').replace('<span>止损 ','<span>条件失效线 ')
    link='<p class="short-deep"><a href="research-'+x['issuer_id']+'.html">深入研究：业务、财务、估值与行动条件 →</a></p>'
    return out[:-10]+link+'</article>'

def library():
    return '<details class="more" id="library"><summary>历史覆盖与其他方法（不属于当前重点名单）</summary><p class="note">旧资料保留追溯，未选中的公司不再出现在主名单。</p><p>'+ ' · '.join('<a href="'+f+'">'+name+'</a>' for f,name in [('coverage-a.html','A股原覆盖'),('coverage-hk.html','港股原覆盖'),('a-turn.html','财报反转'),('hk-turn.html','预期反转'),('dividend.html','A股红利'),('hk-dividend.html','港股红利'),('box.html','国资箱体'),('hk-event.html','回购与事件'),('logic-map.html','方法资料')])+'</p></details>'

def index(root,market=None):
    import market_path
    d,s=load(root);xs=[x for x in d['companies'] if market is None or x['market']==market]
    out='<style>'+SP.CSS+SC.CSS+market_path.CSS+CSS+'</style>'+nav(market)+'<div class="hero"><h1>重点个股 · '+('两市共' if market is None else '港股')+str(len(xs))+'家</h1><p class="sum">'+E(d['conclusion'])+'</p><p class="hero-meta">研究更新 '+d['as_of']+' · '+E(d['limit_note'])+'</p></div>'
    out+='<nav class="lp-jump"><a href="#overview">当前行动</a><a href="#derivation">推导与淘汰</a><a href="#logic1">重点公司</a><a href="#library">历史资料</a></nav>'
    out+='<section id="overview"><h2>当前行动：暂停或等待，新增为0</h2><p>研究席位用于确定下一步精力；买入仍须市场恢复、公司兑现与价格同时满足。当前不分配新增仓位，既有持仓按原组合规则处理。</p><div class="sec-lens">'
    out+='<div><b>先看大盘</b><a href="../index.html#horizon">A股完整分析</a> · <a href="../hk/index.html#horizon">港股完整分析</a></div><div><b>再看行业持续性</b><a href="../boards/index.html">A股板块比较</a> · <a href="../boards/hk.html">港股板块比较</a></div><div><b>最后深研公司</b>'+str(len(d['companies']))+'家 / 上限10家；不靠涨幅或混合总分填满</div></div></section>'
    out+='<section id="derivation"><h2>为什么只留下这些公司</h2><p>大盘 → 可持续性 → 板块比较 → 同业取舍 → 重点研究。不同投资理由分别验收，不做跨理由总排名。</p><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>重点公司</th><th>承接的行业理由</th><th>为什么保留、为什么不继续扩名单</th></tr></thead><tbody>'
    for x in xs:out+='<tr><th><a href="#s-'+x['code']+'">'+E(x['name'])+'</a></th><td><a href="../boards/'+x['sector_id']+'.html">'+E(x['reason'])+'</a></td><td>'+E(x['peer_decision'])+'</td></tr>'
    out+='</tbody></table></div></section><section id="logic1"><h2>深入研究的公司</h2>'
    for m,name in [('a','A股'),('hk','港股')]:
        rows=[x for x in xs if x['market']==m]
        if rows:out+='<h3>'+name+'</h3><div class="sc-grid">'+''.join(card(root,d,s,x) for x in rows)+'</div>'
    out+='</section><section id="weekly"><h2>本次收敛</h2><p>撤下主页面中的广泛初筛名单；保留'+str(len(d['companies']))+'家发行人，每家有同业取舍、失效条件与下次验收。工商银行股息重算已去除期间叠加和币种混用。经营现金／利润只核验现金质量，不再作为投资优先级的替代。</p></section>'
    out+=library()+'<details class="more" id="price-rules"><summary>原价格纪律与节点职责</summary><p>赛道归属：A/B/C只判入池；兑现质量：C→E检验主命题；价格反映：F唯一主估值，H验证时机。D/G在组合层，现金比率不等同未来半年回报。</p><a href="selection-rules.html">规则与数据口径</a> · <a href="portfolio.html">组合约束</a></details>'
    return out

def dossier(root,x):
    d,s=load(root);v=action(root,x);out='<style>'+SP.CSS+SC.CSS+CSS+'</style>'+nav(x['market'])+'<div class="crumb"><a href="index.html">最多10家重点名单</a> ／ '+E(x['name'])+'</div><div class="hero"><h1>'+E(x['name'])+' · 深入研究</h1><p class="sum">'+E(x['thesis'])+'</p><p class="hero-meta">'+E(x['code'])+' · '+('人民币' if x['market']=='a' else '港元')+' · 报价2026-11-27 · 财务2026Q3；TTM单列 · 更新'+d['as_of']+'</p></div>'
    out+='<section class="plan"><h2>'+E(v)+'</h2><p><b>主理由：</b>'+E(x['reason'])+'</p><p><b>上游来源：</b><a href="../'+('index.html' if x['market']=='a' else 'hk/index.html')+'#horizon">本市场大盘</a> → <a href="../boards/'+x['sector_id']+'.html">'+E(s[x['sector_id']]['title'])+'</a> → 本公司</p><p><b>当前新增仓位：</b>0；研究名单不等于同时买入名单。</p></section>'
    out+='<div class="sc-grid">'+card(root,d,s,x)+'<article class="short-compare"><h2>为什么选它而暂不选同业</h2><p>'+E(x['why_selected'])+'</p><p>'+E(x['peer_decision'])+'</p><p><b>下一次验收：</b>'+E(x['trigger'])+'</p></article></div>'
    for part in x['sections']:out+='<section class="short-section"><h2>'+E(part['title'])+'</h2><p>'+E(part['text'])+'</p>'+links(d,part['refs'])+'</section>'
    out+='<section class="lp-two"><article><h2>什么条件才进入行动</h2><p>'+E(x['trigger'])+'</p><p>下一次检查：'+x['review_by']+'；经营兑现随最新公司披露复核。</p></article><article><h2>什么情况下移出重点</h2><p>'+E(x['drop'])+'</p><ul>'+''.join('<li>'+E(t)+'</li>' for t in x['risks'])+'</ul></article></section><p class="note">仅供研究参考，不构成投资建议。市场有风险，交易需谨慎。</p>'
    return out


def rules(root):
    d,_=load(root)
    out='<style>'+SP.CSS+SC.CSS+'</style>'+nav()+'<div class="hero"><h1>筛选规则（当前生效）</h1><p class="sum">大盘 → 可持续性 → 板块 → 同业取舍 → 最多10家深研。每一层都要缩小范围，并写出淘汰理由。</p></div>'
    rows=[('大盘','A股、港股各自判断半年盈利、折现条件与市场约束。','只形成行业需要回答的问题，不直接贴股票名单。'),('可持续性','明确驱动力来自存量经营、政策实际投放还是短期事件，并标出持续时间。','只有一个季度可见度的业务不能外推整个半年。'),('板块','比较经营兑现、唯一主估值与价格反映，给出重点或暂不展开。','不因有标签或龙头就分配个股席位。'),('个股','同理由、同报告期比较业务匹配与兑现质量，说明选它而暂不选同业的原因。','不按现金／利润单指标机械排名，不做跨理由综合总分。'),('深研','业务、财务、现金、估值、风险、行动和失效条件逐项展开。','A/H同发行人计1家，两市总数≤10；没有足够证据可以少于10。')]
    out+='<section><h2>每一步必须交付什么</h2><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>步骤</th><th>输出</th><th>收敛规则</th></tr></thead><tbody>'+''.join('<tr><th>'+a+'</th><td>'+b+'</td><td>'+c+'</td></tr>' for a,b,c in rows)+'</tbody></table></div></section>'
    out+='<section id="layers"><h2>三个决策维度与组合约束</h2><ul><li><b>赛道归属 · A/B/C：</b>只判是否入池；业务与本窗口主理由不匹配则剔除，不给政策或需求重复加分。</li><li><b>兑现质量 · C→E：</b>同一公司统一财务口径；比较主命题的持续兑现，现金、毛利、应收库存用来解释和否决。不同理由不合并排名。</li><li><b>价格反映 · F/H：</b>每个方向只用一个主估值；周期用PB，银行现金回报用税后股息率，成长用正常化PE。辅助指标只作否决，H验证价格条件。</li><li><b>组合约束 · D/G：</b>利率、资金与市场恢复约束新增节奏和总风险，不对个股重复加减分。能源三家视作相关周期暴露。</li></ul></section>'
    out+='<section id="views"><h2>当前行动与换席</h2><p>暂停新增：大盘恢复条件未完成。等待：公司已进入研究，但价格、趋势或经营验收尚未同时满足。条件满足：必须在新的资料复核后明确更新，不由单日价格自动生成买入指令。移出：主理由失效或同业出现更有力的替代证据。</p><p>本次研究名单为'+str(len(d['companies']))+'家，当前新增为0。达到10家后新增必须换席；少于10家也须证明新增研究价值。每次更新先复核上游，不自动恢复历史初筛名单。</p></section>'
    out+='<section id="data"><h2>价格与财务口径</h2><p>卡片保留原版价格计划与位置展示，参考区间属于既有交易纪律，参考上沿不是未来价格预测。进入区间仍需市场、经营和估值验收；当前价格盈亏比与区间中点盈亏比分开。</p><p>累计、单季和TTM分别标注；经营现金减购建长期资产现金仅为采用口径的自由现金流近似。银行看资本、资产质量和每股派息，不套工业现金流模型。港股财务人民币口径先换算，再计算估值；股息不重复叠加期间，按最新末期＋中期方案和明确税率、汇率计算参考回报。</p></section><details class="more"><summary>历史价格模型与覆盖资料</summary><p>原初筛及回测保留在历史页，仅作追溯；未逐股重核的分红、财务币种和旧价格不作为当前行动依据。</p><a href="coverage-a.html#price-rules">A股原价格模型</a> · <a href="coverage-hk.html">港股原价格模型</a></details>'
    return out

def archive(html):
    if 'data-shortlist-archive' in html:return html
    notice='<div class="hero" data-shortlist-archive="true"><h1>历史覆盖资料</h1><p class="sum">此页不再作为当前候选或执行依据；旧样本、回测和记录仅供追溯。未逐股重核的分红、财务币种与价格计划不得直接用于当前决策。</p><p><a href="index.html">返回两市最多10家的重点名单 →</a></p></div><details class="more" id="archived-coverage"><summary>展开历史覆盖（不是当前推荐）</summary>'
    return html.replace('<main class="wrap">','<main class="wrap">'+notice,1).replace('</main>','</details></main>',1)

def build(ctx):
    root=Path(ctx['ROOT']);site=Path(ctx['SITE']);d,s=load(root);out=site/'stocks';page=ctx['page']
    for src,dst in [('index.html','coverage-a.html'),('hk.html','coverage-hk.html')]:
        (out/dst).write_text(archive((out/src).read_text()))
    primary={'index.html','hk.html','selection-rules.html','portfolio.html'}|{'research-'+x['issuer_id']+'.html' for x in d['companies']}
    for p in out.glob('*.html'):
        if p.name not in primary:p.write_text(archive(p.read_text()))
    (out/'selection-rules.html').write_text(page('筛选规则 | A股框架笔记','gg',rules(root),'../'))
    for market,fn in [(None,'index.html'),('hk','hk.html')]:
        (out/fn).write_text(page('重点个股 | A股框架笔记','gg',index(root,market),'../'))
    for x in d['companies']:(out/('research-'+x['issuer_id']+'.html')).write_text(page(x['name']+' | 深入研究','gg',dossier(root,x),'../'))
    (site/'data/research-shortlist.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

CSS='''.short-compare{background:#fff;border:1px solid #dfe6ee;border-radius:12px;padding:18px 22px;align-self:stretch}.short-compare h2{font-size:20px;margin-top:0}.short-compare p{font-size:14px;line-height:1.9}.short-section{margin:28px 0}.short-section p{line-height:1.95}.short-deep{margin:14px 0 0;border-top:1px solid #e4eaf0;padding-top:10px;font-size:14px}.short-section .src{font-size:12px}.sc-dim{opacity:1}.lp-two ul{font-size:14px;line-height:1.8}'''
