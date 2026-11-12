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
        rail+='<div class="factor-links">'+''.join(f'<a href="#node-{k}">{k} {dict(zip('ABCDEFGH',['需求','政策','利润','利率','预期','估值','资金','价格']))[k]}</a>' for k in 'ABCDEFGH')+'</div>'
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
    out+='</div><p class="note">以上是基于本页数据的研究判断。下方区分支持、约束与待验证因素；不将缺失数据当作利空，也不自动抵消已经成立的证据。</p><div class="factor-balance">'
    for k,x in v['factors'].items():
        out+=f'<a class="factor-cell" href="#node-{k}" data-state="{x["status"]}"><strong>{k} · {NAMES[k]}</strong><span>{x["status"]}</span><small>{E(x["reason"])}</small></a>'
    return out+'</div></section>'


def hub(data,market):
    items=[s for s in data['sectors'] if s['market']==market];m=data['market_synthesis'][market];name='A 股' if market=='a' else '港股'
    outlook='../index.html#horizon' if market=='a' else '../hk/index.html#horizon'
    body=f'<div class="hero"><div><h1>{name}板块 · 半年判断</h1><p class="stamp">明细更新 {data["as_of"]} · 总结复核 {data.get("market_synthesis_reviewed_at",data["as_of"])} · {data["window"]}</p></div><div class="hero-meta">首页与板块使用同一组最终判断；保留历史初筛作修订对照。<br><a href="{outlook}">查看大盘 A–H 综合依据 →</a></div></div>'
    body+=f'<section class="final-panel" id="conclusion"><h2>研究汇总</h2><p class="final-headline">{E(m["headline"])}</p><div class="market-verdict"><p class="market-copy">{E(m["body"])}</p><div class="market-actions"><div><b>当前研究重心</b><p>{E(m["focus"])}</p></div><div><b>相较上一轮的变化</b><p>{E(m["revision"])}</p></div></div></div></section>'
    body+='<section class="block"><h2>各板块最终结论 · 横向对照</h2><p class="note">“结构性看好”指特定细分已有需求依据；“条件看好”仍有关键兑现条件；观察类暂不列为优先主线。分类表示研究判断强度，不是收益排序。</p><div class="table-shell"><table class="review-table"><thead><tr><th>板块</th><th>最终判断 / 变化</th><th>未来半年怎样看</th><th>决定性证据</th><th>什么会改变结论</th></tr></thead><tbody>'
    order={'结构性看好':0,'条件看好':1,'防御观察':2,'周期观察':3,'细分观察':4}
    items=sorted(items,key=lambda s:order[s['review']['group']])
    for s in items:
        v=s['review'];facts=v['decisive']
        body+=f'<tr data-sector="{s["id"]}"><td><a href="{s["id"]}.html"><b>{E(s["title"])}</b></a><small>11月11日初筛（历史）：{E(s["macro_tier"])}</small></td><td>{verdict_badge(v)}<small>{E(v["change"])}</small></td><td>{E(v["headline"])}</td><td>'+''.join(f'<p style="margin:0 0 7px"><b>{x["factor"]}</b> {E(x["fact"])}</p>' for x in [facts[0],facts[-1]])+f'<a href="{s["id"]}.html#conclusion">查看完整权衡 →</a></td><td>{E(v["upgrade"])}</td></tr>'
    body+='</tbody></table></div></section><section class="block" id="framework"><h2>按板块展开传导框架</h2><div class="overview-graphs">'
    for s in items:
        body+=f'<details><summary>{E(s["title"])} · {E(s["review"]["group"])}</summary><p>{E(s["review"]["net"])}</p>{diagram(s,s["id"]+".html","hub")}<p><a href="{s["id"]}.html#framework">查看逐节点数据与解释 →</a></p></details>'
    body+=f'</div></section><section class="block"><p class="note">{E(data["coverage"])}。各资料有独立日期，本轮对既有证据重新综合判断；原始数据未统一刷新为当日值。</p></section>'
    return shell(data,market,body)


def detail(data,s):
    market='A 股' if s['market']=='a' else '港股';back='index.html' if s['market']=='a' else 'hk.html';v=s['review']
    body=f'<div class="crumb"><a href="{back}">{market}板块</a> ／ {E(s["title"])}</div><div class="hero"><div><h1>{E(s["title"])}</h1><p class="stamp">{market} · 研究更新 {data["as_of"]}</p></div><div class="hero-meta">判断窗口 {data["window"]}<br>11月11日初筛（历史）：{E(s["macro_tier"])} → 板块核验：{E(v["group"])}</div></div>'
    body+=final_verdict(data,s)+evidence_overview(data,s)
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
    body+=f'<section class="block"><p><a href="../stocks/pool-{s["id"]}.html">进入独立股票研究页 →</a></p></section>'
    return shell(data,s['market'],body,s['id'])


def build(ctx):
    data = json.loads((Path(ctx['ROOT'])/'data/industry_research.json').read_text())
    out = Path(ctx['SITE'])/'boards'
    for market, file in [('a','index.html'),('hk','hk.html')]:
        (out/file).write_text(ctx['page'](('A 股' if market=='a' else '港股')+'板块研究','bk',hub(data,market),'../'))
    build_stock_pools(ctx)
    for s in data['sectors']:
        (out/(s['id']+'.html')).write_text(ctx['page'](s['title']+' | '+('A 股' if s['market']=='a' else '港股')+'板块','bk',detail(data,s),'../'))


NODE_ROLES = [
    ('A', '需求', '入池门', '只回答"业务连接是否成立"，是/否判定，不打分'),
    ('B', '政策与地缘', '入池门', '只回答"政策或事件是否支持这条业务连接"，不打分'),
    ('C', '行业利润与现金流', '入池门 + 兑现质量', '入池时核验业务连接；池内排序时与 E 共用同一套财务口径'),
    ('D', '利率与风险溢价', '组合层', '决定整体仓位上限与折现假设，不对个股单独加减分'),
    ('E', '盈利预期修订', '兑现质量', '作为 C 口径的修正提醒，不与 C 重复加权'),
    ('F', '估值', '时机', '一个主估值指标决定现在追 / 等 / 不追，其余指标只作否决'),
    ('G', '资金与拥挤度', '组合层', '决定加仓节奏与拥挤度预警，不对个股单独加减分'),
    ('H', '价格验证', '时机', '价格是否确认逻辑，与 F 同属时机维度'),
]


def node_role_table():
    rows = ''.join(f'<tr><td><b>{k} · {E(n)}</b></td><td><b>{E(role)}</b></td><td>{E(duty)}</td></tr>' for k, n, role, duty in NODE_ROLES)
    return ('<div class="tblwrap"><table class="mt"><thead><tr><th>框架节点</th><th>在个股筛选层的职能</th><th>职能边界（不做什么）</th></tr></thead><tbody>'
            + rows + '</tbody></table></div>')


def _pool_candidate(scr, x):
    """候选所属子池与理由类型是否与板块接受理由一致。"""
    for pool in scr.get('sub_pools', []):
        if x['code'] in pool['codes']:
            return pool
    return None


def stock_pool(data, s):
    market = 'A 股' if s['market']=='a' else '港股'
    scr = s.get('screen') or {}
    sub_pools = scr.get('sub_pools', [])
    n_main = sum(len(p['codes']) for p in sub_pools if p.get('key') == 'main')
    n_alt = len(s['candidates']) - n_main
    body = STYLE + f'<div class="crumb"><a href="sector-pools.html">股票研究入口</a> ／ {market} · {E(s["title"])}</div><div class="hero"><h1>{E(s["title"])} · 股票研究</h1><p class="sum">此页按三个决策维度组织待选池：赛道归属（入池门）→ 兑现质量（池内排序）→ 价格反映（时机）；利率与资金约束上移到组合层。尚未确定买入个股。行业判断请返回<a href="../boards/{s["id"]}.html">独立板块分析</a>。</p></div>'
    # 筛选规则与节点职能分工
    body += ('<section class="block" id="screen"><h2>本池筛选规则：节点先分工，再筛选</h2>'
             '<p><b>收敛规则一 · 职能分离：</b>A/B/C 只回答"是否入池"，不打分；C→E 用同一套财务口径决定池内优先级；F 只保留一个主估值指标决定时机；D、G 属于组合层，约束仓位与节奏，不在本页对个股加减分。</p>'
             '<p><b>收敛规则二 · 理由唯一：</b>入池必须先回答"当前半年这个方向只接受哪一类理由"；理由类型不同的公司分入不同子池，<b>不合并排序</b>。</p>'
             '<p><b>收敛规则三 · 不重复加权：</b>同一份营收、同一份现金流、同一份估值分位，不在多个节点重复计分。</p>'
             '<h3>A–H 节点在个股筛选层的职能</h3>' + node_role_table() + '</section>')
    # 维度一：赛道归属（入池门）
    gate = scr.get('gate', '入池只核验业务连接：A 需求、B 政策、C 利润与现金流是否支持这条业务链。是/否判定，不打分。')
    body += (f'<section class="block" id="candidates"><h2>维度一 · 赛道归属：入池门（A/B/C 是/否判定）</h2>'
             f'<p class="sub">当前半年（{E(data.get("window", ""))}）本板块只接受一类入池理由：</p>'
             f'<p class="sector-verdict">{E(scr.get("accept_reason", "见板块结论"))}</p>'
             f'<p>{E(scr.get("accept_basis", "依据见板块页结论。"))}</p>'
             f'<p class="note"><b>入池门规则：</b>{E(gate)}</p>'
             f'<p class="note">下表只做是/否判定：业务连接成立且已核 → <b>是</b>；连接 plausible 但业务占比未核验 → <b>待核</b>；触发淘汰条件 → 退回观察或出池。待选不等于已选。</p>'
             '<div class="tblwrap"><table class="mt sector-table"><thead><tr><th>股票 / 研究阶段</th><th>业务连接（承接板块逻辑）</th><th>入池判定</th><th>淘汰或退回观察条件</th></tr></thead><tbody>')
    for x in s['candidates']:
        pool = _pool_candidate(scr, x)
        pool_lab = f'<span class="sector-tag">{E(pool["label"])}</span><br>' if pool else ''
        if pool and pool.get('key') == 'main':
            verdict = '是' if '待核' not in x['status'] else '待核'
            match = '理由类型与板块接受理由一致'
        else:
            verdict = '是' if '待核' not in x['status'] else '待核'
            match = '业务连接成立，但理由类型不同，分入副池'
        body += (f'<tr><td><b>{E(x["name"])}</b><br>{market} {x["code"]}<p class="note">{E(x["status"])}</p></td>'
                 f'<td><b>{E(x["segment"])}</b><br>{E(x["logic"])}</td>'
                 f'<td>{pool_lab}<b>{verdict}</b><br>{E(match)}</td>'
                 f'<td>{E(x["risk"])}</td></tr>')
    body += '</tbody></table></div></section>'
    # 维度二：兑现质量（池内排序）
    cand = {x['code']: x for x in s['candidates']}
    delivery = scr.get('delivery', '池内排序只用一套财务口径：C 利润与现金流 → E 盈利修订（同口径修正）。')
    body += (f'<section class="block" id="delivery"><h2>维度二 · 兑现质量：池内排序（C→E 一套财务口径）</h2>'
             f'<p>{E(delivery)}</p>'
             '<p class="note">排序依据与 A/B 入池判定不叠加；E 盈利修订是 C 口径的修正，不再单独加权。各子池只在池内排序，跨池不合并名次。</p>')
    for pool in sub_pools:
        is_main = pool.get('key') == 'main'
        body += (f'<h3>{E(pool["label"])} · {len(pool["codes"])} 只</h3>'
                 f'<p><b>池内理由：</b>{E(pool["reason"])}</p>'
                 f'<p class="note"><b>排序口径：</b>{E(pool.get("sort", pool.get("metric", "")))}{"" if is_main else "　·　此池理由类型与主池不同，不与主池合并排序"}</p>')
        body += '<div class="tblwrap"><table class="mt sector-table"><thead><tr><th>股票 / 研究阶段</th><th>排序口径下优先核什么</th><th>口径提醒</th></tr></thead><tbody>'
        for code in pool['codes']:
            x = cand.get(code)
            if not x:
                continue
            body += (f'<tr><td><b>{E(x["name"])}</b><br>{market} {x["code"]}<p class="note">{E(x["status"])}</p></td>'
                     f'<td>{E(x["verify"])}<br>{source(data,x["source"],"资料 / 继续核验入口")}</td>'
                     f'<td>{E(pool.get("note", x["segment"]))}</td></tr>')
        body += '</tbody></table></div>'
    body += '</section>'
    # 维度三：价格反映（时机）
    vetoes = scr.get('veto', [])
    veto_html = ''.join(f'<li>{E(v)}</li>' for v in vetoes) or '<li>见板块页估值结论。</li>'
    body += (f'<section class="block" id="timing"><h2>维度三 · 价格反映：时机（F 主指标 + 否决条件）</h2>'
             f'<p><b>本板块唯一主估值指标：</b>{E(scr.get("primary_metric", "见板块页估值结论"))}</p>'
             f'<p class="note">{E(scr.get("primary_metric_note", ""))}</p>'
             '<p>其余估值指标一律降为否决条件，<b>不参与排序</b>，只在触发阈值时把候选降级：</p><ul class="sector-evidence">'
             + veto_html + '</ul>'
             f'<p>{E(scr.get("timing", "主指标在可接受区间且未触发否决 → 分批；被上涨压薄或触顶 → 等待；触发否决 → 不追。"))}</p>'
             '<p class="note">估值分位与价格位置数据见各板块页「数据现状与估值位置」；个股的 PE/PB 与价格通道在个股页「股价层」，两处数据同源，不在本页重复计分。H 价格验证与 F 同属时机维度：价格没有确认逻辑之前，排序靠前也不构成买入理由。</p></section>')
    # 组合层声明
    body += ('<section class="block" id="portfolio"><h2>组合层约束：D 利率与 G 资金不在本页计分</h2>'
             '<p class="sector-verdict">D（利率与风险溢价）与 G（资金与拥挤度）已上移到组合层：D 决定整体仓位上限与折现假设，G 决定加仓节奏与拥挤度预警。它们约束"买多少、多快买"，<b>不对任何个股单独加减分</b>，也不与本页三个维度并列排序。</p>'
             '<p class="note">个股页保留的融资余额、股东户数等数据仅作组合层参考的展示，不进入个股合计分。</p></section>')
    # 龙头观察（附录）
    body += '<section class="block" id="leaders"><h2>龙头与细分标杆观察（行业动向参考，不参与排序）</h2><p class="note">先观察行业龙头，再筛选合适个股。观察身份按主营业务和行业代表性确定，不作市值或市占率排名；最终可以选择龙头，也可以选择其他公司。龙头观察只提供 A/B/C 入池门与行业动向的对标素材，不因其龙头身份在维度二、三获得任何加分。A/H 同一发行人的经营证据复用，估值和交易信号分别处理。</p><div class="tblwrap"><table class="mt sector-table"><thead><tr><th>观察公司 / 市场代码</th><th>为什么观察它</th><th>重点跟踪哪些动向</th><th>已核资料与日期</th></tr></thead><tbody>'
    for stock in s['stocks']:
        observation = stock['observation']
        body += f'<tr><td><b>{E(stock["name"])}</b><br>{market} {stock["code"]}<br><span class="sector-tag">{E(stock["watch_role"])}</span></td><td>{E(stock["watch_reason"])}<p class="note">业务：{E(stock["role"])}</p>{source(data,stock["leader_source"],"业务与行业地位依据")}</td><td><b>对应 {E(stock["watch_nodes"])}</b><br>{E(stock["watch"])}</td><td><b>{E(observation["date"])}</b><br>{E(observation["text"])}<br>{source(data,observation["source"],"查看已核资料")}<p class="note">{E(stock.get("other", ""))}</p></td></tr>'
    body += '</tbody></table></div></section>'
    if s.get('cross_market'):
        body += '<section class="block"><h3>跨市场龙头对照</h3><p class="note">用于比较行业供需，市场标注不同的公司不进入本市场待选池。</p>'
        for x in s['cross_market']:
            body += f'<p><b>{E(x["name"])} · {E(x["market"])} {x["code"]}</b>：{E(x["why"])} {source(data,x["source"])}</p>'
        body += '</section>'
    return body


def build_stock_pools(ctx):
    data=json.loads((Path(ctx['ROOT'])/'data/sector_research.json').read_text())
    out=Path(ctx['SITE'])/'stocks';out.mkdir(exist_ok=True)
    body=STYLE+'<div class="hero"><h1>按板块进入股票研究</h1><p class="sum">行业逻辑在板块页独立分析；此处把每个板块的待选池按三个决策维度组织：赛道归属（入池门）→ 兑现质量（池内排序）→ 价格反映（时机）。利率与资金约束在组合层，不在个股层计分。</p></div>'
    body+=('<section class="block" id="convergence"><h2>从板块池收敛到 10 只的规则</h2>'
           '<p class="sector-verdict">每个板块先声明"当前半年只接受哪一类入池理由"（维度一）；入池候选用同一套财务口径在池内排序（维度二）；排序靠前且未触发估值否决的，再由唯一主估值指标决定追 / 等 / 不追（维度三）。每池只保留排序靠前、理由与池一致、未触发否决的少数标的，全市场合计约 10 只。</p>'
           '<ul class="sector-evidence">'
           '<li><b>主排序理由只能有一个</b>：同一只股票不能既因"需求清晰"又因"低估值"参与排序；"低估值"属于维度三的时机，不进入维度二的排序。</li>'
           '<li><b>理由类型不同 → 分池</b>：副池与主池不合并排序；理由类型改变的候选改判子池，而不是折中名次。</li>'
           '<li><b>同一数据不重复加权</b>：同一份营收、现金流、估值分位只在职能所属的一个维度出现。</li>'
           '</ul>'
           '<h3>A–H 节点在个股筛选层的职能</h3>'+node_role_table()+'</section>')
    for market,label in [('a','A 股'),('hk','港股')]:
        body+=f'<section class="block"><h2>{label}</h2><div class="sector-grid">'
        for s in data['sectors']:
            if s['market']!=market:continue
            file='pool-'+s['id']+'.html'
            (out/file).write_text(ctx['page'](s['title']+' | 股票研究','pool',stock_pool(data,s),'../'))
            scr=s.get('screen') or {}
            sub_pools=scr.get('sub_pools',[])
            n_main=sum(len(p['codes']) for p in sub_pools if p.get('key')=='main')
            n_alt=len(s['candidates'])-n_main
            accept=f'<p class="stamp">当前半年只接受：{E(scr.get("accept_reason","见板块页"))}</p>' if scr else ''
            metric=f'<p class="note">主估值指标：{E(scr.get("primary_metric","见板块页"))}</p>' if scr else ''
            body+=(f'<article class="sector-card"><h3><a href="{file}">{E(s["title"])}</a></h3>{accept}'
                   f'<p>主池 {n_main} 只 · 副池 {n_alt} 只 · 龙头与标杆观察 {len(s["stocks"])} 条</p>{metric}'
                   f'<p class="note">{E(scr.get("delivery",""))[:120]}{"…" if len(scr.get("delivery",""))>120 else ""}</p></article>')
        body+='</div></section>'
    (out/'sector-pools.html').write_text(ctx['page']('股票研究入口','pool',body,'../'))
