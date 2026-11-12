"""Evidence-weighted six-month market-to-sector research; no individual stocks."""
import json, html
from pathlib import Path
E=html.escape

def load(root):
    return json.loads((Path(root)/'data/market_thesis.json').read_text())

def render(ctx, market):
    d=load(ctx['ROOT']);m=d['markets'][market];prefix='' if market=='a' else '../'
    def refs(keys):
        links=[]
        for k in keys:
            s=d['sources'][k];url=s['url']
            if not url.startswith('https://'):url=prefix+url
            links.append('<a href="'+E(url,quote=True)+'">'+E(s['title'])+'</a>')
        return '<p class="src">依据：'+' · '.join(links)+'</p>' if links else ''
    out='<p class="sub">研究复核 '+E(d['as_of'])+' · 判断窗口 '+E(d['window'])+'。行情、估值与经营数据保留各自日期。</p>'
    out+='<section class="market-horizon-head" id="macro-verdict"><h3 class="h3s">未来半年的最终判断</h3><p class="lead-main">'+E(m['headline'])+'</p><p class="thesis-net">'+E(m['net'])+'</p><p class="note"><b>判断对象：</b>'+E(m['target'])+'</p><p class="note"><b>把握程度：</b>'+E(m['confidence'])+'</p></section>'
    # Existing diagram geometry retained, with links to the new six-month evidence rather than stale daily nodes.
    view={n['key']:[n['state'],n['note']] for n in m['nodes']}
    from framework_review import hk_horizon_diagram
    diagram=hk_horizon_diagram({'node_view':view}).replace('href="#hk6-','href="#thesis-')
    if market=='a':
        diagram=diagram.replace('港股A–H','A股A–H').replace('港股市场走势','A股价格与行业表现')
    out+='<div class="market-overview horizon-overview"><div class="market-verdict"><h3 class="h3s">为什么形成这个结论</h3>'
    for title,text,keys in m['why']:
        out+='<article class="thesis-reason"><h4>'+E(title)+'</h4><p>'+E(text)+'</p>'+refs(keys)+'</article>'
    out+='</div><div class="market-transmission" id="macro-map"><h3 class="h3s">A–H 六个月传导图</h3><div class="fwbox">'+diagram+'</div><p class="sub">箭头表示待检验的传导关系，不表示已证明因果。红色支持、绿色约束、灰色分化或未闭合；点击节点查看事实、反证和下一步验证。汇率属于C/F/G的传导，不增设因子。</p><p class="note">'+E(d['method'])+'</p></div></div>'
    out+='<section class="thesis-bridges"><h3 class="h3s">关键传导：证据已经走到哪一步</h3><div class="tblwrap"><table class="mt thesis-table"><thead><tr><th>路径</th><th>已有事实</th><th>仍需证明的中间环节</th><th>对结论的影响</th></tr></thead><tbody>'
    bridges=[
      ('AI需求 A→C→E→F/H','全球支出和服务器数量增加；国内电子订单较强。','全球采购→本地细分份额→交付毛利→自由现金→固定2027盈利修订。全国工业数据不能补齐全部环节。','A股优先研究相关半导体、服务器条件看好；港股硬件缺本地闭环，仍观察。',['idc_ai','idc_server','pmi_detail']),
      ('政策 B→D/C 与 B→G','定向融资工具利率和额度已调整；回购增持工具扩围。','融资使用→招标→交付→回款；申请回购→实际执行。不能以工具额度代替任何一步。','电网细分优先；其他板块须有实际订单，不把稳市场资金当作需求复苏。',['psl','buyback','grid_invest']),
      ('资源 A→C→E，反向影响D/F','上游历史利润强，油运近期回落；EIA预期2027供给逐步恢复。','现货价→实际结算价→正常化利润/现金；供给恢复对运量与有效运力的净影响。','煤炭、油运降为观察；港股能源以正常油价现金为条件，化工按产品价差。',['profit','signal','eia']),
      ('通胀 A→政策 B→利率 D→估值 F','美国核心月率保持0.3%；10月议息已有加息异议，11月讲话偏鹰。','委员会决策→市场收益率→行业要求回报；是否已被价格反映，尚缺利率期货与风险溢价拆分。','不预设降息重估；优先核盈利/现金是否足以抵消估值压力。',['fed','cpi_us','waller'])]
    for path,fact,gap,effect,keys in bridges:
        out+='<tr><th>'+E(path)+'</th><td>'+E(fact)+refs(keys)+'</td><td>'+E(gap)+'</td><td>'+E(effect)+'</td></tr>'
    out+='</tbody></table></div></section>'
    out+='<section id="sector-review"><h3 class="h3s">从大盘到板块：最终取舍与比较</h3><p class="sub">分组已与板块页统一。研究优先级不是预期收益排名；产业方向与当前价格是否合算分别判断。</p><div class="tblwrap"><table class="mt thesis-table sector-comparison"><thead><tr><th>方向 / 判断</th><th>为什么保留或降级</th><th>估值与当前位置如何约束</th><th>维持与改变判断的条件</th></tr></thead><tbody>'
    for s in m['sectors']:
        out+='<tr><th><a href="'+prefix+'boards/'+s['id']+'.html">'+E(s['title'])+'</a><span class="thesis-group">'+E(s['group'])+'</span><p>'+E(s['focus'])+'</p></th><td>'+E(s['compare'])+'</td><td>'+E(s['priced'])+'</td><td>'+E(s['trigger'])+refs(s['refs'])+'</td></tr>'
    out+='</tbody></table></div><div class="thesis-grid">'
    for s in m['sectors']:
        out+='<article class="thesis-path"><h4>'+E(s['title'])+' · 传导与时间</h4><p class="chain-text">'+E(s['path'])+'</p><p><b>未来半年验证：</b>'+E(s['timing'])+'</p><a href="'+prefix+'boards/'+s['id']+'.html">查看板块逐节点研究 →</a></article>'
    out+='</div></section>'
    out+='<section class="thesis-grid thesis-alternatives">'
    for x in m['excluded']:out+='<article><h4>'+E(x['name'])+'</h4><p>'+E(x['text'])+'</p>'+refs(x['refs'])+'</article>'
    out+='</section><section id="thesis-nodes"><h3 class="h3s">A–H：事实、推导、反证逐项核对</h3><p class="sub">每个节点都区分已知事实与研究推断。证据缺口限制判断强度，不取消已有证据支持的方向。</p><div class="thesis-grid">'
    for n in m['nodes']:
        out+='<article class="thesis-node" id="thesis-'+n['key']+'"><header><span class="lc2 '+n['state']+'">'+n['key']+'</span><div><h4>'+E(n['title'])+'</h4><p>'+E(n['note'])+'</p></div></header>'
        for key,title in [('fact','已核事实'),('path','传导关系'),('judgment','对半年判断的影响'),('counter','相反证据与限制'),('verify','下一步验证')]:
            out+='<div class="thesis-node-row"><b>'+title+'</b><p>'+E(n[key])+'</p></div>'
        out+=refs(n['refs'])+'</article>'
    out+='</div></section>'
    out+='<section class="thesis-math"><h3 class="h3s">利润增长多少，才能抵消估值下降</h3><p>在同一成分、正盈利和相同盈利口径下，价格变化 =（1＋盈利变化）×（1＋PE变化）−1。以下仅演示估值约束，不是市场预测；未计股息、汇率、增发或回购。</p><div class="thesis-grid">'
    for eps,pe in [(20,-15),(10,-15),(0,-10)]:
        result=(1+eps/100)*(1+pe/100)*100-100
        out+='<div><b>盈利 '+f'{eps:+d}% / PE {pe:+d}%'+ '</b><strong>'+f'{result:+.1f}%'+'</strong><span>价格变化（算术示例）</span></div>'
    out+='</div><p>若PE下降10%，盈利需增长约11.1%才抵消价格影响；下降15%，需约17.6%。因此“需求增长”不能省略利润率、现金和估值这几步。低PE也须排除周期高盈利造成的分母幻觉。</p></section>'
    out+='<section id="macro-scenarios"><h3 class="h3s">基准、上调与下调：为什么以及何时改变</h3><p class="sub">不编造情景概率。以下是证据触发的复核规则，不是回测后的交易阈值。</p><div class="ol-scs">'
    for x in m['scenarios']:out+='<article class="ol-sc"><h4>'+E(x['name'])+'</h4><p>'+E(x['evidence'])+'</p><p><b>改变什么：</b>'+E(x['change'])+'</p></article>'
    out+='</div><h3 class="h3s">六个月验证时间表</h3><div class="thesis-timeline">'
    for date,title,text in m['timeline']:out+='<article><span>'+E(date)+'</span><h4>'+E(title)+'</h4><p>'+E(text)+'</p></article>'
    out+='</div></section><details class="rules thesis-audit"><summary>资料日期、核验范围和完整来源</summary><p>'+E(d['audit'])+'</p><p><a href="'+prefix+'research/market-thesis-2026-11-12.md">下载完整研究稿（Markdown）</a> · <a href="'+prefix+'data/market_thesis.json">查看结构化研究及来源</a></p><ul>'
    for k,s in d['sources'].items():
        url=s['url'] if s['url'].startswith('https://') else prefix+s['url']
        out+='<li><a href="'+E(url,quote=True)+'">'+E(s['title'])+'</a> · '+E(s['date'])+'。'+E(s['scope'])+'</li>'
    return out+'</ul></details>'

def export(root):
    root=Path(root);d=load(root)
    out=['# A股与港股：从大盘到板块的半年研究','',f"研究复核：{d['as_of']}；窗口：{d['window']}",'',d['method'],'',d['audit']]
    def cite(keys):
        return '；'.join('['+d['sources'][k]['title']+']('+('../'+d['sources'][k]['url'] if not d['sources'][k]['url'].startswith('https://') else d['sources'][k]['url'])+')' for k in keys)
    for m in d['markets'].values():
        out+=['','## '+m['label'],'',m['headline'],'',m['net'],'','判断对象：'+m['target'],'','把握程度：'+m['confidence']]
        for title,text,keys in m['why']:out+=['','### '+title,'',text,'',cite(keys)]
        out+=['','### 板块取舍']
        for s in m['sectors']:
            out+=['','#### '+s['title']+'：'+s['group']]
            for key,title in [('focus','范围'),('compare','为什么这样排序'),('path','传导'),('priced','估值与位置'),('timing','验证时间'),('trigger','改判条件')]:out+=['',title+'：'+s[key]]
            out+=['',cite(s['refs'])]
        out+=['','### A—H逐项核验']
        for n in m['nodes']:
            out+=['','#### '+n['key']+' · '+n['title']]
            for key,title in [('fact','事实'),('path','传导'),('judgment','判断'),('counter','反证与限制'),('verify','下一步')]:out+=['',title+'：'+n[key]]
            out+=['',cite(n['refs'])]
        for x in m['excluded']:out+=['','### '+x['name'],'',x['text'],'',cite(x['refs'])]
        out+=['','### 情景与时间表']
        for x in m['scenarios']:out+=['','**'+x['name']+'**','',x['evidence'],'',x['change']]
        for date,title,text in m['timeline']:out+=['','**'+date+' · '+title+'**','',text]
    out+=['','## 估值敏感性（演示，不是预测）','','同一正盈利、固定成分和口径下，价格变化=(1+盈利变化)×(1+PE变化)−1。盈利+20%、PE−15%时价格+2%；盈利+10%、PE−15%时价格−6.5%。PE下降10%/15%，分别需要约11.1%/17.6%的盈利增长抵消。未计股息、汇率及股本变化。','','## 来源与口径']
    for k,s in d['sources'].items():out+=['',f"- {cite([k])} · {s['date']}。{s['scope']}"]
    dest=root/'docs/research';dest.mkdir(exist_ok=True)
    (dest/'market-thesis-2026-11-12.md').write_text('\n'.join(out)+'\n')
    dest=root/'docs/data';dest.mkdir(exist_ok=True)
    (dest/'market_thesis.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
