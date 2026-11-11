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
    out+='</div>'
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
    return out+'</section>'



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

def hub(data, market):
    items = [s for s in data['sectors'] if s['market'] == market]
    name = 'A 股' if market == 'a' else '港股'
    outlook = '../index.html#horizon' if market == 'a' else '../hk/index.html#horizon'
    summary = ('主要方向是煤炭现金回报和油运盈利；半导体、计算机设备、创新药、化学原料、铜和电网设备条件看好，重点验证订单、价差、利润及现金兑现。'
               if market == 'a' else '主要方向是电信现金回报、能源生产和油运；互联网与半导体、算力硬件条件看好，盈利兑现与美元利率、港元流动性共同决定估值空间。')
    body = STYLE + switch(market) + f'<div class="hero"><h1>{name}板块研究</h1><p class="sum">{E(summary)}</p><p class="stamp">研究更新 {data["as_of"]} · 判断窗口 {data["window"]} · <a href="{outlook}">回看大盘六个月判断</a></p></div>'
    body += '<p class="note">板块分档继承大盘 A–H 判断。本页研究行业需求、供给、政策、利润、估值与资金的传导；每个板块均可展开完整框架。</p>'
    for tier in ['主要方向','条件看好']:
        group = [s for s in items if s['tier'] == tier]
        body += f'<section class="block"><h2>{tier} · {len(group)} 个方向</h2><div class="sector-grid">'
        for s in group:
            body += f'<article class="sector-card"><h3><a href="{s["id"]}.html">{E(s["title"])}</a></h3><p><b>{E(s["summary_takeaway"])}</b></p><p><strong>为什么这样判断：</strong>{E(s["conclusion"]["reason"])}</p><p><strong>板块内如何取舍：</strong>{E(s["conclusion"]["priority"])}</p><p class="sector-preview"><b>估值核验：</b>{E(s["valuation"]["interpretation"])}</p><div class="sector-preview"><b>A/B → C → E/F</b><br>{E(s["diagram"]["A"][0])} → {E(s["diagram"]["C"][0])} → {E(s["diagram"]["F"][0])}</div><p><strong>验证重点：</strong>{E(s["metrics"])}</p><details><summary>展开本板块 A–H 传导框架</summary>{diagram(s, s["id"]+".html", "hub")}<p class="note">颜色区分经营路径、定价约束与市场反馈；不表示利好或利空。手机可横向滑动，点击节点进入详细分析。</p></details><a href="{s["id"]}.html">查看行业因子与完整分析 →</a></article>'
        body += '</div></section>'
    body += f'<section class="block"><h2>本轮资料范围</h2><p class="note">{E(data["coverage"])}。估值分位已区分历史窗口与行业口径；未核齐的细分资料在详情中明确标示。</p></section>'
    return body


def detail(data, s):
    market = 'A 股' if s['market'] == 'a' else '港股'
    back = 'index.html' if s['market'] == 'a' else 'hk.html'
    body = STYLE + switch(s['market']) + f'<div class="crumb"><a href="{back}">{market}板块</a> ／ {E(s["title"])}</div><nav class="market-switch" aria-label="板块内容"><a href="#conclusion">半年结论</a><a href="#evidence">数据与估值</a><a href="#framework">A–H传导</a><a href="#scenarios">改判条件</a></nav><div class="hero"><span class="sector-tag">{market} · {s["tier"]}</span><h1>{E(s["title"])}</h1><p class="stamp">更新 {data["as_of"]} · 判断窗口 {data["window"]}</p></div>'
    c=s['conclusion']
    body += f'<section class="conclusion-body" id="conclusion"><h2>未来半年的研究结论</h2><p class="conclusion-base">{E(c["base"])}</p><h3>证据支持什么判断</h3><p>{E(c["reason"])}</p><h3>板块内部先研究什么</h3><p>{E(c["priority"])}</p><h3>为什么还不能作更强判断</h3><p>{E(c["boundary"])}</p><h3>什么变化会让我改判</h3><p><b>支持保持 / 升级：</b>{E(c["upgrade"])}</p><p><b>触发下调：</b>{E(c["downgrade"])}</p><p class="note">以上为基于已列资料的研究推断，研究顺序不代表收益排名。报告期和数据日期见下方节点表；证据缺口保留。</p><p class="src">结论对应资料：'+ ' · '.join(source(data,k,f'证据 {i+1}') for i,k in enumerate(c['evidence_sources']))+'</p></section>'
    body += evidence_overview(data,s)
    body += f'<section class="block" id="framework"><h2>板块 A–H 传导框架</h2><p class="note">每个节点使用本板块具体变量。蓝色为经营传导，浅金色为定价约束，灰色为资金与价格反馈；颜色不代表涨跌评分。点击节点查看下方依据，手机可横向滑动。</p>{diagram(s)}<p class="note">本板块重点链条：{E(s["chain"])}。H → G 是价格对交易行为的反馈；股价上涨不能倒推经营改善，也不能替代 C/E 验证。</p><h3>逐节点分析</h3><div class="sector-nodes">'
    for k, val in s['nodes'].items():
        nd=s['node_detail'][k]
        body += f'<article class="sector-node node-detail" id="node-{k}"><h3>{k} · {NAMES[k]}</h3><p><b>当前判断：</b>{E(nd["judgment"])}</p><h4>数据与证据</h4><div class="tblwrap"><table class="mt"><thead><tr><th>指标</th><th>数值 / 事实</th><th>日期</th><th>口径 / 来源</th></tr></thead><tbody>'
        for r in nd['rows']:
            link=source(data,r['source']) if r['source'] else '研究口径说明'
            body += f'<tr><td>{E(r["metric"])}</td><td>{E(r["value"])}</td><td>{E(r["date"])}</td><td>{E(r["scope"])}<br>{link}</td></tr>'
        body += '</tbody></table></div><h4>如何传到本板块</h4>'+''.join('<p>'+E(x)+'</p>' for x in nd['analysis'])
        body += f'<h4>反证与解释边界</h4><p>{E(nd["counter"])}</p><h4>下一步如何验证行业判断</h4><p>{E(nd["next"])}</p></article>'
    body += '</div></section>'
    body += '<section class="block" id="scenarios"><h2>未来半年：基准与改判情景</h2><p class="note">以下是研究判断条件，不是概率预测或收益承诺。</p><div class="tblwrap"><table class="mt scenario-table"><thead><tr><th>情景</th><th>条件与判断</th><th>研究应如何调整</th></tr></thead><tbody>'+''.join('<tr><td>'+E(x['name'])+'</td><td>'+E(x['condition'])+'</td><td>'+E(x['action'])+'</td></tr>' for x in s['scenarios'])+'</tbody></table></div></section>'
    body += f'<section class="block"><h2>未来半年如何跟踪</h2><div class="sector-nodes"><article class="sector-node"><h3>保持 / 升级条件</h3><p>{E(s["upgrade"])}</p></article><article class="sector-node"><h3>降级 / 失效条件</h3><p>{E(s["down"])}</p></article></div><p><b>跟踪频率：</b>{E(s["metrics"])}</p></section>'
    refs = list(dict.fromkeys(s['refs']))
    body += '<section class="block"><h2>关联资料</h2><p>'+' · '.join(source(data,k,f'资料 {i+1}') for i,k in enumerate(refs))+'</p><p class="note">'+E(data['coverage'])+'。</p></section>'
    body += f'<section class="block"><p><a href="../stocks/pool-{s["id"]}.html">进入独立股票研究页 →</a></p></section>'
    return body


def build(ctx):
    data = json.loads((Path(ctx['ROOT'])/'data/industry_research.json').read_text())
    out = Path(ctx['SITE'])/'boards'
    for market, file in [('a','index.html'),('hk','hk.html')]:
        (out/file).write_text(ctx['page'](('A 股' if market=='a' else '港股')+'板块研究','bk',hub(data,market),'../'))
    build_stock_pools(ctx)
    for s in data['sectors']:
        (out/(s['id']+'.html')).write_text(ctx['page'](s['title']+' | '+('A 股' if s['market']=='a' else '港股')+'板块','bk',detail(data,s),'../'))


def stock_pool(data, s):
    market = 'A 股' if s['market']=='a' else '港股'
    body = STYLE + f'<div class="crumb"><a href="sector-pools.html">股票研究入口</a> ／ {market} · {E(s["title"])}</div><div class="hero"><h1>{E(s["title"])} · 股票研究</h1><p class="sum">此页保留龙头观察与待选记录，尚未确定买入个股。行业判断请返回<a href="../boards/{s["id"]}.html">独立板块分析</a>。</p></div>'
    body += '<section class="block" id="leaders"><h2>龙头与细分标杆观察</h2><p class="note">先观察行业龙头，再筛选合适个股。观察身份按主营业务和行业代表性确定，不作市值或市占率排名；最终可以选择龙头，也可以选择其他公司。A/H 同一发行人的经营证据复用，估值和交易信号分别处理。</p><div class="tblwrap"><table class="mt sector-table"><thead><tr><th>观察公司 / 市场代码</th><th>为什么观察它</th><th>重点跟踪哪些动向</th><th>已核资料与日期</th></tr></thead><tbody>'
    for stock in s['stocks']:
        observation = stock['observation']
        body += f'<tr><td><b>{E(stock["name"])}</b><br>{market} {stock["code"]}<br><span class="sector-tag">{E(stock["watch_role"])}</span></td><td>{E(stock["watch_reason"])}<p class="note">业务：{E(stock["role"])}</p>{source(data,stock["leader_source"],"业务与行业地位依据")}</td><td><b>对应 {E(stock["watch_nodes"])}</b><br>{E(stock["watch"])}</td><td><b>{E(observation["date"])}</b><br>{E(observation["text"])}<br>{source(data,observation["source"],"查看已核资料")}<p class="note">{E(stock.get("other", ""))}</p></td></tr>'
    body += '</tbody></table></div></section>'
    if s.get('cross_market'):
        body += '<section class="block"><h3>跨市场龙头对照</h3><p class="note">用于比较行业供需，市场标注不同的公司不进入本市场待选池。</p>'
        for x in s['cross_market']:
            body += f'<p><b>{E(x["name"])} · {E(x["market"])} {x["code"]}</b>：{E(x["why"])} {source(data,x["source"])}</p>'
        body += '</section>'
    body += f'<section class="block" id="candidates"><h2>板块内待选股票池 · {len(s["candidates"])} 只</h2><p>{E(s["pool_note"])}</p><p class="note">研究阶段：业务连接 → C利润与现金流 → E盈利变化 → F估值 → G/H交易验证。龙头也需通过这些条件；待选不等于已选。新增初筛公司的来源入口用于继续核验，不表示已经读完财报。</p><div class="tblwrap"><table class="mt sector-table"><thead><tr><th>股票 / 研究阶段</th><th>如何承接板块逻辑</th><th>优先核什么</th><th>淘汰或退回观察条件</th></tr></thead><tbody>'
    for x in s['candidates']:
        body += f'<tr><td><b>{E(x["name"])}</b><br>{market} {x["code"]}<p class="note">{E(x["status"])}</p></td><td><b>{E(x["segment"])}</b><br>{E(x["logic"])}</td><td>{E(x["verify"])}<br>{source(data,x["source"],"资料 / 继续核验入口")}</td><td>{E(x["risk"])}</td></tr>'
    body += '</tbody></table></div></section>'
    return body


def build_stock_pools(ctx):
    data=json.loads((Path(ctx['ROOT'])/'data/sector_research.json').read_text())
    out=Path(ctx['SITE'])/'stocks';out.mkdir(exist_ok=True)
    body=STYLE+'<div class="hero"><h1>按板块进入股票研究</h1><p class="sum">行业逻辑在板块页独立分析；此处保留龙头观察、业务映射与待选池。</p></div>'
    for market,label in [('a','A 股'),('hk','港股')]:
        body+=f'<section class="block"><h2>{label}</h2><div class="sector-grid">'
        for s in data['sectors']:
            if s['market']!=market:continue
            file='pool-'+s['id']+'.html'
            (out/file).write_text(ctx['page'](s['title']+' | 股票研究','pool',stock_pool(data,s),'../'))
            body+=f'<article class="sector-card"><h3><a href="{file}">{E(s["title"])}</a></h3><p>龙头与标杆观察 {len(s["stocks"])} 条 · 待选记录 {len(s["candidates"])} 条</p></article>'
        body+='</div></section>'
    (out/'sector-pools.html').write_text(ctx['page']('股票研究入口','pool',body,'../'))
