"""Overview reads a single macro summary; sector conclusions stay on sector pages."""
import json
from pathlib import Path
from html import escape as E

def diagram(nodes):
    pos={'B':(340,15),'A':(30,155),'C':(30,295),'D':(630,155),'E':(30,435),'F':(630,435)}
    paths=[('B-A','M340 60 H160 V155'),('B-C','M380 105 V265 H160 V295'),('B-D','M600 60 H760 V155'),('A-C','M160 245 V295'),('A-D','M290 200 H630'),('C-E','M160 385 V435'),('D-F','M760 245 V435'),('E-F','M290 480 H630'),('E-result','M160 525 V650 H340'),('F-result','M760 525 V650 H600')]
    out='<svg class="macro-flow" viewBox="0 0 920 730" role="img" aria-label="半年主线：政策与需求传导到盈利，利率与盈利共同决定估值情景"><defs><marker id="macro-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#8798a9"/></marker></defs>'
    for key,path in paths:out+='<path data-edge="'+key+'" d="'+path+'" fill="none" stroke="#8798a9" stroke-width="1.5" marker-end="url(#macro-arrow)"/>'
    for n in nodes:
        if n['key'] not in pos:continue
        k=n['key'];x,y=pos[k];title=k+' · '+n['title'];parts=[title[:16],title[16:]] if len(title)>17 else [title]
        out+=f'<a href="#thesis-{k}"><rect x="{x}" y="{y}" width="260" height="90" rx="8" fill="#f1f5f9" stroke="#b8c8d8"/>'
        for i,line in enumerate(parts):out+=f'<text x="{x+14}" y="{y+34+i*22}" fill="#263b50" font-size="16">'+E(line)+'</text>'
        out+='</a>'
    out+='<rect x="340" y="610" width="260" height="80" rx="8" fill="#21394e"/><text x="360" y="642" fill="#fff" font-size="18">半年判断：盈利 × 估值</text><text x="360" y="670" fill="#fff" font-size="14">基准情景 · 看多 / 看空触发</text></svg>'
    return out

def research_sections(m, refs):
    r=m['macro_research']
    out='<section id="macro-earnings"><h3>上市公司盈利底稿</h3><p class="note">'+E(r['target'])+'</p><div class="tblwrap"><table class="mt macro-audit-table"><thead><tr><th>观察项</th><th>数据</th><th>样本与期间</th><th>对判断的作用</th></tr></thead><tbody>'
    for x in r['financial_rows']:
        out+='<tr><th scope="row">'+E(x['metric'])+'</th><td><b>'+E(x['value'])+'</b></td><td>'+E(x['universe'])+'<br><span class="note">'+E(x['period'])+'</span></td><td>'+E(x['meaning'])+refs(x['refs'])+'</td></tr>'
    out+='</tbody></table></div></section><section id="macro-causal"><h3>从事实到半年判断：每一步如何成立</h3><div class="macro-chain-grid">'
    for x in r['chains']:
        out+='<article><h4>'+E(x['path'])+'</h4>'
        for k,label in [('observation','已知事实'),('mechanism','传导机制'),('assumption','未来假设'),('result','推导结果')]:out+='<p><b>'+label+'：</b>'+E(x[k])+'</p>'
        out+=refs(x['refs'])+'</article>'
    out+='</div></section><section id="macro-pricing" class="macro-chain-grid"><article><h3>两股力量如何权衡</h3><p>'+E(r['opposing'])+'</p></article><article><h3>估值基准与上下行情景</h3><p>'+E(r['pricing'])+'</p></article></section><section id="macro-scenario-detail"><h3>未来半年：基准、上调与下调</h3><p class="note">基准情景随新增证据更新；触发条件分别对应盈利与估值。</p><div class="macro-scenario-grid">'
    for x in r['scenarios']:
        out+='<article><h4>'+E(x['name'])+'</h4>'
        for k,label in [('conditions','前提'),('earnings','盈利'),('valuation','估值'),('review','验证')]:out+='<p><b>'+label+'：</b>'+E(x[k])+'</p>'
        out+='</article>'
    out+='</div><p class="note"><b>验证时间：</b>'+E(r['next_check'])+'</p></section>'
    return out

def export_research(root, d):
    root=Path(root)
    out=['# A股与港股：上市公司盈利与半年判断重写','','复核：'+d['overview_reviewed_at']+'；研究窗口：'+d['window'],'','半年主线：政策与需求→非金融盈利→估值情景；金融利润单独解释总量贡献。短期交易约束独立呈现。']
    def cite(keys):
        return '；'.join('['+d['sources'][k]['title']+']('+('../'+d['sources'][k]['url'] if not d['sources'][k]['url'].startswith('https://') else d['sources'][k]['url'])+')' for k in keys)
    for m in d['markets'].values():
        v=m['macro_overview'];r=m['macro_research']
        out+=['','## '+m['label'],'',v['verdict'],'',v['synthesis'],'','### 两条半年主线']
        for k in ['profit','valuation']:out+=['','**'+v[k]['title']+'**','',v[k]['text']]
        out+=['','看多触发：'+v['upgrade'],'','看空触发：'+v['downgrade']]
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
        out+=['','### 独立短期交易观察','',v['constraint']['title'],'',v['constraint']['text']]
        for n in m['macro_nodes']:out+=['','#### '+n['key']+' · '+n['title'],'',n['role'],'',n['fact'],'',n['limit'],'',cite(n['refs'])]
    used=set()
    for m in d['markets'].values():
        for x in m['macro_overview']['evidence']+[m['macro_overview']['profit'],m['macro_overview']['valuation']]+m['macro_nodes']+m['macro_research']['financial_rows']+m['macro_research']['chains']:used.update(x['refs'])
    out+=['','## 来源与证据等级','','协会及券商的署名转载已核对正文，但未取得其底层全样本财务和预测数据库，不称为本站独立复算。指数、资金留档重算另见站内数据文件。']
    for k in sorted(used):
        x=d['sources'][k];out+=['','- '+cite([k])+' · '+x['date']+'。'+x['scope']]
    (root/'docs/research/market-verdict-2026-11-13.md').write_text('\n'.join(out)+'\n')


def load_context(ctx,market):
    d=json.loads((Path(ctx['ROOT'])/'data/market_thesis.json').read_text());m=d['markets'][market];prefix='' if market=='a' else '../'
    def refs(keys):
        return '<p class="src">'+' · '.join('<a href="'+E(d['sources'][k]['url'] if d['sources'][k]['url'].startswith('https://') else prefix+d['sources'][k]['url'],quote=True)+'">'+E(d['sources'][k]['title'])+'</a>' for k in keys)+'</p>'
    return d,m,prefix,refs

def node_card(n,refs):
    return '<article id="thesis-'+n['key']+'"><h3>'+n['key']+' · '+E(n['title'])+'</h3><p><b>职能：</b>'+E(n['role'])+'</p><p>'+E(n['fact'])+'</p>'+refs(n['refs'])+'</article>'

def render_execution(ctx,market):
    d,m,prefix,refs=load_context(ctx,market);v=m['macro_overview'];x=v['constraint']
    out='<details class="l1 execution-only" id="execution-constraints"><summary><h2>短期交易观察</h2><span class="l1hint">G/H · 筹码、节奏与价格 · 独立于半年主线</span></summary><div class="execution-lead"><h3>'+E(x['title'])+'</h3><p>'+E(x['text'])+'</p></div><div class="thesis-grid">'
    for n in m['macro_nodes']:
        if n['key'] in 'GH':out+=node_card(n,refs)
    return out+'</div><p><a href="'+prefix+'stocks/portfolio.html">查看组合约束 →</a></p></details>'

def legacy(ctx,market):
    d,m,prefix,refs=load_context(ctx,market);v=m['macro_overview']
    out='<section id="macro-verdict" class="verdict-layout"><div class="overview-thesis"><span class="view-label">当前研究基准</span><h3>'+E(v['verdict'])+'</h3><p>'+E(v['synthesis'])+'</p><p class="signal-status">'+E(v['signals']['status'])+'</p></div><aside id="macro-scenarios" class="verdict-signals" aria-label="看多与看空触发条件">'
    for key in ['up','down']:
        x=v['signals'][key];out+='<article class="signal-'+key+'"><h4>'+E(x['title'])+'</h4><p>'+E(x['text'])+'</p><small>'+E(x['follow'])+'</small></article>'
    out+='</aside></section><section class="overview-decisions half-year-pillars" aria-label="两条半年主线">'
    for key,title in [('profit','基本面 · A/B→C→E'),('valuation','估值面 · D/E→F')]:
        x=v[key];out+='<article><span>'+title+'</span><h3>'+E(x['title'])+'</h3><p>'+E(x['text'])+'</p>'+refs(x['refs'])+'</article>'
    out+='</section><section id="macro-basis"><h3 class="h3s">未来半年，驱动力怎样传到盈利和估值</h3><div class="overview-evidence">'
    for x in v['evidence']:out+='<article><h4>'+E(x['title'])+'</h4><p>'+E(x['text'])+'</p>'+refs(x['refs'])+'</article>'
    out+='</div></section>'
    board=prefix+('boards/index.html' if market=='a' else 'boards/hk.html')
    out+='<section class="next-step" id="sector-review"><div><b>下一步：比较板块的盈利兑现</b><p>沿着需求、订单、利润与估值，比较各板块在这个半年基准下的机会。</p></div><a href="'+board+'">进入'+m['label']+'板块 →</a></section>'
    out+='<details class="deep-research" id="macro-research"><summary>展开研究：政策落实、盈利底稿与逐步推导</summary>'+research_sections(m,refs)+'<section id="macro-map"><h3>半年传导主线</h3><p class="note">A/B决定需求与融资条件，C/E推导未来盈利，D/E决定估值情景。G/H短期交易观察单列在下方。</p><div class="macro-flow-wrap">'+diagram(m['macro_nodes'])+'</div></section><details id="macro-node-definitions"><summary>查看A–F节点分工</summary><section id="thesis-nodes"><div class="thesis-grid">'
    for n in m['macro_nodes']:
        if n['key'] not in 'GH':out+=node_card(n,refs)
    out+='</div></section></details><details id="macro-method"><summary>数据口径、观察规则与来源说明</summary><p>'+E(v['boundary'])+'</p>'
    for n in m['macro_nodes']:
        if n['key'] not in 'GH':out+='<p><b>'+n['key']+'：</b>'+E(n['limit'])+'</p>'
    if market=='a':out+='<p>Q3贡献近似计算：上年同期金融利润占比=(11.4−(−10.7))/(11.4−(−29.9))≈53.5%；金融贡献≈53.5%×(−29.9%)=−16.0个百分点；非金融贡献≈46.5%×11.4%=+5.3个百分点。使用中金同源舍入同比，仅用于本季贡献分解。</p>'
    out+='<p>观察规则：订单使用连续两个月和50分界；盈利修订比较同一预测年度、同一覆盖样本。先行信号用于调整研究观点，后续财报确认持续性。港股2026与2027预期分别保留。</p><p class="note">研究窗口 '+E(d['window'])+'；复核 '+E(d['overview_reviewed_at'])+'。财报、预测、估值各自保留数据日。</p><p><a href="'+prefix+'research/market-verdict-2026-11-13.md">完整研究与来源</a> · <a href="'+prefix+'research/market-thesis-2026-11-12.md">11月12日历史研究</a> · <a href="'+prefix+'data/market_thesis.json">研究数据</a></p></details></details>'
    return '<style>'+CSS+'</style>'+out

CSS = """
.verdict-layout{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(340px,1fr);gap:28px;margin:20px 0 24px;align-items:start}
.overview-thesis{border-left:4px solid #365875;padding:5px 0 5px 20px}.view-label{font-size:12px;color:#64798d}.overview-thesis h3{font:600 23px/1.6 var(--sans);color:#223e57;margin:8px 0 15px}.overview-thesis p{font-size:15px;line-height:1.95;margin:0}.overview-thesis .signal-status{font-size:13px;color:#52687b;margin-top:16px}
.verdict-signals{display:grid;gap:12px}.verdict-signals article{padding:16px 18px;border:1px solid #ccd9e5;border-left:4px solid;border-radius:7px}.signal-up{border-left-color:#247961!important;background:#f3faf7}.signal-down{border-left-color:#a65b45!important;background:#fcf6f3}.verdict-signals h4{font-size:16px;margin:0 0 7px}.verdict-signals p{font-size:14px;line-height:1.8;margin:0 0 7px}.verdict-signals small{font-size:12px;line-height:1.7;color:#5e6d7c;display:block}
.overview-decisions.half-year-pillars{grid-template-columns:repeat(2,minmax(0,1fr))}.half-year-pillars article p.src{font-size:11px}.execution-lead{padding:18px 0;line-height:1.9}.execution-lead h3{margin:0 0 12px}
.macro-audit-table{min-width:850px;table-layout:fixed;width:100%}.macro-audit-table th:first-child{width:18%}.macro-audit-table th:nth-child(2){width:23%}.macro-audit-table th:nth-child(3){width:27%}.macro-audit-table td{vertical-align:top}
.macro-chain-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:24px 0}.macro-chain-grid article,.macro-scenario-grid article{border:1px solid #d4dfeb;border-radius:8px;padding:22px;background:#fff}.macro-chain-grid h4,.macro-scenario-grid h4{margin:0 0 14px;font-size:17px}.macro-chain-grid p,.macro-scenario-grid p{line-height:1.85}.macro-scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
#macro-node-definitions,#macro-method{margin:24px 0}#macro-node-definitions>summary,#macro-method>summary{cursor:pointer;font-weight:600;padding:16px;background:#f3f6f9}
@media(max-width:1000px){.verdict-layout{grid-template-columns:1fr}.verdict-signals{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:700px){.overview-decisions.half-year-pillars,.verdict-signals,.macro-chain-grid,.macro-scenario-grid{grid-template-columns:1fr}.overview-thesis h3{font-size:20px}}
"""


def regime(d,market,prefix,refs):
    g=d['macro_regime'];x=g['markets'][market]
    out='<style>'+REGIME_CSS+'</style><section id="regime" class="regime"><div class="regime-head"><span class="view-label">未来半年判断 · 复核 '+E(g['reviewed_at'])+' · 窗口 '+E(g['window'])+'</span><h3>'+E(x['verdict'])+'</h3><p>'+E(x['summary'])+'</p><p class="regime-why"><b>为什么重写：</b>'+E(x['why_new'])+'</p></div>'
    out+='<p class="regime-frame"><b>分析框架</b>'+E(g['framework'])+' <a href="'+prefix+'framework.html">框架说明：如何用在大盘、板块和个股 →</a></p><div class="regime-parts">'
    for p_ in x['parts']:
        out+='<article class="part-'+p_['key']+'"><span class="part-name">'+E(p_['name'])+'</span><h4>'+E(p_['state'])+'</h4><p>'+E(p_['text'])+'</p><p class="part-imp"><b>推出：</b>'+E(p_['implication'])+'</p>'+refs(p_['refs'])+'</article>'
    out+='</div><div class="regime-scen">'
    for s_ in x['scenarios']:
        out+='<article><b>'+E(s_['name'])+'</b><span>'+E(s_['prob'])+'</span><p>'+E(s_['text'])+'</p></article>'
    board=prefix+('boards/index.html' if market=='a' else 'boards/hk.html')
    out+='</div><section id="regime-sectors"><h3 class="h3s">从大盘到板块：每个驱动指向哪里</h3><div class="tblwrap"><table class="mt regime-table"><thead><tr><th>宏观驱动</th><th>半年方向</th><th>顺风</th><th>逆风或等待</th><th>站内板块分档</th></tr></thead><tbody>'
    for r in x['sectors']:out+='<tr>'+''.join('<td>'+E(c)+'</td>' for c in r)+'</tr>'
    out+='</tbody></table></div><p class="regime-next"><a href="'+board+'">进入'+('A股' if market=='a' else '港股')+'板块，查看分档与证据 →</a></p></section>'
    out+='<section id="regime-checks"><h3 class="h3s">可证伪清单：到期对账</h3><p class="note">每条都有现值、判定日期、证实线与证伪线；到期后在此标注对或错。</p><div class="tblwrap"><table class="mt regime-table regime-checks"><thead><tr><th>编号</th><th>命题</th><th>现值</th><th>判定日期</th><th>证实</th><th>证伪及后果</th><th>状态</th></tr></thead><tbody>'
    for c in x['checks']:out+='<tr>'+''.join('<td>'+E(v)+'</td>' for v in c)+'<td>待到期</td></tr>'
    out+='</tbody></table></div></section><p class="note">'+E(g['limits'])+' <a href="'+prefix+g['research']+'">完整研究稿</a> · <a href="'+prefix+g['evidence']+'">计算底稿</a></p></section>'
    return out

def render(ctx,market):
    d,m,prefix,refs=load_context(ctx,market)
    return regime(d,market,prefix,refs)

def render_tracking(ctx,market):
    import tracking
    d,m,prefix,refs=load_context(ctx,market)
    fw=json.loads((Path(ctx['ROOT'])/'data/framework.json').read_text())
    return tracking.render(Path(ctx['ROOT']),d,fw,market,prefix)

REGIME_CSS = """
.regime{margin:18px 0 28px}.regime-head{border-left:4px solid #365875;padding:4px 0 4px 20px;margin-bottom:18px}.regime-head h3{font:600 23px/1.6 var(--sans);color:#223e57;margin:8px 0 12px}.regime-head p{font-size:15px;line-height:1.95;margin:0 0 8px}.regime-why{font-size:13px!important;color:#52687b}
.regime-frame{background:#f3f6f9;border-radius:8px;padding:12px 16px;font-size:14px;line-height:1.8}.regime-frame b{margin-right:10px}
.regime-parts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:18px 0}.regime-parts article{border:1px solid #d4dfeb;border-radius:8px;padding:18px 20px;background:#fff}.part-name{font-size:12px;color:#64798d}.regime-parts h4{margin:6px 0 10px;font-size:17px}.regime-parts p{font-size:14px;line-height:1.85;margin:0 0 8px}.part-imp{background:#f6f8fa;padding:8px 10px;border-radius:6px}
.regime-scen{display:grid;grid-template-columns:2fr 1fr 1fr;gap:14px;margin:0 0 22px}.regime-scen article{border:1px solid #d4dfeb;border-radius:8px;padding:14px 16px}.regime-scen article:first-child{border-left:4px solid #365875}.regime-scen span{float:right;font-size:13px;color:#52687b}.regime-scen p{font-size:14px;line-height:1.8;margin:8px 0 0}
.regime-table{width:100%;min-width:820px}.regime-table td{vertical-align:top;font-size:13.5px;line-height:1.75}.regime-next{margin:10px 0 22px}.regime-checks td:first-child,.regime-checks td:last-child,.regime-checks td:nth-child(4){white-space:nowrap}#regime-calendar{margin:18px 0}#regime-calendar>summary,#macro-legacy>summary{cursor:pointer;font-weight:600;padding:14px 16px;background:#f3f6f9}
@media(max-width:1000px){.regime-parts{grid-template-columns:1fr}.regime-scen{grid-template-columns:1fr}}
"""
