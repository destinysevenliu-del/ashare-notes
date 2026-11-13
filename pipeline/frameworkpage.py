"""Standalone page explaining the reusable framework (分子/分母/水龙头) across market, sector, stock."""
import json
from pathlib import Path
from html import escape as E

def body(fw):
    P={p['key']:p for p in fw['parts']}
    out='<div class="hero"><p class="date">框架版本 '+E(fw['version'])+'</p><h1>研究框架：'+E(fw['name'])+'</h1><p class="sum">'+E(fw['one_line'])+'</p></div><style>'+CSS+'</style>'
    out+='<section class="fw-card"><h2>一个比喻</h2><p>'+E(fw['metaphor'])+'</p></section>'
    out+='<section><h2>三件事，每件事只问一个问题</h2><div class="fw-parts">'
    for p in fw['parts']:out+='<article class="fw-'+p['key']+'"><span>'+E(p['name'])+'</span><h3>'+E(p['question'])+'</h3><p><b>由什么决定：</b>'+E(p['drivers'])+'</p><p class="fw-trap"><b>容易犯的错：</b>'+E(p['trap'])+'</p></article>'
    out+='</div></section><section><h2>同一套问题，用在三个层级</h2><p class="note">横着看是同一层级的三件事，竖着看是同一件事在不同层级换了指标。</p><div class="tblwrap"><table class="mt fw-grid"><thead><tr><th></th>'
    for k in ['num','den','tap']:out+='<th>'+E(P[k]['name'])+'<small>'+E(P[k]['question'])+'</small></th>'
    out+='<th>开关（外部条件）</th><th>这一层的输出</th></tr></thead><tbody>'
    for l in fw['levels']:out+='<tr><th scope="row">'+E(l['name'])+'</th><td>'+E(l['num'])+'</td><td>'+E(l['den'])+'</td><td>'+E(l['tap'])+'</td><td>'+E(l['switch'])+'</td><td><b>'+E(l['output'])+'</b></td></tr>'
    out+='</tbody></table></div></section><section><h2>三层怎样接力</h2><div class="fw-chain">'
    for i,c in enumerate(fw['chain']):out+=('<div class="fw-arrow">→</div>' if i else '')+'<article><b>'+E(c['from'])+' → '+E(c['to'])+'</b><p>'+E(c['rule'])+'</p></article>'
    out+='</div><p class="note">'+E(fw['stock_mapping'])+'</p></section>'
    out+='<section><h2>每一层都交付同样的六样东西</h2><ol class="fw-out">'+''.join('<li>'+E(o)+'</li>' for o in fw['outputs'])+'</ol></section>'
    out+='<section><h2>持续更新：三类信息，三种处理方式</h2><div class="fw-parts">'
    for t in fw['info_types']:out+='<article><span>'+E(t['name'])+'</span><p>'+E(t['what'])+'</p><p class="fw-trap"><b>怎么处理：</b>'+E(t['how'])+'</p></article>'
    out+='</div><h3>什么时候改结论</h3><ol class="fw-out">'+''.join('<li>'+E(r)+'</li>' for r in fw['update_rules'])+'</ol>'
    out+='<h3>突发事件归类</h3><div class="tblwrap"><table class="mt fw-grid"><thead><tr><th>类型</th><th>例子</th><th>归到哪件事</th><th>看什么</th></tr></thead><tbody>'
    for s in fw['shock_rules']:out+='<tr><th scope="row">'+E(s['type'])+'</th><td>'+E(s['examples'])+'</td><td>'+E(s['part'])+'</td><td>'+E(s['watch'])+'</td></tr>'
    out+='</tbody></table></div></section><section class="fw-card"><h2>带走要点</h2><ul><li>先问谁在决定价格：半年尺度上，分母和水龙头常常比分子更重要。</li><li>大盘不选股，只给风向表；板块只研究顺风的，个股只比较谁拿到的分子最多。</li><li>每个结论都要有跟踪单和证伪单；没有触线就不改结论。</li></ul><p><a href="index.html#horizon">看A股的当前应用 →</a>　<a href="hk/index.html#horizon">看港股的当前应用 →</a></p></section>'
    return out

def build(ctx):
    root=Path(ctx['ROOT']);fw=json.loads((root/'data/framework.json').read_text())
    (root/'docs/framework.html').write_text(ctx['page']('研究框架 | A 股框架笔记','fw',body(fw)),encoding='utf-8')

CSS="""
.fw-card{background:#f3f6f9;border-radius:10px;padding:18px 22px;margin:18px 0}.fw-card p,.fw-card li{font-size:15px;line-height:1.95}
.fw-parts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:14px 0}.fw-parts article{border:1px solid #d4dfeb;border-radius:8px;padding:16px 18px;background:#fff}.fw-parts span{font-size:13px;color:#64798d;font-weight:600}.fw-parts h3{font-size:17px;margin:6px 0 10px}.fw-parts p{font-size:14px;line-height:1.85;margin:0 0 8px}.fw-trap{background:#f6f8fa;padding:8px 10px;border-radius:6px}
.fw-num{border-top:4px solid #3d6b8f!important}.fw-den{border-top:4px solid #8a6d3b!important}.fw-tap{border-top:4px solid #3f7d63!important}
.fw-grid{width:100%;min-width:900px}.fw-grid td,.fw-grid th{vertical-align:top;font-size:13.5px;line-height:1.75}.fw-grid thead th small{display:block;font-weight:400;color:#64798d;font-size:12px}
.fw-chain{display:flex;align-items:stretch;gap:10px;margin:12px 0}.fw-chain article{flex:1;border:1px solid #d4dfeb;border-radius:8px;padding:14px 16px}.fw-chain p{font-size:14px;line-height:1.8;margin:8px 0 0}.fw-arrow{align-self:center;font-size:22px;color:#8798a9}
.fw-out li{font-size:14.5px;line-height:1.9}
@media(max-width:900px){.fw-parts{grid-template-columns:1fr}.fw-chain{flex-direction:column}.fw-arrow{transform:rotate(90deg)}}
"""
