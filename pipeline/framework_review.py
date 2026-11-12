"""Compatibility entrypoint for the shared A–H market thesis."""
from html import escape as E

def render(ctx, market='a'):
 import market_thesis
 market_thesis.export(ctx['ROOT'])
 return market_thesis.render(ctx,market)

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
 out+='<path d="M615 540 H930 V445 H850 V410" fill="none" stroke="#b88636" stroke-dasharray="5 4" marker-end="url(#hk6-arrow)"/><text x="665" y="570" font-size="13" fill="#896626">H → G：价格反馈资金</text>'
 return out+'</svg>'

