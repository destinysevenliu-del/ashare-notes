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

def research_sections(m, refs):
    r=m['macro_research']
    out='<section id="macro-earnings"><h3>先把盈利对象与口径说清楚</h3><p class="note">'+E(r['target'])+'</p><div class="tblwrap"><table class="mt macro-audit-table"><thead><tr><th>观察项</th><th>数据</th><th>样本与期间</th><th>对判断的作用</th></tr></thead><tbody>'
    for x in r['financial_rows']:
        out+='<tr><th scope="row">'+E(x['metric'])+'</th><td><b>'+E(x['value'])+'</b></td><td>'+E(x['universe'])+'<br><span class="note">'+E(x['period'])+'</span></td><td>'+E(x['meaning'])+refs(x['refs'])+'</td></tr>'
    out+='</tbody></table></div></section><section id="macro-causal"><h3>从事实到半年判断：每一步如何成立</h3><div class="macro-chain-grid">'
    for x in r['chains']:
        out+='<article><h4>'+E(x['path'])+'</h4>'
        for k,label in [('observation','已知事实'),('mechanism','传导机制'),('assumption','未来假设'),('result','推导结果')]:out+='<p><b>'+label+'：</b>'+E(x[k])+'</p>'
        out+=refs(x['refs'])+'</article>'
    out+='</div></section><section id="macro-pricing" class="macro-chain-grid"><article><h3>反向证据怎样改变判断</h3><p>'+E(r['opposing'])+'</p></article><article><h3>价格已经反映了多少</h3><p>'+E(r['pricing'])+'</p></article></section><section id="macro-scenario-detail"><h3>未来半年：基准、上调与下调</h3><p class="note">以下是研究情景，不是概率模型；没有为数据缺口编造概率、指数目标或盈利增速。</p><div class="macro-scenario-grid">'
    for x in r['scenarios']:
        out+='<article><h4>'+E(x['name'])+'</h4>'
        for k,label in [('conditions','前提'),('earnings','盈利'),('valuation','估值'),('review','验证')]:out+='<p><b>'+label+'：</b>'+E(x[k])+'</p>'
        out+='</article>'
    out+='</div><p class="note"><b>验证时间：</b>'+E(r['next_check'])+'</p></section>'
    return out

def export_research(root, d):
    root=Path(root)
    out=['# A股与港股：上市公司盈利与半年判断重写','','复核：'+d['overview_reviewed_at']+'；研究窗口：'+d['window'],'','本版取代此前由工业利润推导A股盈利、由内需背景推导恒指修复的表述。布局不变，研究基准重建；数据日期不随复核日刷新。']
    def cite(keys):
        return '；'.join('['+d['sources'][k]['title']+']('+('../'+d['sources'][k]['url'] if not d['sources'][k]['url'].startswith('https://') else d['sources'][k]['url'])+')' for k in keys)
    for m in d['markets'].values():
        v=m['macro_overview'];r=m['macro_research']
        out+=['','## '+m['label'],'',v['verdict'],'',v['synthesis'],'','### 三个决策维度']
        for k in ['profit','valuation','constraint']:out+=['','**'+v[k]['title']+'**','',v[k]['text']]
        for e in v['evidence']:out+=['','### '+e['title'],'',e['text'],'',cite(e['refs'])]
        out+=['','### 盈利底稿','','研究对象：'+r['target'],'','| 观察项 | 数据 | 样本 | 期间 | 解释与来源 |','|---|---|---|---|---|']
        for x in r['financial_rows']:out+=['| '+' | '.join(x[k].replace('|','／') for k in ['metric','value','universe','period'])+' | '+x['meaning']+' '+cite(x['refs'])+' |']
        for x in r['chains']:
            out+=['','### '+x['path']]
            for k,label in [('observation','事实'),('mechanism','机制'),('assumption','假设'),('result','结论')]:out+=['',label+'：'+x[k]]
            out+=['',cite(x['refs'])]
        for k,label in [('opposing','反向证据'),('pricing','价格反映'),('next_check','验证时间')]:out+=['','### '+label,'',r[k]]
        for x in r['scenarios']:
            out+=['','### '+x['name']]
            for k in ['conditions','earnings','valuation','review']:out+=['',x[k]]
        out+=['','上调条件：'+v['upgrade'],'','下调条件：'+v['downgrade'],'','边界：'+v['boundary']]
        for n in m['macro_nodes']:out+=['','#### '+n['key']+' · '+n['title'],'',n['role'],'',n['fact'],'',n['limit'],'',cite(n['refs'])]
    used=set()
    for m in d['markets'].values():
        for x in m['macro_overview']['evidence']+m['macro_nodes']+m['macro_research']['financial_rows']+m['macro_research']['chains']:used.update(x['refs'])
    out+=['','## 来源与证据等级','','协会及券商的署名转载已核对正文，但未取得其底层全样本财务和预测数据库，不称为本站独立复算。指数、资金留档重算另见站内数据文件。']
    for k in sorted(used):
        x=d['sources'][k];out+=['','- '+cite([k])+' · '+x['date']+'。'+x['scope']]
    (root/'docs/research/market-verdict-2026-11-13.md').write_text('\n'.join(out)+'\n')


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
    out+='<details class="deep-research" id="macro-research"><summary>展开完整研究：上市公司盈利底稿、逐步推导与情景检验</summary><p class="note">'+E(v['boundary'])+'</p>'+research_sections(m,refs)+'<section id="macro-map"><h3>A–H研究推导顺序</h3><p class="note">实线表示本期检验顺序，并非已完成的因果识别。B既影响需求，也可通过利息直接影响C；金融投资损益中的历史价格影响单独解释，不循环记为需求利好。E与D影响估值，E与F共同决定价格，因此保留E→H。H→G只进入下一期观察。</p><div class="macro-flow-wrap">'+diagram(m['macro_nodes'])+'</div></section><details id="macro-node-definitions"><summary>查看A–H节点职能与口径</summary><section id="thesis-nodes"><div class="thesis-grid">'
    for n in m['macro_nodes']:
        out+='<article id="thesis-'+n['key']+'"><h3>'+n['key']+' · '+E(n['title'])+'</h3><p><b>职能：</b>'+E(n['role'])+'</p><p>'+E(n['fact'])+'</p><p class="note"><b>解释边界：</b>'+E(n['limit'])+'</p>'+refs(n['refs'])+'</article>'
    out+='</div></section></details><p class="note">研究窗口 '+E(d['window'])+'；'+E('本轮复核 '+d['overview_reviewed_at']+'；财报、预测、行情分开标日。')+'</p><p><a href="'+prefix+'research/market-verdict-2026-11-13.md">查看本次综合判断与修订理由</a> · <a href="'+prefix+'research/market-thesis-2026-11-12.md">11月12日历史研究</a> · <a href="'+prefix+'data/market_thesis.json">数据与来源</a></p></details>'
    return '<style>\n.macro-audit-table{min-width:850px;table-layout:fixed;width:100%}.macro-audit-table th:first-child{width:18%}.macro-audit-table th:nth-child(2){width:23%}.macro-audit-table th:nth-child(3){width:27%}.macro-audit-table td{vertical-align:top}.macro-chain-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:24px 0}.macro-chain-grid article,.macro-scenario-grid article{border:1px solid #d4dfeb;border-radius:8px;padding:22px;background:#fff}.macro-chain-grid h4,.macro-scenario-grid h4{margin:0 0 14px;font-size:17px}.macro-chain-grid p,.macro-scenario-grid p{line-height:1.85}.macro-scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}#macro-node-definitions{margin:24px 0}#macro-node-definitions>summary{cursor:pointer;font-weight:600;padding:16px;background:#f3f6f9}@media(max-width:900px){.macro-chain-grid,.macro-scenario-grid{grid-template-columns:1fr}}\n.overview-thesis{border-left:4px solid #365875;padding:4px 0 4px 18px;margin:18px 0 24px}.overview-thesis h3{font:600 21px/1.65 var(--sans);color:#223e57;margin:0 0 10px}.overview-thesis p{font-size:15px;line-height:1.9;margin:0;max-width:1250px}\n</style>'+out
