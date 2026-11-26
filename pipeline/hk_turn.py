"""港股逻辑二（业绩反转：预期上调＋空头未上升＋研究核验）与逻辑三（两地比价，只保留逻辑）的页面。
数据：data/raw/stock_pick/hk_logic2.json（浏览器执行 pipeline/weekly/hk_momentum.js 取数与回测，口径见文件内 source、rules、backtest）。
留档：hk_logic2_reversal_2026-11-25.json（财报拐点版）、hk_logic2_momentum_2026-11-26.json（动量版）。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

REV_MIN = 10       # 一致预期8周上调≥10%
MIN_ORGS = 2       # 至少2家机构
MC_MIN = 100       # 港股市值≥100亿港元
RES_KEYS = (('反转动力', 'driver'), ('高频指标', 'hf'), ('可持续性', 'sustain'), ('证伪条件', 'falsify'))

# list 列下标
C, N, IND, MC, PX, DD, V12, V26, R26, REV, ORGS, F27, F27_OLD, F26, REV26 = range(15)


def load(root):
    p = Path(root)/'data/raw/stock_pick/hk_logic2.json'
    return json.loads(p.read_text()) if p.exists() else None


def verdict(x, res):
    """数据信号已满足；研究层四项写清且没有保留意见，仍需验证高频指标，所以最高到“研究待核”。"""
    r = res.get(x[C], {})
    if r.get('flag', '').startswith('只有') or x[ORGS] < 3:
        return '暂不纳入：覆盖不足', 'bad'
    if not all(r.get(k) for _, k in RES_KEYS):
        return '研究未写', 'wait'
    return '候选：研究待核', 'wait'


def table(L):
    f = SP.f; res = L['research']
    out = ('<div class="tblwrap"><table class="mt lp-table l2t-table"><thead><tr><th>股票</th><th>港股市值<br>（亿港元）</th><th>距一年高点</th><th>相对26周均线</th>'
           '<th>下一财年利润预测<br>8周上调</th><th>覆盖机构</th><th>预测：8周前 → 现在<br><small>亿元，报告货币</small></th><th>判断</th></tr></thead><tbody>')
    for x in L['list']:
        v, cls = verdict(x, res)
        out += ('<tr><th scope="row"><a href="#r-' + x[C] + '">' + E(x[N]) + '</a><small>' + x[C] + ' · ' + E(x[IND]) + '</small></th><td>' + format(x[MC], ',') + '</td><td>' + f(x[DD], '.0f', '%') + '</td><td>' + f(x[V26], '+.0f', '%') +
                '</td><td><b>' + f(x[REV], '+.0f', '%') + '</b></td><td>' + str(x[ORGS]) + '</td><td>' + f(x[F27_OLD], '.1f') + ' → ' + f(x[F27], '.1f') + '</td><td><span class="lp-view ' + cls + '">' + E(v) + '</span></td></tr>')
    return out + '</tbody></table></div>'


def cards(L):
    res = L['research']; out = '<div class="l2r-grid">'
    for x in L['list']:
        r = res.get(x[C], {}); v, cls = verdict(x, res)
        out += ('<article class="l2r-card" id="r-' + x[C] + '"><h3>' + E(x[N]) + ' <small>' + x[C] + '</small> <span class="lp-view ' + cls + '">' + E(v) + '</span></h3><dl>' +
                ''.join('<dt>' + k + '</dt><dd>' + E(r.get(key, '—')) + '</dd>' for k, key in RES_KEYS) + '</dl>' +
                ('<p class="l2r-flag">' + E(r['flag']) + '</p>' if r.get('flag') else '') + '</article>')
    return out + '</div>'


def bt_table(cols, rows):
    return ('<div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in cols) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + E(str(r[0])) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in rows) +
            '</tbody></table></div>')


def page2(root):
    L = load(root)
    if not L or L.get('version') != 'revision':
        return SP.head(4) + '<div class="hero"><h1>港股 · 逻辑二 · 业绩反转</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']; f = SP.f
    out = '<style>' + SP.CSS + SC.CSS + CSS + '</style>' + SP.head(4)
    out += ('<div class="hero"><h1>港股 · 逻辑二 · 业绩反转</h1><p class="sum">找业绩正在反转、而且反转动力强、能持续的公司。港股由机构按盈利预期定价，等财报公布时反转往往已被交易完，'
            '所以这条逻辑用“机构上调盈利预测”提前发现反转，用“空头没有加仓”确认市场认可，再由人工写清反转动力、高频验证指标和证伪条件。价格截至' + E(L['asof']) +
            '，机构预测截至' + E(L['fc_asof']) + '，空头数据截至' + E(L['short_asof']) + '。</p></div>')
    out += '<nav class="lp-jump"><a href="#l2t-status">结论</a><a href="#l2t-list">候选</a><a href="#l2t-research">研究卡</a><a href="#l2t-watch">观察</a><a href="#l2t-rules">规则</a><a href="#l2t-bt">回测</a><a href="#l2t-old">旧版本</a></nav>'
    out += ('<section id="l2t-status"><h2>结论</h2><div class="l2t-box"><p><b>状态：</b>' + E(R['status']) + '</p><p><b>当前：</b>' + str(len(L['list'])) +
            '只满足数据信号，全部处于“研究待核”或“暂不纳入”：研究卡的内容摘自机构研报标题，高频指标还没有逐一验证，验证通过才可买。</p><p><b>仓位：</b>' + E(R['size']) + '</p></div></section>')
    out += ('<section id="l2t-list"><h2>候选（' + str(len(L['list'])) + '只）</h2><p class="note">按预测上调幅度排序。“下一财年”指2027年（阿里巴巴为截至2027年3月的财年）。</p>' + table(L))
    ex = '；'.join(E(n) + '（' + c + '，上调' + str(r) + '%）' for c, n, r in L['excluded'])
    out += '<p class="note"><b>预测上调但因空头条件剔除：</b>' + ex + '。</p></section>'
    out += '<section id="l2t-research"><h2>研究卡</h2><p class="note">每只写清四项。“高频指标”就是下一步要核对的数字。</p>' + cards(L) + '</section>'
    out += ('<section id="l2t-watch"><h2>观察：有反转故事、数据信号未出现</h2><ul class="lens-ul">' + ''.join('<li><b>' + E(w['name']) + '（' + w['code'] + '）</b>：距一年高点' + format(w['dd'], '.0f') + '%，2027年预测8周变化' +
            format(w['rev'], '+.0f') + '%（' + str(w['n']) + '家机构）。' + E(w['note']) + '</li>' for w in L['watch']) + '</ul></section>')
    out += ('<section id="l2t-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('候选范围', 'universe'), ('反转信号', 'signal'), ('空头', 'short'), ('研究核验', 'research'), ('退出', 'exit'), ('仓位', 'size'))) + '</dl></section>')
    P = B['pub']
    out += ('<section id="l2t-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p>' + bt_table(B['cols'], B['rows']) + '<h3>本页规则逐个检验日</h3>' + bt_table(B['by_date_cols'], B['by_date']) +
            '<p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p><h3>' + E(P['title']) + '</h3><p class="note">' + E(P['read']) + '</p>' + bt_table(B['cols'], P['rows']) + '</section>')
    O = L['reversal']; M = L['momentum']
    out += ('<section id="l2t-old"><h2>旧版本</h2><h3>' + E(M['title']) + '</h3><p class="note">' + E(M['read']) + '</p><h3>' + E(O['title']) + '</h3><p class="note">' + E(O['read']) + '</p>' +
            bt_table(B['cols'], O['rows']) + '<p class="note">' + E(L['source']) + '</p></section>')
    return out


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
.l2t-table{min-width:900px}.l2t-table td,.l2t-table th{vertical-align:top;font-size:13.5px}
.l2r-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin:12px 0}
.l2r-card{border:1px solid #dfe5ec;border-radius:10px;padding:12px 16px;background:#fff}.l2r-card h3{font-size:16px;margin:0 0 8px}.l2r-card h3 small{color:#789;font-weight:400}
.l2r-card dt{font-weight:600;font-size:13px;color:#456;margin-top:6px}.l2r-card dd{margin:2px 0 0;font-size:14px;line-height:1.7}
.l2r-flag{background:#fff6e5;border-radius:6px;padding:6px 10px;font-size:13.5px;margin:8px 0 0}
"""
