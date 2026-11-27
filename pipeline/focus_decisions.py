"""Focused sector decisions: one action; independent dated evidence; no total score."""
import json,math
from pathlib import Path
from html import escape as E

def read(root,path):return json.loads((Path(root)/path).read_text())
def decide(item,market):
    if not item.get('thesis_valid',False):status,reason='移出关注',item.get('invalidate','主逻辑未成立')
    elif market.get('paused'):status,reason='暂停新增',market['reason']
    elif item.get('missing'):status,reason='待核',item['missing'][0]
    elif not item.get('entry_met'):status,reason='等待',item.get('entry_rule','参与条件尚未满足')
    else:status,reason='条件满足','已登记的研究、估值与参与条件通过；按各自风险约束执行。'
    return {'status':status,'reason':reason,'next':item['next']}

def position(rows,asof,event='2026-11-27'):
    rows=sorted((r for r in rows if r['date']<=asof and r.get('close',0)>0),key=lambda r:r['date'])
    if not rows:return None
    last=rows[-1];c=last['close'];s=rows[-250:];lo=min(r['close'] for r in s);hi=max(r['close'] for r in s)
    before=[r for r in rows if r['date']<event];prior=before[-1] if before else None
    window=rows[-120:];valid=[r for r in window if r.get('amount',0)>0];bins=[];upper=None
    # Composite-index close bucket, NOT traded cost distribution or current ownership.
    if len(valid)>=60:
        low=min(r['close'] for r in valid);high=max(r['close'] for r in valid);width=(high-low)/12
        if width>0:
            amount=[0.0]*12
            for r in valid:amount[min(11,int((r['close']-low)/width))]+=r['amount']
            total=sum(amount)
            bins=[{'lo':low+i*width,'hi':low+(i+1)*width,'share':v/total*100} for i,v in enumerate(amount)]
            above=[b for b in bins if b['lo']>c]
            upper=max(above,key=lambda b:b['share']) if above else None
    return {'date':last['date'],'close':c,'event_return':round((c/prior['close']-1)*100,2) if prior else None,'event_base':prior,'ma60':sum(r['close'] for r in rows[-60:])/60 if len(rows)>=60 else None,'range_52':[lo,hi] if len(rows)>=250 else None,'range_observed':[lo,hi],'n':len(rows),'low20':min(r['close'] for r in rows[-20:]),'dd':(c/hi-1)*100,'bins':bins,'upper':upper,'history':[r['close'] for r in rows[-120:]],'history_start':window[0]['date'],'activity_n':len(valid)}

def prepare(root):
    d=read(root,'data/focus_decisions.json');g=read(root,'data/market_thesis.json')['macro_regime'];D=g['markets']['a'].get('defense',{})
    markets={'a':{'paused':D.get('on',False),'reason':g['markets']['a']['verdict'],'recover':D.get('recover','见大盘恢复条件')},'hk':{'paused':False,'reason':'港股偏弱；既有规则仍保留高息研究，电信以现金流与估值核验为先。','recover':'其他港股方向恢复仍看恒指持续两周站回22,500且南向20日为正。'}}
    K=read(root,'data/raw/screen/klines.json');names={r['bk']:r['name'] for r in read(root,'data/raw/screen/result.json')}
    hk=read(root,'data/raw/hk/telecom_index.json')
    for x in d['items']:
        x['positions']=[]
        for key in x['indices']:
            h=key=='HSCIT';p=position(hk['rows'] if h else K.get(key,[]),d['as_of'],d['policy_date'])
            if not p:x['missing'].append(key+'缺少行情');continue
            p.update(code=key,name=hk['name'] if h else names[key],source=hk['source'] if h else 'https://quote.eastmoney.com/bk/90.'+key+'.html',range_basis=hk['range_basis'] if h else '近250个交易日收盘高低')
            if h:p['range_52']=hk.get('reported_52_range');p['missing']=hk['missing']
            if p['date']!=d['as_of']:x['missing'].append(key+'行情日期为'+p['date']+'，需补齐截至'+d['as_of']+'的数据')
            x['positions'].append(p)
        x['market_constraint']=markets[x['market']];x['decision']=decide(x,markets[x['market']])
    d['markets']=markets
    return d

def num(v):return '—' if v is None else f'{v:,.2f}'
def link(root,u):return u if u.startswith('http') else root+u
def badge(state):return '<span class="fd-status fd-'+{'移出关注':'off','暂停新增':'pause','待核':'check','等待':'wait','条件满足':'ready'}[state]+'">'+E(state)+'</span>'
def positions_short(x):
    out=[]
    for p in x['positions']:
        r=p['range_52'];where=(p['close']-r[0])/(r[1]-r[0])*100 if r and r[1]>r[0] else None
        out.append(E(p['name'])+'<br><b>'+num(p['close'])+'</b> · 政策前一收盘以来 '+('—' if p['event_return'] is None else f'{p["event_return"]:+.1f}%')+'<br><small>'+('区间位置 '+f'{where:.0f}%' if where is not None else '一年区间数据待补')+' · '+E(p['date'])+'</small>')
    return '<div class="fd-mini">'+'</div><div class="fd-mini">'.join(out)+'</div>'

def home(root,prefix='',market=None):
    d=prepare(root)
    out='<style>'+CSS+'</style><section id="focus" class="fd"><div class="fd-head"><div><span>当前决策 · '+E(d['as_of'])+' 收盘 · A股 / 港股</span><h2>只跟踪三个方向</h2></div><a href="'+prefix+'boards/index.html">重点板块与存档 →</a></div><p class="fd-intro">先看最终行动，再看位置、触发条件和失效条件。研究优先级不等于现在可以买；其他板块暂停主动扩展。</p>'
    out+='<div class="fd-context"><p><b>A股约束</b>'+E(d['markets']['a']['reason'])+'</p><p><b>港股约束</b>'+E(d['markets']['hk']['reason'])+'</p></div>'
    out+='<div class="fd-scroll"><table class="fd-table"><thead><tr><th>研究方向 / 主理由</th><th>最终行动</th><th>现在的位置</th><th>下一步与参与条件</th><th>何时放弃</th></tr></thead><tbody>'
    for x in d['items']:
        out+='<tr data-focus="'+x['id']+'"><th><a href="'+prefix+'boards/'+x['id']+'.html">'+E(x['title'])+'</a><small>'+E(x['reason'])+'</small></th><td>'+badge(x['decision']['status'])+'<p>'+E(x['decision']['reason'])+'</p></td><td>'+positions_short(x)+'</td><td><b>'+E(x['next'])+'</b><p>'+E(x['entry_rule'])+'</p></td><td>'+E(x['invalidate'])+'</td></tr>'
    out+='</tbody></table></div><p class="fd-note">位置为价格区间，不是估值分位。A股用250个交易日收盘范围；港股用来源公布的52周盘中范围，不能直接横向排名。没有用跌幅或历史成交推算当前亏损人数。</p>'
    out+='<details class="fd-policy"><summary>'+E(d['policy']['title'])+'</summary><p>'+E(d['policy']['text'])+'</p>'
    for ev in d['policy']['events']:out+='<p><b>'+E(ev['date'])+' · '+E(ev['title'])+'</b> '+E(ev['new'])+' <a href="'+E(ev['url'],quote=True)+'">原文</a></p>'
    return out+'</details></section>'

def chart(p):
    vals=p['history'];lo=min(vals);hi=max(vals);span=hi-lo or 1
    pts=' '.join(f'{10+i*620/max(len(vals)-1,1):.1f},{120-(v-lo)/span*100:.1f}' for i,v in enumerate(vals))
    return '<svg viewBox="0 0 640 140" class="fd-chart" role="img" aria-label="'+E(p['name'])+'收盘走势"><line x1="10" x2="630" y1="120" y2="120" stroke="#d5dce4"/><polyline points="'+pts+'" fill="none" stroke="#355a78" stroke-width="2.5"/></svg>'

def detail(d,x):
    out='<style>'+CSS+'</style><nav class="crumb"><a href="index.html#focus">三个重点方向</a> / '+E(x['title'])+'</nav><section class="fd"><div class="fd-head"><div><span>'+E(d['as_of'])+' · '+E(d['version'])+'</span><h1>'+E(x['title'])+'</h1></div>'+badge(x['decision']['status'])+'</div><p class="fd-lead">'+E(x['verdict'])+'</p><div class="fd-context"><p><b>行动原因</b>'+E(x['decision']['reason'])+'</p><p><b>下次复核</b>'+E(x['next'])+'</p></div>'
    out+='<h2>位置与潜在压力</h2><p>'+E(x['benchmark'])+'</p><div class="fd-positions">'
    for p in x['positions']:
        r=p['range_52'];u=p['upper']
        out+='<article><h3>'+E(p['name'])+' <small>'+E(p['code'])+'</small></h3>'+chart(p)+'<div class="fd-numbers"><p>最新收盘<b>'+num(p['close'])+'</b></p><p>政策前一收盘以来<b>'+('—' if p['event_return'] is None else f'{p["event_return"]:+.2f}%')+'</b></p><p>60日均线<b>'+num(p['ma60'])+'</b></p></div><p><b>一年区间：</b>'+('—' if not r else num(r[0])+'—'+num(r[1]))+'；'+E(p['range_basis'])+'。</p><p><b>近20日最低收盘：</b>'+num(p['low20'])+'，用于观察低位承接，不自动设为止损或买点。</p>'
        if u:out+='<p><b>上方历史活跃区参考：</b>'+num(u['lo'])+'—'+num(u['hi'])+'；该区间对应样本成交额占比'+f'{u["share"]:.1f}%'+ '。回到这一区域时再观察实际承接与卖压。</p>'
        else:out+='<p><b>上方历史活跃区：</b>当前序列不足或没有完全位于现价之上的有效区间，不输出估计值。</p>'
        out+='<details><summary>行情与历史活动的计算口径</summary><p>行情截至'+E(p['date'])+'。走势从'+E(p['history_start'])+'开始。A股历史活动以最近120个交易日行业指数的收盘点位分成12个等宽区间，累加对应日期的行业成交额，选出现价上方占比最高的区间；区间数量仅为展示参数，未作为买卖阈值。它不是逐笔成交成本、持仓成本或亏损人数；指数成分变化也会影响比较。</p>'+('<p>'+E(p['missing'])+'</p>' if p.get('missing') else '')+'<a href="'+E(p['source'],quote=True)+'">行情来源</a></details></article>'
    out+='</div><h2>一条主逻辑，逐步验收</h2><ol class="fd-chain">'+''.join('<li>'+E(v)+'</li>' for v in x['chain'])+'</ol><ul>'+''.join('<li>'+E(v)+'</li>' for v in x['facts'])+'</ul>'
    out+='<div class="fd-context"><p><b>唯一主估值</b>'+E(x['primary_metric'])+'。尚未完成独立估值区间时，不输出目标收益或用盈亏比倒推目标。</p><p><b>参与条件</b>'+E(x['entry_rule'])+'</p></div><h2>待核事项有结束条件</h2><table class="fd-checks"><thead><tr><th>缺什么</th><th>怎样算完成</th><th>复核时间</th></tr></thead><tbody>'
    for i,a in enumerate(x['missing']):
        b=x['completion'][i] if i<len(x['completion']) else '补齐该项截至判断日的原始数据与来源后重算；缺项期间不升级。'
        out+='<tr><td>'+E(a)+'</td><td>'+E(b)+'</td><td>'+E(x['review_at'])+'</td></tr>'
    out+='</tbody></table><p><b>下一触发：</b>'+E(x['trigger'])+'</p><p><b>失效／移出关注：</b>'+E(x['invalidate'])+'</p><details><summary>证据与原始研究</summary>'+''.join('<p><a href="'+E(link('../',u),quote=True)+'">'+E(n)+'</a></p>' for n,u in x['links'])+'<p><a href="../data/focus-decisions.json">下载本次完整决策与位置数据</a></p></details></section>'
    return out

def archive_note(root,prefix=''):
    return '<div class="fd-archive-note"><b>当前研究范围已收敛。</b>本页保留原策略、候选与风险记录；主研究入口为 <a href="'+prefix+'boards/index.html#focus">AI硬件、券商、港股电信</a>。非重点方向不新增研究，已有持仓仍需按原规则跟踪风险。</div>'

def build(ctx):
    root=Path(ctx['ROOT']);d=prepare(root)
    for x in d['items']:(root/'docs/boards'/f'{x["id"]}.html').write_text(ctx['page'](x['title']+' | 重点决策','bk',detail(d,x),'../'))
    (root/'docs/data/focus-decisions.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

CSS='''
.fd{margin:20px 0 28px;padding:24px;background:#fff;border:1px solid #d6e0e8;border-radius:12px;color:#243746}.fd h1{font-size:28px;margin:6px 0}.fd h2{font-size:21px;margin:22px 0 12px}.fd h3{font-size:17px;margin:0 0 8px}.fd p,.fd li{line-height:1.8}.fd-head{display:flex;justify-content:space-between;align-items:center;gap:20px}.fd-head h2{margin:5px 0}.fd-head span,.fd small,.fd-note{font-size:12px;color:#62788b}.fd-intro{font-size:14px;margin:8px 0 16px}.fd-context{display:grid;grid-template-columns:1fr 1fr;gap:16px;background:#f3f6f9;border-radius:8px;padding:12px 16px;margin:16px 0}.fd-context p{font-size:13px;margin:0}.fd-context b{display:block;margin-bottom:3px}.fd-scroll{overflow-x:auto}.fd-table{width:100%;border-collapse:collapse;table-layout:fixed;min-width:950px}.fd-table th,.fd-table td{vertical-align:top;text-align:left;padding:16px 12px;border-bottom:1px solid #dfe6ed;font-size:13px;line-height:1.7}.fd-table thead th{font-size:12px;color:#64798d;background:#f7f9fb}.fd-table th:first-child{width:18%}.fd-table th:nth-child(2){width:18%}.fd-table th:nth-child(3){width:21%}.fd-table th:nth-child(4){width:26%}.fd-table th:nth-child(5){width:17%}.fd-table tbody th a{font-size:16px;text-decoration:none}.fd-table small{display:block;font-weight:400}.fd-table p{margin:8px 0 0}.fd-mini+.fd-mini{margin-top:8px;padding-top:8px;border-top:1px dashed #dfe6ed}.fd-status{display:inline-block;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:700;white-space:nowrap}.fd-pause,.fd-off{background:#f5e8e4;color:#8b4130}.fd-check,.fd-wait{background:#fff4dc;color:#8a601b}.fd-ready{background:#e2f2e8;color:#286641}.fd-policy{border-top:1px solid #dfe6ed;padding-top:12px;font-size:13px}.fd-policy summary{cursor:pointer;font-weight:600}.fd-positions{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}.fd-positions article{border:1px solid #dbe3eb;border-radius:10px;padding:18px;min-width:0}.fd-positions p,.fd-positions details{font-size:13px}.fd-chart{width:100%;height:150px}.fd-numbers{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.fd-numbers p{font-size:12px;color:#657b8d}.fd-numbers b{display:block;font-size:20px;color:#253e54}.fd-chain{display:flex;gap:8px;padding:0;list-style:none;flex-wrap:wrap}.fd-chain li{flex:1 1 150px;border-top:3px solid #526f88;background:#f3f6f9;padding:12px;font-size:13px}.fd-chain li+li::before{content:'→ ';color:#6e8496}.fd-checks{width:100%;border-collapse:collapse}.fd-checks th,.fd-checks td{padding:12px;text-align:left;border:1px solid #dfe6ed;vertical-align:top;font-size:13px}.fd-checks th{background:#f3f6f9}.fd-lead{font-size:17px;font-weight:600}.fd-archive-note{background:#f1f5f8;border-left:3px solid #54728c;padding:12px 16px;font-size:13px;line-height:1.8;margin:16px 0}.fd-archive summary{cursor:pointer;font-weight:600;padding:14px;background:#f3f6f9}.fd-archive{margin:20px 0}
@media(max-width:800px){.fd{padding:16px}.fd-context,.fd-positions{grid-template-columns:1fr}.fd-head{align-items:flex-start}.fd-head>a{font-size:12px}.fd-checks th,.fd-checks td{padding:6px}}
'''
