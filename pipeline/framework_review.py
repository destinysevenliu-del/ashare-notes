"""Shared A-H six-month research. Dated evidence, no stock selection."""
import html,json
from pathlib import Path
E=html.escape

def load(root): return json.loads((Path(root)/'data/framework_review.json').read_text())
def render(ctx,market='a'):
 r=load(ctx['ROOT']); label='A股' if market=='a' else '港股'
 if market == 'a': return render_a(ctx,r)
 return render_hk(ctx,r)


def sector_final_notice(ctx,market):
 d=json.loads((Path(ctx['ROOT'])/'data/industry_research.json').read_text())
 if 'market_synthesis' not in d:return ''
 m=d['market_synthesis'][market];url='boards/index.html' if market=='a' else '../boards/hk.html'
 return ('<section class="sector-final-notice" id="sector-review"><h3>板块二次核验 · 最新综合判断</h3>'
         '<div><p>'+E(m['body'])+'</p></div><div><p><b>修订：</b>'+E(m['revision'])+'</p>'
         '<p><a href="'+url+'">查看各板块最终结论与证据权衡 →</a></p></div>'
         '<p class="note">上方保留宏观判断与原推导方向；加入行业利润、估值和价格证据后，板块取舍以本次二次核验为准。</p></section>')


def horizon_intro(ctx,r,o,market):
 label='A股' if market=='a' else '港股'
 diagram=(ctx['market_layout'].diagram({k:v[0] for k,v in o['node_view'].items()},{k:v[1] for k,v in o['node_view'].items()},ctx['NODE_NAME'],'h6')
          if market=='a' else hk_horizon_diagram(o))
 keys=[('ppi','价格'),('pmi','需求'),('psl','定向政策'),('fed10','美联储'),('eia','能源情景')] if market=='a' else [('pmi','中国需求'),('fed10','美元政策'),('psl','定向支持'),('eia','能源供给')]
 sources=' · '.join('<a href="'+E(r['sources'][k],quote=True)+'">'+name+'</a>' for k,name in keys)
 return ('<section class="market-horizon-head" id="macro-verdict"><h3 class="h3s">未来半年的综合结论</h3>'
         '<p class="lead-main">'+E(o['headline'])+'</p></section>'
         '<div class="market-overview horizon-overview"><div class="market-verdict"><h3 class="h3s">判断依据与取舍</h3><div class="lead">'
         '<ul class="lead-points">'+''.join('<li>'+v+'</li>' for v in o['points'])+'</ul></div>'
         '<p class="src">结论为基于证据的研究判断。依据：'+sources+'</p></div>'
         '<div class="market-transmission" id="macro-map"><h3 class="h3s">六个月传导图</h3>'
         '<div class="fwbox">'+diagram+'</div><p class="sub">红色为支持、绿色为压力、灰色为分化或缺数据。点击节点查看依据。'
         +('汇率进入C/F/G，不新增框架节点。' if market=='hk' else '')+'</p></div></div>')


def board_title(ctx, market, name):
 d=json.loads((Path(ctx["ROOT"])/"data/sector_research.json").read_text())
 match=next((x for x in d["sectors"] if x["market"]==market and x["outlook_name"]==name),None)
 prefix="boards/" if market=="a" else "../boards/"
 return ('<a href="'+prefix+match["id"]+'.html">'+E(name)+"</a>") if match else E(name)

def render_a(ctx,r):
 o=json.loads((Path(ctx['ROOT'])/'data/outlook.json').read_text())
 out='<p class="sub">判断窗口 '+E(r['window'])+'；依据截至2026-11-11的研究及原日期行情。板块方向已作判断，个股与仓位尚未确定。</p>'
 out+=horizon_intro(ctx,r,o,'a')
 out+=sector_final_notice(ctx,'a')
 out+='<h3 class="h3s">宏观初筛板块分档（推导起点）</h3>'
 for tier in o['tiers']:
  out+='<div class="ol-tier"><div class="ol-th"><span class="tag '+E(tier['cls'])+'">'+E(tier['name'])+'</span><span class="ol-desc">'+E(tier['desc'])+'</span></div><div class="ol-grid">'
  for it in tier['items']:
   out+='<article class="ol-card"><b>'+board_title(ctx,'a',it['name'])+'</b>'
   for key,label in [('why','依据'),('risk','风险'),('falsify','改变判断的条件')]: out+='<p><b>'+label+'</b> '+E(it[key])+'</p>'
   out+='</article>'
  out+='</div></div>'
 out+='<h3 class="h3s" id="macro-scenarios">什么情况下改判断</h3><div class="ol-scs">'
 for x in o['scenarios']:out+='<article class="ol-sc '+E(x['cls'])+'"><b>'+E(x['name'])+'</b><p>'+E(x['trigger'])+'</p><p>'+E(x['result'])+'</p></article>'
 out+='</div><p>'+E(o['next_review'])+'</p><details class="rules"><summary>哪些判断保留，哪些被证据修正</summary>'
 for x in o['corrections']:out+='<p><b>原来：</b>'+E(x['old'])+'<br><b>现在：</b>'+E(x['new'])+'</p>'
 out+='</details><details class="sub2"><summary>核验结果与数据缺口（15项）</summary><div class="tblwrap"><table class="mt"><thead><tr><th>因子 / 项目</th><th>核验结果</th><th>判断边界</th></tr></thead><tbody>'
 for v in r['evidence']:out+='<tr><td>'+E(v['node']+' '+v['item'])+'</td><td>'+E(v['status']+'：'+v['fact'])+'<p>'+E(v['date'])+' · <a href="'+E(v['source'],quote=True)+'">来源</a></p></td><td>'+E(v['impact'])+'</td></tr>'
 return out+'</tbody></table></div></details>'


def hk_horizon_diagram(o):
 pos={'A':(20,20),'B':(650,20),'C':(20,160),'D':(650,160),'E':(20,320),'F':(335,320),'G':(650,320),'H':(335,480)}
 titles={'A':'全球环境与中国需求','B':'内地与美元政策','C':'需求、成本与企业盈利','D':'融资条件与风险偏好','E':'未来盈利预期','F':'投资者愿意支付的估值','G':'仓位、申赎与交易约束','H':'港股市场走势'}
 paths=['M160 110 V160','M710 110 C710 140 240 130 240 160','M790 110 V160','M300 65 H500 Q530 65 530 130 V205 H650','M160 250 V320','M230 250 C230 285 405 280 405 320','M720 250 C720 280 545 280 545 320','M790 250 V320','M300 365 H335','M475 410 V480','M790 410 V450 H560 V480']
 out='<svg class="fw hk-horizon-diagram" viewBox="0 0 950 590" role="img" aria-label="港股A–H六个月判断传导图"><defs><marker id="hk6-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#8592a3"/></marker></defs>'
 for d in paths:out+='<path d="'+d+'" fill="none" stroke="#8592a3" stroke-width="1.5" marker-end="url(#hk6-arrow)"/>'
 for k,(x,y) in pos.items():
  state,note=o['node_view'][k];fill={'up':'#fff1f0','down':'#edf7f1','price':'#172333'}.get(state,'#f6f7f9');color='#fff' if k=='H' else '#172333';border={'up':'#b44f46','down':'#34816c'}.get(state,'#aab4c0')
  out+='<a href="#hk6-'+k+'"><rect x="'+str(x)+'" y="'+str(y)+'" width="280" height="90" rx="10" fill="'+fill+'" stroke="'+border+'"/>'
  out+='<text x="'+str(x+14)+'" y="'+str(y+30)+'" fill="'+color+'" font-size="16" font-weight="600">'+k+' · '+E(titles[k])+'</text>'
  out+='<text x="'+str(x+14)+'" y="'+str(y+60)+'" fill="'+color+'" font-size="13">'+E(note)+'</text></a>'
 return out+'</svg>'


def render_hk(ctx,r):
 o=json.loads((Path(ctx['ROOT'])/'data/hk_outlook.json').read_text())
 out='<p class="sub">研究复核 '+E(o['as_of'])+' · 判断窗口 '+E(r['window'])+'。这是半年方向判断，日行情仍按其原日期展示。</p>'
 out+=horizon_intro(ctx,r,o,'hk')
 out+=sector_final_notice(ctx,'hk')
 out+='<h3 class="h3s">宏观初筛板块分档（推导起点）</h3>'
 for tier in o['tiers']:
  out+='<div class="ol-tier"><div class="ol-th"><span class="tag '+E(tier['cls'])+'">'+E(tier['name'])+'</span><span class="ol-desc">'+E(tier['desc'])+'</span></div><div class="ol-grid">'
  for it in tier['items']:
   out+='<article class="ol-card"><b>'+board_title(ctx,'hk',it['name'])+'</b>'
   for key,label in [('why','依据'),('risk','风险'),('falsify','改变判断的条件')]:out+='<p><b>'+label+'</b> '+E(it[key])+'</p>'
   out+='</article>'
  out+='</div></div>'
 out+='<h3 class="h3s" id="macro-scenarios">什么情况下改判断</h3><div class="ol-scs">'
 for x in o['scenarios']:out+='<article class="ol-sc '+E(x['cls'])+'"><b>'+E(x['name'])+'</b><p>'+E(x['trigger'])+'</p><p>'+E(x['result'])+'</p></article>'
 out+='</div><p>'+E(o['next_review'])+'</p><details class="sub2"><summary>A–H半年判断依据与边界</summary>'
 for k,title,state,a,hk in r['nodes']:out+='<section id="hk6-'+k+'"><h4>'+k+' · '+E(title)+'</h4><p>'+E(o['node_view'][k][1])+'</p><p>'+E(hk)+'</p></section>'
 out+='</details><details class="sub2"><summary>核验结果与数据缺口（15项）</summary><div class="tblwrap"><table class="mt"><thead><tr><th>节点 / 项目</th><th>核验与日期</th><th>影响及边界</th></tr></thead><tbody>'
 for v in r['evidence']:out+='<tr><td>'+E(v['node']+' '+v['item'])+'</td><td>'+E(v['status']+'：'+v['fact'])+'<p>'+E(v['date'])+' · <a href="'+E(v['source'],quote=True)+'">来源</a></p></td><td>'+E(v['impact'])+'</td></tr>'
 return out+'</tbody></table></div></details>'
