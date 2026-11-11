"""Shared A-H six-month research. Dated evidence, no stock selection."""
import html,json
from pathlib import Path
E=html.escape

def load(root): return json.loads((Path(root)/'data/framework_review.json').read_text())
def render(ctx,market='a'):
 r=load(ctx['ROOT']); label='A股' if market=='a' else '港股'
 if market == 'a': return render_a(ctx,r)
 out=f'<p class="sub">研究复核 {r["as_of"]} · 判断窗口 {r["window"]}。专题日期与下方行情日期分别展示，旧行情不标成今日更新。</p>'
 out+='<h3 class="h3s">六个月传导图</h3><p class="sub">A/B → C → E → F → H；B → D → F/G → H。汇率是通向C/F/G的跨节点变量。H用于检验结果，不作为原因。</p><div class="ol-grid">'
 for k,title,state,a,hk in r['nodes']:
  out+=f'<article class="ol-card"><b>{k} · {E(title)}</b><p>{E(state)}</p><p>{E(a if market=="a" else hk)}</p></article>'
 out+='</div><h3 class="h3s">结论</h3><div class="lead"><p class="lead-main">'+E(r['headline'])+'</p><p>这是一组待检验的半年情景，不是对未来结果的保证。E、行业现金流和F历史覆盖不足，当前没有“已确定配置”的板块。</p></div>'
 out+='<h3 class="h3s">板块分档</h3>'
 for tier in ['优先研究','条件候选','观察待证']:
  out+='<h4>'+tier+'</h4><div class="ol-grid">'
  for s in r['sectors']:
   if market not in s['markets'] or s['tier']!=tier: continue
   out+='<article class="ol-card"><b>'+E(s['name'])+'</b>'
   for key,title in [('chain','框架路径'),('why','当前依据'),('check','半年验证'),('risk','相反因素'),('fail','失效条件')]:out+='<p><b>'+title+'</b> '+E(s[key])+'</p>'
   out+='<p>'+' · '.join('<a href="'+E(r['sources'][x],quote=True)+'">来源 '+str(i+1)+'</a>' for i,x in enumerate(s['refs']))+'</p></article>'
  out+='</div>'
 out+='<h3 class="h3s">三种情景与复核</h3><div class="ol-scs">'
 for name,trigger,result in r['scenarios']:out+='<article class="ol-sc"><b>'+E(name)+'</b><p>条件：'+E(trigger)+'</p><p>影响：'+E(result)+'</p></article>'
 out+='</div><p>'+E(r['next_review'])+'</p><details class="sub2" open><summary>待核验项目的研究结果与真实缺口（15项）</summary><p>已核实、部分核验和仍缺数据分开；单项完成不表示全节点已完成。</p><div class="tblwrap"><table class="mt"><thead><tr><th>节点 / 项目</th><th>状态与日期</th><th>本轮核验</th><th>对半年判断的影响</th></tr></thead><tbody>'
 for v in r['evidence']:
  out+='<tr><td>'+E(v['node']+' · '+v['item'])+'</td><td>'+E(v['status'])+'<br>'+E(v['date'])+'</td><td>'+E(v['fact'])+'<br><a href="'+E(v['source'],quote=True)+'">核验来源或已查入口</a></td><td>'+E(v['impact'])+'</td></tr>'
 return out+'</tbody></table></div></details>'


def render_a(ctx,r):
 o=json.loads((Path(ctx['ROOT'])/'data/outlook.json').read_text())
 out='<p class="sub">判断窗口 '+E(r['window'])+'；依据截至2026-11-11的研究及原日期行情。板块方向已作判断，个股与仓位尚未确定。</p>'
 out+='<h3 class="h3s">六个月传导图</h3><div class="fwbox">'+ctx['diagram']({k:v[0] for k,v in o['node_view'].items()},{k:v[1] for k,v in o['node_view'].items()},'h6','A–H半年判断传导图')+'</div>'
 out+='<h3 class="h3s">结论</h3><div class="lead"><p class="lead-main">'+E(o['headline'])+'</p><ul class="lead-points">'+''.join('<li>'+x+'</li>' for x in o['points'])+'</ul></div>'
 out+='<p class="src">本轮核验：'+ ' · '.join('<a href="'+E(r['sources'][k],quote=True)+'">'+label+'</a>' for k,label in [('ppi','价格'),('pmi','需求'),('psl','定向政策'),('fed10','美联储'),('eia','能源情景')])+'</p>'
 out+='<h3 class="h3s">板块分档</h3>'
 for tier in o['tiers']:
  out+='<div class="ol-tier"><div class="ol-th"><span class="tag '+E(tier['cls'])+'">'+E(tier['name'])+'</span><span class="ol-desc">'+E(tier['desc'])+'</span></div><div class="ol-grid">'
  for it in tier['items']:
   out+='<article class="ol-card"><b>'+E(it['name'])+'</b>'
   for key,label in [('why','依据'),('risk','风险'),('falsify','改变判断的条件')]: out+='<p><b>'+label+'</b> '+E(it[key])+'</p>'
   out+='</article>'
  out+='</div></div>'
 out+='<h3 class="h3s">什么情况下改判断</h3><div class="ol-scs">'
 for x in o['scenarios']:out+='<article class="ol-sc '+E(x['cls'])+'"><b>'+E(x['name'])+'</b><p>'+E(x['trigger'])+'</p><p>'+E(x['result'])+'</p></article>'
 out+='</div><p>'+E(o['next_review'])+'</p><details class="rules"><summary>哪些判断保留，哪些被证据修正</summary>'
 for x in o['corrections']:out+='<p><b>原来：</b>'+E(x['old'])+'<br><b>现在：</b>'+E(x['new'])+'</p>'
 out+='</details><details class="sub2"><summary>核验结果与数据缺口（15项）</summary><div class="tblwrap"><table class="mt"><thead><tr><th>因子 / 项目</th><th>核验结果</th><th>判断边界</th></tr></thead><tbody>'
 for v in r['evidence']:out+='<tr><td>'+E(v['node']+' '+v['item'])+'</td><td>'+E(v['status']+'：'+v['fact'])+'<p>'+E(v['date'])+' · <a href="'+E(v['source'],quote=True)+'">来源</a></p></td><td>'+E(v['impact'])+'</td></tr>'
 return out+'</tbody></table></div></details>'
