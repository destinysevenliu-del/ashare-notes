"""当前A/H板块研究；范围严格继承大盘半年判断，个股仅作业务映射。"""
import html
import json
from pathlib import Path

E = html.escape
NAMES = dict(zip('ABCDEFGH', ['需求', '政策与地缘', '行业利润与现金流', '利率与风险溢价', '盈利预期修订', '估值', '资金与拥挤度', '价格验证']))
STYLE = '''<style>.sector-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.sector-card{border:1px solid #d9dfe7;border-radius:12px;padding:22px;background:#fff}.sector-card h3{margin:0 0 12px}.sector-card p{line-height:1.8}.sector-card .stocks{font-size:14px;color:#526072}.sector-verdict{border-left:4px solid #263a50;background:#f5f7fa;padding:20px 24px;font-size:19px;line-height:1.8}.sector-nodes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.sector-node{background:#fff;border:1px solid #d9dfe7;border-radius:10px;padding:20px}.sector-node h3{font-size:17px;margin:0 0 12px}.sector-node p{line-height:1.8;margin:0}.sector-table td{min-width:150px;vertical-align:top;line-height:1.7}.sector-table td:first-child{min-width:110px}.sector-chain{font-size:18px;padding:16px;background:#f3f6f9;border-radius:8px;line-height:2}.sector-evidence li{margin:12px 0;line-height:1.8}.sector-tag{font-size:13px;background:#e9eef4;border-radius:5px;padding:4px 8px;display:inline-block;margin-bottom:12px}@media(max-width:700px){.sector-grid,.sector-nodes{grid-template-columns:1fr}.sector-card{padding:18px}.sector-verdict{padding:16px;font-size:17px}}</style>'''


def switch(market):
    return '<nav class="market-switch" aria-label="板块市场">' + ''.join(f'<a href="{url}"'+(' aria-current="page"' if m == market else '')+f'>{name}</a>' for m,url,name in [('a','index.html','A 股板块'),('hk','hk.html','港股板块')])+'</nav>'


def source(data, key, label='查看原始资料'):
    return f'<a href="{E(data["sources"][key], quote=True)}" target="_blank" rel="noopener noreferrer">{E(label)}</a>'


def hub(data, market):
    items = [s for s in data['sectors'] if s['market'] == market]
    name = 'A 股' if market == 'a' else '港股'
    outlook = '../index.html#horizon' if market == 'a' else '../hk/index.html#horizon'
    summary = ('主要方向是煤炭现金回报和油运盈利；半导体、计算机设备、创新药、化学原料、铜和电网设备条件看好，重点验证订单、价差、利润及现金兑现。'
               if market == 'a' else '主要方向是电信现金回报、能源生产和油运；互联网与半导体、算力硬件条件看好，盈利兑现与美元利率、港元流动性共同决定估值空间。')
    body = STYLE + switch(market) + f'<div class="hero"><h1>{name}板块研究</h1><p class="sum">{E(summary)}</p><p class="stamp">研究更新 {data["as_of"]} · 判断窗口 {data["window"]} · <a href="{outlook}">回看大盘六个月判断</a></p></div>'
    body += '<p class="note">板块分档继承大盘 A–H 判断。对应股票用于看清业务与传导，不代表已经选定的个股或仓位；每个板块可展开查看证据、完整 A–H 分析和失效条件。</p>'
    for tier in ['主要方向','条件看好']:
        group = [s for s in items if s['tier'] == tier]
        body += f'<section class="block"><h2>{tier} · {len(group)} 个方向</h2><div class="sector-grid">'
        for s in group:
            names = '；'.join(f'{x["name"]} {x["code"]}' for x in s['stocks'])
            body += f'<article class="sector-card"><h3><a href="{s["id"]}.html">{E(s["title"])}</a></h3><p><b>{E(s["thesis"])}</b></p><p class="stocks">对应股票：{E(names)}</p><p><strong>验证重点：</strong>{E(s["metrics"])}</p><a href="{s["id"]}.html">展开传导、证据与公司业务 →</a></article>'
        body += '</div></section>'
    body += f'<section class="block"><h2>本轮资料范围</h2><p class="note">{E(data["coverage"])}。E 的完整一致预期、F 的历史估值、G/H 的细分组合数据仍按各节注明的口径处理。</p></section>'
    return body


def detail(data, s):
    market = 'A 股' if s['market'] == 'a' else '港股'
    back = 'index.html' if s['market'] == 'a' else 'hk.html'
    body = STYLE + switch(s['market']) + f'<div class="crumb"><a href="{back}">{market}板块</a> ／ {E(s["title"])}</div><div class="hero"><span class="sector-tag">{market} · {s["tier"]}</span><h1>{E(s["title"])}</h1><p class="stamp">更新 {data["as_of"]} · 判断窗口 {data["window"]}</p><p class="sector-verdict"><b>{E(s["thesis"])}</b></p></div>'
    body += f'<section class="block"><h2>判断如何传导</h2><div class="sector-chain">A 需求 ＋ B 政策 → C 利润与现金流 → E 盈利预期<br>D 利率与风险溢价 → F 估值；E、F 与 G 资金共同影响 H 价格</div><p class="note">本板块重点链条：{E(s["chain"])}。H 用来检验市场反馈，不能倒推经营改善；G/H 走强也不能替代 C/E。</p><div class="sector-nodes">'
    for k, val in s['nodes'].items():
        body += f'<article class="sector-node" id="node-{k}"><h3>{k} · {NAMES[k]}</h3><p>{E(val)}</p></article>'
    body += '</div></section><section class="block"><h2>已核到的证据与反证</h2><ul class="sector-evidence">'
    for fact in s['facts']:
        body += f'<li><b>{E(fact["date"])}</b> · {E(fact["text"])} {source(data,fact["source"])}</li>'
    body += '</ul><p class="note">个别公司样本用于验证传导环节，不外推成整个板块的合计业绩。</p></section>'
    body += '<section class="block"><h2>对应股票与业务边界</h2><p class="note">代表性业务映射，非完整成分表或已确定持仓。A/H 同一发行人的经营证据可以复用，股价、流动性、币种和估值分别处理。</p><div class="tblwrap"><table class="mt sector-table"><thead><tr><th>公司 / 市场代码</th><th>对应业务</th><th>继续核什么</th><th>资料与边界</th></tr></thead><tbody>'
    for stock in s['stocks']:
        body += f'<tr><td><b>{E(stock["name"])}</b><br>{market} {stock["code"]}</td><td>{E(stock["role"])}</td><td>{E(stock["watch"])}</td><td>{source(data,stock["source"],"业务与财报依据")}<br>{E(stock.get("other", ""))}</td></tr>'
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
