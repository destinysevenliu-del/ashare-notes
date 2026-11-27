"""A股 · 分子 · 业绩反转（docs/stocks/a-turn.html）。
规则：财报确认单季利润同比由负转正、股价仍在26周均线下方、距一年高点回撤小于25%。
数据：data/raw/stock_pick/a_turn.json（浏览器取数与回测，口径见文件内 source、rules、backtest）。
与港股业绩反转不同：港股看机构预测上调、等股价站上均线；A股机构预测上调没有超额，财报确认的反转才有效，而且买还没涨的。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

BAND = 0.10   # 买入区：26周均线下方10%至26周均线
STOP = 0.12   # 止损：买入区中点下方12%与一年低点下方3%中较高者

# cand 列下标
C, N, IND, MC, PX, DD, V12, V26, R26, G0, G1, RPT, NOTICE, NPC, REVC, _X, PB, M12, M26, HI, LO = range(21)
ORDER = [('可执行', 'ab-buy', '行业传导、持续利润与估值均通过，价格在买入区'),
         ('价格到位·待核', 'ab-high', '价格在买入区，还要核对利润转正是否来自一次性收益'),
         ('等回落', 'ab-low', '价格已高于26周均线，市场已经反应'),
         ('不买', 'ab-sell', '跌破止损，或大盘转防守暂停新增')]


def load(root):
    p = Path(root)/'data/raw/stock_pick/a_turn.json'
    return json.loads(p.read_text()) if p.exists() else None


def levels(x):
    m26 = x[M26]; c = x[PX]
    b1, b2 = round(m26*(1-BAND), 2), round(m26, 2); mid = (b1+b2)/2
    stop = round(min(max(x[LO]*0.97, mid*(1-STOP)), b1*0.97), 2); sell = round(x[HI], 2)
    pl = {'close': c, 'buy': (b1, b2), 'sell': sell, 'stop': stop, 'rr': round((sell-mid)/(mid-stop), 1) if mid > stop else None,
          'rr_now': round((sell-c)/(c-stop), 1) if stop < c < sell else None}
    pl['where'] = ('已跌破止损价（按规则退出）' if c <= stop else '已在卖出区（到一年高点）' if c >= sell else '在买入区' if b1 <= c <= b2 else
                   '高于买入区' + format((c/b2-1)*100, '.0f') + '%' if c > b2 else '低于买入区' + format((1-c/b1)*100, '.0f') + '%')
    return pl


def raw_view(x, pl):
    s = SC.status(pl)[0]
    return {'买入': '价格到位·待核', '高于': '等回落', '低于': '价格到位·待核', '止损': '不买：已跌破止损', '卖出': '不买：已到卖出参考价'}.get(s, '观察')


def view(x, pl):
    v = raw_view(x, pl)
    if SP.DEFENSE.get('on') and not v.startswith('不买'):
        return '不买：大盘转防守，暂停新增'
    return '不买：待行业验证' if not v.startswith('不买') else v


def card(x):
    f = SP.f; pl = levels(x); v = view(x, pl); ps = SC.status(pl)[0]
    steps = [('板块', '待核', E(x[IND]) + '：财报反转是线索；需先补齐本行业从大盘需求、政策到订单利润的传导，通过后才入反转子池'),
             ('初筛', '通过', x[RPT][:7] + '单季利润同比' + f(x[G0], '+.0f', '%') + '（上一季' + f(x[G1], '+.0f', '%') + '），' + x[NOTICE] + '公告'),
             ('核验', '待核', '利润转正是否来自一次性收益（资产处置、补贴、公允价值变动）需看公告；累计利润同比' + f(x[NPC], '+.0f', '%') + '、营收同比' + f(x[REVC], '+.0f', '%')),
             ('估值', '待核', '市净率' + f(x[PB], '.2f') + '；五年估值分位未接入'),
             ('价格', {'买入': '到位', '高于': '未到', '低于': '到位', '止损': '跌破止损', '卖出': '到卖出价'}.get(ps, '待核'), pl['where'] + '；相对26周均线' + f(x[V26], '+.0f', '%')),
             ('筹码', '提示', '融资余额与股东户数变化待接入')]
    ly = [('反转', '好' if 0 < x[G0] < 30 else '中', E('单季利润同比 ' + f(x[G0], '+.0f', '%') + ' · 上一季 ' + f(x[G1], '+.0f', '%') + ' · 营收同比 ' + f(x[REVC], '+.0f', '%')), {'好': '温和转正', '中': '大幅转正'}),
          ('位置', '好' if x[V26] <= 0 and x[DD] > -25 else '差', E('相对26周均线 ' + f(x[V26], '+.0f', '%') + ' · 距一年高点 ' + f(x[DD], '.0f', '%')), {'好': '还没涨', '差': '已反应'})]
    note = '大盘转防守：规则上暂停新增，原状态为“' + raw_view(x, pl) + '”。' if v.startswith('不买：大盘') else ''
    return SC.card('t-' + x[C], x[N], x[C] + ' · ' + x[IND] + ' · 总市值' + format(x[MC], ',') + '亿', v, SP.VIEW_CLS(v), pl, ly,
                   SC.bar(x[LO], x[HI], pl['buy'], pl['sell'], pl['stop'], pl['close']), note, SP.chain_html({'steps': steps}))


def page(root):
    L = load(root)
    out = '<style>' + SP.CSS + SC.CSS + '</style>' + SP.head(6)
    if not L:
        return out + '<div class="hero"><h1>A股 · 分子 · 业绩反转</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']; rows = sorted(L['cand'], key=lambda x: -x[MC])
    out += ('<div class="hero"><h1>A股 · 分子 · 业绩反转</h1><p class="sum">' + E(R['def']) + '</p><p class="hero-meta">价格截至' + E(L['asof']) + '；最新财报为2026年三季报</p></div>')
    if L.get('update_note'):
        out += '<p class="note"><b>本次更新：</b>' + E(L['update_note']) + '</p>'
    out += '<nav class="lp-jump"><a href="#overview">行动看板</a><a href="#cards">候选</a><a href="#t-rules">规则</a><a href="#t-bt">回测</a></nav>'
    Bk = {}
    for x in rows:
        pl = levels(x); v = view(x, pl)
        Bk.setdefault('不买' if v.startswith('不买') else v, []).append(('t-' + x[C], x[N], x[IND] + ' · ' + raw_view(x, pl).split('：')[-1]))
    out += '<section id="overview"><h2>行动看板</h2><p class="note">' + E(R['status']) + '</p>' + SC.board(Bk, ORDER, '小字为不考虑大盘防守时的状态。') + '</section>'
    out += '<section id="cards"><h2>候选（' + str(len(rows)) + '只）</h2><p class="note">' + E(R['stock']) + '</p><div class="sc-grid">' + ''.join(card(x) for x in rows) + '</div></section>'
    out += ('<section id="t-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('定义', 'def'), ('上涨动力', 'drive'), ('候选范围', 'stock'), ('价格', 'price'), ('什么时候失效', 'fails'))) + '</dl></section>')
    tb = lambda cols, rs: ('<div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in cols) + '</tr></thead><tbody>' +
                           ''.join('<tr><th scope="row">' + E(r[0]) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in rs) + '</tbody></table></div>')
    out += ('<section id="t-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p>' + tb(B['cols'], B['rows']) + '<h3>本页规则逐个检验日</h3>' + tb(['检验日', '样本', '均值（%）', '中位数（%）', '跑赢比例（%）'], B['by_date']) +
            '<p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p><p class="note">' + E(L['source']) + '</p></section>')
    return out


def build(ctx):
    site = Path(ctx['SITE'])
    (site/'stocks/a-turn.html').write_text(ctx['page']('A股 · 业绩反转 | A 股框架笔记', 'gg', page(ctx['ROOT']), '../'), encoding='utf-8')
