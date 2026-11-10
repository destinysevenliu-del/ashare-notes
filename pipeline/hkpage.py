"""Hong Kong market: dated observations, independent inputs, no synthetic backfill."""
import datetime,json
from pathlib import Path
from zoneinfo import ZoneInfo
from hk_fetch import completed_rows

NAMES={'hsi':'恒生指数','hscei':'恒生中国企业指数','hstech':'恒生科技指数'}
VERSION='HK v2 · 2026-11-10'

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

def framework_diagram(titles, notes):
    """Render the user-supplied causal layout with two explicit FX paths."""
    positions = {
        'A': (20, 20, 280), 'B': (440, 20, 580),
        'C': (20, 160, 280), 'D': (440, 160, 260), 'X': (760, 160, 260),
        'E': (20, 320, 210), 'F': (270, 320, 280), 'G': (600, 320, 420),
        'H': (270, 480, 480),
    }
    descriptions = {
        'A': '中国经营基本面 × 美国流动性／美元',
        'B': '内地货币财政产业 · 美联储 · 香港本地制度',
        'C': '需求、利润率、现金流及币种敞口',
        'D': '利率 · 信用与融资 · 风险偏好',
        'X': '人民币业务与港元计价之间的桥梁',
        'E': '机构覆盖 · 同目标年度 EPS 修订',
        'F': '盈利预期 · 折现率 · 风险溢价',
        'G': '南向／境外／本地 · 持仓 · 申赎 · 交易约束',
        'H': '观察价格结果与不同指数的趋势差异',
    }
    parts = [
        '<svg class="hk-diagram" viewBox="0 0 1040 600" role="img" aria-label="港股影响因子框架，含人民币汇率两条传导路径">',
        '<defs><marker id="hk-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#96a1b2"/></marker>',
        '<marker id="hk-fx-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#6fa4fa"/></marker></defs>',
    ]
    paths = [
        'M160 116 L160 160',                    # A -> C
        'M540 116 C540 143 270 130 240 160',     # B -> C
        'M760 116 C760 144 570 136 570 160',     # B -> D
        'M150 256 C150 282 120 290 120 320',     # C -> E
        'M210 256 C210 290 400 280 400 320',     # C -> F
        'M570 256 C570 290 460 285 460 320',     # D -> F
        'M700 208 H735 V298 H810 V320',         # D -> G
        'M230 368 H270',                        # E -> F
        'M410 416 C410 450 470 446 470 480',     # F -> H
        'M810 416 C810 454 650 440 650 480',     # G -> H
    ]
    for path in paths:
        parts.append(f'<path d="{path}" fill="none" stroke="#96a1b2" stroke-width="1.4" marker-end="url(#hk-arrow)"/>')
    for path in ['M840 256 C840 286 320 273 280 256', 'M920 256 C920 288 860 288 860 320']:
        parts.append(f'<path d="{path}" fill="none" stroke="#6fa4fa" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#hk-fx-arrow)"/>')
    parts.append('<text x="440" y="284" class="small" style="fill:#3478db">盈利折算 → C → F</text>')
    parts.append('<text x="918" y="293" class="small" style="fill:#3478db">资金偏好</text>')
    for key, (x, y, width) in positions.items():
        fill = '#eef5ff' if key == 'X' else '#172333' if key == 'H' else '#fff'
        border = '#4e91ff' if key == 'X' else '#172333' if key == 'H' else '#c1c9d3'
        text_color = '#fff' if key == 'H' else '#293e50'
        dash = '' if key in ('X', 'H') else ' stroke-dasharray="4 3"'
        parts.append(f'<a href="#node-{key}"><rect x="{x}" y="{y}" width="{width}" height="96" rx="10" fill="{fill}" stroke="{border}"{dash}/>')
        parts.append(f'<text x="{x + 14}" y="{y + 25}" style="fill:{text_color}" font-size="14" font-weight="600">{key} · {titles[key]}</text>')
        parts.append(f'<text x="{x + 14}" y="{y + 49}" class="small" style="fill:{text_color}">{descriptions[key]}</text>')
        parts.append(f'<text x="{x + 14}" y="{y + 75}" class="small" style="fill:{text_color}">{notes[key]}</text></a>')
    parts.append('</svg>')
    return ''.join(parts)


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
    scores = dict.fromkeys('ABCDEFGX')
    proxy_signals = {'hibor': fundscore, 'southbound': flowscore}
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
    titles = {'A': '全球宏观环境', 'B': '货币、财政与产业政策', 'C': '需求、成本与企业盈利',
              'D': '利率、融资条件与风险偏好', 'X': '人民币汇率', 'E': '未来盈利预期',
              'F': '投资者愿意支付的估值', 'G': '参与者的仓位、申赎与交易约束', 'H': '港股走势'}
    macro=[]
    for label,series,unit in [('制造业 PMI',D.pmi,''),('社会消费品零售总额同比',D.retail,'%'),('工业增加值同比',D.indus,'%'),('出口同比',D.exports,'%')]:
        r=series[-1];macro.append([label,fmt(r['v'],'{:g}',unit),E(r['period'])])
    macro_us = [(date, value) for date, value in D.us10 if date <= asof]
    if macro_us:
        macro.append(['美国 10 年国债收益率', fmt(macro_us[-1][1], '{:.2f}', '%'), macro_us[-1][0]])
    macro.extend([['美元强弱（DXY）', '待数据', '待接入'], ['全球风险偏好／波动率', '待数据', '待接入']])
    sec=section('A',titles['A'],'中国基本面与美国流动性／美元环境如何共同作用？',
        '<p>以中国经营基本面和美国流动性／美元环境作为双重锚。内地需求通过收入与盈利传导，美国利率与全球风险偏好通过融资成本、折现率及资金配置传导。中美贸易和地缘事件按具体业务敞口记录。</p>'+metrics(['宏观背景','最新值','统计期／数据日期'],macro)+
        verdict(None,'内地宏观按统计期展示。美国利率观测见 D，人民币汇率见 X。全球美元强弱、风险偏好与地缘事件待补证据，综合状态待核验。')+
        source('https://data.stats.gov.cn/','国家统计局（站内数据经东方财富整理）'))
    policy_rows = [
        ['中国内地', '货币、财政、地产与产业监管', '需求、利润率、信用风险 → C。资金与互联互通安排 → G', '待补政策原文、生效日和影响对象'],
        ['美联储', '政策利率、资产负债表及政策预期', '美元融资环境、折现率与风险偏好 → D', '待补带日期的政策及市场预期记录'],
        ['香港本地', '金管局流动性安排、证监会监管、交易所制度', '本地融资与交易条件 → D / G', '待补已实施规则和生效日'],
    ]
    sec += section('B', titles['B'], '三层政策分别改变哪个传导环节？',
        metrics(['政策层', '追踪内容', '传导路径', '证据状态'], policy_rows)
        + verdict(None, '三层分别记录发布日、生效日、原始链接、受影响行业和兑现条件，综合状态待核验。')
        + source('https://www.pbc.gov.cn/', '中国人民银行')
        + source('https://www.federalreserve.gov/monetarypolicy.htm', '美联储货币政策')
        + source('https://www.hkma.gov.hk/eng/key-functions/money/linked-exchange-rate-system/', '香港金管局联系汇率制度')
        + source('https://www.sfc.hk/en/News-and-announcements/Policy-statements-and-announcements', '香港证监会政策公告'))
    earnings_rows = [
        ['互联网与科技', '广告、电商、游戏、云与资本开支', '收入、经营利润率、现金流、监管与海外业务敞口'],
        ['金融', '信贷需求、利率与资产质量', '银行净息差／信用成本，保险投资回报与新业务表现'],
        ['地产及本地业务', '销售、租金、融资与再融资', '现金流、债务到期与融资成本'],
        ['消费及其他行业', '销量、价格、原材料与汇兑', '收入、毛利率、利润及经营现金流'],
    ]
    sec += section('C', titles['C'], '指数成分公司的需求、成本和经营结果如何变化？',
        metrics(['业务组', '经营驱动', '验证指标'], earnings_rows)
        + '<p>按指数实际权重和成分结构汇总。人民币业务的利润先分析经营变化，再通过 X 解释港元折算变化。行业监管和海外限制按公司的实际敞口映射。</p>'
        + verdict(None, '成分公司同口径盈利汇总及权重映射待接入，综合盈利状态待数据。')
        + source('https://www.hkexnews.hk/', '披露易公司公告'))
    fundingrows=[]
    if liq:
        last=liq[-1]
        for label,key,unit in [('隔夜 HIBOR','hibor_overnight','%'),('1 个月 HIBOR','hibor_fixing_1m','%'),('贴现窗基本利率','disc_win_base_rate','%'),('银行体系总结余','closing_balance',' 亿港元')]:
            value=last.get(key);value=value/100 if key=='closing_balance' and value is not None else value
            fundingrows.append([label,fmt(value,'{:.2f}',unit),last['end_of_date']])
    us=[(d,v) for d,v in D.us10 if d<=asof]
    if us:fundingrows.append(['美国 10 年国债收益率',fmt(us[-1][1],'{:.2f}','%'),us[-1][0]])
    dbody='<p>分开观察无风险利率、信用／融资条件和风险偏好。联系汇率下，美元货币环境影响港元资金条件，HIBOR 同时受本地供求影响。融资成本对地产、成长公司与银行净息差的作用方向需按行业解释。</p>'+metrics(['指标','最新值','数据日期'],fundingrows)
    dbody+=verdict(None,'港元短端子项得分 '+fmt(fundscore,'{:+d}')+'。1 个月 HIBOR 较 20 个有效观测前变化 '+fmt(delta,'{:+.1f}','bp')+'。信用利差、再融资可得性、波动率及风险偏好待接入，D 的综合状态待核验。')
    hib=[(r['end_of_date'],r['hibor_fixing_1m']) for r in liq if isinstance(r.get('hibor_fixing_1m'),(int,float))]
    if len(hib)>1:dbody+=chart([('1 个月 HIBOR','#456B87',hib[-60:])],ylabel='1 个月 HIBOR（%）',fmt='{:.2f}')
    dbody+=ctx['rules']('<p>较 20 个有效观测前下降至少 25bp：+1；上升至少 25bp：−1；其余：0。少于 21 条或最新观测落后行情超过 7 个自然日：待数据。仅为可调整的观察阈值，未经收益预测验证；总结余不是港股流入金额。</p>')
    dbody+=source('https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity','香港金管局每日银行同业流动资金数据')+source('https://www.hkma.gov.hk/eng/key-functions/money/linked-exchange-rate-system/','香港金管局联系汇率制度')
    dbody += metrics(['D 的组成', '已观察', '待补证据'], [
        ['无风险利率', 'HIBOR 与美国 10 年国债收益率', '美元政策预期、期限结构'],
        ['融资条件', '银行体系总结余', '企业信用利差、杠杆融资成本、再融资可得性'],
        ['风险偏好', '待数据', '波动率、风险溢价与全球配置变化'],
    ])
    sec += section('D', titles['D'], '资金价格、融资可得性与风险承受意愿怎样变化？', dbody)
    fx = [(date, value) for date, value in D.cnh if date <= asof]
    fx_rows = []
    if fx:
        fx_rows.append(['USD/CNH', fmt(fx[-1][1], '{:.4f}'), fx[-1][0]])
        if len(fx) > 20:
            fx_change = (fx[-1][1] / fx[-21][1] - 1) * 100
            fx_rows.append(['20 个观测间隔变化', fmt(fx_change, '{:+.2f}', '%'), fx[-1][0]])
    xbody = '<p>人民币汇率独立连接盈利折算与资金配置两条路径。USD/CNH 上升表示离岸人民币对美元贬值。港股多以港元报价，人民币经营敞口与港元／美元融资敞口需要分别核对。</p>'
    xbody += metrics(['汇率观测', '数值', '数据日期'], fx_rows)
    xbody += metrics(['传导路径', '分析关系', '需要核对'], [
        ['盈利折算 → C → F', '人民币收入及利润折成港元时，人民币走弱可能压低折算值', '收入与成本币种、美元债务、对冲和财报列报币种'],
        ['资金配置 → G → H', '汇率预期与对冲成本可能改变境外投资者配置及内地资金偏好', '实际申赎、持仓与对冲成本变化'],
    ])
    xbody += '<p>汇率影响按企业净敞口与投资者计价币种判断。人民币对港元换算需要同步的美元／港元报价，当前展示的 USD/CNH 用于观察人民币方向。该路径为分析假设，强弱需要后续盈利和资金证据验证。</p>'
    if len(fx) > 1:
        xbody += chart([('USD/CNH', '#3478db', fx[-120:])], ylabel='每美元兑离岸人民币', fmt='{:.2f}')
    xbody += verdict(None, '汇率序列采用站内缓存并标注日期，净敞口和资金反应待核验，X 的方向评分待数据。')
    xbody += source('https://quote.eastmoney.com/forex/USDCNH.html', '东方财富离岸人民币行情')
    xbody += source('https://www.hkma.gov.hk/eng/key-functions/money/linked-exchange-rate-system/', '香港金管局联系汇率制度')
    sec += section('X', titles['X'], '人民币变化如何传导到盈利折算与资金偏好？', xbody, state='fx')
    sec+=section('E',titles['E'],'机构对同一目标年度的盈利预测如何修订？',verdict(None,'缺少带真实采集时间的港股一致预期历史，不计分。')+'<p>追踪国际及本地卖方覆盖、目标年度 EPS、上调／下调覆盖面和分歧度，保存真实采集时间，比较 30／90 天同口径修订。港股对机构预期的敏感程度要结合个股覆盖与市场反应验证。</p>')
    sec+=section('F',titles['F'],'价格里已经包含了多少增长或风险？',verdict(None,'港股指数 PE、PB、股息率及同口径历史尚未接入，不计分。')+
        '<p>从 E 的盈利预期出发，结合 D 的折现率与风险溢价、X 的汇率影响，分析愿意支付的估值。分别观察恒生、国企、恒生科技的 PE、PB、股息率及历史分位，并注明亏损成分处理规则。配对 A/H 折溢价需核对汇率、股息税、投资者准入与流动性。地缘风险溢价需要事件和市场数据支持。</p>'+source('https://www.hsi.com.hk/en-hk/indexes/all-indexes/index-details/?seriesCode=hsi','恒生指数公司'))
    latest=flows[-1] if flows else None
    frows=[]
    if latest:
        frows=[['南向买入成交',fmt(latest['buy'])+' 亿港元',latest['date']],['南向卖出成交',fmt(latest['sell'])+' 亿港元',latest['date']],['南向净买入',fmt(latest['net'],'{:+.2f}')+' 亿港元',latest['date']]]
    frows += [['近 5 个港股交易日合计',fmt(net5,'{:+.2f}',' 亿港元'),asof],['近 20 个港股交易日合计',fmt(net20,'{:+.2f}',' 亿港元'),asof]]
    participant_rows = [
        ['南向资金', '沪港通及深港通买卖成交', '已接入成交，持仓和持仓集中度待补'],
        ['境外与本地投资者', '基金申赎、机构配置、经纪及托管持仓', '申赎及可比持仓待接入，持仓身份需核验'],
        ['杠杆与情绪', '融资条件、沽空成交、借券、波动率与衍生品持仓', '待接入，沽空成交需结合对冲及做市活动解释'],
        ['交易约束', '互联互通资格与日历、卖空和借券规则、流动性与交易成本', '按参与者和证券核对适用规则及日期'],
    ]
    gbody = metrics(['参与者／约束', '观察内容', '证据状态'], participant_rows)
    gbody += metrics(['沪港通 + 深港通（南向）', '金额', '截至日期'], frows)
    gbody += verdict(None, '南向成交子项得分 '+fmt(flowscore, '{:+d}')+'。仓位、基金申赎、境外参与和交易约束待补齐，G 的综合状态待核验。')
    if len(flows)>1:
        # Align on actual observed connect dates; no zero fill or forward fill.
        gbody+=chart([('南向每日净买入（亿港元）','#B44F46',[(r['date'],r['net']) for r in flows[-30:]])],ylabel='南向净买入（亿港元）',bands=[(0,'零线')])
    gbody+=ctx['rules']('<p>净买入 = 沪港通南向买入成交 − 卖出成交 + 深港通南向买入成交 − 卖出成交。港交所原表单位为百万港元，除以 100 换算为亿港元；不使用每日额度余额。最近 5 个港股交易日均有双通道数据时，合计为正记 +1、为负记 −1、为零记 0；缺日、非互联互通交易日或缺一通道都暂不判定，不补零。20 日合计同理。</p>')
    gbody+=source(sb.get('source','https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily?sc_lang=en'),'港交所互联互通历史每日统计')
    gbody += source('https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Reference-Materials/Rules-and-Regulations?sc_lang=en', '港交所互联互通规则')
    sec += section('G', titles['G'], '哪些参与者正在增减仓，申赎与交易约束如何改变边际需求？', gbody)
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
    snapdir=root/'data/snapshots/hk_v2';snapdir.mkdir(parents=True,exist_ok=True)
    history=[]
    for p in snapdir.glob('*.json'):
        data=json.loads(p.read_text())
        if data['date']<asof:history.append(data)
    previous=max(history,key=lambda d:d['date']) if history else None
    labels = {key: titles[key] for key in 'ABCDEFGX'}
    cards = ''
    for key, label in labels.items():
        detail = '待核验 / 待数据'
        if key == 'D':
            detail = 'HIBOR 子项 ' + fmt(fundscore, '{:+d}')
        elif key == 'G':
            detail = '南向子项 ' + fmt(flowscore, '{:+d}')
        cards += f'<div class="hk-score"><span>{key} · {label}</span><strong class="na">综合待核验</strong><small>{E(detail)}</small></div>'
    daily=[]
    for key,rows in indices.items():daily.append(f'<li><b>{NAMES[key]}</b> 收于 {rows[-1]["close"]:,.2f}，较上一交易日 {change(rows,1):+.2f}%。</li>')
    if latest:daily.append(f'<li><b>南向资金</b> {latest["date"]} 净买入 {latest["net"]:+.2f} 亿港元。</li>')
    snapshot_note='本版框架首次记录，后续按同版本快照追踪分项变化。'
    if previous:
        changed=[f'{labels[k]}：{previous["scores"].get(k)} → {v}' for k,v in scores.items() if previous['scores'].get(k)!=v]
        snapshot_note='与上次有效记录 '+previous['date']+' 相比：'+('；'.join(changed) if changed else '分项状态未变')+'。缺失值表示待数据。'
    known = sum(value is not None for value in proxy_signals.values())
    signs = dict.fromkeys(titles, 'na')
    signs['X'] = 'fx'
    signs['H'] = 'price'
    notes = dict.fromkeys(titles, '待核验 / 待数据')
    notes.update({'A': '中国基本面 + 美国流动性', 'B': '内地 + 美联储 + 香港',
                  'D': 'HIBOR 子项 ' + fmt(fundscore, '{:+d}') + ' · 综合待核验',
                  'X': '盈利折算 + 资金偏好', 'G': '南向子项 ' + fmt(flowscore, '{:+d}') + ' · 综合待核验',
                  'H': '恒生 / 国企 / 恒生科技'})
    nodes = ''.join(f'<a href="#node-{key}" class="hk-node {signs[key]}"><b>{key}</b><span>{title}</span><small>{E(notes[key])}</small></a>' for key, title in titles.items())
    diagram = framework_diagram(titles, notes)
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
    body=f'<div class="hero"><p class="date">{asof} · 港股观察 · HK v2</p><h1>港股大盘处在什么状态</h1><p class="sum">中国基本面与美国流动性双重锚，叠加三层政策，追踪人民币汇率、企业盈利、估值与参与者行为。</p><p class="stamp">{stamp}</p></div>'
    if warnings:body+='<div class="hk-notice">'+''.join('<p>'+E(w)+'</p>' for w in warnings)+'</div>'
    body+='<section class="block" id="today"><h2>今天变了什么</h2><p class="sub">行情比较最近两个完整交易日；资金按自身最新披露日展示。</p><ul class="hk-changes">'+''.join(daily)+'</ul><p class="sub">'+E(snapshot_note)+'</p></section>'
    body+='<section class="block" id="map"><h2>传导图</h2><p class="sub">按参考框架展开 A–H，并增加独立的 X 人民币汇率节点。点击节点查看影响路径、指标和证据状态。</p>'+diagram+'<div class="hk-map">'+nodes+'</div><p class="sub">蓝色节点及箭头标出人民币的盈利折算与资金偏好路径。灰色虚线框表示综合判断待证据，深色 H 展示价格结果。图中箭头表示待验证的影响路径。</p></section>'
    body+=f'<section class="block" id="score"><h2>信号观察卡</h2><p class="sub">A–G 与 X 共八个分析节点，已接入 {known} 个可计算子项。D 的 HIBOR、G 的南向成交各自展示子项得分。综合判断等待其余证据，缺项单独标记，暂不合成总分。</p><div class="hk-scores">{cards}</div></section>'
    body+='<section class="block" id="nodes"><h2>逐项展开</h2><p class="sub">按 A / B / C / D / X / E / F / G / H 展开，分别列出已接入数据和待补证据。</p>'+sec+'</section>'
    body+='<section class="block" id="conds"><h2>港股关注条件</h2><p class="sub">触发仅提示补看证据，阈值可以调整。</p>'+metrics(['关注项','当前状态','判断依据'],conditions)+'</section>'
    (out/'index.html').write_text(page('港股大盘 | A 股框架笔记','hk',body,'../'),encoding='utf-8')
    snapshot={'date':asof,'observed_at':now.isoformat(),'rules_version':VERSION,'scores':scores,'proxy_signals':proxy_signals,'net5':net5,'net20':net20,'hibor_20obs_bp':delta,'sources':{k:rows[-1]['date'] for k,rows in indices.items()}}
    (snapdir/(asof+'.json')).write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
    print('built HK',asof,'valid dimensions',known)
