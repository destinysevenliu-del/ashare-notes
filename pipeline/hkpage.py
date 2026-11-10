"""Hong Kong market: dated observations, independent inputs, no synthetic backfill."""
import datetime,json
from pathlib import Path
from zoneinfo import ZoneInfo
from hk_fetch import completed_rows

NAMES={'hsi':'恒生指数','hscei':'恒生中国企业指数','hstech':'恒生科技指数'}
VERSION='HK v1 · 2026-11-10'

def change(rows,n):
    return (rows[-1]['close']/rows[-n-1]['close']-1)*100 if len(rows)>n else None

def aligned_series(indices,n=120):
    dates=sorted(set.intersection(*(set(r['date'] for r in rows) for rows in indices.values())))[-n:]
    if not dates:return []
    colors=['#B44F46','#456B87','#947539'];out=[]
    for (key,rows),color in zip(indices.items(),colors):
        values={r['date']:r['close'] for r in rows};base=values[dates[0]]
        out.append((NAMES[key],color,[(d,values[d]/base*100) for d in dates]))
    return out

def funding_score(rows,asof):
    values=[r for r in rows if r['end_of_date']<=asof and isinstance(r.get('hibor_fixing_1m'),(float,int))]
    if len(values)<21 or (datetime.date.fromisoformat(asof)-datetime.date.fromisoformat(values[-1]['end_of_date'])).days>7:return None,None
    delta=(values[-1]['hibor_fixing_1m']-values[-21]['hibor_fixing_1m'])*100
    return (1 if delta<=-25 else -1 if delta>=25 else 0),delta

def flow_window(rows,dates,n):
    # Require observations for every recent HK trading day: missing data is not zero.
    expected=dates[-n:];bydate={r['date']:r for r in rows}
    if len(expected)<n or any(d not in bydate for d in expected):return None
    return sum(bydate[d]['net'] for d in expected)

def build(ctx):
    root=Path(ctx['ROOT']);raw=root/'data/raw/hk';out=root/'docs/hk';out.mkdir(exist_ok=True)
    E=ctx['E'];page=ctx['page'];chart=ctx['line_chart'];D=ctx['D'];now=datetime.datetime.now(ZoneInfo('Asia/Shanghai'))
    def read(name,default):
        p=raw/(name+'.json');return json.loads(p.read_text()) if p.exists() else default
    fetched={key:read(key,{'rows':[]}) for key in NAMES}
    indices={key:completed_rows(data,now) for key,data in fetched.items()}
    if any(not rows for rows in indices.values()):
        (out/'index.html').write_text(page('港股大盘 | A 股框架笔记','hk','<div class="hero"><h1>港股大盘</h1><p>港股收盘数据暂缺，更新后展示完整框架。</p></div>','../'));return
    asof=min(rows[-1]['date'] for rows in indices.values())
    indices={k:[r for r in rows if r['date']<=asof] for k,rows in indices.items()}
    dates=[r['date'] for r in indices['hsi']];liquidity=read('liquidity',{'rows':[]});liq=[r for r in liquidity['rows'] if r['end_of_date']<=asof]
    sb=read('southbound',{'rows':[]});flows=[r for r in sb['rows'] if r['date']<=asof]
    status=read('status',{});fundscore,delta=funding_score(liq,asof)
    net5=flow_window(flows,dates,5);net20=flow_window(flows,dates,20)
    flowscore=None if net5 is None else (1 if net5>0 else -1 if net5<0 else 0)
    # These are two explicitly bounded proxy signals, never a full-market aggregate score.
    scores={'external':None,'economy':None,'policy':None,'liquidity':fundscore,'valuation':None,'funds':flowscore}
    def fmt(v,pattern='{:.2f}',unit=''):
        return '待数据' if v is None else pattern.format(v)+unit
    def link(url,title):return f'<a href="{E(url,quote=True)}" target="_blank" rel="noopener noreferrer">{E(title)}</a>'
    def source(url,title):return '<p class="src">来源：'+link(url,title)+'</p>'
    def metrics(headers,rows):
        return '<div class="tblwrap"><table class="mt"><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    def verdict(score,reason):
        state='na' if score is None else 'up' if score>0 else 'down' if score<0 else 'flat'
        return ctx['verdict'](state,score,[],E(reason))
    def section(key,title,q,body,score=None,state=None):
        state=state or ('na' if score is None else 'up' if score>0 else 'down' if score<0 else 'flat')
        return f'<section class="nd" id="node-{key}"><div class="ndh"><span class="lc2 {state}">{key}</span><div><h3>{title}</h3><p class="q">{q}</p></div></div>{body}</section>'
    titles={'A':'经济与外部环境','B':'政策与监管','C':'企业盈利','D':'港元与美元资金成本','E':'盈利预期修订','F':'港股估值','G':'南向资金','H':'指数与价格位置'}
    macro=[]
    for label,series,unit in [('制造业 PMI',D.pmi,''),('社会消费品零售总额同比',D.retail,'%'),('工业增加值同比',D.indus,'%'),('出口同比',D.exports,'%')]:
        r=series[-1];macro.append([label,fmt(r['v'],'{:g}',unit),E(r['period'])])
    sec=section('A',titles['A'],'内地需求与全球风险偏好，分别通过什么路径影响港股？',
        '<p>内地经营业务较多的港股，关注消费、制造业与出口；香港本地地产、金融另看本地经济。地缘关系和海外风险偏好需要有日期的原始证据单独记录。</p>'+metrics(['内地宏观背景','最新值','统计期间'],macro)+
        verdict(None,'背景数据沿用站内已抓取的内地宏观序列，按各自统计期展示；尚未映射到港股指数的收入结构，经济和外部环境两项暂不计分。')+
        source('https://data.stats.gov.cn/','国家统计局（站内数据经东方财富整理）'))
    sec+=section('B',titles['B'],'政策是否已落地，影响哪类公司、收入或资金准入？',
        verdict(None,'待补有生效日期、原始链接和影响对象的政策记录。没有核验记录不等于政策中性。')+
        '<p>分开追踪内地行业监管、香港资本市场制度、互联互通范围，以及海外限制。将“发布消息”与“盈利或交易机制实际改变”分开。</p>'+
        source('https://www.sfc.hk/en/News-and-announcements/Policy-statements-and-announcements','香港证监会政策公告')+
        source('https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily?sc_lang=en','港交所互联互通'))
    sec+=section('C',titles['C'],'收入、利润和现金流是否一起兑现？',
        verdict(None,'尚未接入恒生、国企、恒生科技成分公司的同口径盈利汇总，不计分。')+
        '<p>后续按金融、互联网、消费、本地地产等分组，追踪同一批公司的收入、归母利润和经营现金流。先解释权重与成分变动，再汇总；银行使用适合其业务的财务指标。</p>'+
        source('https://www.hkexnews.hk/','披露易公司公告'))
    fundingrows=[]
    if liq:
        last=liq[-1]
        for label,key,unit in [('隔夜 HIBOR','hibor_overnight','%'),('1 个月 HIBOR','hibor_fixing_1m','%'),('贴现窗基本利率','disc_win_base_rate','%'),('银行体系总结余','closing_balance',' 亿港元')]:
            value=last.get(key);value=value/100 if key=='closing_balance' and value is not None else value
            fundingrows.append([label,fmt(value,'{:.2f}',unit),last['end_of_date']])
    us=[(d,v) for d,v in D.us10 if d<=asof]
    if us:fundingrows.append(['美国 10 年国债收益率',fmt(us[-1][1],'{:.2f}','%'),us[-1][0]])
    dbody='<p>联系汇率使港元货币环境与美元相联，但 HIBOR 也受本地资金供求影响。资金成本下降通常有助融资和估值，银行净息差等行业影响需另看。</p>'+metrics(['指标','最新值','数据日期'],fundingrows)
    dbody+=verdict(fundscore,'1 个月 HIBOR 较 20 个有效观测前变化 '+fmt(delta,'{:+.1f}','bp')+'。这里只评估港元短端成本；美债收益率、总结余仅作背景。')
    hib=[(r['end_of_date'],r['hibor_fixing_1m']) for r in liq if isinstance(r.get('hibor_fixing_1m'),(int,float))]
    if len(hib)>1:dbody+=chart([('1 个月 HIBOR','#456B87',hib[-60:])],ylabel='1 个月 HIBOR（%）',fmt='{:.2f}')
    dbody+=ctx['rules']('<p>较 20 个有效观测前下降至少 25bp：+1；上升至少 25bp：−1；其余：0。少于 21 条或最新观测落后行情超过 7 个自然日：待数据。仅为可调整的观察阈值，未经收益预测验证；总结余不是港股流入金额。</p>')
    dbody+=source('https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity','香港金管局每日银行同业流动资金数据')+source('https://www.hkma.gov.hk/eng/key-functions/money/linked-exchange-rate-system/','香港金管局联系汇率制度')
    sec+=section('D',titles['D'],'港元融资成本是否变松？',dbody,fundscore)
    sec+=section('E',titles['E'],'同一目标年度的盈利预测，是被上调还是下调？',verdict(None,'缺少带真实采集时间的港股一致预期历史，不计分。')+'<p>后续保存同一机构覆盖、同一指数成分、同一目标财年的 EPS 预测快照，比较 30／90 天修订。不同年份预测之间的增长不是预期修订。</p>')
    sec+=section('F',titles['F'],'价格里已经包含了多少增长或风险？',verdict(None,'港股指数 PE、PB、股息率及同口径历史尚未接入，不计分。')+
        '<p>恒生、国企、恒生科技分别使用各自的估值历史。后续区分 PE／PB／股息率及亏损公司处理规则；A/H 溢价只用于同一发行人的两地股票比较，不代替整个港股市场估值。</p>'+source('https://www.hsi.com.hk/en-hk/indexes/all-indexes/index-details/?seriesCode=hsi','恒生指数公司'))
    latest=flows[-1] if flows else None
    frows=[]
    if latest:
        frows=[['南向买入成交',fmt(latest['buy'])+' 亿港元',latest['date']],['南向卖出成交',fmt(latest['sell'])+' 亿港元',latest['date']],['南向净买入',fmt(latest['net'],'{:+.2f}')+' 亿港元',latest['date']]]
    frows += [['近 5 个港股交易日合计',fmt(net5,'{:+.2f}',' 亿港元'),asof],['近 20 个港股交易日合计',fmt(net20,'{:+.2f}',' 亿港元'),asof]]
    gbody=metrics(['沪港通 + 深港通（南向）','金额','截至日期'],frows)+verdict(flowscore,'仅看最近 5 个港股交易日南向净买入方向；不代表全部外资或整个港股市场的资金流。')
    if len(flows)>1:
        # Align on actual observed connect dates; no zero fill or forward fill.
        gbody+=chart([('南向每日净买入（亿港元）','#B44F46',[(r['date'],r['net']) for r in flows[-30:]])],ylabel='南向净买入（亿港元）',bands=[(0,'零线')])
    gbody+=ctx['rules']('<p>净买入 = 沪港通南向买入成交 − 卖出成交 + 深港通南向买入成交 − 卖出成交。港交所原表单位为百万港元，除以 100 换算为亿港元；不使用每日额度余额。最近 5 个港股交易日均有双通道数据时，合计为正记 +1、为负记 −1、为零记 0；缺日、非互联互通交易日或缺一通道都暂不判定，不补零。20 日合计同理。</p>')
    gbody+=source(sb.get('source','https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily?sc_lang=en'),'港交所互联互通历史每日统计')
    sec+=section('G',titles['G'],'内地经互联互通买入港股的力量如何变化？',gbody,flowscore)
    price=[]
    for key,rows in indices.items():
        close=rows[-1]['close'];ma20=sum(r['close'] for r in rows[-20:])/20;ma60=sum(r['close'] for r in rows[-60:])/60
        draw=(close/max(r['close'] for r in rows[-250:])-1)*100
        price.append([NAMES[key],f'{close:,.2f}',fmt(change(rows,1),'{:+.2f}','%'),fmt(change(rows,5),'{:+.2f}','%'),fmt(change(rows,20),'{:+.2f}','%'),f'{ma20:,.2f} / {ma60:,.2f}',f'{draw:.2f}%'])
    hbody=metrics(['指数','收盘','日涨跌','5 日','20 日','MA20 / MA60','距近 250 日收盘高点'],price)
    aligned=aligned_series(indices)
    if aligned:hbody+=chart(aligned,ylabel='共同起点 = 100，价格指数，不含股息')
    hbody+='<p class="sub">对齐三个指数的共同交易日，展示最近 120 日相对走势；为价格指数，未计股息再投资。均线和回撤用于定位当前价格，不纳入信号评分。</p>'
    hbody+=source('https://quote.eastmoney.com/gb/zsHSI.html','东方财富指数日 K（恒生 / 国企 / 恒生科技）')
    sec+=section('H',titles['H'],'不同指数的趋势是否一致？',hbody,state='price')
    # Store only observed snapshots. First collection never claims reconstructed yesterday scores.
    snapdir=root/'data/snapshots/hk_v1';snapdir.mkdir(parents=True,exist_ok=True)
    history=[]
    for p in snapdir.glob('*.json'):
        data=json.loads(p.read_text())
        if data['date']<asof:history.append(data)
    previous=max(history,key=lambda d:d['date']) if history else None
    labels={'external':'外部环境','economy':'内地经济背景','policy':'政策','liquidity':'港元资金成本','valuation':'港股估值','funds':'南向资金'}
    cards=''
    for key,label in labels.items():
        score=scores[key];state='na' if score is None else 'up' if score>0 else 'down' if score<0 else 'flat'
        text='待核验 / 待数据' if score is None else f'{score:+d}' if score else '0'
        cards+=f'<div class="hk-score"><span>{label}</span><strong class="{state}">{text}</strong><small>{"不计分" if score is None else "局部代理信号"}</small></div>'
    daily=[]
    for key,rows in indices.items():daily.append(f'<li><b>{NAMES[key]}</b> 收于 {rows[-1]["close"]:,.2f}，较上一交易日 {change(rows,1):+.2f}%。</li>')
    if latest:daily.append(f'<li><b>南向资金</b> {latest["date"]} 净买入 {latest["net"]:+.2f} 亿港元。</li>')
    snapshot_note='首次建立港股信号记录，暂不展示昨天的评分变化。'
    if previous:
        changed=[f'{labels[k]}：{previous["scores"].get(k)} → {v}' for k,v in scores.items() if previous['scores'].get(k)!=v]
        snapshot_note='与上次有效记录 '+previous['date']+' 相比：'+('；'.join(changed) if changed else '分项状态未变')+'。缺失值表示待数据。'
    known=sum(v is not None for v in scores.values())
    signs={k:'na' for k in titles};signs['D']='na' if fundscore is None else 'up' if fundscore>0 else 'down' if fundscore<0 else 'flat';signs['G']='na' if flowscore is None else 'up' if flowscore>0 else 'down' if flowscore<0 else 'flat';signs['H']='price'
    nodes=''.join(f'<a href="#node-{k}" class="hk-node {signs[k]}"><b>{k}</b><span>{v}</span><small>{"价格结果" if k=="H" else "已接入 · 局部观察" if k in "DG" and signs[k]!="na" else "背景参考" if k=="A" else "待核验 / 待数据"}</small></a>' for k,v in titles.items())
    positions={'A':(20,20),'B':(20,140),'C':(230,20),'D':(440,140),'E':(440,20),'F':(650,20),'G':(650,140),'H':(860,20)}
    svg=['<svg class="hk-diagram" viewBox="0 0 1050 245" role="img" aria-label="港股八节点传导图"><defs><marker id="hk-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#9ca5ad"/></marker></defs>']
    for path in ['M190 58 H230','M105 140 V110 H315 V96','M400 58 H440','M610 58 H650','M525 140 V115 H735 V96','M820 58 H860','M820 178 H945 V96']:
        svg.append(f'<path d="{path}" fill="none" stroke="#9ca5ad" stroke-width="1.5" marker-end="url(#hk-arrow)"/>')
    for key,(x,y) in positions.items():
        color={'up':'#B44F46','down':'#34816c'}.get(signs[key],'#8b959d')
        svg.append(f'<a href="#node-{key}"><rect x="{x}" y="{y}" width="170" height="76" rx="5" fill="#fff" stroke="{color}"/><text x="{x+12}" y="{y+25}" font-size="14">{key} · {titles[key]}</text><text x="{x+12}" y="{y+52}" class="small">点击展开指标与证据</text></a>')
    svg.append('</svg>');diagram=''.join(svg)
    warnings=[]
    if status.get('liquidity','').startswith('error'):
        warnings.append('港元数据沿用最近成功获取的披露记录；本次刷新未取得新数据，各指标日期见下表。')
    if (now.date()-datetime.date.fromisoformat(asof)).days>4:warnings.append('指数数据距今超过 4 个自然日，请确认是否为假期或更新中断。')
    failed=[k for k in NAMES if status.get(k,'').startswith('error')]
    if failed:warnings.append('部分指数本次获取失败，使用最近一次成功缓存：'+ '、'.join(NAMES[k] for k in failed)+'。')
    if fundscore is None:warnings.append('港元资金成本：有效历史不足、数据过期或接口缺失，暂停计分。')
    if net5 is None or net20 is None:warnings.append('南向合计：部分观察窗口缺日或遇到非互联互通交易日，不补零、不输出完整窗口合计。')
    conditions=[('港元成本明显变动', '已触发' if delta is not None and abs(delta)>=25 else '未触发' if delta is not None else '待数据','1 个月 HIBOR 较 20 个观测前变动至少 25bp。'),('南向短期转为净卖出','已触发' if net5 is not None and net5<0 else '未触发' if net5 is not None else '待数据','最近 5 个港股交易日合计净买入为负。'),('恒生跌破 60 日均线','已触发' if indices['hsi'][-1]['close']<sum(r['close'] for r in indices['hsi'][-60:])/60 else '未触发','只作趋势观察，不作为买卖指令。'),('盈利与估值证据','待补齐','C / E / F 未接入前，不形成港股整体便宜或盈利改善的结论。')]
    stamp=f'三个指数统一截至 {asof} 收盘；页面生成于 {now.strftime("%Y-%m-%d %H:%M")}（香港 / 北京时间）。当日 17:00 前剔除当日 K 线；各数据源日期见下表。'
    body=f'<div class="hero"><p class="date">{asof} · 港股观察</p><h1>港股大盘处在什么状态</h1><p class="sum">用同一套 A–H 框架，分别看内地经营环境、港元资金成本、南向资金与港股价格。</p><p class="stamp">{stamp}</p></div>'
    if warnings:body+='<div class="hk-notice">'+''.join('<p>'+E(w)+'</p>' for w in warnings)+'</div>'
    body+='<section class="block" id="today"><h2>今天变了什么</h2><p class="sub">行情比较最近两个完整交易日；资金按自身最新披露日展示。</p><ul class="hk-changes">'+''.join(daily)+'</ul><p class="sub">'+E(snapshot_note)+'</p></section>'
    body+='<section class="block" id="map"><h2>传导图</h2><p class="sub">经济 / 政策 → 盈利与预期；资金成本影响估值；估值与资金共同反映到价格。点击节点查看指标与证据。</p>'+diagram+'<div class="hk-map">'+nodes+'</div><p class="sub">红色为正向代理信号、绿色为负向代理信号；灰色待数据与中性在文字中区分。传导方向是分析假设，不是已证实因果。</p></section>'
    body+=f'<section class="block" id="score"><h2>信号观察卡</h2><p class="sub">六个维度，目前 {known} / 6 项有可计算的局部信号。缺项不按 0 分处理，不合成总分，也不与 A 股总分比较。</p><div class="hk-scores">{cards}</div></section>'
    body+='<section class="block" id="nodes"><h2>逐项展开</h2><p class="sub">沿用 A 股的 A–H 顺序，港股使用自身指标与来源。</p>'+sec+'</section>'
    body+='<section class="block" id="conds"><h2>港股关注条件</h2><p class="sub">触发仅提示补看证据，阈值可以调整。</p>'+metrics(['关注项','当前状态','判断依据'],conditions)+'</section>'
    (out/'index.html').write_text(page('港股大盘 | A 股框架笔记','hk',body,'../'),encoding='utf-8')
    snapshot={'date':asof,'observed_at':now.isoformat(),'rules_version':VERSION,'scores':scores,'net5':net5,'net20':net20,'hibor_20obs_bp':delta,'sources':{k:rows[-1]['date'] for k,rows in indices.items()}}
    (snapdir/(asof+'.json')).write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
    print('built HK',asof,'valid dimensions',known)
