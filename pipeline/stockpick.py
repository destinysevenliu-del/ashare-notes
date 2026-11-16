"""个股页：两条选股逻辑（顺势选股 / 国资箱体）。"""
import json
from pathlib import Path
from html import escape as E
import logic1_rules, logic2_box, stockcards as SC

HK={'hk-telecom':['中国移动 00941','中国电信 00728','工商银行 01398','建设银行 00939'],'hk-energy':['中国海洋石油 00883','中国神华 01088','中国石油股份 00857'],'hk-tanker':['中远海能 01138'],'hk-internet':['腾讯控股 00700','阿里巴巴 09988','美团 03690'],'hk-hardware':['中芯国际 00981','华虹半导体 01347']}

def f(x,p='.1f',suf=''):
    return '—' if x is None else format(x,p)+suf

def switch_state(root):
    idx=json.loads((Path(root)/'data/raw/idx_all.json').read_text())['rows'];last={'close':idx[-1]['close'],'date':idx[-1]['date']}
    p=Path(root)/'data/raw/weekly/state.json'
    if p.exists():
        w=json.loads(p.read_text()).get('csi_all')
        if w and w['date']>last['date']:last={'close':w['close'],'date':w['date']}
    return {**last,'on':last['close']>=4700}

def asof(root):
    return json.loads((Path(root)/'data/raw/stock_pick/l1_enrich.json').read_text())['_meta']['as_of']

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
    pl=x.get('pl') or {}
    if rating!='等开关' and str(pl.get('where','')).startswith('已在卖出区'):return '不买：已到卖出参考价',''
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
    logic1_rules.CN10Y=logic1_rules.cn10y(root)['value']
    r=logic1_rules.select_v2(root,S['sectors'])
    for v in r.values():
        for x in v['picks']:x['pl']=logic1_rules.price_levels(v['type'],x)
    return r

def money(v):return '—' if v is None else format(v,'.2f')

def plan_table(t,picks,day='2026-11-13'):
    R=logic1_rules.PRICE_RULES[t]
    out='<div class="plan"><p class="plan-h"><b>价格计划</b>（研究规则，未回测；按'+day+'收盘计算'+('，10年国债'+format(logic1_rules.CN10Y,'.2f')+'%' if t=='crowded' else '')+'；每周重算；<a href="#price-rules">完整规则与原因 →</a>）</p><ul><li><b>买入：</b>'+E(R['buy'])+'</li><li><b>卖出：</b>'+E(R['sell'])+'</li><li><b>止损：</b>'+E(R['stop'])+'</li></ul><div class="tblwrap"><table class="mt lp-table plan-table"><thead><tr><th>股票</th><th>现价</th><th>参考买入区间</th><th>卖出参考价</th><th>第二目标</th><th>止损价</th><th>盈亏比</th><th>现价状态</th></tr></thead><tbody>'
    for x in picks:
        pl=x.get('pl')
        if not pl:out+='<tr><th scope="row">'+E(x['name'])+'</th><td colspan="7">价格数据不足</td></tr>';continue
        out+='<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+'</small></th><td>'+money(pl['close'])+'</td><td><b>'+money(pl['buy'][0])+' — '+money(pl['buy'][1])+'</b></td><td><b>'+money(pl['sell'])+'</b></td><td>'+money(pl.get('sell2'))+'</td><td>'+money(pl.get('stop'))+'</td><td>'+('—' if pl.get('rr') is None else format(pl['rr'],'.1f'))+'</td><td>'+E(pl['where'])+'</td></tr>'
    return out+'</tbody></table></div><p class="note">表中的盈亏比＝（卖出参考价−买入区中点）÷（买入区中点−止损价）；低于2说明按这套价位做，赚的空间不足亏的两倍，需要更好的买点。</p></div>'

def overview_html(L1,sec,L2,sw=None,F={}):
    out='<section id="overview"><h2>候选总览</h2><p class="note">先看这张表，点股票名直接跳到它所在的板块。每只股票分三层判断：基本面（各板块看的指标不同）、位置、筹码。</p><div class="tblwrap"><table class="mt lp-table ov-table"><thead><tr><th>板块</th><th>档位</th><th>这个板块的个股看什么</th><th>候选与初步意见</th></tr></thead><tbody>'
    order=['顺风','前半段','等开关']
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        s=sec[sid];r=L1[sid];chips=[]
        for i,x in enumerate(r['picks']):
            v,c=view_of(s['rating'],sid,x,i);pl=x.get('pl');pr=('买'+money(pl['buy'][0])+'—'+money(pl['buy'][1])+' · 卖'+money(pl['sell'])) if pl else ''
            chips.append('<a class="ov-c '+c+'" href="#l1-'+sid+'">'+E(x['name'])+'<small>'+E(v)+'</small><small>'+E(pr)+'</small></a>')
        out+='<tr><th scope="row"><a href="#l1-'+sid+'">'+E(s['title'])+'</a></th><td><span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span></td><td><small>'+E(r['lens']['name'])+'：'+E(r['lens']['fund'].split('：')[0])+'</small></td><td>'+''.join(chips)+'</td></tr>'
    out+='<tr><th scope="row"><a href="box.html">逻辑二：国资箱体</a></th><td><span class="lp-badge lp-wait">观察</span></td><td><small>地板（净资产与退市红线）、箱体位置、筹码、烟花频率</small></td><td>'+''.join('<a class="ov-c wait" href="box.html#logic2">'+E(x['name'])+'</a>' for x in L2['top'][:8])+'<a class="ov-c" href="box.html#logic2">…共'+str(L2['funnel'][-1][1])+'只</a></td></tr>'
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
        out+='</tbody></table></div>'+plan_table(t,r['picks'],asof(root))+'<p class="note">进入个股研究时还要比较：'+E('；'.join(s['handoff']))+'</p></details>'
    out+='<article class="lp-sec" id="l1-hk"><h3>港股（规则待数据）</h3><p class="note">港股尚无同口径公司数据，暂按板块列出代表公司，不排序。</p><ul>'
    for sid,names in HK.items():out+='<li><b>'+E(sec[sid]['title'])+'（'+E(sec[sid]['rating'])+'）</b>：'+E('、'.join(names))+'</li>'
    return out+'</ul></article></section>'

def box_px(x):
    b=logic1_rules.box_levels(x)
    return '<td><b>'+money(b['buy'][0])+'—'+money(b['buy'][1])+'</b><small>现价'+money(b['close'])+' · '+E(b['where'])+'</small></td><td><b>'+money(b['sell'])+'</b></td><td>'+money(b['stop'])+'<small>盈亏比'+format(b['rr'],'.1f')+'</small></td>'

def l2_fund(root):
    p=Path(root)/'data/raw/stock_pick/l2_fund.json'
    return json.loads(p.read_text()) if p.exists() else {}

VORD=['优先','备选','观察：筹码不稳','等回到买入区','等收回箱底','等回落','暂停开新仓','已破位，不接','剔除：地板不牢']
VCLS={'优先':'go','备选':'','观察：筹码不稳':'wait','等回到买入区':'wait','等收回箱底':'wait','等回落':'wait','暂停开新仓':'wait','已破位，不接':'bad','剔除：地板不牢':'bad'}

def l2_judged(L2,sw,F):
    rows=[]
    for x in L2['top']:rows.append((x,logic2_box.judge(x,F.get(x['code']),x.get('en'),sw['on']),False))
    r=L2['reference'];rows.append((r,logic2_box.judge(r,F.get(r['code']),r.get('en'),sw['on']),True))
    rows.sort(key=lambda t:(t[2],VORD.index(t[1]['view']),t[0]['pos']))
    return rows

def l2_judge_html(L2,sw,F):
    Z=logic2_box.L2_LENS;rows=l2_judged(L2,sw,F)
    out='<section id="l2-judge"><h2>逐只判断</h2><p class="note">箱体股赚的是“地板附近买、天花板附近卖、遇到烟花兑现”的钱，所以四层看的东西和逻辑一不同。策略整体结论仍是“观察”（见下方回测）：单只判断用来决定组合里放谁、先放谁、剔除谁，不用来预测单只涨跌。价格截至'+E(L2.get('px_asof','—'))+'，财报为2026年三季报。</p>'
    groups={}
    for x,j,ref in rows:
        if not ref:groups.setdefault(j['view'],[]).append(x)
    out+='<div class="l2-groups">'+''.join('<div class="l2-g"><span class="lp-view '+VCLS[v]+'">'+E(v)+' · '+str(len(groups[v]))+'只</span> '+'、'.join('<a href="#j-'+x['code']+'">'+E(x['name'])+'</a>' for x in groups[v])+'</div>' for v in VORD if v in groups)+'</div>'
    out+='<details class="lens"><summary><b>四层各看什么、怎么判“好/中/差”</b></summary><ul>'+''.join('<li><b>'+E(Z[k][0])+'（'+{'fund':'基本面','pos':'位置','chip':'筹码','box':'箱体质量'}[k]+'）：</b>'+E(Z[k][1])+'</li>' for k in ('fund','pos','chip','box'))+'<li><b>结论怎么得出：</b>'+E(Z['view'])+'</li></ul></details>'
    out+='<div class="tblwrap"><table class="mt lp-table l2j-table"><thead><tr><th rowspan="2">股票</th><th colspan="5">基本面：地板结不结实</th><th colspan="3">位置：离箱底多近</th><th colspan="4">筹码：谁在里面</th><th colspan="3">箱体质量</th><th rowspan="2">结论与理由</th></tr><tr><th>前三季营收（亿）</th><th>前三季利润（亿）</th><th>PB</th><th>ROE</th><th>判断</th><th>箱体位置</th><th>参考买入</th><th>判断</th><th>户数变化</th><th>融资20日</th><th>6个月解禁</th><th>判断</th><th>往返</th><th>脉冲 / 涨停</th><th>判断</th></tr></thead><tbody>'
    for x,j,ref in rows:
        q=(F.get(x['code']) or {}).get('q3') or {};pb=(F.get(x['code']) or {}).get('pb');e=x.get('en') or {};b=logic1_rules.box_levels(x)
        out+='<tr id="j-'+x['code']+'"'+(' class="l2-ref"' if ref else '')+'><th scope="row">'+E(x['name'])+'<small>'+x['code']+' · '+E(x['ind'])+(' · 参考样本' if ref else '')+'</small></th>'
        out+='<td>'+f(q.get('rev_m') and q['rev_m']/100,'.1f')+'</td><td>'+f(q.get('np_m') is not None and q['np_m']/100 or (0 if q.get('np_m')==0 else None),'+.2f')+'</td><td>'+f(pb,'.2f')+'</td><td>'+f(q.get('roe'),'.1f','%')+'</td><td>'+lay(j['fund'])+'</td>'
        out+='<td>'+f(x['pos'],'.2f')+'<small>现价'+money(x['close'])+'</small></td><td>'+money(b['buy'][0])+'—'+money(b['buy'][1])+'</td><td>'+lay(j['pos'])+'</td>'
        out+='<td>'+f(e.get('holdersChg'),'+.0f','%')+'</td><td>'+f(e.get('margin20'),'+.0f','%')+'</td><td>'+f(e.get('lift6m'),'.1f','%')+'</td><td>'+lay(j['chip'])+'</td>'
        out+='<td>'+str(x['swings'])+'</td><td>'+str(x['sp'])+' / '+str(x['lu'])+'</td><td>'+lay(j['box'])+'</td>'
        out+='<td><span class="lp-view '+VCLS[j['view']]+'">'+E(j['view'])+'</span><small class="l2-why">'+E(j['why'] or '四层无扣分项')+'</small></td></tr>'
    return out+'</tbody></table></div><p class="note">融资一栏为“—”表示该股不是融资融券标的。基本面每季度更新，位置和筹码每周更新。</p></section>'

def l2_row(x,note):
    return '<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+' · '+E(x['ind'])+'</small></th><td>'+str(x['mc'])+'</td><td>'+f(x['W']*100,'.0f','%')+'</td><td>'+str(x['swings'])+'</td><td>'+str(x['lu'])+' / '+str(x['sp'])+'</td><td>'+f(x['pos'],'.2f')+'</td><td>'+f(x['corr'],'.2f')+'</td><td>'+f(x.get('rev9m'),'.0f')+' / '+f(x.get('np9m'),'.2f')+'</td><td>'+E('、'.join(x['tags'][:3]))+'</td>'+box_px(x)+'<td>'+E(note)+'</td></tr>'

def logic2_html(L2,sw,F={}):
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
    out+='<details class="more"><summary>查看候选名单全部参数（箱体、标签、价格）</summary><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>股票</th><th>市值（亿）</th><th>箱体宽度</th><th>往返</th><th>涨停 / 脉冲</th><th>当前位置</th><th>与大盘相关</th><th>前三季营收 / 利润（亿）</th><th>主要标签</th><th>参考买入</th><th>卖出参考</th><th>止损</th><th>逐只判断</th></tr></thead><tbody>'
    J={x['code']:j['view'] for x,j,_ in l2_judged(L2,sw,F)}
    for x in L2['top']:out+=l2_row(x,J[x['code']])
    out+=l2_row(ref,'参考样本：满足六项条件，未进首批（脉冲1次、往返2次，重复性不足）')
    out+='</tbody></table></div><p class="note">排序：往返次数＋2×脉冲次数，从高到低；同分时位置更低者优先。这里列出前15名，另有'+str(fun[-1][1]-len(L2['top']))+'只同样满足条件。亏损公司需单独确认没有财务类退市风险。</p></details></section>'
    return out


def rules_html():
    D=logic1_rules.PRICE_DOC
    out='<section id="price-rules"><h2>价格规则：买入价、卖出价、止损价怎么算</h2><p class="note">本页所有价格都按下面的规则计算。规则写在这里，以后跟进时按同一套口径重算，不凭当时的感觉调。</p>'
    out+='<h3>一、四类板块各用一套规则</h3><div class="tblwrap"><table class="mt lp-table pr-table"><thead><tr><th>板块类型</th><th>买入</th><th>卖出</th><th>止损</th><th>为什么这样定</th></tr></thead><tbody>'
    for r in D['types']:out+='<tr><th scope="row">'+E(r['name'])+'<small>'+E(r['sectors'])+'</small></th><td>'+E(r['buy'])+'</td><td>'+E(r['sell'])+'</td><td>'+E(r['stop'])+'</td><td><small>'+E(r['why'])+'</small></td></tr>'
    out+='</tbody></table></div><h3>二、共同原则</h3><dl class="pr-dl">'+''.join('<dt>'+E(a)+'</dt><dd>'+E(b)+'</dd>' for a,b in D['common'])+'</dl>'
    out+='<details class="pr-in"><summary><b>三、输入数据怎么来</b>（一年高低点、60日均线等的换算）</summary><dl class="pr-dl">'+''.join('<dt>'+E(a)+'</dt><dd>'+E(b)+'</dd>' for a,b in D['inputs'])+'</dl></details>'
    return out+'<p class="note">逻辑二（国资箱体）的价格规则见 <a href="box.html#box-rules">国资箱体页</a>。</p></section>'

def box_rules_html():
    B=logic1_rules.PRICE_DOC['box']
    return '<section id="box-rules"><h2>价格规则：箱体怎么定买卖价</h2><dl class="pr-dl"><dt>箱体</dt><dd>'+E(B['inputs'])+'</dd><dt>买入</dt><dd>'+E(B['buy'])+'</dd><dt>卖出</dt><dd>'+E(B['sell'])+'</dd><dt>止损</dt><dd>'+E(B['stop'])+'</dd><dt>暂停</dt><dd>'+E(B['pause'])+'</dd><dt>为什么</dt><dd>'+E(B['why'])+'</dd><dt>盈亏比</dt><dd>'+E(dict(logic1_rules.PRICE_DOC['common'])['盈亏比'])+'</dd></dl></section>'

def weekly_html(root):
    p=Path(root)/'data/weekly_changes.json'
    if not p.exists():return '<section id="weekly"><h2>本周变化</h2><p class="note">还没有跑过每周更新（pipeline/weekly_update.py）。第一次运行只建立基准快照，从第二次开始列出变化。</p></section>'
    W=json.loads(p.read_text())
    out='<section id="weekly"><h2>本周变化</h2><p class="note">截止'+E(W['asof'])+(('，与'+E(W['prev'])+'相比') if W['prev'] else '（首次建立基准快照，下次更新开始列出变化）')+'。只列状态有变化的股票；状态分布：'+E('，'.join(k+str(v)+'只' for k,v in W['summary'].items()))+'。</p>'
    out+=''.join('<p class="wk-alert">'+E(a)+'</p>' for a in W['alerts'])
    if W['prev']:
        if not W['items']:out+='<p>本周没有股票改变状态。</p>'
        else:
            out+='<div class="tblwrap"><table class="mt lp-table wk-table"><thead><tr><th>股票</th><th>逻辑</th><th>上周</th><th>本周</th><th>现价</th></tr></thead><tbody>'
            for x in W['items']:out+='<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+'</small></th><td>'+E(x['logic'])+'</td><td>'+E(x['from'])+'</td><td><b>'+E(x['to'])+'</b></td><td>'+money(x['close'])+'</td></tr>'
            out+='</tbody></table></div>'
    return out+'</section>'

# ================= 卡片式展现（2026-11-16 改版） =================
def short(t):return t.split('（')[0]

def l1_texts(t,x):
    e=x.get('en') or {}
    fund=' · '.join(h+' '+v for h,v in zip(FH[t],fund_cells(t,x)))
    pos='一年位置 '+f(e.get('pos52'),'.2f')+' · 距一年高点 '+f(e.get('dd'),'.0f','%')+' · 相对60日线 '+f(e.get('vsMA60'),'+.0f','%')
    chip='股东户数 '+f(e.get('holdersChg'),'+.0f','%')+' · 融资20日 '+f(e.get('margin20'),'+.0f','%')+' · 融资占比 '+f(e.get('marginPct'),'.1f','%')+' · 6个月解禁 '+f(e.get('lift6m'),'.1f','%')
    return fund,pos,chip

def l1_bar(t,x):
    pl=x.get('pl')
    if not pl:return ''
    if t in ('upstream','cost'):
        R=logic1_rules._range(x.get('en') or {})
        if R and R['lo'] is not None:return SC.bar(R['lo'],R['hi'],pl['buy'],pl['sell'],pl['stop'],pl['close'])
    return SC.bar(None,None,pl['buy'],pl['sell'],pl.get('stop'),pl['close'])

def l1_bucket(rating,x):
    st=SC.status(x.get('pl'))[0]
    if rating=='等开关':return '等开关'
    return {'买入':'在买入区','高于':'等回落','低于':'低于买入区','止损':'低于买入区','卖出':'已到卖出价'}.get(st,'低于买入区')

L1_ORDER=[('在买入区','ab-buy','顺风或前半段板块，价格在参考买入区'),('等回落','ab-high','高于买入区，等价格回到区间再买'),('低于买入区','ab-low','接近一年低点，先观察区间是否失效'),('已到卖出价','ab-sell','持有者兑现，新资金不买'),('等开关','ab-wait','板块开关未打开，任何价格都不买')]

def board_l1(L1,sec):
    B={}
    for sid,r in L1.items():
        for x in r['picks']:
            k=l1_bucket(sec[sid]['rating'],x);sm=short(sec[sid]['title'])
            if k=='等开关':sm+=' · '+('价格已确认' if SC.status(x.get('pl'))[0]!='未确认' else '未确认')
            B.setdefault(k,[]).append(('s-'+x['code'],x['name'],sm))
    return '<section id="overview"><h2>行动看板</h2><p class="note">按“现在该做什么”把候选分组，点名字跳到它的卡片。分组只看板块档位和价格位置；卡片里的三层判断决定同一组里先看谁。</p>'+SC.board(B,L1_ORDER,'价格截至最近一次每周更新；规则见页面底部“价格规则”。',wide=('等开关',))+'</section>'

def card_l1(sid,s,r,x,i):
    t=r['type'];v,c=view_of(s['rating'],sid,x,i);fund,pos,chip=l1_texts(t,x)
    note='；'.join(([x['flag']] if x.get('flag') else [])+[n for n in x.get('notes',[]) if not n.startswith(('股东户数','融资','6个月解禁'))])
    return SC.card('s-'+x['code'],x['name'],x['code']+' · '+short(s['title']),v,c,x.get('pl'),[('基本面',x['fund'],E(fund)),('位置',x['pos'],E(pos)),('筹码',x['chip'],E(chip))],l1_bar(t,x),note)

def sector_l1(root,sid,s,r):
    t=r['type'];Lz=r['lens'];R=logic1_rules.PRICE_RULES[t]
    nb=sum(1 for x in r['picks'] if SC.status(x.get('pl'))[0]=='买入')
    out='<details class="lp-sec" id="l1-'+sid+'"'+('' if s['rating']=='等开关' else ' open')+'><summary><span class="sec-h"><h3>'+E(s['title'])+'</h3><span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span><span class="sec-meta">'+str(len(r['picks']))+'只 · 在买入区'+str(nb)+'只 · '+E(Lz['name'])+'</span></span></summary>'
    out+='<div class="sec-lens">'+''.join('<div><b>'+k+'看什么</b>'+E(Lz[key])+'</div>' for k,key in (('基本面','fund'),('位置','pos'),('筹码','chip')))+'</div>'
    out+='<p class="sec-rule"><b>价格规则：</b>买入 '+E(R['buy'])+'；卖出 '+E(R['sell'])+'；止损 '+E(R['stop'])+'。<a href="#price-rules">为什么这样定 →</a><br><b>门槛：</b>'+E(r['gate'])+'（通过'+str(r['passed'])+' / '+str(r['pool'])+'家）　<a href="../boards/'+sid+'.html">板块依据 →</a></p>'
    out+='<div class="sc-grid">'+''.join(card_l1(sid,s,r,x,i) for i,x in enumerate(r['picks']))+'</div>'
    return out+'<p class="note">进入个股研究时还要比较：'+E('；'.join(s['handoff']))+'</p></details>'

def logic1_cards(root,S,sec,L1):
    order=['顺风','前半段','等开关']
    out='<section id="logic1"><h2>按板块展开</h2><p class="note">每个板块按自己的类型看三层：基本面、位置、筹码。每张卡片从上到下是：结论、现价与价格状态、位置条（绿色为买入区，红线为卖出价，黑线为止损）、价格计划、三层判断。等开关的板块默认收起。</p>'
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):out+=sector_l1(root,sid,sec[sid],L1[sid])
    out+='<details class="more"><summary>查看全部指标表（逐板块）</summary>'+logic1_html(root,S,sec,L1).replace('<section id="logic1">','<div>').replace('</section>','</div>')+'</details>'
    out+='<article class="lp-sec" id="l1-hk"><h3>港股（规则待数据）</h3><p class="note">港股尚无同口径公司数据，暂按板块列出代表公司，不排序。</p><ul>'
    for sid,names in HK.items():out+='<li><b>'+E(sec[sid]['title'])+'（'+E(sec[sid]['rating'])+'）</b>：'+E('、'.join(names))+'</li>'
    return out+'</ul></article></section>'

def weekly_cards(root):
    p=Path(root)/'data/weekly_changes.json'
    if not p.exists():return weekly_html(root)
    W=json.loads(p.read_text())
    out='<section id="weekly"><h2>本周变化</h2><p class="note">截止'+E(W['asof'])+(('，与'+E(W['prev'])+'相比，只列状态有变化的股票。') if W['prev'] else '（首次建立基准快照）。')+'</p>'
    out+=''.join('<p class="wk-alert">'+E(a)+'</p>' for a in W['alerts'])
    if W['prev']:
        out+='<div class="wk">'+(''.join('<span class="wk-i"><a href="'+('#s-' if x['logic']=='逻辑一' else 'box.html#j-')+x['code']+'">'+E(x['name'])+'</a> <em>'+E(x['from'])+' → </em><b>'+E(x['to'])+'</b> <em>'+money(x['close'])+'</em></span>' for x in W['items']) or '<span class="wk-i">本周没有股票改变状态</span>')+'</div>'
    return out+'<div class="wk-sum">'+''.join('<span>'+E(k)+' '+str(v)+'只</span>' for k,v in W['summary'].items())+'</div></section>'

L2_ORDER=[('优先','ab-buy','在买入区，四层里至少两层为好'),('备选','ab-high','在买入区，有一两层一般'),('观察：筹码不稳','ab-wait','在买入区，但有解禁或散户涌入'),('等回到买入区','ab-low','在箱体中部'),('等收回箱底','ab-low','跌到箱底下方、未到止损'),('剔除：地板不牢','ab-bad','净资产快速缩水或触及退市红线')]

def card_l2(x,j,F,ref=False):
    q=(F.get(x['code']) or {}).get('q3') or {};pb=(F.get(x['code']) or {}).get('pb');e=x.get('en') or {}
    b=logic1_rules.box_levels(x);L=x['close']/(1+x['pos']*x['W']);H=L*(1+x['W'])
    fund='前三季营收 '+f(q.get('rev_m') and q['rev_m']/100,'.1f','亿')+' · 利润 '+(f(q['np_m']/100,'+.2f','亿') if q.get('np_m') is not None else '—')+' · PB '+f(pb,'.2f')+' · ROE '+f(q.get('roe'),'.1f','%')
    pos='箱体位置 '+f(x['pos'],'.2f')+'（0＝箱底，1＝箱顶）· 箱宽 '+f(x['W']*100,'.0f','%')
    chip='股东户数 '+f(e.get('holdersChg'),'+.0f','%')+' · 融资20日 '+f(e.get('margin20'),'+.0f','%')+' · 6个月解禁 '+f(e.get('lift6m'),'.1f','%')
    box='两年往返 '+str(x['swings'])+'次 · 脉冲 '+str(x['sp'])+'次 · 涨停 '+str(x['lu'])+'次'
    return SC.card('j-'+x['code'],x['name'],x['code']+' · '+x['ind']+(' · 参考样本' if ref else ''),j['view'],VCLS[j['view']],b,[('基本面',j['fund'],E(fund)),('位置',j['pos'],E(pos)),('筹码',j['chip'],E(chip)),('箱体',j['box'],E(box))],SC.bar(L,H,b['buy'],b['sell'],b['stop'],b['close'],'箱底','箱顶'),j['why'])

def l2_cards(L2,sw,F):
    rows=l2_judged(L2,sw,F);B={}
    for x,j,ref in rows:
        if not ref:B.setdefault(j['view'],[]).append(('j-'+x['code'],x['name'],x['ind']))
    known=[o[0] for o in L2_ORDER];order=[o for o in L2_ORDER if o[0] in B]+[(v,'ab-low','') for v in B if v not in known]
    out='<section id="l2-judge"><h2>逐只判断</h2><p class="note">四层：基本面看地板结不结实，位置看离箱底多近，筹码看谁在里面，箱体质量看烟花放得勤不勤。策略整体结论仍是“观察”：这些判断用来决定组合里放谁、先放谁、剔除谁，不用来预测单只涨跌。价格截至'+E(L2.get('px_asof','—'))+'，财报为2026年三季报。</p>'
    out+=SC.board(B,order,'组合按回测规则分散持有（上限20只、等权），单只不重仓。')
    Z=logic2_box.L2_LENS
    out+='<details class="more"><summary>四层怎么判“好、中、差”</summary><ul class="lens-ul">'+''.join('<li><b>'+E(Z[k][0])+'：</b>'+E(Z[k][1])+'</li>' for k in ('fund','pos','chip','box'))+'<li><b>结论：</b>'+E(Z['view'])+'</li></ul></details>'
    out+='<div class="sc-grid">'+''.join(card_l2(x,j,F,ref) for x,j,ref in rows)+'</div>'
    out+='<details class="more"><summary>查看全部指标表</summary>'+l2_judge_html(L2,sw,F).replace('<section id="l2-judge">','<div>').replace('</section>','</div>')+'</details>'
    return out+'</section>'

def head(active):
    return '<nav class="lp-tabs"><a href="index.html"'+(' aria-current="page"' if active==1 else '')+'><b>逻辑一 · 顺势选股</b><span>大盘→板块→个股</span></a><a href="box.html"'+(' aria-current="page"' if active==2 else '')+'><b>逻辑二 · 国资箱体</b><span>地板、天花板、烟花</span></a></nav>'

def page(ctx):
    root=Path(ctx['ROOT']);S=json.loads((root/'data/sector_selection.json').read_text());P=json.loads((root/'data/stock_pick.json').read_text())
    sec={s['id']:s for s in S['sectors']};L1=logic1_data(root,S)
    out='<style>'+CSS+SC.CSS+'</style><div class="hero"><h1>个股</h1><p class="sum">两条逻辑分开看：逻辑一顺着大盘和板块选；逻辑二利用A股国资股的箱体特征。价格截至'+asof(root)+'（每周更新），本页只提候选，不做买卖决定。</p></div>'+head(1)
    out+='<nav class="lp-jump"><a href="#weekly">本周变化</a><a href="#overview">行动看板</a><a href="#logic1">按板块展开</a><a href="#price-rules">价格规则</a></nav>'
    out+=weekly_cards(root)+board_l1(L1,sec)+logic1_cards(root,S,sec,L1)+rules_html()
    return out+'<p class="note">'+E(P['source'])+' 位置与筹码数据：'+E(json.loads((root/'data/raw/stock_pick/l1_enrich.json').read_text())['_meta']['source'])+'。</p>'

def box_page(ctx):
    root=Path(ctx['ROOT']);P=json.loads((root/'data/stock_pick.json').read_text());sw=switch_state(root)
    out='<style>'+CSS+SC.CSS+'</style><div class="hero"><h1>个股 · 国资箱体</h1><p class="sum">有地板、有天花板、偶尔放烟花的房间。规则、验证与候选都在本页。价格截至'+E(P['logic2'].get('px_asof','2026-11-13'))+'（每周更新；箱底箱顶每季度重算）。</p></div>'+head(2)
    out+='<nav class="lp-jump"><a href="#l2-judge">逐只判断</a><a href="#logic2">箱体规则</a><a href="#box-rules">价格规则</a><a href="#l2-bt">回测</a><a href="#l2-list">候选名单</a></nav>'
    F=l2_fund(root)
    return out+l2_cards(P['logic2'],sw,F)+logic2_html(P['logic2'],sw,F).replace('<h3 id="l2-bt">',box_rules_html()+'<h3 id="l2-bt">',1)+'<p class="note">'+E(P['source'])+'</p>'

def build(ctx):
    site=Path(ctx['SITE'])
    (site/'stocks/index.html').write_text(ctx['page']('个股 | A 股框架笔记','gg',page(ctx),'../'),encoding='utf-8')
    (site/'stocks/box.html').write_text(ctx['page']('国资箱体 | A 股框架笔记','gg',box_page(ctx),'../'),encoding='utf-8')

CSS="""
.lens-ul{font-size:13px;line-height:1.75;padding-left:18px}
.l2-groups{display:flex;flex-direction:column;gap:6px;margin:10px 0 12px}.l2-g{font-size:14px;line-height:1.8}.l2j-table{min-width:1250px}.l2-why{display:block;color:#52687b;font-size:12px;line-height:1.6;margin-top:4px;max-width:260px}.l2-ref{background:#fafbfc}.lp-view.bad,.ov-c.bad{background:#f1f1f1;color:#777}#l2-judge{margin:24px 0}
#weekly{margin:20px 0;border:1px solid #d4dfeb;border-radius:10px;padding:14px 20px;background:#fff}.wk-alert{background:#fff4dc;border-radius:8px;padding:8px 12px;font-size:14px}.wk-table{min-width:520px}
#price-rules,#box-rules{margin:30px 0;border:1px solid #d4dfeb;border-radius:10px;padding:16px 20px;background:#fff}.pr-table{min-width:880px}.pr-table td small{font-size:12.5px;color:#455a6e;line-height:1.7}.pr-dl{display:grid;grid-template-columns:7.5em minmax(0,1fr);gap:6px 14px;margin:8px 0;font-size:14px;line-height:1.8}.pr-dl dt{font-weight:600;color:#223e57}.pr-dl dd{margin:0}.pr-in{margin-top:10px}.pr-in summary{cursor:pointer}
@media(max-width:640px){.pr-dl{grid-template-columns:1fr}.pr-dl dd{margin-bottom:6px}}
.plan{border:1px dashed #b8c8d8;border-radius:8px;padding:10px 14px;margin:10px 0}.plan-h{margin:0 0 4px}.plan ul{margin:2px 0 8px;padding-left:18px;font-size:13.5px;line-height:1.75}.plan-table{min-width:760px}.ov-c small+small{color:#9b3d27}
.lp-tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0 14px}.lp-tabs a{border:1px solid #d4dfeb;border-radius:10px;padding:12px 16px;background:#fff;text-decoration:none;color:#223e57}.lp-tabs a[aria-current]{border-color:#365875;box-shadow:inset 0 -3px 0 #365875}.lp-tabs b{display:block;font-size:16px}.lp-tabs span{font-size:12.5px;color:#64798d}
.lp-jump{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px;position:sticky;top:56px;z-index:5;background:var(--paper,#f2f4f7);padding:8px 0}@media(max-width:760px){.lp-jump{position:static}.lp-tabs b{font-size:14.5px}.lp-tabs a{padding:10px 12px}}.lp-jump a{font-size:13px;padding:4px 10px;border-radius:14px;background:#eef2f6;text-decoration:none}
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
