"""分母 · 红利高股息（A股：docs/stocks/dividend.html；港股：docs/stocks/hk-dividend.html，含A股与H股比价工具）。
数据：data/raw/stock_pick/a_dividend.json、hk_dividend.json（浏览器取数与回测，口径见文件内 source、rules、backtest）。
卡片与其他选股页同一格式：判断链为板块、初筛、核验、估值、价格、筹码。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

BUY_SPREAD = 2.5    # 税后股息率≥10年国债+2.5个百分点：买入价
SELL_SPREAD = 2.0   # 税后股息率≤10年国债+2.0个百分点：卖出价
PAYOUT_MAX = 80     # 分红率上限（%），超过视为不可持续
NP_MIN = -10        # 最近一期利润同比下限（%）
OCF_MIN = 1.0       # 经营现金流覆盖（每股经营现金流÷每股收益）下限

# cand 列下标
C, N, IND, MC, PX, DPS, DY, DYN, PAY, NPY, OCF, PB, DPS0, V26, FLAG = range(15)

ORDER = [('可执行', 'ab-buy', '分红可持续、税后股息率达到买入线'),
         ('价格到位·待核', 'ab-high', '股息率达到买入线，分红可持续性还有缺项'),
         ('等回落', 'ab-low', '分红可持续，股息率还不够，等价格回落'),
         ('不买', 'ab-sell', '分红可持续性未通过、已到卖出价、板块拥挤或大盘转防守')]


def load(root, fname):
    p = Path(root)/'data/raw/stock_pick'/fname
    return json.loads(p.read_text()) if p.exists() else None


def verify(x):
    """分红可持续性：分红率、利润同比、经营现金流覆盖。返回（状态，原因）。"""
    bad, miss = [], []
    fin = any(k in str(x[IND]) for k in ('银行', '保险', '证券', '金融'))  # 金融企业经营现金流含存贷款与客户资金变动，不用覆盖倍数
    checks = [(x[PAY], lambda v: 0 < v <= PAYOUT_MAX, '分红率'), (x[NPY], lambda v: v >= NP_MIN, '利润同比')]
    if not fin:
        checks.append((x[OCF], lambda v: v >= OCF_MIN, '经营现金流覆盖'))
    for v, ok, lab in checks:
        if v is None:
            miss.append(lab)
        elif not ok(v):
            bad.append(lab)
    if bad:
        return '未通过', '、'.join(bad) + '不达标'
    if miss:
        return '待核', '、'.join(miss) + '缺数据'
    return '通过', '分红率、利润同比、经营现金流覆盖都达标'


def levels(L, x):
    tax = L.get('tax', 0); y = L['cn10y']
    net = x[DPS]*(1-tax)
    if not net:
        return None
    b = net/((y+BUY_SPREAD)/100); s = net/((y+SELL_SPREAD)/100); c = x[PX]
    pl = {'close': c, 'buy': (round(b*0.97, 2), round(b, 2)), 'sell': round(s, 2), 'stop': None, 'rr': None, 'rr_now': None}
    pl['where'] = '已在卖出区（股息率不足）' if c >= s else ('在买入区（股息率达标）' if c <= b else '等待：高于买入价' + format((c/b-1)*100, '.0f') + '%')
    return pl


def view(L, x, pl):
    st, _ = verify(x)
    if x[FLAG] == 'pause':
        return '不买：板块拥挤，暂停新增'
    if x[FLAG] in ('rise', 'high'):
        return '不买：空头在增加'
    if st == '未通过':
        return '不买：分红可持续性未通过'
    if L['market'] == 'a' and SP.DEFENSE.get('on'):
        return '不买：大盘转防守，暂停新增'
    s = SC.status(pl)[0]
    if s == '卖出':
        return '不买：已到卖出参考价'
    if s == '买入':
        return '可执行' if st == '通过' else '价格到位·待核'
    return '等回落'


def bucket(v):
    for k in ('可执行', '价格到位·待核', '等回落'):
        if v.startswith(k):
            return k
    return '不买'


def chain(L, x, pl, v):
    f = SP.f; st, why = verify(x); ps = SC.status(pl)[0]
    chip = {'rise': ('未通过', '空头8周内上升≥0.5个百分点'), 'high': ('未通过', '空头≥3%且没有下降'), 'pause': ('提示', '板块成交拥挤，暂停新增'),
            'na': ('提示', 'A股没有可报告淡仓数据')}.get(x[FLAG], ('提示', '空头占比低或在回补'))
    steps = [('板块', '暂停' if x[FLAG] == 'pause' else '通过', E(x[IND]) + ('：成交拥挤度超过上限，暂停新增' if x[FLAG] == 'pause' else '')),
             ('初筛', '通过', '税后股息率' + f(x[DYN], '.2f', '%') + '，市值' + format(x[MC], ',') + '亿'),
             ('核验', st, why + '（分红率' + f(x[PAY], '.0f', '%') + '、利润同比' + f(x[NPY], '+.0f', '%') + '、经营现金流覆盖' + f(x[OCF], '.1f') + '倍）'),
             ('估值', '通过', '市净率' + f(x[PB], '.2f') + '；红利股的估值就是股息率，价格规则已按股息率定'),
             ('价格', {'买入': '到位', '高于': '未到', '卖出': '到卖出价'}.get(ps, '待核'), pl['where'] if pl else '—'),
             ('筹码', chip[0], chip[1])]
    return SP.chain_html({'steps': steps})


def card(L, x):
    f = SP.f; pl = levels(L, x); v = view(L, x, pl); st, _ = verify(x)
    tax = L.get('tax', 0)
    fund = ('每股分红（近12个月）' + f(x[DPS], '.3f') + ' · 股息率' + f(x[DY], '.2f', '%') + ('（税后' + f(x[DYN], '.2f', '%') + '）' if tax else '') +
            ' · 上一年度每股分红' + f(x[DPS0], '.3f') + ' · 分红率' + f(x[PAY], '.0f', '%'))
    sus = '利润同比' + f(x[NPY], '+.0f', '%') + ' · 经营现金流覆盖' + f(x[OCF], '.1f') + '倍 · 市净率' + f(x[PB], '.2f') + ' · 相对26周均线' + f(x[V26], '+.0f', '%')
    ly = [('股息', '好' if (x[DYN] or 0) >= L['cn10y'] + BUY_SPREAD else '中', E(fund), {'好': '达买入线', '中': '未达'}),
          ('可持续', {'通过': '好', '待核': '中', '未通过': '差'}[st], E(sus), {'好': '通过', '中': '待核', '差': '未通过'})]
    note = '分红比上一年度减少，需确认原因。' if x[DPS0] and x[DPS] < x[DPS0]*0.9 else ''
    return SC.card('d-' + x[C], x[N], x[C] + ' · ' + x[IND], v, SP.VIEW_CLS(v), pl, ly, '', note, chain(L, x, pl, v))


def ah_table(L):
    A = L.get('ah') or []
    if not A:
        return ''
    f = SP.f
    out = ('<section id="ah"><h2>工具：同一公司买A股还是H股</h2><p class="note">' + E(L['ah_note']) + '</p><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>公司</th><th>H股税后股息率</th><th>A股股息率（持有满一年免税）</th>'
           '<th>H股相对A股折价</th><th>更划算</th></tr></thead><tbody>')
    for a in A:
        out += ('<tr><th scope="row">' + E(a[1]) + '<small>H ' + a[0] + ' · A ' + a[2] + '</small></th><td>' + f(a[3], '.2f', '%') + '</td><td>' + f(a[4], '.2f', '%') + '</td><td>' + f(a[5], '.0f', '%') +
                '</td><td><b>' + ('H股' if a[3] > a[4] else 'A股') + '</b></td></tr>')
    return out + '</tbody></table></div></section>'


def render(L, hid, mkt):
    if not L:
        return SP.head(hid) + '<div class="hero"><h1>' + mkt + ' · 分母 · 红利高股息</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']
    rows = sorted(L['cand'], key=lambda x: -(x[DYN] or 0))
    out = '<style>' + SP.CSS + SC.CSS + '</style>' + SP.head(hid)
    out += ('<div class="hero"><h1>' + mkt + ' · 分母 · 红利高股息</h1><p class="sum">' + E(R['def']) + '</p><p class="hero-meta">价格截至' + E(L['asof']) + '；10年国债' + format(L['cn10y'], '.2f') +
            '%；买入线＝税后股息率≥国债+' + format(BUY_SPREAD, '.1f') + '个百分点，卖出线＝国债+' + format(SELL_SPREAD, '.1f') + '个百分点</p></div>')
    out += '<nav class="lp-jump"><a href="#overview">行动看板</a><a href="#cards">按行业展开</a>' + ('<a href="#ah">买A还是买H</a>' if L.get('ah') else '') + '<a href="#d-rules">规则</a><a href="#d-bt">回测</a></nav>'
    Bk = {}
    for x in rows:
        if verify(x)[0] == '未通过':
            continue
        pl = levels(L, x); v = view(L, x, pl)
        why = v.split('：')[-1].replace('板块拥挤，暂停新增', '拥挤暂停').replace('大盘转防守，暂停新增', '大盘防守') if v.startswith('不买') else ''
        Bk.setdefault(bucket(v), []).append(('d-' + x[C], x[N], format(x[DYN] or 0, '.1f') + '% · ' + (why + '，' if why else '') + SC.status(pl)[1].replace('（股息率达标）', '').replace('（股息率不足）', '')))
    out += ('<section id="overview"><h2>行动看板</h2><p class="note">' + E(R['status']) + '</p>' + SC.board(Bk, ORDER, '按税后股息率排序；小字为股息率、不买的原因和价格状态。价格截至' + L['asof'] + '。') + '</section>')
    bad = [x for x in rows if verify(x)[0] == '未通过']
    rows = [x for x in rows if verify(x)[0] != '未通过']
    out += '<section id="cards"><h2>按行业展开（' + str(len(rows)) + '只）</h2><p class="note">' + E(R['universe']) + '分红可持续性未通过的' + str(len(bad)) + '只不展开，列在本节末尾。</p>'
    inds = []
    for x in rows:
        if x[IND] not in inds:
            inds.append(x[IND])
    for ind in inds:
        xs = [x for x in rows if x[IND] == ind]
        out += ('<details class="lp-sec" open><summary><span class="sec-h"><h3>' + E(ind) + '</h3><span class="sec-meta">' + str(len(xs)) + '只 · 税后股息率' +
                format(min(x[DYN] for x in xs), '.1f') + '%—' + format(max(x[DYN] for x in xs), '.1f') + '%</span></span></summary><div class="sc-grid">' + ''.join(card(L, x) for x in xs) + '</div></details>')
    if bad:
        out += ('<details class="more"><summary>分红可持续性未通过的' + str(len(bad)) + '只</summary><p class="note">' +
                '；'.join(E(x[N]) + '（' + E(verify(x)[1]) + '）' for x in bad) + '</p></details>')
    out += '</section>' + ah_table(L)
    out += ('<section id="d-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('定义', 'def'), ('上涨动力', 'drive'), ('候选范围', 'universe'), ('可持续性', 'verify'), ('价格', 'price'), ('什么时候失效', 'fails'))) + '</dl></section>')
    out += ('<section id="d-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p><div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in B['cols']) +
            '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + E(r[0]) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in B['rows']) +
            '</tbody></table></div><p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p><p class="note">' + E(L['source']) + '</p></section>')
    return out


def build(ctx):
    site = Path(ctx['SITE']); root = ctx['ROOT']
    (site/'stocks/dividend.html').write_text(ctx['page']('A股 · 红利高股息 | A 股框架笔记', 'gg', render(load(root, 'a_dividend.json'), 7, 'A股'), '../'), encoding='utf-8')
    (site/'stocks/hk-dividend.html').write_text(ctx['page']('港股 · 红利高股息 | A 股框架笔记', 'gg', render(load(root, 'hk_dividend.json'), 8, '港股'), '../'), encoding='utf-8')
