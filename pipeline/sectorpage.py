"""当前A/H板块研究：专属A–H传导图、龙头动向观察；个股选择另行进行。"""
import html
import json
from pathlib import Path

E = html.escape
NAMES = dict(zip('ABCDEFGH', ['需求', '政策与地缘', '行业利润与现金流', '利率与风险溢价', '盈利预期修订', '估值', '资金与拥挤度', '价格验证']))
STYLE = '''<style>#framework,#leaders,.sector-node[id]{scroll-margin-top:110px}.sector-diagram-scroll{overflow-x:auto;max-width:100%;border:1px solid #d9dfe7;background:#fff;border-radius:12px;padding:10px;margin:16px 0}.sector-diagram{display:block;width:100%;min-width:860px;height:auto}.sector-card:has(details[open]){grid-column:1 / -1}.sector-preview{padding:12px 14px;background:#f1f5fa;border-radius:8px;line-height:1.8;font-size:14px}.sector-card summary{cursor:pointer;color:#24476b;font-weight:600;padding:12px 0}.sector-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.sector-card{border:1px solid #d9dfe7;border-radius:12px;padding:22px;background:#fff}.sector-card h3{margin:0 0 12px}.sector-card p{line-height:1.8}.sector-card .stocks{font-size:14px;color:#526072}.sector-verdict{border-left:4px solid #263a50;background:#f5f7fa;padding:20px 24px;font-size:19px;line-height:1.8}.sector-nodes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.sector-node{background:#fff;border:1px solid #d9dfe7;border-radius:10px;padding:20px}.sector-node h3{font-size:17px;margin:0 0 12px}.sector-node p{line-height:1.8;margin:0}.sector-table td{min-width:150px;vertical-align:top;line-height:1.7}.sector-table td:first-child{min-width:110px}.sector-chain{font-size:18px;padding:16px;background:#f3f6f9;border-radius:8px;line-height:2}.sector-evidence li{margin:12px 0;line-height:1.8}.sector-tag{font-size:13px;background:#e9eef4;border-radius:5px;padding:4px 8px;display:inline-block;margin-bottom:12px}@media(max-width:700px){.sector-grid,.sector-nodes{grid-template-columns:1fr}.sector-card{padding:18px}.sector-verdict{padding:16px;font-size:17px}}</style>'''


def switch(market):
    return '<nav class="market-switch" aria-label="板块市场">' + ''.join(f'<a href="{url}"'+(' aria-current="page"' if m == market else '')+f'>{name}</a>' for m,url,name in [('a','index.html','A 股板块'),('hk','hk.html','港股板块')])+'</nav>'


def source(data, key, label='查看原始资料'):
    return f'<a href="{E(data["sources"][key], quote=True)}" target="_blank" rel="noopener noreferrer">{E(label)}</a>'



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
    body += '<p class="note">板块分档继承大盘 A–H 判断。先观察龙头与细分标杆的经营动向，了解行业变化，再在板块内筛选合适个股；最终不一定选龙头。每个板块均可展开完整传导框架。</p>'
    for tier in ['主要方向','条件看好']:
        group = [s for s in items if s['tier'] == tier]
        body += f'<section class="block"><h2>{tier} · {len(group)} 个方向</h2><div class="sector-grid">'
        for s in group:
            names = '；'.join(f'{x["name"]} {x["code"]}' for x in s['stocks'])
            body += f'<article class="sector-card"><h3><a href="{s["id"]}.html">{E(s["title"])}</a></h3><p><b>{E(s["thesis"])}</b></p><p class="stocks">龙头 / 标杆观察：{E(names)}</p><div class="sector-preview"><b>A/B → C → E/F</b><br>{E(s["diagram"]["A"][0])} → {E(s["diagram"]["C"][0])} → {E(s["diagram"]["F"][0])}</div><p><strong>验证重点：</strong>{E(s["metrics"])}</p><details><summary>展开本板块 A–H 传导框架</summary>{diagram(s, s["id"]+".html", "hub")}<p class="note">颜色区分经营路径、定价约束与市场反馈；不表示利好或利空。手机可横向滑动，点击节点进入详细分析。</p></details><a href="{s["id"]}.html">查看板块分析与龙头动向 →</a></article>'
        body += '</div></section>'
    body += f'<section class="block"><h2>本轮资料范围</h2><p class="note">{E(data["coverage"])}。E 的完整一致预期、F 的历史估值、G/H 的细分组合数据仍按各节注明的口径处理。</p></section>'
    return body


def detail(data, s):
    market = 'A 股' if s['market'] == 'a' else '港股'
    back = 'index.html' if s['market'] == 'a' else 'hk.html'
    body = STYLE + switch(s['market']) + f'<div class="crumb"><a href="{back}">{market}板块</a> ／ {E(s["title"])}</div><div class="hero"><span class="sector-tag">{market} · {s["tier"]}</span><h1>{E(s["title"])}</h1><p class="stamp">更新 {data["as_of"]} · 判断窗口 {data["window"]}</p><p class="sector-verdict"><b>{E(s["thesis"])}</b></p></div>'
    body += f'<section class="block" id="framework"><h2>板块 A–H 传导框架</h2><p class="note">每个节点使用本板块具体变量。蓝色为经营传导，浅金色为定价约束，灰色为资金与价格反馈；颜色不代表涨跌评分。点击节点查看下方依据，手机可横向滑动。</p>{diagram(s)}<p class="note">本板块重点链条：{E(s["chain"])}。H → G 是价格对交易行为的反馈；股价上涨不能倒推经营改善，也不能替代 C/E 验证。</p><h3>逐节点分析</h3><div class="sector-nodes">'
    for k, val in s['nodes'].items():
        body += f'<article class="sector-node" id="node-{k}"><h3>{k} · {NAMES[k]}</h3><p>{E(val)}</p></article>'
    body += '</div></section><section class="block"><h2>已核到的证据与反证</h2><ul class="sector-evidence">'
    for fact in s['facts']:
        body += f'<li><b>{E(fact["date"])}</b> · {E(fact["text"])} {source(data,fact["source"])}</li>'
    body += '</ul><p class="note">个别公司样本用于验证传导环节，不外推成整个板块的合计业绩。</p></section>'
    body += '<section class="block" id="leaders"><h2>龙头与细分标杆观察</h2><p class="note">先观察行业龙头，再筛选合适个股。观察身份按主营业务和行业代表性确定，不作市值或市占率排名；最终可以选择龙头，也可以选择其他公司。A/H 同一发行人的经营证据复用，估值和交易信号分别处理。</p><div class="tblwrap"><table class="mt sector-table"><thead><tr><th>观察公司 / 市场代码</th><th>为什么观察它</th><th>重点跟踪哪些动向</th><th>已核资料与日期</th></tr></thead><tbody>'
    for stock in s['stocks']:
        observation = stock['observation']
        body += f'<tr><td><b>{E(stock["name"])}</b><br>{market} {stock["code"]}<br><span class="sector-tag">{E(stock["watch_role"])}</span></td><td>{E(stock["watch_reason"])}<p class="note">业务：{E(stock["role"])}</p>{source(data,stock["leader_source"],"业务与行业地位依据")}</td><td><b>对应 {E(stock["watch_nodes"])}</b><br>{E(stock["watch"])}</td><td><b>{E(observation["date"])}</b><br>{E(observation["text"])}<br>{source(data,observation["source"],"查看已核资料")}<p class="note">{E(stock.get("other", ""))}</p></td></tr>'
    body += '</tbody></table></div></section>'
    body += f'<section class="block"><h2>未来半年如何跟踪</h2><div class="sector-nodes"><article class="sector-node"><h3>保持 / 升级条件</h3><p>{E(s["upgrade"])}</p></article><article class="sector-node"><h3>降级 / 失效条件</h3><p>{E(s["down"])}</p></article></div><p><b>跟踪频率：</b>{E(s["metrics"])}</p></section>'
    refs = list(dict.fromkeys(s['refs']+[f['source'] for f in s['facts']]+[x['source'] for x in s['stocks']]))
    body += '<section class="block"><h2>关联资料</h2><p>'+' · '.join(source(data,k,f'资料 {i+1}') for i,k in enumerate(refs))+'</p><p class="note">'+E(data['coverage'])+'。</p></section>'
    return body


def build(ctx):
    data = json.loads((Path(ctx['ROOT'])/'data/sector_research.json').read_text())
    out = Path(ctx['SITE'])/'boards'
    for market, file in [('a','index.html'),('hk','hk.html')]:
        (out/file).write_text(ctx['page'](('A 股' if market=='a' else '港股')+'板块研究','bk',hub(data,market),'../'))
    for s in data['sectors']:
        (out/(s['id']+'.html')).write_text(ctx['page'](s['title']+' | '+('A 股' if s['market']=='a' else '港股')+'板块','bk',detail(data,s),'../'))
