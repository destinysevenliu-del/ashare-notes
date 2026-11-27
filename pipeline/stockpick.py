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
    # 防守状态由大盘按连续10个交易日恢复规则维护，单日站回不能解除暂停。
    thesis=json.loads((Path(root)/'data/market_thesis.json').read_text())
    defense=thesis['macro_regime']['markets']['a'].get('defense') or {}
    return {**last,'on':last['close']>=4700 and not defense.get('on',False)}

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

BADGE={'顺风':'up','前半段':'early','等开关':'wait','逆风':'wait'}
LAY={'好':'g','中':'m','差':'b'}
def lay(v):return '<span class="ly ly-'+LAY[v]+'">'+v+'</span>'


# ================= 判断链（2026-11-17）：板块→初筛→核验→估值→价格→筹码 =================
def verify_data(root):
    p=Path(root)/'data/raw/stock_pick/verify.json'
    return json.loads(p.read_text()) if p.exists() else {}

def sub_state(s,v):
    """板块层：公司利润主要来自的业务是否适用板块档位。"""
    if s['rating']=='等开关':return '等开关','板块开关未打开'
    if s.get('no_new'):return '暂停',s['no_new']
    subs={b['name']:b['state'] for b in s.get('subs',[])}
    if not subs or not v:return '通过','板块档位'+s['rating']+'适用'
    sub=v.get('sub','')
    if sub.startswith('一体化'):
        st=subs.get('炼化及贸易','待核')
        return ('待核','一体化公司：上游适用前半段，炼化部分'+st) if st!='前半段' else ('通过','上游与炼化均适用')
    st=subs.get(sub)
    if st in ('前半段','顺风'):return '通过',sub+'：'+st
    return '待核',(sub or '业务归属')+'：'+(st or '未判断')

def verify_step(t,v):
    """个股核验：按类型核验业务、现金与分红支撑（口径见 verify.json 的 _meta.defs）。"""
    if not v:return '待核','未取得核验数据'
    pre=(v['mix']+'。') if v.get('mix') else ''
    tail='；滚动利润为2021—2025年平均的%.0f%%'%(v['np_ttm']/v['np_avg5']*100) if v.get('np_avg5') and v['np_avg5']>0 else '；近五年平均利润为负，无法比较'
    if t=='crowded':
        ok=(v.get('cet1') or 0)>=7.5 and (v.get('cov') or 0)>=150 and (v.get('np_yoy') or -1)>=0
        txt='核心一级资本充足率%s%%、拨备覆盖率%.0f%%（上年同期%.0f%%）、不良率%.2f%%、前三季利润同比%+.1f%%；分红约占滚动利润%.0f%%'%(v['cet1'] if v.get('cet1') is not None else '—',v['cov'],v['cov_prev'],v['npl'],v['np_yoy'],v['div_np']*100)
        return ('通过' if ok else '待核'),txt+('（高于监管底线，只说明分红有支撑）' if ok else '')
    if t=='upstream':
        if v.get('fcf_div') is not None and v['fcf_div']<1:return '未通过',pre+'资本开支后自由现金流%.1f亿元，不覆盖分红%.1f亿元（扩张性开支占比待核）'%(v['fcf_ttm'],v['div'])+tail
        if (v.get('ocf_np') or 0)>=1:return '通过',pre+'经营现金流覆盖%.1f倍；资本开支后自由现金流%.1f亿元，覆盖分红%.1f倍'%(v['ocf_np'],v['fcf_ttm'],v['fcf_div'] or 0)+tail
        return '待核',pre+'经营现金流覆盖不足1倍'+tail
    if v['ocf_ttm']<0:return '未通过','滚动经营现金流为负（%.1f亿元）'%v['ocf_ttm']
    why=[]
    if v.get('ocf_np') is None or v['ocf_np']<1:why.append('经营现金流覆盖%s倍，低于1'%('—' if v.get('ocf_np') is None else format(v['ocf_np'],'.2f')))
    if v['fcf_ttm']<0:why.append('资本开支后自由现金流为负')
    for k,lab in (('ar_days','应收'),('inv_days','存货')):
        a,b=v.get(k),v.get(k+'_prev')
        if a and b and a>b*1.2 and a-b>=10:why.append('%s周转天数由%.0f天升到%.0f天'%(lab,b,a))
    base='经营现金流覆盖%s倍；资本开支后自由现金流%.1f亿元；应收周转%s天、存货周转%s天'%('—' if v.get('ocf_np') is None else format(v['ocf_np'],'.2f'),v['fcf_ttm'],format(v['ar_days'],'.0f') if v.get('ar_days') else '—',format(v['inv_days'],'.0f') if v.get('inv_days') else '—')
    return ('待核' if why else '通过'),base+('；待核：'+'、'.join(why) if why else '')+tail

def value_step(t,v,c):
    window=v.get('valuation_window','近五年') if v else '近五年'
    if v and v['pb']>v['pb95']:return '否决','PB %.2f高于自身%s95%%分位%.2f（站内初始研究规则，未回测）'%(v['pb'],window,v['pb95'])
    if t=='crowded':
        return ('通过','股息率达到10年国债+2.5个百分点') if c=='买入' else (('否决','股息率低于10年国债+2.0个百分点') if c=='卖出' else ('未到','股息率还没到买入线'))
    if not v:return '待核','未做估值核验'
    pn='按五年平均利润约%.0f倍'%v['pe_norm'] if v.get('pe_norm') else '近五年平均利润为负，正常化PE不可用'
    return '待核','PB %.2f（%s分位%d%%）未触发否决；PE(TTM) %s倍，%s，正常化估值待验证'%(v['pb'],window,v['pbpct5'],'—' if v['pe_ttm'] is None else format(v['pe_ttm'],'.1f'),pn)

def chain(sid,s,t,x,V):
    pl=x.get('pl');c=SC.status(pl)[0];v=V.get(x['code'])
    st=[]
    a,at=sub_state(s,v);st.append(('板块',a,at))
    st.append(('初筛','通过','进入候选（门槛与排序见本板块）'))
    k,kt=verify_step(t,v)
    st.append(('核验',k,kt))
    g,gt=value_step(t,v,c)
    st.append(('估值',g,gt))
    st.append(('价格',{'买入':'到位','高于':'未到','低于':'低于区间','止损':'跌破止损','卖出':'到卖出价','未确认':'未确认','无':'待核'}[c],SC.status(pl)[1]))
    st.append(('筹码','提示',{'好':'无明显拥挤','中':'一般','差':'有拥挤或解禁压力'}[x['chip']]))
    D={k:val for k,val,_ in st}
    if s['rating']=='等开关':view='等开关：不买'
    elif c=='卖出':view='不买：已到卖出价'
    elif D['板块']=='暂停':view='不买：板块拥挤，暂停新增'
    elif D['估值']=='否决':view='不买：估值否决'
    elif D['核验']=='未通过':view='不买：核验未通过'
    elif DEFENSE.get('on') and s.get('market','a')=='a':view='不买：大盘转防守，暂停新增'
    elif c=='买入':view='可执行' if all(D[k]=='通过' for k in ('板块','核验','估值')) else '价格到位·待核'
    elif c=='高于':view='等回落'+('（业务待核）' if D['板块']=='待核' else '')
    elif c=='未确认':view='观察：上升趋势未确认'
    else:view='观察：低于买入区'
    return {'steps':st,'view':view}

VIEW_CLS=lambda v:'go' if v=='可执行' else 'bad' if v.startswith('不买') else 'wait' if ('待核' in v or v.startswith('等开关')) else ''
STEP_CLS={'暂停':'no','通过':'ok','到位':'ok','待核':'chk','未到':'chk','未确认':'chk','低于区间':'chk','提示':'tip','未通过':'no','否决':'no','跌破止损':'no','到卖出价':'no','等开关':'chk'}

def chain_html(ch):
    out='<ol class="ch">'+''.join('<li class="ch-'+STEP_CLS.get(b,'chk')+'"><span>'+E(a)+'</span><b>'+E(b)+'</b></li>' for a,b,_ in ch['steps'])+'</ol>'
    det=[(a,tx) for a,b,tx in ch['steps'] if a in ('板块','核验','估值')]
    return out+'<dl class="ch-d">'+''.join('<div><dt>'+E(a)+'</dt><dd>'+E(tx)+'</dd></div>' for a,tx in det)+'</dl>'

def view_of(rating,sid,x,i):
    if x.get('chain'):v=x['chain']['view'];return v,VIEW_CLS(v)
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
FH={'crowded':['股息率','单季利润同比','PB','前三季ROE'],'upstream':['单季利润同比','股息率','经营现金流覆盖（前三季）','毛利率变化'],'growth':['单季利润同比','加速（百分点）','营收同比','经营现金流覆盖（前三季）'],'cost':['毛利率变化','单季利润同比','营收同比','经营现金流覆盖（前三季）']}

DEFENSE={}
def logic1_data(root,S):
    global DEFENSE
    DEFENSE=json.loads((Path(root)/'data/market_thesis.json').read_text())['macro_regime']['markets']['a'].get('defense') or {}
    logic1_rules.CN10Y=logic1_rules.cn10y(root)['value']
    r=logic1_rules.select_v2(root,S['sectors']);V=verify_data(root);sec={s['id']:s for s in S['sectors']}
    for sid,v in r.items():
        for x in v['picks']:x['pl']=logic1_rules.price_levels(v['type'],x);x['chain']=chain(sid,sec[sid],v['type'],x,V)
    return r

def money(v):return '—' if v is None else format(v,'.2f')

def plan_table(t,picks,day='2026-11-13'):
    R=logic1_rules.PRICE_RULES[t]
    out='<div class="plan"><p class="plan-h"><b>价格计划</b>（研究规则，未回测；按'+day+'收盘计算'+('，10年国债'+format(logic1_rules.CN10Y,'.2f')+'%' if t=='crowded' else '')+'；每周重算；<a href="#price-rules">完整规则与原因 →</a>）</p><ul><li><b>买入：</b>'+E(R['buy'])+'</li><li><b>卖出：</b>'+E(R['sell'])+'</li><li><b>止损：</b>'+E(R['stop'])+'</li></ul><div class="tblwrap"><table class="mt lp-table plan-table"><thead><tr><th>股票</th><th>现价</th><th>参考买入区间</th><th>卖出参考价</th><th>第二目标</th><th>止损价</th><th>计划盈亏比</th><th>现价状态</th></tr></thead><tbody>'
    for x in picks:
        pl=x.get('pl')
        if not pl:out+='<tr><th scope="row">'+E(x['name'])+'</th><td colspan="7">价格数据不足</td></tr>';continue
        out+='<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+'</small></th><td>'+money(pl['close'])+'</td><td><b>'+money(pl['buy'][0])+' — '+money(pl['buy'][1])+'</b></td><td><b>'+money(pl['sell'])+'</b></td><td>'+money(pl.get('sell2'))+'</td><td>'+money(pl.get('stop'))+'</td><td>'+('—' if pl.get('rr') is None else format(pl['rr'],'.1f'))+'</td><td>'+E(pl['where'])+'</td></tr>'
    return out+'</tbody></table></div><p class="note">计划盈亏比＝（卖出参考价−买入区中点）÷（买入区中点−止损价）；现价盈亏比见卡片。低于2说明赚的空间不足亏的两倍。</p></div>'

def overview_html(L1,sec,L2,sw=None,F={}):
    out='<section id="overview"><h2>候选总览</h2><p class="note">先看这张表，点股票名直接跳到它所在的板块。每只股票分三层判断：基本面（各板块看的指标不同）、位置、筹码。</p><div class="tblwrap"><table class="mt lp-table ov-table"><thead><tr><th>板块</th><th>档位</th><th>这个板块的个股看什么</th><th>候选与初步意见</th></tr></thead><tbody>'
    order=['顺风','前半段','等开关']
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        s=sec[sid];r=L1[sid];chips=[]
        for i,x in enumerate(r['picks']):
            v,c=view_of(s['rating'],sid,x,i);pl=x.get('pl');pr=('买'+money(pl['buy'][0])+'—'+money(pl['buy'][1])+' · 卖'+money(pl['sell'])) if pl else ''
            chips.append('<a class="ov-c '+c+'" href="#l1-'+sid+'">'+E(x['name'])+'<small>'+E(v)+'</small><small>'+E(pr)+'</small></a>')
        out+='<tr><th scope="row"><a href="#l1-'+sid+'">'+E(s['title'])+'</a></th><td><span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span></td><td><small>'+E(r['lens']['name'])+'：'+E(r['lens']['fund'].split('：')[0])+'</small></td><td>'+''.join(chips)+'</td></tr>'
    out+='<tr><th scope="row"><a href="box.html">国资箱体</a></th><td><span class="lp-badge lp-wait">观察</span></td><td><small>地板（净资产与退市红线）、箱体位置、筹码、烟花频率</small></td><td>'+''.join('<a class="ov-c wait" href="box.html#logic2">'+E(x['name'])+'</a>' for x in L2['top'][:8])+'<a class="ov-c" href="box.html#logic2">…共'+str(L2['funnel'][-1][1])+'只</a></td></tr>'
    return out+'</tbody></table></div></section>'

def logic1_html(root,S,sec,L1):
    out='<section id="logic1"><h2>景气顺势（按板块展开）</h2><p class="note">门槛与基本面排名同前（市值只作门槛）。在此基础上，每个板块按自己的类型加看“位置”和“筹码”，三层合成排序：基本面百分位、位置、筹码各占三分之一；基本面出现硬伤（例如毛利率下降、现金流为负）时总分减半。</p>'
    order=['顺风','前半段','等开关']
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        s=sec[sid];r=L1[sid];t=r['type'];Lz=r['lens']
        out+='<details class="lp-sec" id="l1-'+sid+'"'+('' if s['rating']=='等开关' else ' open')+'><summary><h3>'+E(s['title'])+' <span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span></h3><span class="lp-sum">'+'、'.join(E(x['name']) for x in r['picks'])+'</span></summary>'
        out+='<div class="lens"><p><b>这类板块（'+E(Lz['name'])+'）看什么：</b></p><ul><li><b>基本面：</b>'+E(Lz['fund'])+'</li><li><b>位置：</b>'+E(Lz['pos'])+'</li><li><b>筹码：</b>'+E(Lz['chip'])+'</li></ul><p class="lp-rule"><b>门槛：</b>'+E(r['gate'])+'　<b>通过：</b>'+str(r['passed'])+' / '+str(r['pool'])+'家　<a href="../boards/'+sid+'.html">板块依据 →</a></p></div>'
        out+='<div class="tblwrap"><table class="mt lp-table"><thead><tr><th rowspan="2">股票</th><th colspan="5">基本面</th><th colspan="4">位置</th><th colspan="5">筹码</th><th rowspan="2">提示</th><th rowspan="2">初步意见</th></tr><tr>'+''.join('<th>'+h+'</th>' for h in FH[t])+'<th>判断</th><th>一年位置</th><th>距高点</th><th>相对60日线</th><th>判断</th><th>股东户数变化</th><th>融资20日</th><th>融资占比</th><th>6个月解禁</th><th>判断</th></tr></thead><tbody>'
        for i,x in enumerate(r['picks']):
            e=x['en'] or {};v,c=view_of(s['rating'],sid,x,i)
            out+='<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+'</small></th>'+''.join('<td>'+v_+'</td>' for v_ in fund_cells(t,x))+'<td>'+lay(x['fund'])+'</td><td>'+f(e.get('pos52'),'.2f')+'</td><td>'+f(e.get('dd'),'.0f','%')+'</td><td>'+f(e.get('vsMA60'),'+.0f','%')+'</td><td>'+lay(x['pos'])+'</td><td>'+f(e.get('holdersChg'),'+.0f','%')+'<small>'+E(e.get('hdate') or '')+'</small></td><td>'+f(e.get('margin20'),'+.0f','%')+'</td><td>'+f(e.get('marginPct'),'.1f','%')+'</td><td>'+f(e.get('lift6m'),'.1f','%')+'</td><td>'+lay(x['chip'])+'</td><td><small>'+E('；'.join(([x['flag']] if x['flag'] else [])+x['notes']))+'</small></td><td><span class="lp-view '+c+'">'+E(v)+'</span></td></tr>'
        out+='</tbody></table></div>'+plan_table(t,r['picks'],asof(root))+'<details class="more"><summary>进入个股研究时还要比较什么</summary><p class="note">'+E('；'.join(s['handoff']))+'</p></details></details>'
    return out+'</section>'

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
    out='<section id="l2-judge"><h2>逐只判断</h2><p class="note">箱体股赚的是“地板附近买、天花板附近卖、遇到烟花兑现”的钱，所以四层看的东西和景气顺势不同。策略整体结论仍是“观察”（见下方回测）：单只判断用来决定组合里放谁、先放谁、剔除谁，不用来预测单只涨跌。价格截至'+E(L2.get('px_asof','—'))+'，财报为2026年三季报。</p>'
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
    return '<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+' · '+E(x['ind'])+'</small></th><td>'+str(x['mc'])+'</td><td>'+f(x['W']*100,'.0f','%')+'</td><td>'+str(x['swings'])+'</td><td>'+str(x['lu'])+' / '+str(x['sp'])+'</td><td>'+f(x['pos'],'.2f')+'</td><td>'+f(x['corr'],'.2f')+'</td><td>'+f(x.get('rev9m'),'.0f')+' / '+f(x.get('np9m'),'.2f')+'</td><td>'+(format(x['holders'],',') if x.get('holders') else '—')+'</td><td>'+E('、'.join(x['tags'][:3]))+'</td>'+box_px(x)+'<td>'+E(note)+'</td></tr>'

def logic2_html(L2,sw,F={}):
    ref=L2['reference'];R=logic2_box.RULES;A=logic2_box.ACTIONS
    out='<section id="logic2"><h2>国资箱体</h2><div class="l2-intro"><div>'+box_svg(ref)+'</div><div><p>把一只股票想成一个房间：<b>地板</b>是国资背景和净资产带来的下限，<b>天花板</b>是没有业绩支撑时游资和散户愿意追到的上限，<b>烟花</b>是政策、重组、题材事件带来的脉冲。</p><p>它赚钱的方式不是盈利增长，而是“在地板附近买、在天花板附近卖、遇到烟花就兑现”。</p><p class="note">图中“现在”按乐凯胶片当前位置（'+f(ref['pos'],'.2f')+'）画出。</p></div></div>'
    out+='<h3>七个可量化的入选条件（以乐凯胶片为例）</h3><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>条件</th><th>怎么算</th><th>乐凯胶片</th><th>是否满足</th></tr></thead><tbody>'
    rows=[('国资与安全',R['universe'],'市值'+str(ref['mc'])+'亿 · PB '+f(ref['pb'],'.2f'),True),('有箱体',R['box'],'宽度'+f(ref['W']*100,'.0f','%'),.25<=ref['W']<=1.2),('没有单边趋势',R['flat'],f(ref['trend'],'+.2f'),abs(ref['trend'])<=.3),('来回震荡',R['swings'],str(ref['swings'])+'次',ref['swings']>=2),('地板有效',R['floor'],f(ref['floor']*100,'.0f','%'),ref['floor']>=-.15),('有事件脉冲',R['hot'],'涨停'+str(ref['lu'])+'次 · 脉冲'+str(ref['sp'])+'次',ref['lu']>=4 and ref['sp']>=1),('股东户数少',R['holders'],(format(ref['holders'],',')+'户（'+ref.get('hdate','')+'）') if ref.get('holders') else '—',(ref.get('holders') or 10**9)<50000)]
    for a,b,c,ok in rows:out+='<tr><th scope="row">'+E(a)+'</th><td>'+E(b)+'</td><td>'+E(c)+'</td><td>'+('满足' if ok else '不满足')+'</td></tr>'
    HR=L2.get('holders_rule')
    out+='</tbody></table></div>'+(('<div class="l2-hr"><p><b>关于“股东户数低于5万户”：</b>'+E(HR['basis'])+'（'+E(HR['origin'])+'）</p><p><b>现有证据：</b>'+E(HR['evidence'])+'</p><p><b>状态：</b>'+E(HR['status'])+'</p></div>') if HR else '')+'<h3>三个动作与一个暂停条件</h3><div class="l2-act"><p><b>买：</b>'+E(A['buy'])+'</p><p><b>卖：</b>'+E(A['sell'])+'</p><p><b>止损：</b>'+E(A['stop'])+'</p><p class="l2-sw '+('on' if sw['on'] else 'off')+'"><b>'+E(A['switch'])+'<br>现在：中证全指'+f(sw['close'],',.0f')+'（'+sw['date']+'）→ '+('规则允许研究买点' if sw['on'] else '暂停开新仓')+'</p></div>'
    pb=L2.get('pbt');o=L2['oos_1y']
    out+='<h3 id="l2-bt">按真实规则做组合回测</h3><div class="l2-bt"><p class="note">注意：回测的股票池没有包含2026-11-19加入的“股东户数低于5万户”条件。</p>'
    if pb:
        B=pb['base'];M=pb['bench']
        out+='<p>'+E(pb['setup'])+'</p><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>指标</th><th>策略（'+str(B['K'])+'只上限，成本'+f(B['cost'],'.1f','%')+'）</th><th>同一股票池等权持有</th></tr></thead><tbody>'
        for lab,k,suf in [('年化收益','cagr','%'),('累计收益','total','%'),('最大回撤','mdd','%')]:out+='<tr><th scope="row">'+lab+'</th><td>'+f(B[k],'+.1f',suf)+'</td><td>'+f(M[k],'+.1f',suf)+'</td></tr>'
        out+='<tr><th scope="row">平均仓位</th><td>'+str(B['exposure'])+'%</td><td>100%</td></tr><tr><th scope="row">交易次数 / 胜率</th><td>'+str(B['trades'])+' / '+str(B['win'])+'%</td><td>—</td></tr><tr><th scope="row">单笔平均 / 中位</th><td>'+f(B['avg'],'+.1f','%')+' / '+f(B['median'],'+.1f','%')+'</td><td>—</td></tr><tr><th scope="row">收益最高的10%交易占总盈利</th><td>'+str(B['top10share'])+'%</td><td>—</td></tr><tr><th scope="row">退出方式</th><td>'+E('、'.join(k+str(v)+'次' for k,v in B['exits'].items()))+'</td><td>—</td></tr>'
        ys=sorted(B['annual']);out+='</tbody></table></div><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>年份</th>'+''.join('<th>'+y+'</th>' for y in ys)+'</tr></thead><tbody><tr><th scope="row">策略</th>'+''.join('<td>'+f(B['annual'][y],'+.1f','%')+'</td>' for y in ys)+'</tr><tr><th scope="row">等权基准</th>'+''.join('<td>'+f(M['annual'].get(y),'+.1f','%')+'</td>' for y in ys)+'</tr></tbody></table></div>'
        out+='<p><b>稳健性：</b>'+E(pb['robust'])+'</p><p class="note"><b>偏差：</b>'+E(pb['bias'])+'</p>'
    out+='<p class="note"><b>信号层面统计（旧口径）：</b>2019—2026年2,357次箱底信号，120日平均+4.5%、中位+0.2%；最近一年箱体股信号平均'+f(o['box_hot']['mean'],'+.1f','%')+'。</p><p class="l2-con"><b>结论：</b>'+E(L2.get('verdict',''))+'</p></div>'
    fun=L2['funnel'];out+='<h3 id="l2-list">候选名单</h3><ol class="lp-funnel">'+''.join('<li>'+E(a)+'：<b>'+str(b)+'</b></li>' for a,b in fun)+'</ol>'
    out+='<details class="more"><summary>查看候选名单全部参数（箱体、标签、价格）</summary><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>股票</th><th>市值（亿）</th><th>箱体宽度</th><th>往返</th><th>涨停 / 脉冲</th><th>当前位置</th><th>与大盘相关</th><th>前三季营收 / 利润（亿）</th><th>股东户数</th><th>主要标签</th><th>参考买入</th><th>卖出参考</th><th>止损</th><th>逐只判断</th></tr></thead><tbody>'
    J={x['code']:j['view'] for x,j,_ in l2_judged(L2,sw,F)}
    for x in L2['top']:out+=l2_row(x,J[x['code']])
    out+=l2_row(ref,'参考样本：满足箱体条件与户数条件，但当前低于箱底（位置'+f(ref['pos'],'.2f')+'），重复性不足（脉冲1次、往返2次）')
    out+='</tbody></table></div><p class="note">排序：往返次数＋2×脉冲次数，从高到低；同分时位置更低者优先。这里列出前15名，另有'+str(fun[-1][1]-len(L2['top']))+'只同样满足条件'+(('：'+E('、'.join(L2['rest']))) if L2.get('rest') else '')+'。'+(('因股东户数≥5万户被排除的'+str(len(L2['holders_out']))+'只：'+E('、'.join(L2['holders_out']))+'。') if L2.get('holders_out') else '')+'亏损公司需单独确认没有财务类退市风险。</p></details></section>'
    return out


def rules_html():
    D=logic1_rules.PRICE_DOC
    out='<section id="price-rules"><h2>价格规则：买入价、卖出价、止损价怎么算</h2><p class="note">本页所有价格都按下面的规则计算。规则写在这里，以后跟进时按同一套口径重算，不凭当时的感觉调。</p>'
    out+='<h3>一、四类板块各用一套规则</h3><div class="tblwrap"><table class="mt lp-table pr-table"><thead><tr><th>板块类型</th><th>买入</th><th>卖出</th><th>止损</th><th>为什么这样定</th></tr></thead><tbody>'
    for r in D['types']:out+='<tr><th scope="row">'+E(r['name'])+'<small>'+E(r['sectors'])+'</small></th><td>'+E(r['buy'])+'</td><td>'+E(r['sell'])+'</td><td>'+E(r['stop'])+'</td><td><small>'+E(r['why'])+'</small></td></tr>'
    out+='</tbody></table></div><h3>二、共同原则</h3><dl class="pr-dl">'+''.join('<dt>'+E(a)+'</dt><dd>'+E(b)+'</dd>' for a,b in D['common'])+'</dl>'
    out+='<details class="pr-in"><summary><b>三、输入数据怎么来</b>（一年高低点、60日均线等的换算）</summary><dl class="pr-dl">'+''.join('<dt>'+E(a)+'</dt><dd>'+E(b)+'</dd>' for a,b in D['inputs'])+'</dl></details>'
    return out+'<p class="note">国资箱体的价格规则见 <a href="box.html#box-rules">国资箱体页</a>；六层职责与状态定义见 <a href="selection-rules.html">筛选规则</a>。</p></section>'

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
    v=x['chain']['view']
    if v=='可执行':return '可执行'
    if v.startswith('价格到位'):return '价格到位·待核'
    if v.startswith('不买'):return '不买'
    if v.startswith('等开关'):return '等开关'
    if v.startswith('等回落'):return '等回落'
    return '观察'

L1_ORDER=[('可执行','ab-buy','板块、核验、估值都通过，价格在买入区'),('价格到位·待核','ab-high','价格已在买入区，但核验或估值没完成，不直接买'),('等回落','ab-high','高于买入区，等价格回到区间'),('观察','ab-low','低于买入区或接近止损，先观察区间是否失效；港股为上升趋势未确认'),('不买','ab-sell','已到卖出价、估值否决、核验未通过、板块拥挤暂停新增，或大盘转防守暂停新增'),('等开关','ab-wait','板块开关未打开，任何价格都不买')]

# 动力不属于“景气顺势”的板块移到对应逻辑页（见 logic_map.py）：银行靠股息率（分母），归入红利高股息。
MOVED={'a-bank':'银行的上涨动力是股息率相对国债的吸引力（分母），已移到“分母 · 红利高股息”页（dividend.html），与公用事业、运营商等一起按同一把尺子比较。'}

def board_l1(L1,sec):
    B={}
    for sid,r in L1.items():
        if sid in MOVED:continue
        for x in r['picks']:
            k=l1_bucket(sec[sid]['rating'],x);sm=short(sec[sid]['title'])
            if k=='等开关':sm+=' · '+('价格已确认' if SC.status(x.get('pl'))[0]!='未确认' else '未确认')
            elif k=='不买':sm+=' · '+x['chain']['view'].replace('不买：','').replace('板块拥挤，暂停新增','拥挤暂停').replace('大盘转防守，暂停新增','大盘防守')
            B.setdefault(k,[]).append(('s-'+x['code'],x['name'],sm))
    return '<section id="overview"><h2>行动看板</h2><p class="note">按“现在该做什么”把候选分组，点名字跳到它的卡片。判断顺序：板块 → 初筛 → 核验 → 估值 → 价格 → 筹码。进入候选只表示值得研究；价格到了买入区，核验或估值没完成时仍是“待核”，不直接买。</p>'+SC.board(B,L1_ORDER,'价格截至最近一次每周更新；规则见页面底部“价格规则”。',wide=('等开关',))+'</section>'

def card_l1(sid,s,r,x,i):
    t=r['type'];v,c=view_of(s['rating'],sid,x,i);fund,pos,chip=l1_texts(t,x)
    note='；'.join(([x['flag']] if x.get('flag') else [])+[n for n in x.get('notes',[]) if not n.startswith(('股东户数','融资','6个月解禁'))])
    posk='回撤条件' if t=='upstream' else '位置'
    plab={'好':'达标','中':'一般','差':'未达标'} if t=='upstream' else None
    return SC.card('s-'+x['code'],x['name'],x['code']+' · '+short(s['title']),v,c,x.get('pl'),[('初筛指标',x['fund'],E(fund)),(posk,x['pos'],E(pos),plab),('筹码',x['chip'],E(chip))],l1_bar(t,x),note,chain_html(x['chain']))

def sector_l1(root,sid,s,r):
    t=r['type'];Lz=r['lens'];R=logic1_rules.PRICE_RULES[t]
    nb=sum(1 for x in r['picks'] if SC.status(x.get('pl'))[0]=='买入')
    out='<details class="lp-sec" id="l1-'+sid+'"'+('' if s['rating']=='等开关' else ' open')+'><summary><span class="sec-h"><h3>'+E(s['title'])+'</h3><span class="lp-badge lp-'+BADGE[s['rating']]+'">'+E(s['rating'])+'</span><span class="sec-meta">'+str(len(r['picks']))+'只 · 在买入区'+str(nb)+'只 · '+E(Lz['name'])+'</span></span></summary>'
    out+='<details class="more"><summary>看什么、价格规则与门槛</summary><div class="sec-lens">'+''.join('<div><b>'+k+'看什么</b>'+E(Lz[key])+'</div>' for k,key in (('基本面','fund'),('位置','pos'),('筹码','chip')))+'</div>'
    out+='<p class="sec-rule"><b>价格规则：</b>买入 '+E(R['buy'])+'；卖出 '+E(R['sell'])+'；止损 '+E(R['stop'])+'。<a href="#price-rules">为什么这样定 →</a><br><b>门槛：</b>'+E(r['gate'])+'（通过'+str(r['passed'])+' / '+str(r['pool'])+'家）　<a href="../boards/'+sid+'.html">板块依据 →</a></p></details>'
    out+='<div class="sc-grid">'+''.join(card_l1(sid,s,r,x,i) for i,x in enumerate(r['picks']))+'</div>'
    return out+'<details class="more"><summary>进入个股研究时还要比较什么</summary><p class="note">'+E('；'.join(s['handoff']))+'</p></details></details>'

def logic1_cards(root,S,sec,L1):
    order=['顺风','前半段','等开关']
    out='<section id="logic1"><h2>按板块展开</h2><p class="note">每个板块按自己的类型看三层：基本面、位置、筹码。每张卡片从上到下是：结论、现价与价格状态、位置条（绿色为买入区，红线为卖出价，黑线为止损）、价格计划、判断链（板块、初筛、核验、估值、价格、筹码各一格）、初筛的三层指标。等开关的板块默认收起。</p>'
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        if sid in MOVED:out+='<article class="lp-sec" id="l1-'+sid+'"><h3>'+E(sec[sid]['title'])+'</h3><p>'+E(MOVED[sid])+' <a href="dividend.html">去红利高股息 →</a></p></article>';continue
        out+=sector_l1(root,sid,sec[sid],L1[sid])
    out+='<details class="more"><summary>查看全部指标表（逐板块）</summary>'+logic1_html(root,S,sec,L1).replace('<section id="logic1">','<div>').replace('</section>','</div>')+'</details>'

    return out+'</section>'

def weekly_cards(root):
    p=Path(root)/'data/weekly_changes.json'
    if not p.exists():return weekly_html(root)
    W=json.loads(p.read_text())
    out='<section id="weekly"><h2>本周变化</h2><p class="note">截止'+E(W['asof'])+(('，与'+E(W['prev'])+'相比，只列状态有变化的股票。') if W['prev'] else '（首次建立基准快照）。')+'</p>'
    out+=''.join('<p class="wk-alert">'+E(a)+'</p>' for a in W['alerts'])
    if W['prev']:
        out+='<details class="more"'+(' open' if len(W['items'])<=8 else '')+'><summary>'+str(len(W['items']))+'只股票状态有变化</summary><div class="wk">'+(''.join('<span class="wk-i"><a href="'+('#s-' if x['logic']=='逻辑一' else 'box.html#j-')+x['code']+'">'+E(x['name'])+'</a> <em>'+E(x['from'])+' → </em><b>'+E(x['to'])+'</b> <em>'+money(x['close'])+'</em></span>' for x in W['items']) or '<span class="wk-i">本周没有股票改变状态</span>')+'</div></details>'
    return out+'<div class="wk-sum">'+''.join('<span>'+E(k)+' '+str(v)+'只</span>' for k,v in W['summary'].items())+'</div></section>'

L2_ORDER=[('优先','ab-buy','在买入区，四层里至少两层为好'),('备选','ab-high','在买入区，有一两层一般'),('观察：筹码不稳','ab-wait','在买入区，但有解禁或散户涌入'),('等回到买入区','ab-low','在箱体中部'),('等收回箱底','ab-low','跌到箱底下方、未到止损'),('剔除：地板不牢','ab-bad','净资产快速缩水或触及退市红线')]

# 估值修复的“兑现”一层：分红是否提高（市值管理指引把分红、回购列为估值提升工具）
try:PAYOUT=json.loads((Path(__file__).resolve().parent.parent/'data/raw/stock_pick/box_payout.json').read_text())['rows']
except Exception:PAYOUT={}

def card_l2(x,j,F,ref=False):
    q=(F.get(x['code']) or {}).get('q3') or {};pb=(F.get(x['code']) or {}).get('pb');e=x.get('en') or {}
    b=logic1_rules.box_levels(x);L=x['close']/(1+x['pos']*x['W']);H=L*(1+x['W'])
    fund='前三季营收 '+f(q.get('rev_m') and q['rev_m']/100,'.1f','亿')+' · 利润 '+(f(q['np_m']/100,'+.2f','亿') if q.get('np_m') is not None else '—')+' · PB '+f(pb,'.2f')+' · ROE '+f(q.get('roe'),'.1f','%')
    pos='箱体位置 '+f(x['pos'],'.2f')+'（0＝箱底，1＝箱顶）· 箱宽 '+f(x['W']*100,'.0f','%')
    chip=(('股东'+format(x['holders']/1e4,'.1f')+'万户 ') if x.get('holders') else '股东户数 ')+f(e.get('holdersChg'),'+.0f','%')+' · 融资20日 '+f(e.get('margin20'),'+.0f','%')+' · 6个月解禁 '+f(e.get('lift6m'),'.1f','%')
    box='两年往返 '+str(x['swings'])+'次 · 脉冲 '+str(x['sp'])+'次 · 涨停 '+str(x['lu'])+'次'
    dv=PAYOUT.get(x['code'])
    if dv:fund+=' · 分红兑现：'+('近两年未分红' if not dv[0] and not dv[1] else ('提高' if dv[0]>dv[1]*1.05 else '减少' if dv[0]<dv[1]*0.95 else '持平')+'（近12个月每股'+format(dv[0],'.3f')+'元，之前12个月'+format(dv[1],'.3f')+'元）')
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

# ================= 当前生效的筛选规则页（覆盖旧版 selection-rules.html） =================
LAYERS=[('板块','这个业务现在有没有盈利驱动','大盘风向 + 板块三件事；煤炭、石油、油运按业务拆开（动力煤/焦煤/煤化工，上游/炼化，油轮/港口集运）','可以：开关未打开或业务待核时，不进入可执行'),
 ('个股初筛','值不值得研究','各板块自己的门槛和排序（单季利润同比、股息率等），只用来缩小范围','不否决，只决定进不进候选'),
 ('个股核验','公司是否真的受益、利润能否持续、现金能否兑现','按类型：银行看资本与拨备；资源与运输看资本开支后自由现金流对分红的覆盖；成长与成本类看经营现金流覆盖、自由现金流和应收存货周转','可以：资源与运输类自由现金流不覆盖分红、成长与成本类经营现金流为负为“核验未通过”'),
 ('估值','价格是否已经充分反映这些收益','所有类型：PB对比自身五年95%分位（否决线）；TTM PE与按五年平均利润的正常化PE并列；银行另看股息率对比10年国债','可以：触发否决为“不买”；没有正常化结论时为“待核”'),
 ('价格','什么价格参与、何时兑现、何时止损','各类型的价格规则（研究规则，未回测）','只在前三层通过后用于执行'),
 ('筹码','拥挤和交易风险','股东户数、融资余额、解禁','只提示，不代替盈利或估值证据')]
VIEWS=[('可执行','板块、核验、估值都通过，价格在买入区'),('价格到位·待核','价格在买入区，但板块业务、核验或估值没有完成'),('等回落','高于买入区'),('观察','低于买入区或接近止损'),('不买','已到卖出价、估值否决或核验未通过'),('等开关','板块开关未打开')]

def rules_page(root):
    S=json.loads((Path(root)/'data/sector_selection.json').read_text());V=verify_data(root)
    out='<style>'+CSS+SC.CSS+'.rp table{min-width:760px}</style><div class="hero"><h1>筛选规则（当前生效）</h1><p class="sum">2026-11-17起生效。进入候选只表示值得研究；只有板块、核验、估值都通过且价格在买入区，才显示“可执行”。</p></div><nav class="lp-jump"><a href="index.html">← 个股页</a><a href="#layers">六层职责</a><a href="#views">状态定义</a><a href="#types">各类型规则</a><a href="#data">数据口径</a><a href="#legacy">旧版说明</a></nav>'
    out+='<section id="layers" class="rp"><h2>六层职责</h2><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>层</th><th>回答什么问题</th><th>用什么</th><th>能否否决</th></tr></thead><tbody>'+''.join('<tr><th scope="row">'+E(a)+'</th><td>'+E(b)+'</td><td>'+E(c)+'</td><td>'+E(d)+'</td></tr>' for a,b,c,d in LAYERS)+'</tbody></table></div></section>'
    out+='<section id="views"><h2>状态定义</h2><ul class="lens-ul">'+''.join('<li><b>'+E(a)+'：</b>'+E(b)+'</li>' for a,b in VIEWS)+'</ul></section>'
    out+='<section id="types" class="rp"><h2>各类型规则</h2><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>类型</th><th>初筛看什么</th><th>核验</th><th>估值</th><th>价格规则</th></tr></thead><tbody>'
    VAL={'crowded':'PB高于自身五年95%分位为否决；否则看股息率对比10年国债：达到+2.5个百分点为通过，低于+2.0个百分点为否决','upstream':'PB高于自身五年95%分位为否决；否则列出TTM PE与按五年平均利润的正常化PE，正常化结论待验证','growth':'PB高于自身五年95%分位为否决；否则列出TTM PE与正常化PE（近五年平均利润为负时不可用），待验证','cost':'同成长类'}
    VER={'crowded':'核心一级资本充足率、拨备覆盖率高于监管底线（7.5%、150%）且前三季度利润同比不为负为通过；只说明分红有支撑','upstream':'业务归属；经营现金流覆盖倍数；资本开支后自由现金流覆盖分红，不覆盖为未通过','growth':'滚动经营现金流为负为未通过；经营现金流覆盖≥1、资本开支后自由现金流不为负、应收与存货周转天数上升不超过两成为通过；其余待核','cost':'同成长类'}
    for t,Lz in logic1_rules.LENS.items():
        R=logic1_rules.PRICE_RULES[t];out+='<tr><th scope="row">'+E(Lz['name'])+'</th><td>'+E(Lz['fund'])+'</td><td>'+E(VER[t])+'</td><td>'+E(VAL[t])+'</td><td>买入 '+E(R['buy'])+'；卖出 '+E(R['sell'])+'；止损 '+E(R['stop'])+'</td></tr>'
    out+='</tbody></table></div><p class="note">煤炭、石油、油运按业务分开判断，见<a href="../boards/a-coal.html#subs">煤炭</a>、<a href="../boards/a-oil.html#subs">石油</a>、<a href="../boards/a-tanker.html#subs">油运</a>板块页；标为“待核”的业务，相关公司不进入可执行。价格规则的完整原因见<a href="index.html#price-rules">个股页“价格规则”</a>。</p></section>'
    m=V.get('_meta',{});out+='<section id="data"><h2>数据口径</h2><ul class="lens-ul">'+''.join('<li>'+E(v)+'</li>' for v in m.get('defs',{}).values())+'<li>数据来源：'+E(m.get('source',''))+'（截至'+E(m.get('as_of',''))+'）</li><li>同比与环比、单季与累计与滚动12个月、实际值与机构预测、现货与期货分开标注；没有依据的阈值标“待核”。</li></ul></section>'
    out+='<section id="legacy"><h2>旧版说明</h2><p class="note">2026-11-13版的“子池合同与研究席位、A–H职能、追/等/不追”已停用。保留两条：辅助估值高于五年95%分位否决（现为估值层否决规则，仍未回测）；正常化自由现金流的思路（现为核验层的分红覆盖检查）。旧版个股研究页和组合约束页只作历史资料。</p></section>'
    return out

# 选股逻辑按上涨动力分类命名（见 logic_map.py）：分子＝利润在涨，分母＝估值在变，事件＝有明确买方或时点。
MARKETS={'a':{'name':'A股','href':'index.html','sub':[(1,'index.html','分子 · 景气顺势','大盘→板块→个股：周期、成长板块'),(6,'a-turn.html','分子 · 业绩反转','行业预期上调＋利润仍在谷底'),(7,'dividend.html','分母 · 红利高股息','股息率比国债高多少'),(2,'box.html','分母 · 估值修复','国资箱体：净资产地板与分红兑现')]},
         'hk':{'name':'港股','href':'hk.html','sub':[(3,'hk.html','分子 · 景气顺势','大盘→板块→个股：能源、油运、硬件'),(4,'hk-turn.html','分子 · 业绩反转','行业预期上调＋空头不加仓'),(8,'hk-dividend.html','分母 · 红利高股息','税后股息率；含A股与H股比价'),(9,'hk-event.html','事件 · 回购与私有化','公司真金白银买入')]}}
def head(active):
    """两层导航：先选市场（A股／港股），再选该市场下的选股逻辑。A股两条逻辑，港股一条。"""
    m='hk' if active in {n for n,*_ in MARKETS['hk']['sub']}|{5} else 'a'
    out='<nav class="lp-mkt" aria-label="市场">'+''.join('<a href="'+v['href']+'"'+(' aria-current="page"' if k==m else '')+'><b>'+v['name']+'</b><span>'+str(len(v['sub']))+'条选股逻辑：'+'、'.join(x[2].split(' · ')[-1] for x in v['sub'])+'</span></a>' for k,v in MARKETS.items())+'</nav>'
    out+='<p class="lp-map"><a href="logic-map.html">选股逻辑地图：12条逻辑的定义、上涨动力与本站覆盖 →</a></p>' if active else ''
    out+='<nav class="lp-tabs" aria-label="'+MARKETS[m]['name']+'选股逻辑">'+''.join('<a href="'+h+'"'+(' aria-current="page"' if n==active else '')+'><b>'+E(t)+'</b><span>'+E(d)+'</span></a>' for n,h,t,d in MARKETS[m]['sub'])+'</nav>'
    return out

def page(ctx):
    root=Path(ctx['ROOT']);S=json.loads((root/'data/sector_selection.json').read_text());P=json.loads((root/'data/stock_pick.json').read_text())
    sec={s['id']:s for s in S['sectors']};L1=logic1_data(root,S)
    out='<style>'+CSS+SC.CSS+'</style>'+head(1)+'<div class="hero"><h1>A股 · 分子 · 景气顺势</h1><p class="sum">大盘 → 板块 → 个股，顺着大盘和板块选。只提候选，不做买卖决定。</p><p class="hero-meta">价格截至'+asof(root)+'，每周更新</p></div>'
    out+='<nav class="lp-jump"><a href="#weekly">本周变化</a><a href="#overview">行动看板</a><a href="#logic1">按板块展开</a><a href="#price-rules">价格规则</a></nav>'
    out+=weekly_cards(root)+board_l1(L1,sec)+logic1_cards(root,S,sec,L1)+rules_html()
    return out+'<p class="note">'+E(P['source'])+' 位置与筹码数据：'+E(json.loads((root/'data/raw/stock_pick/l1_enrich.json').read_text())['_meta']['source'])+'。</p>'

def box_page(ctx):
    root=Path(ctx['ROOT']);P=json.loads((root/'data/stock_pick.json').read_text());sw=switch_state(root)
    out='<style>'+CSS+SC.CSS+'</style>'+head(2)+'<div class="hero"><h1>A股 · 分母 · 估值修复（国资箱体）</h1><p class="sum">有地板、有天花板、偶尔放烟花的房间：只适用A股国资背景的箱体股。</p><p class="hero-meta">价格截至'+E(P['logic2'].get('px_asof','2026-11-13'))+'，每周更新；箱底箱顶每季度重算</p></div>'
    out+='<nav class="lp-jump"><a href="#l2-judge">逐只判断</a><a href="#logic2">箱体规则</a><a href="#box-rules">价格规则</a><a href="#l2-bt">回测</a><a href="#l2-list">候选名单</a></nav>'
    F=l2_fund(root)
    return out+l2_cards(P['logic2'],sw,F)+logic2_html(P['logic2'],sw,F).replace('<h3 id="l2-bt">',box_rules_html()+'<h3 id="l2-bt">',1)+'<p class="note">'+E(P['source'])+'</p>'

def build(ctx):
    site=Path(ctx['SITE'])
    (site/'stocks/index.html').write_text(ctx['page']('个股 | A 股框架笔记','gg',page(ctx),'../'),encoding='utf-8')
    (site/'stocks/box.html').write_text(ctx['page']('国资箱体 | A 股框架笔记','gg',box_page(ctx),'../'),encoding='utf-8')
    (site/'stocks/selection-rules.html').write_text(ctx['page']('筛选规则 | A 股框架笔记','gg',rules_page(ctx['ROOT']),'../'),encoding='utf-8')
    import hk_pick;hk_pick.build(ctx)
    import hk_turn;hk_turn.build(ctx)
    import a_turn;a_turn.build(ctx)
    import dividend;dividend.build(ctx)
    import hk_event;hk_event.build(ctx)
    import logic_map;logic_map.build(ctx)
    vp=Path(ctx['ROOT'])/'data/raw/stock_pick/verify.json'
    if vp.exists():(site/'data/verify.json').write_text(vp.read_text(encoding='utf-8'),encoding='utf-8')

CSS="""
.l2-hr{background:#f6f8fa;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13.5px;line-height:1.8}.l2-hr p{margin:2px 0}
.lens-ul{font-size:13px;line-height:1.75;padding-left:18px}
.l2-groups{display:flex;flex-direction:column;gap:6px;margin:10px 0 12px}.l2-g{font-size:14px;line-height:1.8}.l2j-table{min-width:1250px}.l2-why{display:block;color:#52687b;font-size:12px;line-height:1.6;margin-top:4px;max-width:260px}.l2-ref{background:#fafbfc}.lp-view.bad,.ov-c.bad{background:#f1f1f1;color:#777}#l2-judge{margin:24px 0}
#weekly{margin:20px 0;border:1px solid #d4dfeb;border-radius:10px;padding:14px 20px;background:#fff}.wk-alert{background:#fff4dc;border-radius:8px;padding:8px 12px;font-size:14px}.wk-table{min-width:520px}
#price-rules,#box-rules{margin:30px 0;border:1px solid #d4dfeb;border-radius:10px;padding:16px 20px;background:#fff}.pr-table{min-width:880px}.pr-table td small{font-size:12.5px;color:#455a6e;line-height:1.7}.pr-dl{display:grid;grid-template-columns:7.5em minmax(0,1fr);gap:6px 14px;margin:8px 0;font-size:14px;line-height:1.8}.pr-dl dt{font-weight:600;color:#223e57}.pr-dl dd{margin:0}.pr-in{margin-top:10px}.pr-in summary{cursor:pointer}
@media(max-width:640px){.pr-dl{grid-template-columns:1fr}.pr-dl dd{margin-bottom:6px}}
.plan{border:1px dashed #b8c8d8;border-radius:8px;padding:10px 14px;margin:10px 0}.plan-h{margin:0 0 4px}.plan ul{margin:2px 0 8px;padding-left:18px;font-size:13.5px;line-height:1.75}.plan-table{min-width:760px}.ov-c small+small{color:#9b3d27}
.lp-mkt{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0 8px}.lp-mkt a{border:1px solid #c9d6e3;border-radius:10px;padding:12px 18px;background:#f6f8fa;text-decoration:none;color:#223e57}.lp-mkt a[aria-current]{background:#223e57;color:#fff;border-color:#223e57}.lp-mkt a[aria-current] span{color:#d5e0ea}.lp-mkt b{display:block;font-size:18px}.lp-mkt span{font-size:12.5px;color:#64798d}
.lp-tabs{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:0 0 14px}.lp-tabs a{border:1px solid #d4dfeb;border-radius:10px;padding:12px 16px;background:#fff;text-decoration:none;color:#223e57}.lp-tabs a[aria-current]{border-color:#365875;box-shadow:inset 0 -3px 0 #365875}.lp-tabs b{display:block;font-size:16px}.lp-tabs span{font-size:12.5px;color:#64798d}
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
