"""Shared A-H six-month research. Dated evidence, no stock selection."""
import html,json
from pathlib import Path
E=html.escape

def load(root): return json.loads((Path(root)/'data/framework_review.json').read_text())
def render(ctx,market='a'):
 r=load(ctx['ROOT']); label='A股' if market=='a' else '港股'
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
