"""个股页：两条选股逻辑（顺势选股 / 国资箱体）。"""
import json
from pathlib import Path
from html import escape as E
import logic1_rules, logic2_box

HK={'hk-telecom':['中国移动 00941','中国电信 00728','工商银行 01398','建设银行 00939'],'hk-energy':['中国海洋石油 00883','中国神华 01088','中国石油股份 00857'],'hk-tanker':['中远海能 01138'],'hk-internet':['腾讯控股 00700','阿里巴巴 09988','美团 03690'],'hk-hardware':['中芯国际 00981','华虹半导体 01347']}

def f(x,p='.1f',suf=''):
    return '—' if x is None else format(x,p)+suf

def switch_state(root):
    idx=json.loads((Path(root)/'data/raw/idx_all.json').read_text())['rows']
    return {'close':idx[-1]['close'],'date':idx[-1]['date'],'on':idx[-1]['close']>=4700}

def box_svg(ref):
    pos=max(0,min(1,ref['pos']));y=lambda v:200-160*v
    pts='40,195 90,170 130,120 160,50 180,150 230,198 280,175 320,90 350,45 370,130 420,190 470,160 520,'+str(int(y(pos)))
    out='<svg viewBox="0 0 640 270" class="l2-svg" role="img" aria-label="箱体示意：地板、天花板、脉冲与当前位置"><rect x="30" y="40" width="560" height="160" fill="#f6f8fb"/>'
    out+='<rect x="30" y="168" width="560" height="32" fill="#e9f5ef"/><rect x="30" y="40" width="560" height="32" fill="#fbe9e4"/>'
    out+='<line x1="30" y1="200" x2="590" y2="200" stroke="#2f6f53" stroke-width="2"/><line x1="30" y1="40" x2="590" y2="40" stroke="#9b3d27" stroke-width="2"/>'
    out+='<line x1="30" y1="232" x2="590" y2="232" stroke="#2f6f53" stroke-dasharray="5 5"/><polyline points="'+pts+'" fill="none" stroke="#2f4f6f" stroke-width="2.5"/>'
    out+='<circle cx="520" cy="'+str(int(y(pos)))+'" r="7" fill="#c4572a"/><text x="532" y="'+str(int(y(pos))-12)+'" font-size="14" fill="#c4572a">现在</text>'
    out+='<text x="36" y="32" font-size="13" fill="#9b3d27">天花板：箱顶（90%分位）· 卖出区</text><text x="36" y="218" font-size="13" fill="#2f6f53">地板：箱底（10%分位）· 买入区</text><text x="36" y="250" font-size="13" fill="#2f6f53">止损线：跌破箱底15%</text><text x="168" y="62" font-size="13" fill="#455a6e">事件脉冲</text></svg>'
    return out

BADGE={'顺风':'up','前半段':'early','等开关':'wait'}
LAY={'好':'g','中':'m','差':'b'}
def lay(v):return '<span class="ly ly-'+LAY[v]+'">'+v+'</span>'

def view_of(rating,sid,x,i):
    if rating=='等开关':return ('观察：价格已确认，等开关' if x['pos']=='好' else '观察，开关前不买'),'wait'
    if x['fund']=='差' or x['chip']=='差':return '备选（有一层为差）',''
    if x['pos']=='差':return '等回落（位置偏高）',''
    return ('建议跟踪','go') if i<2 else ('备选','')

def fund_cells(t,x):
    e=x['en'] or {}
    if t=='crowded':return [f(x['dy'],'.2f','%'),f(x['np_yoy'],'+.0f','%'),f(x['pb'],'.2f'),f(e.get('roe'),'.1f','%')]
    if t=='upstream':return [f(x['np_yoy'],'+.0f','%'),f(x['dy'] if x['dy'] is not None else e.get('dy'),'.2f','%'),f(e.get('cashEps'),'.2f'),f(e.get('gmChg'),'+.1f')]
    if t=='growth':return [f(x['np_yoy'],'+.0f','%'),f((x['np_yoy'] or 0)-(x['h1_yoy'] or 0),'+.0f'),f(x['rev_yoy'],'+.0f','%'),f(e.get('cashEps'),'.2f')]
    return [f(e.get('gmChg'),'+.1f'),f(x['np_yoy'],'+.0f','%'),f(x['rev_yoy'],'+.0f','%'),f(e.get('cashEps'),'.2f')]
FH={'crowded':['股息率','单季利润同比','PB','前三季ROE'],'upstream':['单季利润同比','股息率','现金/利润','毛利率变化'],'growth':['单季利润同比','加速（百分点）','营收同比','现金/利润'],'cost':['毛利率变化','单季利润同比','营收同比','现金/利润']}

def logic1_data(root,S):
    return logic1_rules.select_v2(root,S['sectors'])

def overview_html(L1,sec,L2):
    out='<section id="overview"><h2>候选总览</h2><p class="note">先看这张表，点股票名直接跳到它所在的板块。每只股票分三层判断：基本面（各板块看的指标不同）、位置、筹码。</p><div class="tblwrap"><table class="mt lp-table ov-table"><thead><tr><th>板块</th><th>档位</th><th>这个板块的个股看什么</th><th>候选与初步意见</th></tr></thead><tbody>'
    order=['顺风','前半段','等开关']
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        s=sec[sid];r=L1[sid];chips=[]
        for i,x in enumerate(r['picks']):
            v,c=view_of(s['rating'],sid,x,i);chips.append('<a class="ov-c '+c+'" href="#l1-'+sid+'">'+E(x['name'])+'<small>'+E(v)+'</small></a>')
        out+='<tr><th scope="row"><a href="#l1-'+sid+'">'+E(s['title'])+'</a></th><td><span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span></td><td><small>'+E(r['lens']['name'])+'：'+E(r['lens']['fund'].split('：')[0])+'</small></td><td>'+''.join(chips)+'</td></tr>'
    out+='<tr><th scope="row"><a href="box.html">逻辑二：国资箱体</a></th><td><span class="lp-badge lp-wait">观察</span></td><td><small>箱体位置、往返次数、事件脉冲</small></td><td>'+''.join('<a class="ov-c wait" href="box.html#logic2">'+E(x['name'])+'</a>' for x in L2['top'][:8])+'<a class="ov-c" href="box.html#logic2">…共'+str(L2['funnel'][-1][1])+'只</a></td></tr>'
    return out+'</tbody></table></div></section>'

def logic1_html(root,S,sec,L1):
    out='<section id="logic1"><h2>逻辑一：顺势选股（按板块展开）</h2><p class="note">门槛与基本面排名同前（市值只作门槛）。在此基础上，每个板块按自己的类型加看“位置”和“筹码”，三层合成排序：基本面百分位、位置、筹码各占三分之一；基本面出现硬伤（例如毛利率下降、现金流为负）时总分减半。</p>'
    order=['顺风','前半段','等开关']
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        s=sec[sid];r=L1[sid];t=r['type'];Lz=r['lens']
        out+='<details class="lp-sec" id="l1-'+sid+'"'+('' if s['rating']=='等开关' else ' open')+'><summary><h3>'+E(s['title'])+' <span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span></h3><span class="lp-sum">'+'、'.join(E(x['name']) for x in r['picks'])+'</span></summary>'
        out+='<div class="lens"><p><b>这类板块（'+E(Lz['name'])+'）看什么：</b></p><ul><li><b>基本面：</b>'+E(Lz['fund'])+'</li><li><b>位置：</b>'+E(Lz['pos'])+'</li><li><b>筹码：</b>'+E(Lz['chip'])+'</li></ul><p class="lp-rule"><b>门槛：</b>'+E(r['gate'])+'　<b>通过：</b>'+str(r['passed'])+' / '+str(r['pool'])+'家　<a href="../boards/'+sid+'.html">板块依据 →</a></p></div>'
        out+='<div class="tblwrap"><table class="mt lp-table"><thead><tr><th rowspan="2">股票</th><th colspan="5">基本面</th><th colspan="4">位置</th><th colspan="5">筹码</th><th rowspan="2">提示</th><th rowspan="2">初步意见</th></tr><tr>'+''.join('<th>'+h+'</th>' for h in FH[t])+'<th>判断</th><th>一年位置</th><th>距高点</th><th>相对60日线</th><th>判断</th><th>股东户数变化</th><th>融资20日</th><th>融资占比</th><th>6个月解禁</th><th>判断</th></tr></thead><tbody>'
        for i,x in enumerate(r['picks']):
            e=x['en'] or {};v,c=view_of(s['rating'],sid,x,i)
            out+='<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+'</small></th>'+''.join('<td>'+v_+'</td>' for v_ in fund_cells(t,x))+'<td>'+lay(x['fund'])+'</td><td>'+f(e.get('pos52'),'.2f')+'</td><td>'+f(e.get('dd'),'.0f','%')+'</td><td>'+f(e.get('vsMA60'),'+.0f','%')+'</td><td>'+lay(x['pos'])+'</td><td>'+f(e.get('holdersChg'),'+.0f','%')+'<small>'+E(e.get('hdate') or '')+'</small></td><td>'+f(e.get('margin20'),'+.0f','%')+'</td><td>'+f(e.get('marginPct'),'.1f','%')+'</td><td>'+f(e.get('lift6m'),'.1f','%')+'</td><td>'+lay(x['chip'])+'</td><td><small>'+E('；'.join(([x['flag']] if x['flag'] else [])+x['notes']))+'</small></td><td><span class="lp-view '+c+'">'+E(v)+'</span></td></tr>'
        out+='</tbody></table></div><p class="note">进入个股研究时还要比较：'+E('；'.join(s['handoff']))+'</p></details>'
    out+='<article class="lp-sec" id="l1-hk"><h3>港股（规则待数据）</h3><p class="note">港股尚无同口径公司数据，暂按板块列出代表公司，不排序。</p><ul>'
    for sid,names in HK.items():out+='<li><b>'+E(sec[sid]['title'])+'（'+E(sec[sid]['rating'])+'）</b>：'+E('、'.join(names))+'</li>'
    return out+'</ul></article></section>'

def l2_row(x,note):
    return '<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+' · '+E(x['ind'])+'</small></th><td>'+str(x['mc'])+'</td><td>'+f(x['W']*100,'.0f','%')+'</td><td>'+str(x['swings'])+'</td><td>'+str(x['lu'])+' / '+str(x['sp'])+'</td><td>'+f(x['pos'],'.2f')+'</td><td>'+f(x['corr'],'.2f')+'</td><td>'+f(x.get('rev9m'),'.0f')+' / '+f(x.get('np9m'),'.2f')+'</td><td>'+E('、'.join(x['tags'][:3]))+'</td><td>'+E(note)+'</td></tr>'

def logic2_html(L2,sw):
    ref=L2['reference'];R=logic2_box.RULES;A=logic2_box.ACTIONS
    out='<section id="logic2"><h2>逻辑二：国资箱体</h2><div class="l2-intro"><div>'+box_svg(ref)+'</div><div><p>把一只股票想成一个房间：<b>地板</b>是国资背景和净资产带来的下限，<b>天花板</b>是没有业绩支撑时游资和散户愿意追到的上限，<b>烟花</b>是政策、重组、题材事件带来的脉冲。</p><p>它赚钱的方式不是盈利增长，而是“在地板附近买、在天花板附近卖、遇到烟花就兑现”。</p><p class="note">图中“现在”按乐凯胶片当前位置（'+f(ref['pos'],'.2f')+'）画出。</p></div></div>'
    out+='<h3>六个可量化的入选条件（以乐凯胶片为例）</h3><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>条件</th><th>怎么算</th><th>乐凯胶片</th><th>是否满足</th></tr></thead><tbody>'
    rows=[('国资与安全',R['universe'],'市值'+str(ref['mc'])+'亿 · PB '+f(ref['pb'],'.2f'),True),('有箱体',R['box'],'宽度'+f(ref['W']*100,'.0f','%'),.25<=ref['W']<=1.2),('没有单边趋势',R['flat'],f(ref['trend'],'+.2f'),abs(ref['trend'])<=.3),('来回震荡',R['swings'],str(ref['swings'])+'次',ref['swings']>=2),('地板有效',R['floor'],f(ref['floor']*100,'.0f','%'),ref['floor']>=-.15),('有事件脉冲',R['hot'],'涨停'+str(ref['lu'])+'次 · 脉冲'+str(ref['sp'])+'次',ref['lu']>=4 and ref['sp']>=1)]
    for a,b,c,ok in rows:out+='<tr><th scope="row">'+E(a)+'</th><td>'+E(b)+'</td><td>'+E(c)+'</td><td>'+('满足' if ok else '不满足')+'</td></tr>'
    out+='</tbody></table></div><h3>三个动作与一个暂停条件</h3><div class="l2-act"><p><b>买：</b>'+E(A['buy'])+'</p><p><b>卖：</b>'+E(A['sell'])+'</p><p><b>止损：</b>'+E(A['stop'])+'</p><p class="l2-sw '+('on' if sw['on'] else 'off')+'"><b>'+E(A['switch'])+'<br>现在：中证全指'+f(sw['close'],',.0f')+'（'+sw['date']+'）→ '+('规则允许研究买点' if sw['on'] else '暂停开新仓')+'</p></div>'
    pb=L2.get('pbt');o=L2['oos_1y']
    out+='<h3 id="l2-bt">按真实规则做组合回测</h3><div class="l2-bt">'
    if pb:
        B=pb['base'];M=pb['bench']
        out+='<p>'+E(pb['setup'])+'</p><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>指标</th><th>策略（'+str(B['K'])+'只上限，成本'+f(B['cost'],'.1f','%')+'）</th><th>同一股票池等权持有</th></tr></thead><tbody>'
        for lab,k,suf in [('年化收益','cagr','%'),('累计收益','total','%'),('最大回撤','mdd','%')]:out+='<tr><th scope="row">'+lab+'</th><td>'+f(B[k],'+.1f',suf)+'</td><td>'+f(M[k],'+.1f',suf)+'</td></tr>'
        out+='<tr><th scope="row">平均仓位</th><td>'+str(B['exposure'])+'%</td><td>100%</td></tr><tr><th scope="row">交易次数 / 胜率</th><td>'+str(B['trades'])+' / '+str(B['win'])+'%</td><td>—</td></tr><tr><th scope="row">单笔平均 / 中位</th><td>'+f(B['avg'],'+.1f','%')+' / '+f(B['median'],'+.1f','%')+'</td><td>—</td></tr><tr><th scope="row">收益最高的10%交易占总盈利</th><td>'+str(B['top10share'])+'%</td><td>—</td></tr><tr><th scope="row">退出方式</th><td>'+E('、'.join(k+str(v)+'次' for k,v in B['exits'].items()))+'</td><td>—</td></tr>'
        ys=sorted(B['annual']);out+='</tbody></table></div><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>年份</th>'+''.join('<th>'+y+'</th>' for y in ys)+'</tr></thead><tbody><tr><th scope="row">策略</th>'+''.join('<td>'+f(B['annual'][y],'+.1f','%')+'</td>' for y in ys)+'</tr><tr><th scope="row">等权基准</th>'+''.join('<td>'+f(M['annual'].get(y),'+.1f','%')+'</td>' for y in ys)+'</tr></tbody></table></div>'
        out+='<p><b>稳健性：</b>'+E(pb['robust'])+'</p><p class="note"><b>偏差：</b>'+E(pb['bias'])+'</p>'
    out+='<p class="note"><b>信号层面统计（旧口径）：</b>2019—2026年2,357次箱底信号，120日平均+4.5%、中位+0.2%；最近一年箱体股信号平均'+f(o['box_hot']['mean'],'+.1f','%')+'。</p><p class="l2-con"><b>结论：</b>'+E(L2.get('verdict',''))+'</p></div>'
    fun=L2['funnel'];out+='<h3 id="l2-list">候选名单</h3><ol class="lp-funnel">'+''.join('<li>'+E(a)+'：<b>'+str(b)+'</b></li>' for a,b in fun)+'</ol>'
    out+='<div class="tblwrap"><table class="mt lp-table"><thead><tr><th>股票</th><th>市值（亿）</th><th>箱体宽度</th><th>往返</th><th>涨停 / 脉冲</th><th>当前位置</th><th>与大盘相关</th><th>前三季营收 / 利润（亿）</th><th>主要标签</th><th>初步意见</th></tr></thead><tbody>'
    for x in L2['top']:out+=l2_row(x,'观察（组合化跟踪）' if sw['on'] else '暂停')
    out+=l2_row(ref,'参考样本：满足六项条件，未进首批（脉冲1次、往返2次，重复性不足）')
    out+='</tbody></table></div><p class="note">排序：往返次数＋2×脉冲次数，从高到低；同分时位置更低者优先。这里列出前15名，另有'+str(fun[-1][1]-len(L2['top']))+'只同样满足条件。亏损公司需单独确认没有财务类退市风险。</p></section>'
    return out

def head(active):
    return '<nav class="lp-tabs"><a href="index.html"'+(' aria-current="page"' if active==1 else '')+'><b>逻辑一 · 顺势选股</b><span>大盘→板块→个股</span></a><a href="box.html"'+(' aria-current="page"' if active==2 else '')+'><b>逻辑二 · 国资箱体</b><span>地板、天花板、烟花</span></a></nav>'

def page(ctx):
    root=Path(ctx['ROOT']);S=json.loads((root/'data/sector_selection.json').read_text());P=json.loads((root/'data/stock_pick.json').read_text())
    sec={s['id']:s for s in S['sectors']};L1=logic1_data(root,S)
    out='<style>'+CSS+'</style><div class="hero"><h1>个股</h1><p class="sum">两条逻辑分开看：逻辑一顺着大盘和板块选；逻辑二利用A股国资股的箱体特征。数据截至2026-11-13，本页只提候选，不做买卖决定。</p></div>'+head(1)
    out+=overview_html(L1,sec,P['logic2'])+logic1_html(root,S,sec,L1)
    return out+'<p class="note">'+E(P['source'])+' 位置与筹码数据：'+E(json.loads((root/'data/raw/stock_pick/l1_enrich.json').read_text())['_meta']['source'])+'。</p>'

def box_page(ctx):
    root=Path(ctx['ROOT']);P=json.loads((root/'data/stock_pick.json').read_text());sw=switch_state(root)
    out='<style>'+CSS+'</style><div class="hero"><h1>个股 · 国资箱体</h1><p class="sum">有地板、有天花板、偶尔放烟花的房间。规则、验证与候选都在本页。</p></div>'+head(2)
    out+='<nav class="lp-jump"><a href="#logic2">规则</a><a href="#l2-bt">回测</a><a href="#l2-list">候选名单</a></nav>'
    return out+logic2_html(P['logic2'],sw)+'<p class="note">'+E(P['source'])+'</p>'

def build(ctx):
    site=Path(ctx['SITE'])
    (site/'stocks/index.html').write_text(ctx['page']('个股 | A 股框架笔记','gg',page(ctx),'../'),encoding='utf-8')
    (site/'stocks/box.html').write_text(ctx['page']('国资箱体 | A 股框架笔记','gg',box_page(ctx),'../'),encoding='utf-8')

CSS="""
.lp-tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0 22px;position:sticky;top:56px;z-index:5;background:var(--paper,#f4f5f7);padding:6px 0}.lp-tabs a{border:1px solid #d4dfeb;border-radius:10px;padding:12px 16px;background:#fff;text-decoration:none;color:#223e57}.lp-tabs a[aria-current]{border-color:#365875;box-shadow:inset 0 -3px 0 #365875}.lp-tabs b{display:block;font-size:16px}.lp-tabs span{font-size:12.5px;color:#64798d}
.lp-jump{display:flex;gap:10px;margin:0 0 10px}.lp-jump a{font-size:13px;padding:4px 10px;border-radius:14px;background:#eef2f6;text-decoration:none}
.ov-c{display:inline-block;margin:3px 6px 3px 0;padding:4px 9px;border-radius:8px;background:#f3f6f9;font-size:13px;text-decoration:none;color:#223e57}.ov-c small{display:block;font-size:11px;color:#64798d}.ov-c.go{background:#fbe9e4}.ov-c.wait{background:#e8eef6}
.lens{background:#f6f8fa;border-radius:8px;padding:10px 14px;margin:8px 0}.lens ul{margin:4px 0 6px;padding-left:18px}.lens li,.lens p{font-size:13.5px;line-height:1.75;margin:2px 0}
.ly{display:inline-block;padding:1px 7px;border-radius:9px;font-size:12px}.ly-g{background:#e9f5ef;color:#2f6f53}.ly-m{background:#eef2f6;color:#455a6e}.ly-b{background:#fbe9e4;color:#9b3d27}
.lp-sum{font-size:13px;color:#52687b;margin-left:10px}details.lp-sec>summary{cursor:pointer}details.lp-sec>summary h3{display:inline}
.lp-table thead tr:first-child th{text-align:center;background:#f3f6f9}
.lp-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin:20px 0}.lp-two article{border:1px solid #d4dfeb;border-radius:10px;padding:18px 22px;background:#fff}.lp-two span{font-size:13px;color:#64798d;font-weight:600}.lp-two h2{font-size:20px;margin:6px 0 12px}.lp-two p{font-size:14.5px;line-height:1.85;margin:0 0 8px}
.lp-funnel{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}.lp-funnel li{background:#f3f6f9;border-radius:8px;padding:8px 12px;font-size:13.5px;line-height:1.6}
.lp-sec{border-top:1px solid #e1e8f0;padding:14px 0}.lp-sec h3{font-size:18px;margin:6px 0;display:inline}details.lp-sec>summary{cursor:pointer;list-style-position:outside}.lp-rule{font-size:13.5px;color:#455a6e;line-height:1.8}
.lp-badge{font-size:12.5px;padding:2px 9px;border-radius:12px;margin-left:6px}.lp-up{background:#fbe9e4;color:#9b3d27}.lp-early{background:#fff4dc;color:#8a5a00}.lp-wait{background:#e8eef6;color:#2f4f6f}
.lp-table{width:100%;min-width:900px}.lp-table td,.lp-table th{font-size:13.5px;line-height:1.7;vertical-align:top}.lp-table th small{display:block;font-weight:400;color:#6b7c8c;font-size:11.5px}
.lp-view{font-size:12.5px;padding:2px 8px;border-radius:10px;background:#eef2f6;white-space:nowrap}.lp-view.go{background:#fbe9e4;color:#9b3d27}.lp-view.wait{background:#e8eef6;color:#2f4f6f}
.l2-intro{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:20px;align-items:center}.l2-intro p{font-size:14.5px;line-height:1.9}.l2-svg{width:100%;height:auto}
.l2-act{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.l2-act p{margin:0;background:#f6f8fa;border-radius:8px;padding:10px 12px;font-size:14px;line-height:1.8}.l2-sw{grid-column:1/-1}.l2-sw.off{background:#eef2f6!important}.l2-sw.on{background:#e9f5ef!important}
.l2-bt p{font-size:14.5px;line-height:1.9}.l2-con{background:#fff4dc;border-radius:8px;padding:10px 14px}
#logic1,#logic2{margin:34px 0}
@media(max-width:900px){.lp-two,.l2-intro,.l2-act{grid-template-columns:1fr}}
"""
