"""Evidence-weighted six-month market-to-sector research; no individual stocks."""
import json, html
from pathlib import Path
E=html.escape

def load(root):
    return json.loads((Path(root)/'data/market_thesis.json').read_text())

def render(ctx, market):
    import overview_page
    return overview_page.render(ctx,market)


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
