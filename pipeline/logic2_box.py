"""Logic 2: 国资箱体 (SOE range-bound small caps with event spikes). Pure functions; identical to the browser computation used on 2026-11-13.
Input series: list of [date, change_rate_pct] ascending (前复权近似：用每日涨跌幅连乘得到调整价格)."""
import math

GENERIC={'融资融券','沪股通','深股通','标准普尔','富时罗素','MSCI中国','小盘股','中盘股','大盘股','低价股','小盘成长','小盘价值','中盘成长','中盘价值','超跌股','基金增仓','连续亏损','预盈预增','预亏预减','QFII重仓','社保重仓','机构重仓','证金持股','汇金持股','央国企改革','创业板综','深成500','上证380','上证180_','HS300_','中证500','茅指数','破净股','高送转','股权激励','养老金','次新股','注册制次新股','长江三角','京津冀','成渝特区','粤港自贸','深圳特区','上海自贸','西部大开发','东北振兴','雄安新区','海峡西岸','湖北自贸','长株潭'}

# 入选条件（全部可量化）
RULES={
 'universe':'东方财富标签含“央国企改革”的A股；总市值15亿—120亿；非ST；PB>0（净资产为正）；剔除北交所',
 'box':'近两年调整价格的10%分位为箱底L、90%分位为箱顶H；箱体宽度H/L−1在25%—120%之间',
 'flat':'最近60日均价相对最早60日均价的对数变化绝对值≤0.30（没有单边趋势）',
 'swings':'价格在“箱底20%区”与“箱顶20%区”之间至少来回2次',
 'floor':'两年最低价不低于箱底15%以上（地板有效）',
 'hot':'两年内涨停≥4次，且至少1次10个交易日内上涨≥30%（有事件脉冲）',
 'holders':'最近一期股东户数低于5万户（公告日不晚于筛选日；2026-11-19起加入，未回测）',
}
ACTIONS={'buy':'位置在0—0.25（箱底区）','sell':'位置≥0.8（箱顶区），或单次脉冲上涨≥30%时兑现','stop':'收盘跌破箱底15%，视为箱体失效','switch':'暂停条件：中证全指收盘跌破4,700（首页命题P4，托底失效）时不开新仓'}

def q(xs,p):
    s=sorted(xs);return s[min(len(s)-1,int(p*(len(s)-1)))]

def adjusted(series):
    a=[1.0]
    for _,c in series[1:]:a.append(a[-1]*(1+((c or 0) if c==c else 0)/100))
    return a

def metrics(code,series,limit=None):
    if len(series)<420:return None
    a=adjusted(series);n=len(a);L,H=q(a,.1),q(a,.9);W=H/L-1
    m=lambda s,e:sum(a[s:e])/(e-s);trend=math.log(m(n-60,n)/m(0,60))
    bz,tz=L+.2*(H-L),H-.2*(H-L);st=sw=0
    for x in a:
        z=-1 if x<=bz else 1 if x>=tz else 0
        if z and z!=st:
            if st:sw+=1
            st=z
    lim=limit or (19.6 if code.startswith(('300','301','688')) else 9.8)
    lu=sum(1 for _,c in series if c is not None and c>=lim);sp=0;i=0
    while i<n-10:
        if max(a[j]/a[i]-1 for j in range(i+1,i+11))>=.3:sp+=1;i+=21
        else:i+=1
    return {'W':round(W,2),'trend':round(trend,2),'swings':sw,'floor':round(min(a)/L-1,2),'lu':lu,'sp':sp,'pos':round((a[-1]-L)/(H-L),2)}

def qualifies(x):
    return .25<=x['W']<=1.2 and abs(x['trend'])<=.3 and x['swings']>=2 and x['floor']>=-.15 and x['lu']>=4 and x['sp']>=1

# ---------- 2026-11-16：逐只判断（基本面、位置、筹码、箱体质量） ----------
# 箱体股赚的是“地板附近买、天花板附近卖、遇到烟花兑现”的钱，所以四层看的东西和逻辑一不同：
# 基本面看“地板结不结实”，位置看“离箱底多近”，筹码看“谁在里面、会不会有人砸”，箱体质量看“过去烟花放得勤不勤”。
# 这些是研究规则（未单独回测）；组合回测只验证了“箱底买、箱顶卖”的整体规则，单只判断用来排除和排优先级，不用来预测单只涨跌。
L2_LENS={
 'fund':('地板结不结实','地板来自净资产、国资背景和不退市。三条红线任一触发为“差”：①亏损且年化营收低于3亿（财务类退市标准）；②前三季加权ROE≤−10%（一年内净资产被亏掉一成以上，地板在下移）；③每股净资产低于0.5元。“好”＝前三季盈利、PB≤2.5、每股经营现金流不为负；其余为“中”。'),
 'pos':('离箱底多近','箱体位置0—0.25为“好”（买入区）；0.25—0.5或低于箱底但在止损线上方为“中”（等回到买入区或等收回箱底）；高于0.5或跌破止损线为“差”。'),
 'chip':('谁在里面','股东户数不增、融资余额20日增幅不超过10%、未来6个月解禁低于5%为“好”（筹码没有分散、没有杠杆追入、没有解禁砸盘）；户数增加≥15%（散户大量涌入）、融资20日增幅≥30%或6个月解禁≥5%任一为“差”；其余为“中”。'),
 'box':('烟花放得勤不勤','两年内往返≥4次且脉冲≥2次为“好”；满足入选门槛（往返≥2次、脉冲≥1次）为“中”。'),
 'view':'先看暂停条件（中证全指＜4,700不开新仓）；基本面“差”的剔出组合；位置不在买入区的等；在买入区的，筹码“差”只观察，其余按“基本面、筹码、箱体质量”中“好”的个数排序：两个以上为“优先”，否则为“备选”。组合按回测规则分散持有（上限20只、等权），单只不重仓。',
}

def judge(x, fund, en, switch_on):
    """返回 {'fund','pos','chip','box','view','why'}；fund 为 l2_fund.json 中该股记录，en 为每周筹码数据。"""
    why = []
    q = (fund or {}).get('q3') or {}
    if not q:
        f = '中'; why.append('缺少财报数据')
    else:
        red = []
        if q['np_m'] < 0 and q['rev_m'] * 4 / 3 < 300: red.append('亏损且年化营收不足3亿')
        if q['roe'] is not None and q['roe'] <= -10: red.append('前三季ROE %.1f%%，净资产在快速缩水' % q['roe'])
        if q['bps'] is not None and q['bps'] < 0.5: red.append('每股净资产仅%.2f元' % q['bps'])
        if red: f = '差'; why += red
        elif q['np_m'] > 0 and fund['pb'] <= 2.5 and (q['cfps'] or 0) >= 0: f = '好'; why.append('前三季盈利%.2f亿、PB %.2f，地板有净资产支撑' % (q['np_m'] / 100, fund['pb']))
        else:
            f = '中'
            if q['np_m'] < 0: why.append('前三季亏损%.2f亿' % (-q['np_m'] / 100))
            if fund['pb'] > 2.5: why.append('PB %.1f，净资产对价格的支撑弱' % fund['pb'])
            if (q['cfps'] or 0) < 0: why.append('经营现金流为负')
    p = x['pos']; W = x['W']; stop_pos = -0.15 / W
    if 0 <= p <= 0.25: ps = '好'
    elif p <= stop_pos or p > 0.5: ps = '差'; why.append('已跌破止损线' if p <= stop_pos else '位置偏高（%.2f）' % p)
    else: ps = '中'; why.append('低于箱底，等收回' if p < 0 else '在箱体中部，等回到买入区')
    hc = (en or {}).get('holdersChg'); m20 = (en or {}).get('margin20'); lf = (en or {}).get('lift6m') or 0
    bad = []
    if hc is not None and hc >= 15: bad.append('股东户数增加%.0f%%' % hc)
    if m20 is not None and m20 >= 30: bad.append('融资20日增%.0f%%' % m20)
    if lf >= 5: bad.append('6个月内解禁%.1f%%' % lf)
    if bad: c = '差'; why += bad
    elif (hc is None or hc <= 0) and (m20 is None or m20 <= 10): c = '好'
    else:
        c = '中'
        if hc is not None and hc > 0: why.append('股东户数增加%.0f%%' % hc)
        if m20 is not None and m20 > 10: why.append('融资20日增%.0f%%' % m20)
    b = '好' if x['swings'] >= 4 and x['sp'] >= 2 else '中'
    if b == '好': why.append('两年往返%d次、脉冲%d次' % (x['swings'], x['sp']))
    if not switch_on: v = '暂停开新仓'
    elif f == '差': v = '剔除：地板不牢'
    elif ps == '差': v = '已破位，不接' if p <= stop_pos else '等回落'
    elif ps == '中': v = '等收回箱底' if p < 0 else '等回到买入区'
    elif c == '差': v = '观察：筹码不稳'
    else: v = '优先' if [f, c, b].count('好') >= 2 else '备选'
    return {'fund': f, 'pos': ps, 'chip': c, 'box': b, 'view': v, 'why': '；'.join(why)}
