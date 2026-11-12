"""行业与个股分离：行业页面只读取industry_research，股票池独立读取sector_research。"""
import html
import json
from pathlib import Path

E = html.escape
NAMES = dict(zip('ABCDEFGH', ['需求', '政策与地缘', '行业利润与现金流', '利率与风险溢价', '盈利预期修订', '估值', '资金与拥挤度', '价格验证']))
STYLE = '''<style>#conclusion,#framework,#leaders,#candidates,.sector-node[id]{scroll-margin-top:110px}.sector-diagram-scroll{overflow-x:auto;max-width:100%;border:1px solid #d9dfe7;background:#fff;border-radius:12px;padding:10px;margin:16px 0}.sector-diagram{display:block;width:100%;min-width:860px;height:auto}.sector-card:has(details[open]){grid-column:1 / -1}.sector-preview{padding:12px 14px;background:#f1f5fa;border-radius:8px;line-height:1.8;font-size:14px}.sector-card summary{cursor:pointer;color:#24476b;font-weight:600;padding:12px 0}.sector-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.sector-card{border:1px solid #d9dfe7;border-radius:12px;padding:22px;background:#fff}.sector-card h3{margin:0 0 12px}.sector-card p{line-height:1.8}.sector-card .stocks{font-size:14px;color:#526072}.conclusion-body{border:1px solid #d9dfe7;border-radius:12px;background:#fff;padding:24px;margin:22px 0}.conclusion-body h3{font-size:19px;margin:22px 0 10px}.conclusion-body p{font-size:16px;line-height:1.95;margin:12px 0}.conclusion-body .conclusion-base{font-size:18px;font-weight:600}.sector-verdict{border-left:4px solid #263a50;background:#f5f7fa;padding:20px 24px;font-size:19px;line-height:1.8}.sector-nodes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.sector-node{background:#fff;border:1px solid #d9dfe7;border-radius:10px;padding:20px}.sector-node table{font-size:14px}.sector-node .mt td{white-space:normal;min-width:100px;vertical-align:top}.sector-nodes:has(.node-detail){grid-template-columns:minmax(0,1fr)}.sector-node{min-width:0}.node-detail p{margin:12px 0}.node-detail h4{margin:20px 0 8px}.sector-node h3{font-size:17px;margin:0 0 12px}.sector-node p{line-height:1.8;margin:0}.sector-table td{min-width:150px;vertical-align:top;line-height:1.7}.sector-table td:first-child{min-width:110px}.sector-chain{font-size:18px;padding:16px;background:#f3f6f9;border-radius:8px;line-height:2}.sector-evidence li{margin:12px 0;line-height:1.8}.sector-tag{font-size:13px;background:#e9eef4;border-radius:5px;padding:4px 8px;display:inline-block;margin-bottom:12px}@media(max-width:700px){.sector-grid,.sector-nodes{grid-template-columns:1fr}.sector-card{padding:18px}.sector-verdict{padding:16px;font-size:17px}}</style>'''


STYLE += '''<style>.percent-track{height:8px;background:#e6edf3;border-radius:5px;max-width:220px;min-width:100px;margin:6px 0}.percent-track span{height:100%;display:block;background:#58748b;border-radius:5px}.position-chart{display:block;width:100%;max-height:320px}.sector-card small{color:#667589;line-height:1.7}.evidence-badge{display:inline-block;margin:4px 6px 4px 0;padding:4px 8px;background:#edf2f6;border-radius:4px;font-size:13px}.scenario-table td{white-space:normal;vertical-align:top;min-width:140px;line-height:1.8}#evidence,#scenarios{scroll-margin-top:110px}</style>'''

def switch(market):
    return '<nav class="market-switch" aria-label="板块市场">' + ''.join(f'<a href="{url}"'+(' aria-current="page"' if m == market else '')+f'>{name}</a>' for m,url,name in [('a','index.html','A 股板块'),('hk','hk.html','港股板块')])+'</nav>'


def source(data, key, label='查看原始资料'):
    title=data.get('source_titles',{}).get(key)
    if title and (label.startswith('资料 ') or label.startswith('证据 ') or label=='查看原始资料'):
        label=title
    return f'<a href="{E(data["sources"][key], quote=True)}" target="_blank" rel="noopener noreferrer">{E(label)}</a>'


def evidence_overview(data,s):
    out='<section class="block" id="evidence"><h2>数据现状与估值位置</h2><div class="sector-grid">'
    for k,label in [('A','需求依据'),('C','盈利依据')]:
        nd=s['node_detail'][k]
        out+=f'<article class="sector-card"><span class="sector-tag">{k} · {label}</span><h3>{E(nd["judgment"])}</h3>'
        for r in nd['rows'][:2]:
            out+=f'<p><b>{E(r["metric"])}：</b>{E(r["value"])}<br><small>{E(r["date"])} · {E(r["scope"])}</small></p>'
        out+=f'<a href="#node-{k}">看数据来源与完整传导 ↓</a></article>'
    out+='</div><div class="evidence-grid">'
    v=s['valuation']
    out+=f'<div class="conclusion-body"><h3>F · 当前贵不贵：{E(v["name"])}</h3><p class="stamp">估值日期：{E(v["date"])}</p><div class="tblwrap"><table class="mt"><thead><tr><th>指标</th><th>当前数值</th><th>历史位置 / 窗口</th></tr></thead><tbody>'
    for i in v['items']:
        pct=i['percentile']
        meter=f'<div class="percent-track" role="img" aria-label="历史分位{pct}%"><span style="width:{pct}%"></span></div><b>{pct:g}% 分位</b>' if pct is not None else '<b>分位未核齐</b>'
        out+=f'<tr><td>{E(i["metric"])}</td><td>{E(i["value"])}</td><td>{meter}<br>{E(i["window"])}</td></tr>'
    out+=f'</tbody></table></div><p>{E(v["interpretation"])}</p><p class="note">{E(v["scope"])} 历史分位越低，只表示相对自身历史估值越低；不是上涨概率。</p><p class="src">{source(data,v["source"])}</p>'
    if v.get('additional'):
        out+=f'<p class="note">{E(v["additional"]["text"])} {source(data,v["additional"]["source"])}</p>'
    out+='</div>'
    pos=s.get('position')
    if pos:
        values=[r['value'] for r in pos['series']];lo=min(values)*.96;hi=max(values)*1.04
        coords=' '.join(f'{55+i*800/(len(values)-1):.1f},{225-(v-lo)/(hi-lo)*190:.1f}' for i,v in enumerate(values))
        out+=f'<article class="sector-card"><h3>H · 此前上涨后，现在处于什么位置</h3><p>{E(pos["name"])} · 截至 {E(pos["date"])}</p><svg class="position-chart" viewBox="0 0 910 280" role="img" aria-label="{E(pos["name"])}区间价格走势，首日等于100"><line x1="55" y1="225" x2="855" y2="225" stroke="#ccd5df"/><polyline points="{coords}" fill="none" stroke="#315a7c" stroke-width="2.5"/><text x="6" y="40" font-size="14">{hi:.0f}</text><text x="6" y="225" font-size="14">{lo:.0f}</text><text x="55" y="255" font-size="14">{pos["series"][0]["date"]}</text><text x="855" y="255" font-size="14" text-anchor="end">{pos["date"]}</text></svg><p>区间首个收盘价设为100。'
        for key,label in [('d20','20日'),('d60','60日'),('rs60','60日相对沪深300'),('drawdown','距250日最高收盘')]:
            if pos.get(key) is not None:out+=f' <b>{label}：{pos[key]:+.2f}{"个百分点" if key=="rs60" else "%"}</b>；'
        out+=f'</p><p class="note">{E(pos["scope"])} 价格回撤与估值分位是不同指标。{source(data,pos["source"])}</p></article>'
    return out+'</div></section>'



def diagram(s, prefix='', context='detail'):
    """八节点固定框架，变量由板块提供；不用当前股价反推经营结论。"""
    uid = s['id'] + '-' + context
    positions = {'A':(20,20), 'B':(650,20), 'C':(20,190), 'D':(650,190),
                 'E':(20,360), 'F':(335,360), 'G':(650,360), 'H':(335,530)}
    paths = [
        'M160 120 V190',
        'M720 120 V145 H240 V190',
        'M790 120 V190',
        'M160 290 V360',
        'M720 290 V320 H475 V360',
        'M790 290 V360',
        'M300 410 H335',
        'M160 460 V580 H335',
        'M475 460 V530',
        'M790 460 V580 H615',
    ]
    out = f'<div class="sector-diagram-scroll" role="region" aria-label="{E(s["title"])}传导图，可横向滚动" tabindex="0"><svg class="sector-diagram" viewBox="0 0 950 655" role="img" aria-labelledby="{uid}-title {uid}-desc">'
    out += f'<title id="{uid}-title">{E(s["title"])} A–H 传导框架</title><desc id="{uid}-desc">需求和政策影响利润，利润影响盈利预期；利率影响估值和资金，盈利预期、估值与资金影响价格，价格反馈交易。点击节点查看分析。</desc>'
    out += f'<defs><marker id="{uid}-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#7b8a9b"/></marker></defs>'
    for path in paths:
        out += f'<path d="{path}" fill="none" stroke="#7b8a9b" stroke-width="1.7" marker-end="url(#{uid}-arrow)"/>'
    out += f'<path d="M615 610 H920 V480 H860 V460" fill="none" stroke="#a87f36" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#{uid}-arrow)"/>'
    out += '<text x="734" y="632" fill="#896626" font-size="13">H → G：价格反馈交易行为</text>'
    for k,(x,y) in positions.items():
        fill = '#edf4fb' if k in 'ABCE' else '#faf5eb' if k in 'DF' else '#f1f3f6'
        out += f'<a href="{prefix}#node-{k}" aria-label="展开{k} {NAMES[k]}"><rect x="{x}" y="{y}" width="280" height="100" rx="10" fill="{fill}" stroke="#b5c2d0"/>'
        out += f'<text x="{x+15}" y="{y+27}" fill="#172333" font-size="16" font-weight="600">{k} · {NAMES[k]}</text>'
        for i,line in enumerate(s['diagram'][k]):
            out += f'<text x="{x+15}" y="{y+54+i*23}" fill="#425266" font-size="14">{E(line)}</text>'
        out += '</a>'
    return out+'</svg></div>'

# Desktop-first research layout, scoped to industry pages only.
DESKTOP_STYLE='''<style>
.wrap:has(.sector-research){max-width:1760px;padding:0 32px}
header.top:has(+main .sector-research) .wrap{max-width:1760px}
.sector-research{display:grid;grid-template-columns:174px minmax(0,1fr);gap:28px;align-items:start;padding-top:24px}
.research-rail{position:sticky;top:80px;max-height:calc(100vh - 100px);overflow:auto;padding:5px 12px 20px 0;font-size:13px}
.research-rail .rail-title{font-size:12px;color:#768295;letter-spacing:.08em;margin:15px 0 7px}
.research-rail a{display:block;color:#536275;padding:6px 9px;border-radius:5px;line-height:1.4}
.research-rail a:hover,.research-rail a.active{background:#e7edf3;color:#213d58;font-weight:600}
.research-rail .factor-links{display:grid;grid-template-columns:1fr 1fr;gap:2px}
.research-content{min-width:0}.framework-grid>div,.node-columns>div,.decision-grid>div,.takeaway-grid>div{min-width:0}.sector-research .hero{padding:10px 0 18px;display:flex;justify-content:space-between;gap:25px;align-items:flex-start}.sector-research .hero h1{font-size:32px}.sector-research .hero .stamp{margin-top:6px}.hero-meta{text-align:right;max-width:360px;font-size:13px;color:#667589;line-height:1.7}
.sector-research .block{padding-top:28px}.sector-research .note{max-width:none}.sector-research h2{font-size:22px;margin-bottom:14px}.sector-research h3{font-size:16px}.sector-research .market-switch{margin:0 0 10px}
.final-panel{border:1px solid #ced9e3;background:#fff;border-radius:12px;padding:24px;margin:0 0 20px}.final-panel h2{font-family:var(--sans);font-size:14px;color:#64758a;margin:0 0 13px}.final-panel .final-headline{font:600 24px/1.6 var(--serif);margin:0 0 15px;color:#162c40}.verdict-badge{display:inline-block;border-radius:5px;background:#eaf1f7;color:#25455e;padding:5px 9px;font-size:13px;font-weight:600}.verdict-badge.watch{background:#f3ede2;color:#795d29}.revision-note{font-size:13px;color:#6b7787;margin-left:12px}.decision-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:28px}.decision-copy{font-size:16px;line-height:1.9}.decision-copy p{margin:0 0 12px}.decision-net{padding:12px 15px;border-left:3px solid #426581;background:#f2f6fa;font-size:15px;line-height:1.8}.decisive-list{border-left:1px solid #e0e6ed;padding-left:24px}.decisive-item{padding:0 0 12px;margin:0 0 12px;border-bottom:1px solid #edf0f4}.decisive-item:last-child{border:0;margin:0}.decisive-item strong{display:block;font-size:15px}.decisive-item p{font-size:14px;line-height:1.7;color:#4d5d6d;margin:4px 0}.decisive-item .src{font-size:12px;line-height:1.5}
.takeaway-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:20px;border-top:1px solid #e0e6ed;padding-top:18px}.takeaway-grid h3{margin:0 0 6px}.takeaway-grid p{margin:0;font-size:14px;line-height:1.8}
.factor-balance{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:20px 0}.factor-cell{display:block;padding:11px 13px;background:#f3f6f9;border:1px solid #e0e6ed;border-radius:7px;color:#25384b}.factor-cell strong{font-size:13px}.factor-cell span{float:right;font-size:12px;color:#6a7989}.factor-cell small{display:block;line-height:1.6;color:#5e6b7c;margin-top:4px}.factor-cell[data-state="约束"]{border-left:3px solid #af8a50}.factor-cell[data-state="支撑"]{border-left:3px solid #557b71}
.evidence-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;align-items:start}.evidence-grid>.conclusion-body{margin:0}.evidence-grid>.sector-card{margin:0}.sector-research .sector-card{padding:19px}.sector-research .conclusion-body{padding:20px}.sector-research .conclusion-body p{font-size:14px;line-height:1.8}.sector-research .conclusion-body h3{margin-top:0}.sector-research #evidence>.sector-grid{margin-bottom:18px}.sector-research #evidence .sector-card p{font-size:14px;line-height:1.7;margin:10px 0}.sector-research #evidence .mt td{white-space:normal}
.framework-grid{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:20px;align-items:start}.framework-grid .sector-diagram{min-width:0}.framework-aside{padding:18px;background:#edf2f7;border-radius:8px;font-size:14px;line-height:1.8}.framework-aside h3{margin:0 0 8px}.framework-aside p{margin:8px 0}.sector-research .sector-diagram-scroll{margin:0}
.sector-research .sector-nodes:has(.node-detail){display:block}.sector-research .node-detail{margin:18px 0;padding:22px}.node-heading{display:grid;grid-template-columns:220px minmax(0,1fr);gap:20px;align-items:start;border-bottom:1px solid #e1e7ee;padding-bottom:14px;margin-bottom:16px}.node-heading h3{margin:0;font-size:18px}.node-heading p{font-size:15px;line-height:1.75}.node-columns{display:grid;grid-template-columns:minmax(0,.95fr) minmax(0,1.2fr);gap:26px;align-items:start}.node-columns h4{margin:0 0 10px;font-size:13px;color:#667589}.node-columns p{font-size:14px;line-height:1.85;margin:0 0 12px}.node-columns .mt{font-size:13px}.sector-research .node-columns .mt td{min-width:0;white-space:normal;padding:10px 8px}.node-columns .mt td:first-child{width:26%}.node-columns .mt td:nth-child(2){width:34%}.node-limit{background:#f5f7fa;padding:13px 15px;margin-top:15px;border-radius:6px}.node-limit p:last-child{margin-bottom:0}.sector-research .node-limit h4{margin:8px 0 4px}
.market-verdict{display:grid;grid-template-columns:1.4fr 1fr;gap:30px}.market-verdict .market-copy{font-size:16px;line-height:1.9;margin:0}.market-actions{display:grid;gap:15px}.market-actions p{margin:4px 0 0;font-size:14px;line-height:1.8}.review-table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:14px;background:#fff}.review-table th{background:#eef3f7;color:#53677a;font-size:12px;text-align:left;padding:12px}.review-table td{padding:16px 12px;border-top:1px solid #e0e6ec;vertical-align:top;line-height:1.75}.review-table th:nth-child(1){width:13%}.review-table th:nth-child(2){width:15%}.review-table th:nth-child(3){width:29%}.review-table th:nth-child(4){width:24%}.review-table th:nth-child(5){width:19%}.review-table small{display:block;color:#6e7c8d;font-size:12px;margin-top:7px;line-height:1.6}.table-shell{border:1px solid #d5dfe8;border-radius:10px;overflow:hidden}.overview-graphs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.overview-graphs details{padding:15px 18px;background:#fff;border:1px solid #d9e1e9;border-radius:9px;min-width:0}.overview-graphs summary{cursor:pointer;font-weight:600}.overview-graphs details[open]{grid-column:1/-1}.overview-graphs details[open] .sector-diagram{max-width:1000px;margin:auto}.overview-graphs p{font-size:14px;line-height:1.8}.sector-research .scenario-table td{min-width:0}.refs-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;font-size:13px}
@media(min-width:1600px){.decision-grid{gap:36px}.node-columns{grid-template-columns:minmax(0,1fr) minmax(0,1.3fr)}}
@media(max-width:1200px){.sector-research{grid-template-columns:150px minmax(0,1fr);gap:20px}.wrap:has(.sector-research){padding:0 20px}.framework-grid{grid-template-columns:1fr}.framework-aside{display:none}.evidence-grid{grid-template-columns:1fr}.node-columns{grid-template-columns:1fr 1.1fr}.final-panel .final-headline{font-size:22px}.decision-grid{gap:18px}.decisive-list{padding-left:18px}}
@media(max-width:900px){.sector-research{display:block}.research-rail{position:static;max-height:none;display:flex;gap:5px;flex-wrap:wrap;border-bottom:1px solid #d9e0e7;padding:0 0 12px;margin-bottom:15px}.research-rail .rail-title,.research-rail .rail-sectors,.research-rail .factor-links{display:none}.research-rail a{display:inline-block}.decision-grid,.market-verdict,.node-columns{grid-template-columns:1fr}.decisive-list{border-left:0;border-top:1px solid #e0e6ed;padding:16px 0 0}.takeaway-grid{grid-template-columns:1fr}.factor-balance{grid-template-columns:repeat(2,minmax(0,1fr))}.node-heading{grid-template-columns:1fr;gap:6px}.sector-research .hero{display:block}.hero-meta{text-align:left;max-width:none}.review-table{min-width:920px}.table-shell{overflow-x:auto}.overview-graphs{grid-template-columns:1fr}.refs-grid{grid-template-columns:1fr}.revision-note{display:block;margin:8px 0}.final-panel{padding:20px}.sector-research .sector-diagram{min-width:760px}.overview-graphs details[open]{grid-column:auto}}
</style>'''


def shell(data,market,content,current=None):
    back='index.html' if market=='a' else 'hk.html'
    rail='<aside class="research-rail" aria-label="研究目录"><div class="rail-title">板块研究</div><a href="index.html"'+(' class="active"' if market=='a' else '')+'>A 股总览</a><a href="hk.html"'+(' class="active"' if market=='hk' else '')+'>港股总览</a>'
    if current:
        rail+='<div class="rail-title">本页内容</div>'+''.join(f'<a href="#{a}">{t}</a>' for a,t in [('conclusion','最终结论'),('evidence','数据 · 估值 · 位置'),('framework','传导框架'),('scenarios','升级与降级条件')])
    rail+='<div class="rail-sectors"><div class="rail-title">同市场板块</div>'
    for s in data['sectors']:
        if s['market']==market:rail+=f'<a href="{s["id"]}.html"'+(' class="active"' if s['id']==current else '')+f'>{E(s["title"])}</a>'
    rail+='</div></aside>'
    return STYLE+DESKTOP_STYLE+'<div class="sector-research">'+rail+'<div class="research-content">'+content+'</div></div>'


def verdict_badge(v):
    return '<span class="verdict-badge'+(' watch' if '观察' in v['group'] else '')+'">'+E(v['group'])+'</span>'


def final_verdict(data,s):
    v=s['review']
    out='<section class="final-panel" id="conclusion"><h2>综合 A–H 后的最终结论</h2>'+verdict_badge(v)+f'<span class="revision-note">{E(v["change"])}</span><p class="final-headline">{E(v["headline"])}</p><div class="decision-grid"><div class="decision-copy"><p>{E(v["synthesis"])}</p><div class="decision-net"><b>证据权衡：</b>{E(v["net"])}</div></div><div class="decisive-list"><h3>决定这个结论的三条证据</h3>'
    for x in v['decisive']:
        out+=f'<div class="decisive-item"><strong>{x["factor"]} · {E(x["fact"])}</strong><p>{E(x["implication"])}</p><div class="src">{source(data,x["source"])}</div></div>'
    out+='</div></div><div class="takeaway-grid">'
    for title,text in [('看好的范围',v['positive']),('不成立的延伸',v['exclude']),('这次如何改判',v['change']+'。'+v['net'])]:
        out+=f'<div><h3>{title}</h3><p>{E(text)}</p></div>'
    out+='</div><details class="sector-factor-notes"><summary>查看A–H证据分工</summary><p class="note">以上是基于本页数据的研究判断。下方区分支持、约束与待验证因素；不将缺失数据当作利空，也不自动抵消已经成立的证据。</p><div class="factor-balance">'
    for k,x in v['factors'].items():
        out+=f'<a class="factor-cell" href="#node-{k}" data-state="{x["status"]}"><strong>{k} · {NAMES[k]}</strong><span>{x["status"]}</span><small>{E(x["reason"])}</small></a>'
    return out+'</div></details></section>'


def hub(data,market):
    items=[s for s in data['sectors'] if s['market']==market];m=data['market_synthesis'][market];name='A 股' if market=='a' else '港股'
    outlook='../index.html#horizon' if market=='a' else '../hk/index.html#horizon'
    body=f'<div class="hero"><div><h1>{name}板块 · 半年判断</h1><p class="stamp">明细更新 {data["as_of"]} · 总结复核 {data.get("market_synthesis_reviewed_at",data["as_of"])} · {data["window"]}</p></div><div class="hero-meta">板块结论统一维护在此，点击进入公司筛选。<br><a href="{outlook}">查看大盘 A–H 综合依据 →</a></div></div>'
    body+=f'<section class="final-panel" id="conclusion"><h2>研究汇总</h2><p class="final-headline">{E(m["headline"])}</p><div class="market-verdict"><p class="market-copy">{E(m["body"])}</p><div class="market-actions"><div><b>当前研究重心</b><p>{E(m["focus"])}</p></div><div><b>相较上一轮的变化</b><p>{E(m["revision"])}</p></div></div></div></section>'
    body+='<section class="block"><h2>各板块最终结论 · 横向对照</h2><p class="note">“结构性看好”指特定细分已有需求依据；“条件看好”仍有关键兑现条件；观察类暂不列为优先主线。分类表示研究判断强度，不是收益排序。</p><div class="table-shell"><table class="review-table"><thead><tr><th>板块</th><th>最终判断 / 变化</th><th>未来半年怎样看</th><th>决定性证据</th><th>什么会改变结论</th></tr></thead><tbody>'
    order={'结构性看好':0,'条件看好':1,'防御观察':2,'周期观察':3,'细分观察':4}
    items=sorted(items,key=lambda s:order[s['review']['group']])
    for s in items:
        v=s['review'];facts=v['decisive']
        body+=f'<tr data-sector="{s["id"]}"><td><a href="{s["id"]}.html"><b>{E(s["title"])}</b></a></td><td>{verdict_badge(v)}<small>{E(v["change"])}</small></td><td>{E(v["headline"])}</td><td>'+''.join(f'<p style="margin:0 0 7px"><b>{x["factor"]}</b> {E(x["fact"])}</p>' for x in [facts[0],facts[-1]])+f'<a href="{s["id"]}.html#conclusion">查看完整权衡 →</a></td><td>{E(v["upgrade"])}</td></tr>'
    body+='</tbody></table></div></section><details class="deep-research" id="framework"><summary>展开各板块传导框架</summary><div class="overview-graphs">'
    for s in items:
        body+=f'<details><summary>{E(s["title"])} · {E(s["review"]["group"])}</summary><p>{E(s["review"]["net"])}</p>{diagram(s,s["id"]+".html","hub")}<p><a href="{s["id"]}.html#framework">查看逐节点数据与解释 →</a></p></details>'
    body+=f'</div></details><section class="block"><p class="note">{E(data["coverage"])}。各资料有独立日期，本轮对既有证据重新综合判断；原始数据未统一刷新为当日值。</p></section>'
    return shell(data,market,body)


def detail(data,s):
    market='A 股' if s['market']=='a' else '港股';back='index.html' if s['market']=='a' else 'hk.html';v=s['review']
    body=f'<div class="crumb"><a href="{back}">{market}板块</a> ／ {E(s["title"])}</div><div class="hero"><div><h1>{E(s["title"])}</h1><p class="stamp">{market} · 研究更新 {data["as_of"]}</p></div><div class="hero-meta">判断窗口 {data["window"]}<br>11月11日初筛（历史）：{E(s["macro_tier"])} → 板块核验：{E(v["group"])}</div></div>'
    body+=final_verdict(data,s)+'<details class="deep-research" id="full-evidence"><summary>展开完整研究：估值、传导图、A–H数据与反证</summary>'+evidence_overview(data,s)
    body+=f'<section class="block" id="framework"><h2>板块 A–H 传导框架</h2><div class="framework-grid"><div>{diagram(s)}</div><aside class="framework-aside"><h3>这条链怎样得出结论</h3><p>{E(v["net"])}</p><h3>影响半年判断的关键</h3><p>{E(v["upgrade"])}</p><p class="note">A/B影响C，再影响E；D约束F/G，E/F/G共同接受H验证。点击节点查看依据。</p></aside></div></section><section class="block"><h2>逐节点分析 · 数据与解释并排</h2><div class="sector-nodes">'
    for k in 'ABCDEFGH':
        n=s['node_detail'][k]
        body+=f'<article class="sector-node node-detail" id="node-{k}"><div class="node-heading"><h3>{k} · {NAMES[k]}</h3><p><b>{E(n["judgment"])}</b></p></div><div class="node-columns"><div><h4>数据与证据</h4><div class="tblwrap"><table class="mt"><thead><tr><th>指标</th><th>数值 / 事实</th><th>日期 · 口径 · 来源</th></tr></thead><tbody>'
        for r in n['rows']:
            link=source(data,r['source']) if r['source'] else '研究口径说明'
            body+=f'<tr><td>{E(r["metric"])}</td><td>{E(r["value"])}</td><td><b>{E(r["date"])}</b><br>{E(r["scope"])}<br>{link}</td></tr>'
        body+='</tbody></table></div></div><div><h4>怎样影响本板块</h4>'+''.join('<p>'+E(x)+'</p>' for x in n['analysis'])
        body+=f'<div class="node-limit"><h4>反证与解释边界</h4><p>{E(n["counter"])}</p><h4>下一步验证</h4><p>{E(n["next"])}</p></div></div></div></article>'
    body+='</div></section><section class="block" id="scenarios"><h2>最终判断如何升级或失效</h2><div class="tblwrap"><table class="mt scenario-table"><thead><tr><th style="width:12%">情景</th><th style="width:53%">判断与条件</th><th>研究如何调整</th></tr></thead><tbody>'
    for x in s['scenarios']:body+=f'<tr><td>{E(x["name"])}</td><td>{E(x["condition"])}</td><td>{E(x["action"])}</td></tr>'
    body+=f'</tbody></table></div><p class="note">{E(s["metrics"])}</p></section><section class="block"><h2>关联资料</h2><div class="refs-grid">'+''.join(source(data,k,f'资料 {i+1}') for i,k in enumerate(s['refs']))+'</div></section>'
    body+='</details>'
    body+=f'<section class="block"><p><a href="../stocks/pool-{s["id"]}.html">进入独立股票研究页 →</a></p></section>'
    return shell(data,s['market'],body,s['id'])


def build(ctx):
    data = json.loads((Path(ctx['ROOT'])/'data/industry_research.json').read_text())
    out = Path(ctx['SITE'])/'boards'
    for market, file in [('a','index.html'),('hk','hk.html')]:
        (out/file).write_text(ctx['page'](('A 股' if market=='a' else '港股')+'板块研究','bk',hub(data,market),'../'))
    for s in data['sectors']:
        (out/(s['id']+'.html')).write_text(ctx['page'](s['title']+' | '+('A 股' if s['market']=='a' else '港股')+'板块','bk',detail(data,s),'../'))

