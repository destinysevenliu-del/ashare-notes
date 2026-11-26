"""港股逻辑二（业绩拐点，观察）与逻辑三（两地比价，只保留逻辑）的页面。
数据：data/raw/stock_pick/hk_logic2.json（浏览器取数与回测结果，口径见文件内 source、rules、backtest）。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

SHORT_RISE = 1.0  # 近8周空头占比上升≥1个百分点：剔除


def load(root):
    p = Path(root)/'data/raw/stock_pick/hk_logic2.json'
    return json.loads(p.read_text()) if p.exists() else None


def verdict(x):
    """观察名单里的每只股：逻辑整体未启用，个股再看价格确认与空头。"""
    above = x[7] > 0
    if not above:
        return '观察：价格未确认', '仍在12周均线下方'
    return '观察：价格已确认，逻辑未启用', '已站上12周均线，等逻辑启用条件'


def table(L):
    f = SP.f
    out = ('<div class="tblwrap"><table class="mt lp-table l2t-table"><thead><tr><th>股票</th><th>港股市值<br>（亿港元）</th><th>距一年高点</th><th>相对12周均线</th>'
           '<th>拐点依据</th><th>本期利润 / 上期</th><th>近三期毛利率（旧→新）</th><th>空头占港股股本<br>（11-13 / 8周前）</th><th>判断</th></tr></thead><tbody>')
    for x in L['list']:
        why = []
        if x[8]: why.append('亏损收窄或扭亏')
        if x[9]: why.append('毛利率连续两期回升')
        v, vt = verdict(x)
        gm = ' → '.join('—' if g is None else format(g, '.1f') + '%' for g in x[14])
        out += ('<tr><th scope="row">' + E(x[1]) + '<small>' + x[0] + ' · ' + E(x[2]) + '</small></th><td>' + format(x[3], ',') + '</td><td>' + f(x[5], '.0f', '%') + '</td><td>' + f(x[7], '+.0f', '%') +
                '</td><td>' + E('、'.join(why)) + '</td><td>' + E(x[10]) + ' ' + f(x[11], '+.1f') + '亿<br><small>' + E(x[12]) + ' ' + f(x[13], '+.1f') + '亿</small></td><td>' + gm +
                '</td><td>' + f(x[15][0], '.1f', '%') + ' / ' + f(x[15][2], '.1f', '%') + '</td><td><span class="lp-view wait">' + E(v) + '</span><br><small>' + E(vt) + '</small></td></tr>')
    return out + '</tbody></table></div>'


def page2(root):
    L = load(root)
    if not L:
        return SP.head(4) + '<div class="hero"><h1>港股 · 逻辑二 · 业绩拐点</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']; f = SP.f
    out = '<style>' + SP.CSS + SC.CSS + CSS + '</style>' + SP.head(4)
    out += ('<div class="hero"><h1>港股 · 逻辑二 · 业绩拐点（观察）</h1><p class="sum">港股能做空、由机构按盈利预期定价，深度下跌的公司一旦业绩拐头，可能出现快速修复。'
            '但用过去一年的数据检验，这条逻辑没有带来超额收益，所以本页只列观察名单，满足启用条件前不买。价格截至' + E(L['asof']) + '，空头数据截至' + E(L['short_asof']) + '。</p></div>')
    out += '<nav class="lp-jump"><a href="#l2t-status">结论</a><a href="#l2t-list">观察名单</a><a href="#l2t-rules">规则</a><a href="#l2t-bt">回测</a></nav>'
    out += ('<section id="l2t-status"><h2>结论</h2><div class="l2t-box"><p><b>状态：</b>' + E(R['status']) + '</p><p><b>' + E(R['enable'].split('：')[0]) + '：</b>' + E(R['enable'].split('：', 1)[1]) +
            '</p><p><b>回测说明了什么：</b>' + E(B['read']) + '</p></div></section>')
    out += ('<section id="l2t-list"><h2>观察名单（' + str(len(L['list'])) + '只）</h2><p class="note">按港股市值排序。全部满足“回撤≥40%＋业绩拐点＋空头没有上升”，没有一只处于可买状态。</p>' + table(L))
    ex = '；'.join(E(n) + '（' + c + '，' + f(s[2], '.1f') + '%→' + f(s[0], '.1f') + '%）' for c, n, s in L['excluded_short_rising'])
    out += '<p class="note"><b>因空头8周内上升≥1个百分点剔除：</b>' + ex + '。</p></section>'
    out += ('<section id="l2t-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('候选范围', 'universe'), ('回撤', 'drawdown'), ('业绩拐点', 'turn'), ('空头', 'short'), ('价格确认与止损', 'confirm'))) + '</dl></section>')
    out += ('<section id="l2t-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p><div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in B['cols']) +
            '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + E(r[0]) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in B['rows']) +
            '</tbody></table></div><p class="note">' + E(L['source']) + '</p></section>')
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
    (site/'stocks/hk-turn.html').write_text(ctx['page']('港股 · 业绩拐点 | A 股框架笔记', 'gg', page2(root), '../'), encoding='utf-8')
    (site/'stocks/hk-ah.html').write_text(ctx['page']('港股 · 两地比价 | A 股框架笔记', 'gg', page3(root), '../'), encoding='utf-8')


CSS = """
.l2t-box{background:#f3f6f9;border-radius:10px;padding:14px 18px;margin:10px 0}.l2t-box p{font-size:14.5px;line-height:1.9;margin:4px 0}
.l2t-table{min-width:1100px}.l2t-table td,.l2t-table th{vertical-align:top;font-size:13.5px}
"""
