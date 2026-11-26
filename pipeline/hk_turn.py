"""港股逻辑二（业绩反转：大盘 → 板块 → 个股的预测版）与逻辑三（两地比价，只保留逻辑）的页面。
个股卡片与港股逻辑一同一格式：现价、位置条、价格计划、判断链（板块、初筛、核验、估值、价格、筹码）、三层判断。
数据：data/raw/stock_pick/hk_logic2.json（version=predict；浏览器执行 pipeline/weekly/hk_momentum.js 取数与回测）。
留档：hk_logic2_reversal_2026-11-25.json、hk_logic2_momentum_2026-11-26.json、hk_logic2_revision_2026-11-26.json。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

BREADTH_MIN = 0.2   # 行业上调广度>0.2：行业盈利在反转
MC_MIN = 100        # 港股市值≥100亿港元
BAND = 0.08         # 买入区：26周均线至其上方8%
STOP = 0.08         # 止损：26周均线下方8%

# cand 列下标
C, N, IND, MC, PX, DD, V12, V26, R26, G0, G1, OWN, ORGS, SHORT = range(14)

ORDER = [('可执行', 'ab-buy', '板块、核验、估值都通过，价格在买入区'),
         ('价格到位·待核', 'ab-high', '已站上26周均线、在买入区，核验或估值还没完成，不直接买'),
         ('等回落', 'ab-high', '高于买入区上沿，等回到区间'),
         ('观察', 'ab-low', '行业在反转、利润还在谷底，股价没站上26周均线'),
         ('不买', 'ab-sell', '空头在增加，或已跌破止损')]
SHORT_TXT = {'na': ('中', 'A股没有可报告淡仓数据；融资余额变化待接入'), 'low': ('中', '空头占比低于3%，8周内没有上升'), 'fall': ('好', '空头8周内下降≥0.5个百分点（回补）'),
             'rise': ('差', '空头8周内上升≥0.5个百分点'), 'high': ('差', '空头≥3%且没有下降')}


def load(root, fname='hk_logic2.json'):
    p = Path(root)/'data/raw/stock_pick'/fname
    return json.loads(p.read_text()) if p.exists() else None


def turning(L):
    return [b for b in L['breadth'] if b[4] > BREADTH_MIN and b[1] >= 3]


def levels(L, x):
    m12, m26, hi, lo = L['px'][x[C]]; c = x[PX]
    b1, b2 = round(m26, 2), round(m26*(1+BAND), 2); mid = (b1+b2)/2; stop = round(m26*(1-STOP), 2); sell = round(hi, 2)
    pl = {'close': c, 'buy': (b1, b2), 'sell': sell, 'stop': stop, 'hi': hi, 'lo': lo, 'm12': m12, 'm26': m26,
          'rr': round((sell-mid)/(mid-stop), 1) if sell > mid else None, 'rr_now': round((sell-c)/(c-stop), 1) if b1 <= c < sell else None}
    if c < b1:
        pl['where'] = '未确认：需先站上26周均线（约' + format(b1, '.2f') + '）'
    elif c >= sell:
        pl['where'] = '已在卖出区（到一年高点）'
    elif c <= b2:
        pl['where'] = '在买入区'
    else:
        pl['where'] = '高于买入区' + format((c/b2-1)*100, '.0f') + '%'
    return pl


def view(x, pl):
    if x[SHORT] in ('rise', 'high'):
        return '不买：空头在增加'
    st = SC.status(pl)[0]
    return {'未确认': '观察：未站上26周均线', '买入': '价格到位·待核', '高于': '等回落', '卖出': '不买：已到卖出参考价'}.get(st, '观察')


def bucket(v):
    for k in ('价格到位·待核', '等回落', '不买', '观察'):
        if v.startswith(k):
            return k
    return '观察'


def chain(L, x, pl):
    f = SP.f; b = {r[0]: r for r in L['breadth']}[x[IND]]; r = L['research'].get(x[C], {}); F = L['fin'].get(x[C])
    st = SC.status(pl)[0]
    pe = x[PX]/F[3] if F and F[3] and F[3] > 0 else None
    pb = x[PX]/F[4] if F and F[4] else None
    steps = [('板块', '通过', '行业上调广度' + format(b[4], '+.2f') + '（' + str(b[1]) + '家有预测，' + str(b[2]) + '家上调、' + str(b[3]) + '家下调）。' + L['drivers'].get(x[IND], '')),
             ('初筛', '通过', '最近一期单期利润同比' + f(x[G0], '+.0f', '%') + '，利润仍在下降'),
             ('核验', '待核', '反转动力：' + r.get('driver', '—') + ' 高频指标：' + r.get('hf', '—') + ' 兑现条件（' + r.get('next', '下一份报告') + '）：' + r.get('cond', '—') + ' 证伪：' + r.get('falsify', '—')),
             ('估值', '待核', '市盈率（TTM）' + ('亏损' if pe is None else format(pe, '.1f') + '倍') + '、市净率' + ('—' if pb is None else format(pb, '.2f')) + '；港股五年估值分位未接入，正常化估值待验证'),
             ('价格', {'未确认': '未确认', '买入': '到位', '高于': '未到', '卖出': '到卖出价'}.get(st, '待核'), pl['where']),
             ('筹码', '未通过' if x[SHORT] in ('rise', 'high') else '提示', SHORT_TXT[x[SHORT]][1])]
    return SP.chain_html({'steps': steps})


def card(L, x):
    f = SP.f; pl = levels(L, x); v = view(x, pl); F = L['fin'].get(x[C]) or [None]*6; S = L.get('short', {})
    fund = ('最近一期单期利润同比 ' + f(x[G0], '+.0f', '%') + ' · 上一期 ' + f(x[G1], '+.0f', '%') + ' · ' + (F[0] or '—') + '累计利润同比 ' + f(F[1], '+.0f', '%') +
            ' · 营收同比 ' + f(F[2], '+.0f', '%') + ' · 下一财年预测8周 ' + ('无预测' if x[OWN] is None else f(x[OWN], '+.0f', '%')) + '（' + str(x[ORGS]) + '家）')
    pos = '相对26周均线 ' + f(x[V26], '+.0f', '%') + ' · 相对12周均线 ' + f(x[V12], '+.0f', '%') + ' · 26周涨跌 ' + f(x[R26], '+.0f', '%') + ' · 距一年高点 ' + f(x[DD], '.0f', '%')
    fs = '好' if (F[2] or 0) > 0 else '中'
    ly = [('初筛指标', fs, E(fund), {'好': '营收在增', '中': '营收未增'}),
          ('价格确认', '好' if x[V26] > 0 else '差', E(pos), {'好': '已站上', '差': '未站上'}),
          ('筹码', SHORT_TXT[x[SHORT]][0], E(SHORT_TXT[x[SHORT]][1]))]
    note = '覆盖机构只有' + str(x[ORGS]) + '家，研报最新一篇在8月，反转动力的信息不足。' if x[ORGS] < 3 else ''
    return SC.card('s-' + x[C], x[N], x[C] + ' · ' + x[IND], v, SP.VIEW_CLS(v), pl, ly,
                   SC.bar(pl['lo'], pl['hi'], pl['buy'], pl['sell'], pl['stop'], pl['close']), note, chain(L, x, pl))


def breadth_table(L):
    """反转中、被下调的行业直接列出；中性行业折叠。"""
    f = SP.f
    head = '<div class="tblwrap"><table class="mt ss-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in L['breadth_cols']) + '<th>判断</th></tr></thead><tbody>'
    def row(b):
        j = '反转中' if b[4] > BREADTH_MIN else ('被下调' if b[4] < -BREADTH_MIN else '中性')
        return ('<tr><th scope="row">' + E(b[0]) + '</th><td>' + str(b[1]) + '</td><td>' + str(b[2]) + '</td><td>' + str(b[3]) + '</td><td><b>' + format(b[4], '+.2f') + '</b></td><td>' + f(b[5], '+.1f') +
                '</td><td><small>' + E(b[6]) + '</small></td><td style="white-space:nowrap">' + j + '</td></tr>')
    key = [b for b in L['breadth'] if abs(b[4]) > BREADTH_MIN]
    mid = [b for b in L['breadth'] if abs(b[4]) <= BREADTH_MIN]
    out = head + ''.join(row(b) for b in key) + '</tbody></table></div>'
    if mid:
        out += '<details class="more"><summary>其余' + str(len(mid)) + '个行业（上调广度在±0.2以内，判断为中性）</summary>' + head + ''.join(row(b) for b in mid) + '</tbody></table></div></details>'
    return out


def page2(root):
    return render(load(root), 4, '港股', '港股大盘目前为下调状态，按总览页的港股仓位上限执行。', '行业为东方财富港股行业，样本为港股通可买的股票。')


def render(L, hid, mkt, market_note, uni_note):
    """A股、港股共用：大盘 → 板块 → 个股的业绩反转页。"""
    if not L or L.get('version') != 'predict':
        return SP.head(hid) + '<div class="hero"><h1>' + mkt + ' · 分子 · 业绩反转</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']
    out = '<style>' + SP.CSS + SC.CSS + CSS + '</style>' + SP.head(hid)
    out += ('<div class="hero"><h1>' + mkt + ' · 分子 · 业绩反转</h1><p class="sum">从大盘到板块到个股，预测哪些公司可能业绩反转：盈利周期正在反转的行业里，利润还在下降、反转尚未体现在财报里的公司；股价站上26周均线再买。</p><p class="hero-meta">价格截至' + E(L['asof']) + '，机构预测截至' + E(L['fc_asof']) + '，空头数据截至' + E(L['short_asof']) + '</p></div>')
    out += '<nav class="lp-jump"><a href="#overview">行动看板</a><a href="#sectors">板块：哪些行业在反转</a><a href="#logic2">按板块展开</a><a href="#l2t-rules">规则</a><a href="#l2t-bt">回测</a></nav>'
    cands = [x for x in L['cand'] if x[MC] >= MC_MIN]
    Bk = {}
    for x in cands:
        pl = levels(L, x); v = view(x, pl)
        Bk.setdefault(bucket(v), []).append(('s-' + x[C], x[N], x[IND] + ' · ' + v.split('：')[-1]))
    out += ('<section id="overview"><h2>行动看板</h2><p class="note">' + E(R['status']) + market_note + '</p>' +
            SC.board(Bk, ORDER, '价格截至' + L['asof'] + '；规则见本页“规则”。') + '</section>')
    out += ('<section id="sectors"><h2>板块：哪些行业的盈利在反转</h2><p class="note">' + E(R['sector']) + uni_note + '</p>' + breadth_table(L) + '</section>')
    out += '<section id="logic2"><h2>按板块展开</h2><p class="note">' + E(R['stock']) + '</p>'
    for b in turning(L):
        xs = [x for x in cands if x[IND] == b[0]]
        out += ('<details class="lp-sec" open><summary><span class="sec-h"><h3>' + E(b[0]) + '</h3><span class="lp-badge lp-' + SP.BADGE['顺风'] + '">反转中</span><span class="sec-meta">上调广度' +
                format(b[4], '+.2f') + ' · 候选' + str(len(xs)) + '只</span></span></summary><p class="sec-rule"><b>反转动力：</b>' + E(L['drivers'].get(b[0], '—')) + '<br><b>价格规则：</b>' + E(R['price']) + '</p>')
        out += ('<div class="sc-grid">' + ''.join(card(L, x) for x in xs) + '</div>') if xs else '<p class="note">本行业没有利润仍在下降的大市值公司：反转已经体现在财报里，不属于“预测反转”。</p>'
        out += '</details>'
    out += ('<article class="lp-sec"><h3>观察</h3>' + ''.join('<p><b>' + E(w['name']) + '（' + w['code'] + '）</b>：' + E(w['note']) + '</p>' for w in L.get('watch', [])) + '</article></section>')
    out += ('<section id="l2t-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('判断链', 'chain'), ('板块', 'sector'), ('个股', 'stock'), ('价格', 'price'), ('筹码', 'chip'), ('核验', 'verify'))) + '</dl></section>')
    out += ('<section id="l2t-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p>' + bt_table(B['cols'], B['rows']) + '<p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p><p class="note">' + E(B['rev_note']) +
            '</p><p class="note">' + E(L['source']) + '</p></section>')
    return out


def bt_table(cols, rows):
    return ('<div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in cols) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + E(str(r[0])) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in rows) +
            '</tbody></table></div>')


def page3(root):
    """旧链接：两地比价已并入港股红利高股息页。"""
    out = SP.head(8)
    out += ('<div class="hero"><h1>两地比价已并入“港股 · 分母 · 红利高股息”</h1><p class="sum">研究显示AH价差不会自动收敛，所以不单独作为选股逻辑，只用来比较同一家公司买A股还是H股股息更高。</p>'
            '<p><a href="hk-dividend.html#ah">去比较工具 →</a></p></div>')
    return out


def build(ctx):
    site = Path(ctx['SITE']); root = ctx['ROOT']
    (site/'stocks/hk-turn.html').write_text(ctx['page']('港股 · 业绩反转 | A 股框架笔记', 'gg', page2(root), '../'), encoding='utf-8')
    (site/'stocks/hk-ah.html').write_text(ctx['page']('港股 · 两地比价 | A 股框架笔记', 'gg', page3(root), '../'), encoding='utf-8')


CSS = """
.l2t-box{background:#f3f6f9;border-radius:10px;padding:14px 18px;margin:10px 0}.l2t-box p{font-size:14.5px;line-height:1.9;margin:4px 0}
"""
