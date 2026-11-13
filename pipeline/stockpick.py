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

def logic1_html(root,S,sec):
    L1=logic1_rules.select(root,S['sectors'])
    out='<section id="logic1"><h2>逻辑一：顺势选股</h2><ol class="lp-funnel"><li><b>大盘</b>给出风向表（首页）</li><li><b>板块</b>分四档：顺风、前半段、等开关、逆风（逆风不选）</li><li><b>门槛</b>每个板块用自己的硬条件筛（市值、利润、估值）</li><li><b>排序</b>每个板块一个主排序指标，取前几名</li></ol><p class="note">初步意见：顺风与前半段板块的前两名“建议跟踪”，其余“备选”；等开关板块全部“观察，开关前不买”。</p>'
    order=['顺风','前半段','等开关']
    for sid in sorted(L1,key=lambda k:order.index(sec[k]['rating'])):
        s=sec[sid];r=L1[sid];wait=s['rating']=='等开关'
        out+=('<details class="lp-sec" id="l1-'+sid+'"><summary>' if wait else '<article class="lp-sec" id="l1-'+sid+'">')+'<h3><a href="../boards/'+sid+'.html">'+E(s['title'])+'</a> <span class="lp-badge lp-'+{'顺风':'up','前半段':'early','等开关':'wait'}[s['rating']]+'">'+E(s['rating'])+'</span></h3><p class="lp-rule"><b>门槛：</b>'+E(r['gate'])+'　<b>排序：</b>'+E(r['rank'])+'　<b>通过：</b>'+str(r['passed'])+' / '+str(r['pool'])+'家</p>'+('</summary>' if wait else '')
        out+='<div class="tblwrap"><table class="mt lp-table"><thead><tr><th>股票</th><th>三季度单季利润</th><th>单季利润同比</th><th>上半年同比</th><th>PE</th><th>PB</th><th>股息率</th><th>市值（亿）</th><th>初步意见</th></tr></thead><tbody>'
        for i,x in enumerate(r['picks']):
            view='观察，开关前不买' if wait else ('建议跟踪' if i<2 else '备选')
            out+='<tr><th scope="row">'+E(x['name'])+'<small>'+x['code']+' · '+E(x['industry'])+'</small></th><td>'+f(x['q_np'],'.1f','亿')+'</td><td>'+f(x['np_yoy'],'+.0f','%')+'</td><td>'+f(x['h1_yoy'],'+.0f','%')+'</td><td>'+f(x['pe'],'.1f')+'</td><td>'+f(x['pb'],'.2f')+'</td><td>'+f(x['dy'],'.2f','%')+'</td><td>'+str(x['mc'])+'</td><td><span class="lp-view'+(' wait' if wait else (' go' if i<2 else ''))+'">'+view+'</span></td></tr>'
        out+='</tbody></table></div><p class="note">进入个股研究时比较：'+E('；'.join(s['handoff']))+'</p>'+('</details>' if wait else '</article>')
    out+='<article class="lp-sec" id="l1-hk"><h3>港股（规则待数据）</h3><p class="note">港股尚无同口径公司财务数据，暂按板块列出代表公司，不排序；补齐数据后按同样的门槛和排序重算。</p><ul>'
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
    o=L2['oos_1y'];bt=L2.get('backtest')
    out+='<h3>这个逻辑过去有没有用</h3><div class="l2-bt">'
    if bt:
        out+='<p><b>多年滚动检验（'+E(bt['period'])+'，'+str(bt['stocks'])+'只）：</b>'+E(bt['summary'])+'</p><div class="tblwrap"><table class="mt lp-table"><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in bt['head'])+'</tr></thead><tbody>'
        for row in bt['rows']:out+='<tr>'+''.join('<td>'+E(str(v))+'</td>' for v in row)+'</tr>'
        out+='</tbody></table></div>'
    out+='<p class="note"><b>最近一年单独看：</b>'+E(o['note'])+'。箱体股共'+str(o['box_hot']['trades'])+'次信号，到箱顶'+f(o['box_hot']['win']*100,'.0f','%')+'、止损'+f(o['box_hot']['loss']*100,'.0f','%')+'，平均收益'+f(o['box_hot']['mean'],'+.1f','%')+'；同期小盘国资股中位数'+f(o['universe_median_y2'],'+.1f','%')+'，中证全指'+f(o['index_y2'],'+.1f','%')+'。箱底区之后60日内跌15%的概率'+f(o['bottom_vs_other']['bottom_dd15']*100,'.0f','%')+'，其他位置'+f(o['bottom_vs_other']['other_dd15']*100,'.0f','%')+'；60日内涨25%的概率'+f(o['bottom_vs_other']['bottom_spike25']*100,'.0f','%')+'对'+f(o['bottom_vs_other']['other_spike25']*100,'.0f','%')+'。</p><p class="l2-con"><b>结论：</b>'+E(L2.get('verdict','地板有保护作用，但脉冲不能靠位置预测；收益高度依赖小盘资金环境，必须加开关，开关打开前只观察，单只仓位要小。'))+'</p></div>'
    fun=L2['funnel'];out+='<h3>候选名单</h3><ol class="lp-funnel">'+''.join('<li>'+E(a)+'：<b>'+str(b)+'</b></li>' for a,b in fun)+'</ol>'
    out+='<div class="tblwrap"><table class="mt lp-table"><thead><tr><th>股票</th><th>市值（亿）</th><th>箱体宽度</th><th>往返</th><th>涨停 / 脉冲</th><th>当前位置</th><th>与大盘相关</th><th>前三季营收 / 利润（亿）</th><th>主要标签</th><th>初步意见</th></tr></thead><tbody>'
    for x in L2['top']:out+=l2_row(x,'可小仓位验证' if sw['on'] else '暂停')
    out+=l2_row(ref,'参考样本：满足六项条件，未进首批（脉冲1次、往返2次，重复性不足）')
    out+='</tbody></table></div><p class="note">排序：往返次数＋2×脉冲次数，从高到低；同分时位置更低者优先。这里列出前15名，另有'+str(fun[-1][1]-len(L2['top']))+'只同样满足条件。亏损公司需单独确认没有财务类退市风险。</p></section>'
    return out

def page(ctx):
    root=Path(ctx['ROOT']);S=json.loads((root/'data/sector_selection.json').read_text());P=json.loads((root/'data/stock_pick.json').read_text())
    sec={s['id']:s for s in S['sectors']};L2=P['logic2'];sw=switch_state(root)
    out='<style>'+CSS+'</style><div class="hero"><h1>个股：两条选股逻辑</h1><p class="sum">逻辑一顺着大盘和板块找“风口上最强的船”；逻辑二利用A股制度特点找“有地板、有天花板、偶尔放烟花的房间”。两条逻辑独立筛选，候选名单由我们一起决定。</p><p class="stamp">数据截至2026-11-13 · 本轮只提出候选，不做买卖决定</p></div>'
    out+='<section class="lp-two"><article><span>逻辑一 · 顺势选股</span><h2>风往哪吹，就在那里找最强的船</h2><p><b>来源：</b>大盘风向 → 板块档位 → 板块内的门槛与排序。</p><p><b>赚的是：</b>盈利兑现（分子）与估值修复（分母）。</p><p><b>现在：</b>银行可研究买点；煤炭、石油、油运只做前半段；等开关的方向只观察。</p><a href="#logic1">看候选 →</a></article>'
    out+='<article><span>逻辑二 · 国资箱体</span><h2>有地板、有天花板，偶尔放烟花</h2><p><b>来源：</b>国资背景不易退市（地板）、标签多（事件来了会被炒）、游资和散户定价（来回震荡）。</p><p><b>赚的是：</b>箱底到箱顶的位置差与事件脉冲。</p><p><b>现在：</b>'+('规则允许研究买点，但2026年的信号整体为负，建议先小仓位验证。' if sw['on'] else '大盘跌破托底线，暂停开新仓。')+'</p><a href="#logic2">看规则与候选 →</a></article></section>'
    out+=logic1_html(root,S,sec)+logic2_html(L2,sw)
    out+='<p class="note">'+E(P['source'])+' <a href="sector-pools.html">旧的个股三维筛选资料（历史）</a></p>'
    return out

def build(ctx):
    (Path(ctx['SITE'])/'stocks/index.html').write_text(ctx['page']('个股 | A 股框架笔记','gg',page(ctx),'../'),encoding='utf-8')

CSS="""
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
