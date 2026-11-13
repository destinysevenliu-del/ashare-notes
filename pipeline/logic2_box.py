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
