"""港股 · 事件 · 回购与私有化（docs/stocks/hk-event.html）。
数据：data/raw/stock_pick/hk_event.json（东方财富港股回购日表＋南向持股周收盘，浏览器取数与回测）；
私有化逐单记录：data/raw/stock_pick/hk_privatization.json（人工维护：公告日、要约价、条件、时间表、结果）。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

BAND = 0.05   # 买入区：公司近13周回购均价上下5%
STOP = 0.15   # 止损：回购均价下方15%（公司自己都不买的价格以下）

# cand 列下标
C, N, IND, MC, PX, AMT, PCT, DAYS, LAST, AVG, DD, V26, SHORT, HI = range(14)
ORDER = [('价格到位·待核', 'ab-high', '回购持续、已站上26周均线、价格在公司回购均价附近'),
         ('等回落', 'ab-low', '价格高于回购均价5%以上'),
         ('观察', 'ab-wait', '未站上26周均线，或价格低于回购均价'),
         ('不买', 'ab-sell', '空头在增加，或价格低于公司回购均价15%以上')]
SHORT_TXT = {'low': ('提示', '空头占比低于3%，8周内没有上升'), 'fall': ('提示', '空头8周内下降（回补）'), 'rise': ('未通过', '空头8周内上升≥0.5个百分点'), 'high': ('未通过', '空头≥3%且没有下降')}


def load(root, fname='hk_event.json'):
    p = Path(root)/'data/raw/stock_pick'/fname
    return json.loads(p.read_text()) if p.exists() else None


def levels(x):
    a = x[AVG]; c = x[PX]
    if not a:
        return None
    b1, b2 = round(a*(1-BAND), 2), round(a*(1+BAND), 2); mid = (b1+b2)/2; stop = round(a*(1-STOP), 2); sell = round(x[HI], 2)
    pl = {'close': c, 'buy': (b1, b2), 'sell': sell, 'stop': stop, 'rr': round((sell-mid)/(mid-stop), 1) if sell > mid else None,
          'rr_now': round((sell-c)/(c-stop), 1) if stop < c < sell else None}
    pl['where'] = ('已跌破止损价（按规则退出）' if c <= stop else '已在卖出区（到一年高点）' if c >= sell else '在买入区' if b1 <= c <= b2 else
                   '高于买入区' + format((c/b2-1)*100, '.0f') + '%' if c > b2 else '低于买入区' + format((1-c/b1)*100, '.0f') + '%')
    return pl


def view(x, pl):
    if x[SHORT] in ('rise', 'high'):
        return '不买：空头在增加'
    s = SC.status(pl)[0]
    if x[V26] <= 0 and s not in ('止损', '卖出'):
        return '观察：未站上26周均线'
    return {'买入': '价格到位·待核', '高于': '等回落', '低于': '观察：低于回购均价', '止损': '不买：低于回购均价15%以上', '卖出': '不买：已到卖出参考价'}.get(s, '观察')


def bucket(v):
    for k in ('价格到位·待核', '等回落', '观察', '不买'):
        if v.startswith(k):
            return k
    return '观察'


def card(L, x):
    f = SP.f; pl = levels(x); v = view(x, pl); ps = SC.status(pl)[0]
    steps = [('板块', '提示', E(x[IND]) + '：回购逻辑不依赖板块档位，但板块逆风时回购只能托底、难以推动上涨'),
             ('初筛', '通过', '近13周回购' + f(x[AMT], '.1f') + '亿港元，占港股市值' + f(x[PCT], '.2f', '%') + '，' + str(x[DAYS]) + '个交易日有回购，最近一次' + x[LAST]),
             ('核验', '待核', '回购资金来自自由现金流还是借款、回购后是否注销、是否有未用完的回购授权，需逐家核对公告'),
             ('估值', '待核', '港股五年估值分位未接入'),
             ('价格', {'买入': '到位', '高于': '未到', '低于': '低于区间', '止损': '跌破止损', '卖出': '到卖出价'}.get(ps, '待核'), pl['where'] if pl else '—'),
             ('筹码', SHORT_TXT[x[SHORT]][0], SHORT_TXT[x[SHORT]][1])]
    ly = [('回购力度', '好' if x[PCT] >= 1 else '中', E('近13周回购占港股市值 ' + f(x[PCT], '.2f', '%') + ' · 回购均价 ' + f(x[AVG], '.2f') + ' · 回购天数 ' + str(x[DAYS])), {'好': '≥1%', '中': '0.5%—1%'}),
          ('位置', '好' if x[V26] > 0 else '中', E('相对26周均线 ' + f(x[V26], '+.0f', '%') + ' · 距一年高点 ' + f(x[DD], '.0f', '%')), {'好': '已站上', '中': '未站上'})]
    return SC.card('e-' + x[C], x[N], x[C] + ' · ' + x[IND] + ' · 港股市值' + format(x[MC], ',') + '亿', v, SP.VIEW_CLS(v), pl, ly,
                   SC.bar(None, x[HI], pl['buy'], pl['sell'], pl['stop'], pl['close']) if pl else '', '', SP.chain_html({'steps': steps}))


def page(root):
    L = load(root)
    out = '<style>' + SP.CSS + SC.CSS + '</style>' + SP.head(9)
    if not L:
        return out + '<div class="hero"><h1>港股 · 事件 · 回购与私有化</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']; rows = sorted(L['cand'], key=lambda x: -x[PCT])
    out += ('<div class="hero"><h1>港股 · 事件 · 回购与私有化</h1><p class="sum">' + E(R['def']) + '</p><p class="hero-meta">价格截至' + E(L['asof']) + '，回购数据截至' + E(L['bb_asof']) + '</p></div>')
    out += '<nav class="lp-jump"><a href="#overview">行动看板</a><a href="#cards">回购候选</a><a href="#priv">私有化</a><a href="#e-rules">规则</a><a href="#e-bt">回测</a></nav>'
    Bk = {}
    for x in rows:
        pl = levels(x); v = view(x, pl)
        Bk.setdefault(bucket(v), []).append(('e-' + x[C], x[N], format(x[PCT], '.2f') + '% · ' + v.split('：')[-1]))
    out += '<section id="overview"><h2>行动看板</h2><p class="note">' + E(R['status']) + '</p>' + SC.board(Bk, ORDER, '按近13周回购占市值排序。') + '</section>'
    out += '<section id="cards"><h2>回购候选（' + str(len(rows)) + '只）</h2><p class="note">' + E(R['universe']) + '</p><div class="sc-grid">' + ''.join(card(L, x) for x in rows) + '</div></section>'
    P = L.get('privatization') or []
    out += ('<section id="priv"><h2>私有化：逐单记录</h2><p class="note">' + E(R['priv']) + '</p>' +
            ('<div class="tblwrap"><table class="mt lp-table"><thead><tr><th>公司</th><th>公告日</th><th>要约价</th><th>现价</th><th>空间</th><th>条件与时间表</th><th>状态</th></tr></thead><tbody>' +
             ''.join('<tr><th scope="row">' + E(p['name']) + '<small>' + p['code'] + '</small></th><td>' + p['date'] + '</td><td>' + str(p['offer']) + '</td><td>' + str(p.get('px', '—')) + '</td><td>' +
                     (format((p['offer']/p['px']-1)*100, '+.1f') + '%' if p.get('px') else '—') + '</td><td>' + E(p['terms']) + '</td><td>' + E(p['status']) + '</td></tr>' for p in P) + '</tbody></table></div>'
             if P else '<p class="note">目前没有记录在册的私有化要约。东方财富数据中心没有港股私有化数据表，需要按港交所公告人工登记。</p>') + '</section>')
    out += ('<section id="e-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('定义', 'def'), ('上涨动力', 'drive'), ('候选范围', 'universe'), ('价格', 'price'), ('什么时候失效', 'fails'), ('私有化', 'priv'))) + '</dl></section>')
    out += ('<section id="e-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p><div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in B['cols']) +
            '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + E(r[0]) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in B['rows']) +
            '</tbody></table></div><p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p><p class="note">' + E(L['source']) + '</p></section>')
    return out


def build(ctx):
    site = Path(ctx['SITE'])
    (site/'stocks/hk-event.html').write_text(ctx['page']('港股 · 回购与私有化 | A 股框架笔记', 'gg', page(ctx['ROOT']), '../'), encoding='utf-8')
