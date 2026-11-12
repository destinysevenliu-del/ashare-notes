"""Overview reads a single macro summary; sector conclusions stay on sector pages."""
import json
from pathlib import Path
from html import escape as E

def diagram(nodes):
    pos={'B':(360,15),'A':(35,155),'C':(35,295),'D':(685,155),'E':(35,435),'F':(360,435),'G':(685,435),'H':(360,590)}
    edges=[('B','A','M360 60 H165 V155'),('B','C','M400 105 V265 H200 V295'),('B','D','M620 60 H815 V155'),('A','C','M165 245 V295'),('A','D','M295 200 H685'),('C','E','M165 385 V435'),('D','F','M815 245 V405 H490 V435'),('E','F','M295 480 H360'),('E','H','M165 525 V635 H360'),('F','H','M490 525 V590'),('G','H','M815 525 V635 H620')]
    out='<svg class="macro-flow" viewBox="0 0 1000 720" role="img" aria-label="政策与需求经盈利预期、估值和交易约束传到价格"><defs><marker id="macro-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#8798a9"/></marker></defs>'
    for a,b,path in edges:out+=f'<path data-edge="{a}-{b}" d="{path}" fill="none" stroke="#8798a9" stroke-width="1.5" marker-end="url(#macro-arrow)"/>'
    out+='<path data-edge="H-G" d="M620 660 H985 V560 H865 V525" fill="none" stroke="#ad843b" stroke-dasharray="5 4" marker-end="url(#macro-arrow)"/><text x="660" y="700" font-size="13" fill="#896626">价格反馈：只进入下一期观察</text>'
    for n in nodes:
        k=n['key'];x,y=pos[k];dark=k=='H'
        out+=f'<a href="#thesis-{k}"><rect x="{x}" y="{y}" width="260" height="90" rx="8" fill="'+('#21394e' if dark else '#f1f5f9')+'" stroke="#b8c8d8"/>'
        text=k+' · '+n['title'];parts=[text[:16],text[16:]] if len(text)>17 else [text]
        for i,line in enumerate(parts):out+=f'<text x="{x+14}" y="{y+34+i*22}" fill="'+('#fff' if dark else '#263b50')+'" font-size="16">'+E(line)+'</text>'
        out+='</a>'
    return out+'</svg>'

def render(ctx,market):
    d=json.loads((Path(ctx['ROOT'])/'data/market_thesis.json').read_text());m=d['markets'][market];v=m['macro_overview'];prefix='' if market=='a' else '../'
    def refs(keys):
        return '<p class="src">'+' · '.join('<a href="'+E(d['sources'][k]['url'] if d['sources'][k]['url'].startswith('https://') else prefix+d['sources'][k]['url'],quote=True)+'">'+E(d['sources'][k]['title'])+'</a>' for k in keys)+'</p>'
    out='<section id="macro-verdict"><div class="overview-thesis"><h3>'+E(v['verdict'])+'</h3><p>'+E(v['synthesis'])+'</p></div><div class="overview-decisions">'
    for key,title in [('profit','盈利方向'),('valuation','估值方向'),('constraint','近期组合节奏 · D/G')]:
        item=v[key];out+='<article><span>'+title+'</span><h3>'+E(item['title'])+'</h3><p>'+E(item['text'])+'</p></article>'
    out+='</div><p class="overview-change"><b>本次变化：</b>'+E(v['change'])+'</p></section><section id="macro-basis"><h3 class="h3s">决定判断的三组证据</h3><div class="overview-evidence">'
    for e in v['evidence']:out+='<article><h4>'+E(e['title'])+'</h4><p>'+E(e['text'])+'</p>'+refs(e['refs'])+'</article>'
    out+='</div></section><section id="macro-scenarios" class="overview-conditions"><div><b>什么会让我上调判断</b><p>'+E(v['upgrade'])+'</p></div><div><b>什么会让我下调判断</b><p>'+E(v['downgrade'])+'</p></div></section>'
    board=prefix+('boards/index.html' if market=='a' else 'boards/hk.html')
    out+='<section class="next-step" id="sector-review"><div><b>下一步：比较板块</b><p>在这个市场环境下，比较各板块的盈利来源、估值位置和兑现条件。</p></div><a href="'+board+'">进入'+m['label']+'板块 →</a></section>'
    out+='<details class="deep-research" id="macro-research"><summary>展开完整研究：传导图、节点分工与证据边界</summary><p class="note">'+E(v['boundary'])+'</p><section id="macro-map"><h3>A–H研究推导顺序</h3><p class="note">实线用于组织本期研究，不代表经济没有反馈。E和D共同影响F；盈利也直接影响价格，因此保留E→H。F表示重估约束，不用当前PE循环解释当前价格。</p><div class="macro-flow-wrap">'+diagram(m['macro_nodes'])+'</div></section><section id="thesis-nodes"><div class="thesis-grid">'
    for n in m['macro_nodes']:
        out+='<article id="thesis-'+n['key']+'"><h3>'+n['key']+' · '+E(n['title'])+'</h3><p><b>职能：</b>'+E(n['role'])+'</p><p>'+E(n['fact'])+'</p><p class="note"><b>解释边界：</b>'+E(n['limit'])+'</p>'+refs(n['refs'])+'</article>'
    out+='</div></section><p class="note">研究窗口 '+E(d['window'])+'；'+E(d['audit'])+'</p><p><a href="'+prefix+'research/market-verdict-2026-11-13.md">查看本次综合判断与修订理由</a> · <a href="'+prefix+'research/market-thesis-2026-11-12.md">11月12日历史研究</a> · <a href="'+prefix+'data/market_thesis.json">数据与来源</a></p></details>'
    return '<style>\n.overview-thesis{border-left:4px solid #365875;padding:4px 0 4px 18px;margin:18px 0 24px}.overview-thesis h3{font:600 21px/1.65 var(--sans);color:#223e57;margin:0 0 10px}.overview-thesis p{font-size:15px;line-height:1.9;margin:0;max-width:1250px}\n</style>'+out
