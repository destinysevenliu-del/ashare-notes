"""港股逻辑二（业绩反转：预期上调＋空头未上升＋研究核验）与逻辑三（两地比价，只保留逻辑）的页面。
个股展示与A股、港股逻辑一同一格式：行动看板 → 个股卡片（现价、价格计划、位置条、判断链、分层判断）。
数据：data/raw/stock_pick/hk_logic2.json（浏览器执行 pipeline/weekly/hk_momentum.js 取数与回测，口径见文件内 source、rules、backtest）。
留档：hk_logic2_reversal_2026-11-25.json（财报拐点版）、hk_logic2_momentum_2026-11-26.json（动量版）。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

REV_MIN = 10       # 一致预期8周上调≥10%
MIN_ORGS = 2       # 至少2家机构（入选）
ORGS_OK = 3        # 少于3家：暂不纳入
MC_MIN = 100       # 港股市值≥100亿港元
BAND = 0.05        # 参考买入＝信号周收盘价上下5%
STOP = 0.15        # 止损＝买入区中点下方15%
RES_KEYS = (('反转动力', 'driver'), ('高频指标', 'hf'), ('可持续性', 'sustain'), ('证伪条件', 'falsify'))

# list 列下标
C, N, IND, MC, PX, DD, V12, V26, R26, REV, ORGS, F27, F27_OLD, F26, REV26 = range(15)

ORDER = [('可买', 'ab-buy', '数据信号、空头、研究四项都通过，高频指标已验证，价格在买入区'),
         ('研究待核', 'ab-high', '预期上调且空头未上升；研究卡已写，高频指标还没核对'),
         ('等回落', 'ab-low', '研究已通过，价格高于买入区'),
         ('暂不纳入', 'ab-bad', '覆盖机构太少或研究有保留意见'),
         ('观察：信号未出现', 'ab-wait', '有反转故事，但机构预测还没有上调')]


def load(root):
    p = Path(root)/'data/raw/stock_pick/hk_logic2.json'
    return json.loads(p.read_text()) if p.exists() else None


def levels(L, x):
    sig = L.get('signal', {}).get(x[C])
    if not sig:
        return None
    c = x[PX]; p0 = sig[1]; b1, b2 = round(p0*(1-BAND), 2), round(p0*(1+BAND), 2); mid = (b1+b2)/2
    hi = L.get('hi52', {}).get(x[C]); stop = round(mid*(1-STOP), 2)
    sell = hi if hi and hi > b2 else round(b2*1.3, 2)
    pl = {'close': c, 'buy': (b1, b2), 'sell': sell, 'stop': stop, 'hi': hi, 'sig': sig,
          'rr': round((sell-mid)/(mid-stop), 1), 'rr_now': round((sell-c)/(c-stop), 1) if stop < c < sell else None}
    pl['where'] = ('已跌破止损价（按规则退出）' if c <= stop else '已在卖出区（到一年高点）' if c >= sell else '在买入区' if b1 <= c <= b2 else
                   '高于买入区' + format((c/b2-1)*100, '.0f') + '%' if c > b2 else '低于买入区' + format((1-c/b1)*100, '.0f') + '%')
    return pl


def layers(L, x):
    r = L['research'].get(x[C], {}); s = L.get('short', {}).get(x[C])
    sig = '好' if x[REV] >= 20 and x[ORGS] >= 5 else ('中' if x[ORGS] >= ORGS_OK else '差')
    sh = '中' if s is None else ('好' if s[0] < 1.5 or s[1]-s[0] >= 0.5 else '中')
    pos = '好' if x[DD] <= -25 else ('中' if x[DD] <= -10 else '差')
    res = '差' if r.get('flag', '').startswith('只有') else '中'
    return {'sig': sig, 'short': sh, 'pos': pos, 'res': res, 'r': r, 's': s}


def verdict(x, res):
    """数据信号已满足；高频指标验证前最高只到“研究待核”。"""
    r = res.get(x[C], {})
    if r.get('flag', '').startswith('只有') or x[ORGS] < ORGS_OK:
        return '暂不纳入', 'bad'
    if not all(r.get(k) for _, k in RES_KEYS):
        return '研究未写', 'wait'
    if r.get('verified'):
        return '可买', 'go'
    return '研究待核', 'wait'


def chain(x, Y, pl, v):
    st = SC.status(pl)[0]
    steps = [('预期', '通过', ''), ('空头', '通过', ''), ('研究', '待核' if v != '暂不纳入' else '未通过', ''),
             ('价格', {'买入': '到位', '高于': '未到', '低于': '低于区间', '止损': '跌破止损', '卖出': '到卖出价'}.get(st, '待核'), '')]
    r = Y['r']
    out = '<ol class="ch">' + ''.join('<li class="ch-' + SP.STEP_CLS.get(b, 'chk') + '"><span>' + E(a) + '</span><b>' + E(b) + '</b></li>' for a, b, _ in steps) + '</ol>'
    out += '<dl class="ch-d">' + ''.join('<div><dt>' + k + '</dt><dd>' + E(r.get(key, '—')) + '</dd></div>' for k, key in RES_KEYS[1:]) + '</dl>'
    return out


def card(L, x):
    Y = layers(L, x); pl = levels(L, x); v, cls = verdict(x, L['research']); f = SP.f; s = Y['s']
    sig = '下一财年利润预测8周' + f(x[REV], '+.0f', '%') + '（' + str(x[ORGS]) + '家机构）：' + f(x[F27_OLD], '.1f') + ' → ' + f(x[F27], '.1f') + '亿元'
    sh = '证监会名单内无可报告淡仓' if s is None else '空头占港股股本 ' + f(s[0], '.2f', '%') + '（8周前 ' + f(s[1], '.2f', '%') + '）'
    pos = '距一年高点 ' + f(x[DD], '.0f', '%') + ' · 相对26周均线 ' + f(x[V26], '+.0f', '%') + ' · 26周涨跌 ' + f(x[R26], '+.0f', '%')
    ly = [('反转信号', Y['sig'], E(sig)), ('空头', Y['short'], E(sh), {'好': '低或回补', '中': '未上升'}),
          ('位置', Y['pos'], E(pos), {'好': '深跌后', '中': '中等回撤', '差': '近高点'}),
          ('研究', Y['res'], E(Y['r'].get('driver', '—')), {'中': '待核', '差': '有保留'})]
    bar = SC.bar(None, pl['hi'], pl['buy'], pl['sell'], pl['stop'], pl['close'], '一年低点', '一年高点') if pl else ''
    return SC.card('r-' + x[C], x[N], x[C] + ' · ' + x[IND] + ' · 港股市值' + format(x[MC], ',') + '亿', v, cls, pl, ly, bar, Y['r'].get('flag', ''), chain(x, Y, pl, v))


def page2(root):
    L = load(root)
    if not L or L.get('version') != 'revision':
        return SP.head(4) + '<div class="hero"><h1>港股 · 逻辑二 · 业绩反转</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']
    rows = sorted(L['list'], key=lambda x: -x[REV])
    out = '<style>' + SP.CSS + SC.CSS + CSS + '</style>' + SP.head(4)
    out += ('<div class="hero"><h1>港股 · 逻辑二 · 业绩反转</h1><p class="sum">找业绩正在反转、而且反转动力强、能持续的公司。港股由机构按盈利预期定价，等财报公布时反转往往已被交易完，'
            '所以这条逻辑用“机构上调盈利预测”提前发现反转，用“空头没有加仓”确认市场认可，再由人工写清反转动力、高频验证指标和证伪条件。格式与其他选股页相同：行动看板 → 个股卡片。'
            '价格截至' + E(L['asof']) + '，机构预测截至' + E(L['fc_asof']) + '，空头数据截至' + E(L['short_asof']) + '。</p></div>')
    out += '<nav class="lp-jump"><a href="#overview">行动看板</a><a href="#l2t-cards">逐只判断</a><a href="#l2t-rules">规则</a><a href="#l2t-bt">回测</a><a href="#l2t-old">旧版本</a></nav>'
    Bk = {}
    for x in rows:
        v, _ = verdict(x, L['research']); pl = levels(L, x)
        if v == '可买' and pl and SC.status(pl)[0] == '高于':
            v = '等回落'
        Bk.setdefault(v, []).append(('r-' + x[C], x[N], '预测' + format(x[REV], '+.0f') + '%'))
    for w in L.get('watch', []):
        Bk.setdefault('观察：信号未出现', []).append(('w-' + w['code'], w['name'], '预测' + format(w['rev'], '+.0f') + '%'))
    out += ('<section id="overview"><h2>行动看板</h2><p class="note">判断顺序：预期 → 空头 → 研究 → 价格。进入候选只表示值得研究；研究卡的高频指标核对通过之前，价格到了买入区也只是“研究待核”。' + E(R['status']) + '</p>' +
            SC.board(Bk, ORDER, '仓位：' + R['size']) + '</section>')
    out += ('<section id="l2t-cards"><h2>逐只判断</h2><p class="note">四层：反转信号看机构上调了多少、多少家覆盖；空头看专业资金是否认可；位置看是不是深跌后的反转；研究看反转动力。卡片下方是要核对的高频指标、可持续性和证伪条件。</p>'
            '<div class="sc-grid">' + ''.join(card(L, x) for x in rows) + '</div>')
    out += ''.join('<article class="sc" id="w-' + w['code'] + '"><header><div><b>' + E(w['name']) + '</b><small>' + w['code'] + ' · 观察</small></div><span class="lp-view wait">观察：信号未出现</span></header><p class="sc-note">距一年高点' +
                   format(w['dd'], '.0f') + '%，2027年预测8周变化' + format(w['rev'], '+.0f') + '%（' + str(w['n']) + '家机构）。' + E(w['note']) + '</p></article>' for w in L.get('watch', []))
    ex = '；'.join(E(n) + '（' + c + '，上调' + str(r) + '%）' for c, n, r in L['excluded'])
    out += '<p class="note"><b>预测上调但因空头条件剔除：</b>' + ex + '。</p></section>'
    out += ('<section id="l2t-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('候选范围', 'universe'), ('反转信号', 'signal'), ('空头', 'short'), ('研究核验', 'research'), ('价格', 'price'), ('退出', 'exit'), ('仓位', 'size'))) + '</dl></section>')
    P = B['pub']
    out += ('<section id="l2t-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p>' + bt_table(B['cols'], B['rows']) + '<h3>本页规则逐个检验日</h3>' + bt_table(B['by_date_cols'], B['by_date']) +
            '<p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p><h3>' + E(P['title']) + '</h3><p class="note">' + E(P['read']) + '</p>' + bt_table(B['cols'], P['rows']) + '</section>')
    O = L['reversal']; M = L['momentum']
    out += ('<section id="l2t-old"><h2>旧版本</h2><h3>' + E(M['title']) + '</h3><p class="note">' + E(M['read']) + '</p><h3>' + E(O['title']) + '</h3><p class="note">' + E(O['read']) + '</p>' +
            bt_table(B['cols'], O['rows']) + '<p class="note">' + E(L['source']) + '</p></section>')
    return out


def bt_table(cols, rows):
    return ('<div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in cols) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + E(str(r[0])) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in rows) +
            '</tbody></table></div>')


def page3(root):
    L = load(root) or {}
    g = L.get('logic3', {})
    out = '<style>' + SP.CSS + SC.CSS + CSS + '</style>' + SP.head(5)
    out += ('<div class="hero"><h1>港股 · 逻辑三 · ' + E(g.get('name', 'A股与H股比价')) + '</h1><p class="sum">' + E(g.get('status', '')) + '</p></div>'
            '<section><h2>规则</h2><div class="l2t-box"><p>' + E(g.get('rule', '')) + '</p></div><p class="note">高息资产（中资银行、电信）的板块判断仍在<a href="../boards/hk-telecom.html">港股板块页</a>。</p></section>')
    return out


def build(ctx):
    site = Path(ctx['SITE']); root = ctx['ROOT']
    (site/'stocks/hk-turn.html').write_text(ctx['page']('港股 · 业绩反转 | A 股框架笔记', 'gg', page2(root), '../'), encoding='utf-8')
    (site/'stocks/hk-ah.html').write_text(ctx['page']('港股 · 两地比价 | A 股框架笔记', 'gg', page3(root), '../'), encoding='utf-8')


CSS = """
.l2t-box{background:#f3f6f9;border-radius:10px;padding:14px 18px;margin:10px 0}.l2t-box p{font-size:14.5px;line-height:1.9;margin:4px 0}
"""
