"""Sector selection under the 分子/分母/水龙头 framework: hubs, detail pages, removed-page notes."""
import json
from pathlib import Path
from html import escape as E

PART_NAME={'num':'分子 · 板块赚的钱','den':'分母 · 估值位置','tap':'水龙头 · 资金与拥挤'}
ORDER=['顺风','前半段','等开关','逆风']

def load(root):
    d=json.loads((Path(root)/'data/sector_selection.json').read_text())
    rows={r['bk']:r for r in json.loads((Path(root)/'docs/data/sector-screen.json').read_text())['rows']}
    return d,rows

def refs(d,keys,prefix):
    out=[]
    for k in keys:
        s=d['sources'][k];u=s['url'] if s['url'].startswith('http') else prefix+s['url']
        out.append('<a href="'+E(u,quote=True)+'">'+E(s['title'])+'</a>')
    return '<p class="src">来源：'+' · '.join(out)+'</p>'

def f(x,p='+.0f',suf=''):
    return '—' if x is None else format(x,p)+suf

def screen_table(rows,bks):
    out='<div class="tblwrap"><table class="mt ss-table"><thead><tr><th>行业（东方财富）</th><th>样本</th><th>三季度单季营收同比</th><th>三季度单季利润同比</th><th>上半年利润同比</th><th>PE 现在 / 一年前</th><th>距一年高点</th><th>60日相对沪深300</th><th>成交拥挤度分位</th></tr></thead><tbody>'
    for b in bks:
        r=rows[b];out+='<tr><th scope="row">'+E(r['name'])+'<small>'+E(b)+'</small></th><td>'+str(r['n'])+'家（亏损'+str(r['loss_n'])+'）</td><td>'+f(r['rev_yoy'],'+.0f','%')+'</td><td><b>'+f(r['np_yoy'],'+.0f','%')+'</b></td><td>'+f(r['h1_yoy'],'+.0f','%')+'</td><td>'+f(r['pe'],'.0f')+' / '+f(r['pe1'],'.0f')+'</td><td>'+f(r['dd'],'.0f','%')+'</td><td>'+f(r['rs60'],'+.0f','%')+'</td><td>'+f(r['sh_pct'],'.0f','%')+'</td></tr>'
    return out+'</tbody></table></div>'

def badge(r):return '<span class="ss-badge ss-'+{'顺风':'up','前半段':'early','等开关':'wait','逆风':'down'}[r]+'">'+E(r)+'</span>'

def hub(d,rows,market):
    secs=[s for s in d['sectors'] if s['market']==market];name='A股' if market=='a' else '港股'
    home='../index.html' if market=='a' else '../hk/index.html'
    out='<style>'+CSS+'</style><div class="hero"><div><h1>'+name+'板块 · 按大盘风向选出</h1><p class="stamp">选板块 '+E(d['as_of'])+' · 窗口 '+E(d['window'])+'</p></div><div class="hero-meta">上游是<a href="'+home+'#horizon">大盘未来半年判断</a>；下游是个股研究（本轮暂不选股）。</div></div>'
    out+='<section class="ss-sum" id="conclusion"><h2>结论</h2><div class="tblwrap"><table class="mt ss-table"><thead><tr><th>板块</th><th>档位</th><th>对应的大盘驱动</th><th>一句话</th><th>开关或降级信号</th><th>变化</th></tr></thead><tbody>'
    for s in sorted(secs,key=lambda s:ORDER.index(s['rating'])):
        out+='<tr data-sector="'+s['id']+'"><td><a href="'+s['id']+'.html"><b>'+E(s['title'])+'</b></a></td><td>'+badge(s['rating'])+'</td><td>'+E(s['driver'])+'</td><td>'+E(s['verdict'])+'</td><td>'+E(s['switch'])+'</td><td><small>'+E(s['prev'])+'</small></td></tr>'
    out+='</tbody></table></div><div class="ss-legend">'+''.join('<p>'+badge(r['key'])+E(r['desc'])+'</p>' for r in d['ratings'])+'</div></section>'
    out+='<section id="excluded"><h2>未入选的方向与原因</h2><ul class="ss-ex">'
    for x in d['excluded']:
        if x['market']==market:out+='<li><b>'+E(x['name'])+'</b>：'+E(x['reason'])+'</li>'
    out+='</ul></section><details class="deep-research" id="method"><summary>选板块的方法与数据口径</summary><ol class="ss-steps">'+''.join('<li><b>'+E(x['name'])+'</b>：'+E(x['text'])+'</li>' for x in d['steps'])+'</ol>'
    if market=='a':
        bks=[b for s in secs for b in s['bks']]+[b for x in d['excluded'] if x['market']=='a' for b in x['bks']]
        out+='<h3>入选与未入选行业的同口径数据</h3>'+screen_table(rows,bks)
    else:
        out+='<p>港股尚无全行业同口径财务数据；本轮只在大盘驱动明确指向、且已有行业证据的方向内选择，数据缺口在各板块页标明。</p>'
    out+='<p class="note">'+E(d['data_note'])+' <a href="../data/sector-screen.json">全部120个行业数据</a></p></details>'
    return out

def detail(d,rows,s):
    mk='A股' if s['market']=='a' else '港股';back='index.html' if s['market']=='a' else 'hk.html'
    out='<style>'+CSS+'</style><div class="crumb"><a href="'+back+'">'+mk+'板块</a> ／ '+E(s['title'])+'</div><div class="hero"><div><h1>'+E(s['title'])+' '+badge(s['rating'])+'</h1><p class="sum">'+E(s['verdict'])+'</p></div><div class="hero-meta">窗口 '+E(d['window'])+'<br>变化：'+E(s['prev'])+'</div></div>'
    out+='<section id="why"><h2>为什么在这个方向里</h2><p>'+E(s['why'])+'</p><p class="note">对应大盘驱动：'+E(s['driver'])+'。</p></section>'
    out+='<section id="parts"><h2>板块自身的三件事</h2><div class="ss-parts">'
    for k in ['num','den','tap']:
        p=s['parts'][k];out+='<article class="ss-'+k+'"><span>'+PART_NAME[k]+'</span><h3>'+E(p['state'])+'</h3><p>'+E(p['text'])+'</p>'+refs(d,p['refs'],'../')+'</article>'
    out+='</div>'
    if s['bks']:out+='<details><summary>同口径行业数据</summary>'+screen_table(rows,s['bks'])+'<p class="note">'+E(d['data_note'])+'</p></details>'
    out+='</section><section id="switch"><h2>开关与降级信号</h2><p class="ss-switch">'+E(s['switch'])+'</p></section>'
    out+='<section id="tracking"><h2>跟踪单</h2><div class="tblwrap"><table class="mt ss-table"><thead><tr><th>指标</th><th>频率</th><th>现值</th><th>阈值与动作</th><th>数据从哪来</th></tr></thead><tbody>'
    for r in s['tracking']:out+='<tr>'+''.join('<td>'+E(x)+'</td>' for x in r)+'</tr>'
    out+='</tbody></table></div></section><section id="checks"><h2>证伪单</h2><div class="tblwrap"><table class="mt ss-table"><thead><tr><th>命题</th><th>现值</th><th>判定日</th><th>证实</th><th>证伪及动作</th><th>状态</th></tr></thead><tbody>'
    for r in s['checks']:out+='<tr>'+''.join('<td>'+E(x)+'</td>' for x in r)+'<td>待到期</td></tr>'
    out+='</tbody></table></div></section><section id="handoff"><h2>交给个股阶段：比较什么</h2><ul>'+''.join('<li>'+E(x)+'</li>' for x in s['handoff'])+'</ul><p class="note">本轮不选个股；以上是下一步研究个股时的比较维度。</p></section>'
    return out

def removed(text,back):
    return '<style>'+CSS+'</style><div class="hero"><h1>该板块已移出</h1><p class="sum">'+E(text)+'</p><p><a href="'+back+'">返回板块结论 →</a></p></div>'

def build(ctx):
    root=Path(ctx['ROOT']);d,rows=load(root);out=Path(ctx['SITE'])/'boards';page=ctx['page']
    for m,fn in [('a','index.html'),('hk','hk.html')]:
        (out/fn).write_text(page(('A股' if m=='a' else '港股')+'板块 | A 股框架笔记','bk',hub(d,rows,m),'../'),encoding='utf-8')
    for s in d['sectors']:
        (out/(s['id']+'.html')).write_text(page(s['title']+' | 板块','bk',detail(d,rows,s),'../'),encoding='utf-8')
    for k,t in d['removed_pages'].items():
        (out/(k+'.html')).write_text(page('已移出 | 板块','bk',removed(t,'index.html#excluded'),'../'),encoding='utf-8')
    (out/'screen.html').write_text(page('旧初筛页已停用 | 板块','bk',removed('旧的全市场初筛评分已停用；同口径数据与新的选板块方法见A股板块页。','index.html#method'),'../'),encoding='utf-8')

CSS="""
.ss-badge{display:inline-block;font-size:13px;font-weight:600;padding:2px 10px;border-radius:12px;vertical-align:middle;margin-right:8px;white-space:nowrap}.ss-up{background:#fbe9e4;color:#9b3d27}.ss-early{background:#fff4dc;color:#8a5a00}.ss-wait{background:#e8eef6;color:#2f4f6f}.ss-down{background:#e9f5ef;color:#2f6f53}
.ss-table{width:100%;min-width:900px}.ss-table td,.ss-table th{vertical-align:top;font-size:13.5px;line-height:1.75}.ss-table th small{display:block;font-weight:400;color:#6b7c8c;font-size:11px}
.ss-legend{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 20px;margin:14px 0;font-size:13.5px;line-height:1.8}.ss-legend p{margin:0}
.ss-ex li,.ss-steps li{font-size:14px;line-height:1.9}
.ss-parts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:12px 0}.ss-parts article{border:1px solid #d4dfeb;border-radius:8px;padding:16px 18px;background:#fff}.ss-parts span{font-size:12px;color:#64798d}.ss-parts h3{font-size:17px;margin:6px 0 10px}.ss-parts p{font-size:14px;line-height:1.85;margin:0 0 8px}.ss-parts .src{font-size:11.5px}
.ss-num{border-top:4px solid #3d6b8f!important}.ss-den{border-top:4px solid #8a6d3b!important}.ss-tap{border-top:4px solid #3f7d63!important}
#why,#parts,#switch,#tracking,#checks,#handoff,#excluded,#conclusion{margin:30px 0}.hero h1 .ss-badge{font-size:14px}
.ss-switch{background:#f3f6f9;border-radius:8px;padding:12px 16px;font-size:15px;line-height:1.8}
@media(max-width:900px){.ss-parts,.ss-legend{grid-template-columns:1fr}}
"""
