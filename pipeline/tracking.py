"""Tracking sheet: regular data vs thresholds, scheduled events, shock rules, update log."""
import json
from pathlib import Path
from html import escape as E

def _j(root,*p):
    d=json.loads(Path(root,'data','raw',*p).read_text());return d['rows'] if isinstance(d,dict) and 'rows' in d else d

def values(root):
    v={}
    def idx(name,key):
        r=_j(root,name);v[key]=(r[-1]['close'],r[-1]['date'])
    idx('idx_all.json','a_idx_all');idx('idx_kc50.json','a_kc50')
    r=_j(root,'idx_all.json');v['a_turnover']=(round(r[-1]['amount']/1e12,2),r[-1]['date'])
    m=sorted(_j(root,'margin.json'),key=lambda x:x['DIM_DATE']);v['a_margin']=(round(m[-1]['RZRQYE']/1e12,2),m[-1]['DIM_DATE'][:10])
    b=sorted(_j(root,'bond.json'),key=lambda x:x['SOLAR_DATE'])
    cn=[x for x in b if x.get('EMM00166466')][-1];us=[x for x in b if x.get('EMG00001310')][-1]
    v['cn10y']=(round(cn['EMM00166466'],2),cn['SOLAR_DATE'][:10]);v['us10y']=(us['EMG00001310'],us['SOLAR_DATE'][:10])
    for key,f,field in [('ppi','ppi.json','BASE_SAME'),('cpi','cpi.json','NATIONAL_SAME'),('exports','exports.json','EXIT_BASE_SAME'),('pmi','pmi.json','MAKE_INDEX'),('m1','money.json','CURRENCY_SAME')]:
        x=next(r for r in _j(root,f) if r.get(field) is not None);v[key]=(x[field],x['TIME'])
    x=_j(root,'lpr.json')[0];v['lpr1y']=(x['LPR1Y'],x['TRADE_DATE'][:10])
    for key,f in [('hk_hsi','hsi.json'),('hk_hstech','hstech.json')]:
        r=_j(root,'hk',f);v[key]=(r[-1]['close'],r[-1]['date'])
    l=_j(root,'hk','liquidity.json');v['hk_hibor']=(round(l[-1]['hibor_fixing_1m'],2),l[-1]['end_of_date'])
    s=_j(root,'hk','southbound.json')
    for n in (5,20):v['hk_south%d'%n]=(round(sum(x['net'] for x in s[-n:]),1),s[-1]['date'])
    return v

def status(row,val):
    if not isinstance(val,(int,float)):return '人工跟踪','na'
    lo,hi=row.get('lo'),row.get('hi')
    if lo is not None and val<lo:return '触线：'+row['lo_label'],'hit'
    if hi is not None and val>hi:return '触线：'+row['hi_label'],'hit'
    for b in [lo,hi]:
        if b is not None and abs(val-b)<=abs(b)*0.03+(0.05 if abs(b)<10 else 0):return '接近阈值','near'
    return ('区间内' if lo is not None or hi is not None else '观察'),'ok'

def fmt(x):
    return f'{x:,.2f}'.rstrip('0').rstrip('.') if isinstance(x,float) else (f'{x:,}' if isinstance(x,int) else str(x))

def render(root,d,fw,market,prefix):
    g=d['macro_regime'];x=g['markets'][market];vals=values(root)
    out='<style>'+CSS+'</style><p class="trk-lead">三类信息，三种处理方式：<b>定期数据</b>只更新现值，越过阈值才进入改判；<b>已排期事件</b>事前写预期、事后对照；<b>突发事件</b>先归到分子、分母或水龙头，再看是否触线。</p>'
    out+='<section id="track-regular"><h3 class="h3s">定期跟踪单</h3><div class="tblwrap"><table class="mt trk-table"><thead><tr><th>部件</th><th>指标</th><th>频率</th><th>现值</th><th>阈值</th><th>状态</th><th>命题</th><th>为什么看它</th></tr></thead><tbody>'
    for r in x['tracking']:
        if r['src'].startswith('manual:'):val,date=r['src'][7:],''
        else:val,date=vals[r['src']]
        st,cls=status(r,val)
        th='；'.join(t for t in [('低于'+fmt(r['lo'])+'：'+r['lo_label'].split('：')[0]) if r['lo'] is not None else '',('高于'+fmt(r['hi'])+'：'+r['hi_label'].split('：')[0]) if r['hi'] is not None else ''] if t) or '—'
        out+='<tr><td>'+E(r['part'])+'</td><td><b>'+E(r['name'])+'</b></td><td>'+E(r['freq'])+'</td><td class="trk-v">'+E(fmt(val))+('<small>'+E(date)+'</small>' if date else '')+'</td><td>'+E(th)+'</td><td><span class="trk-s '+cls+'">'+E(st)+'</span></td><td>'+E(r['check'] or '—')+'</td><td>'+E(r['note'])+'</td></tr>'
    out+='</tbody></table></div><p class="note">日度与月度数值随每次构建从站内数据自动读取；“人工跟踪”项需在研究数据中手动更新。</p></section>'
    out+='<section id="track-events"><h3 class="h3s">已排期事件</h3><div class="tblwrap"><table class="mt trk-table"><thead><tr><th>时间</th><th>事件</th><th>影响哪个部件</th></tr></thead><tbody>'
    for c in g['calendar']:out+='<tr>'+''.join('<td>'+E(v)+'</td>' for v in c)+'</tr>'
    out+='</tbody></table></div></section><section id="track-shocks"><h3 class="h3s">突发事件：怎么归类、看什么</h3><div class="trk-shocks">'
    for s in fw['shock_rules']:out+='<article><b>'+E(s['type'])+'</b><span>'+E(s['part'])+'</span><p>'+E(s['examples'])+'</p><small>看：'+E(s['watch'])+'</small></article>'
    out+='</div></section><section id="track-rules"><h3 class="h3s">什么时候改结论</h3><ol class="trk-rules">'+''.join('<li>'+E(r)+'</li>' for r in fw['update_rules'])+'</ol></section>'
    out+='<section id="track-log"><h3 class="h3s">更新日志</h3><div class="tblwrap"><table class="mt trk-table"><thead><tr><th>日期</th><th>部件</th><th>变化</th><th>证据</th></tr></thead><tbody>'
    for c in g['changelog']:out+='<tr><td>'+E(c['date'])+'</td><td>'+E(c['part'])+'</td><td>'+E(c['change'])+'</td><td>'+E(c['evidence'])+'</td></tr>'
    return out+'</tbody></table></div></section>'

CSS="""
.trk-lead{font-size:15px;line-height:1.9;background:#f3f6f9;border-radius:8px;padding:12px 16px}
.trk-table{width:100%;min-width:900px}.trk-table td{vertical-align:top;font-size:13.5px;line-height:1.7}.trk-table td:first-child{white-space:nowrap}.trk-v{white-space:nowrap;font-variant-numeric:tabular-nums}.trk-v small{display:block;color:#6b7c8c;font-size:11px}
.trk-s{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;white-space:nowrap;background:#eef2f6;color:#455a6e}.trk-s.hit{background:#fbe9e4;color:#9b3d27}.trk-s.near{background:#fff4dc;color:#8a5a00}.trk-s.ok{background:#e9f5ef;color:#2f6f53}
.trk-shocks{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.trk-shocks article{border:1px solid #d4dfeb;border-radius:8px;padding:12px 14px}.trk-shocks span{float:right;font-size:12px;color:#52687b}.trk-shocks p{font-size:13.5px;line-height:1.7;margin:8px 0 6px}.trk-shocks small{font-size:12.5px;color:#455a6e;line-height:1.6;display:block}
.trk-rules li{font-size:14px;line-height:1.9}
"""
