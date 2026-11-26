"""港股逻辑二（动量＋空头下降）与逻辑三（两地比价，只保留逻辑）的页面。
数据：data/raw/stock_pick/hk_logic2.json（浏览器执行 pipeline/weekly/hk_momentum.js 取数与回测，口径见文件内 source、rules、backtest）。
旧版“业绩拐点”数据留档：data/raw/stock_pick/hk_logic2_reversal_2026-11-25.json。
"""
import json
from pathlib import Path
from html import escape as E
import stockpick as SP
import stockcards as SC

DD_MAX = 15        # 距一年高点不超过15%
SHORT_HIGH = 3.0   # 空头占港股股本≥3%视为高空头
SHORT_STEP = 0.5   # 近8周变化≥0.5个百分点视为上升或下降
ENTRY = (0, 8)     # 买点：高于12周均线0%—8%
NO_CHASE = 15      # 高于12周均线15%以上不追，持有者减仓

# list 列下标
C, N, IND, MC, PX, DD, V12, V26, R26, NPUP, FALL, SH, FIN = range(13)


def load(root):
    p = Path(root)/'data/raw/stock_pick/hk_logic2.json'
    return json.loads(p.read_text()) if p.exists() else None


def short_ok(s):
    """s=[现在%, 8周前%]；None表示该股不在证监会名单（无可报告淡仓），按低空头处理。"""
    if not s:
        return True
    now, ago = s
    if now - ago >= SHORT_STEP:
        return False
    return now < SHORT_HIGH or ago - now >= SHORT_STEP


def verdict(x):
    v = x[V12]
    if v is None:
        return '数据缺', 'wait'
    if v > NO_CHASE:
        return '不追：高于12周均线' + format(v, '.0f') + '%', 'wait'
    if v > ENTRY[1]:
        return '等回调：高于12周均线' + format(v, '.0f') + '%', 'wait'
    if v < ENTRY[0]:
        return '等站回12周均线（低' + format(-v, '.0f') + '%）', 'wait'
    return '买点：回调到均线附近', 'go'


def groups(L):
    g = {'go': [], 'pull': [], 'back': []}
    for x in L['list']:
        v = x[V12]
        g['go' if ENTRY[0] <= v <= ENTRY[1] else ('pull' if v > ENTRY[1] else 'back')].append(x)
    return g


def table(rows):
    f = SP.f
    out = ('<div class="tblwrap"><table class="mt lp-table l2t-table"><thead><tr><th>股票</th><th>港股市值<br>（亿港元）</th><th>现价</th><th>距一年高点</th><th>相对12周均线</th><th>相对26周均线</th><th>26周涨跌</th>'
           '<th>空头占港股股本<br>（11-13 / 8周前）</th><th>最近一期利润同比<br><small>营收同比</small></th><th>利润不低于上一期</th><th>判断</th></tr></thead><tbody>')
    for x in rows:
        v, cls = verdict(x)
        sh = '不在名单' if x[SH] is None else (f(x[SH][0], '.2f', '%') + ' / ' + f(x[SH][1], '.2f', '%') + ('<br><small>下降</small>' if x[FALL] else ''))
        fin = x[FIN] or [None, None, None]
        out += ('<tr><th scope="row">' + E(x[N]) + '<small>' + x[C] + ' · ' + E(x[IND]) + '</small></th><td>' + format(x[MC], ',') + '</td><td>' + format(x[PX], 'g') + '</td><td>' + f(x[DD], '.0f', '%') +
                '</td><td>' + f(x[V12], '+.0f', '%') + '</td><td>' + f(x[V26], '+.0f', '%') + '</td><td>' + f(x[R26], '+.0f', '%') + '</td><td>' + sh + '</td><td>' + f(fin[1], '+.1f', '%') + '<br><small>' + E(fin[0] or '') + ' · ' + f(fin[2], '+.1f', '%') +
                '</small></td><td>' + {1: '是', 0: '否'}.get(x[NPUP], '—') + '</td><td><span class="lp-view ' + cls + '">' + E(v) + '</span></td></tr>')
    return out + '</tbody></table></div>'


def bt_table(cols, rows):
    return ('<div class="tblwrap"><table class="mt lp-table"><thead><tr>' + ''.join('<th>' + E(c) + '</th>' for c in cols) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + E(str(r[0])) + '</th><td>' + str(r[1]) + '</td><td>' + format(r[2], '+.1f') + '</td><td>' + format(r[3], '+.1f') + '</td><td>' + str(r[4]) + '</td></tr>' for r in rows) +
            '</tbody></table></div>')


def page2(root):
    L = load(root)
    if not L or L.get('version') != 'momentum':
        return SP.head(4) + '<div class="hero"><h1>港股 · 逻辑二 · 动量＋空头下降</h1><p>数据尚未取得。</p></div>'
    R = L['rules']; B = L['backtest']; G = groups(L)
    out = '<style>' + SP.CSS + SC.CSS + CSS + '</style>' + SP.head(4)
    out += ('<div class="hero"><h1>港股 · 逻辑二 · 动量＋空头下降</h1><p class="sum">港股由机构定价、可以做空。过去一年的数据显示：离一年高点越近的股票越强，空头在增加的股票随后越弱，空头在回补或本来就少的股票更强。'
            '所以这条逻辑找“离高点近、空头少或在回补”的股票，等它回调到12周均线附近再买。价格截至' + E(L['asof']) + '，空头数据截至' + E(L['short_asof']) + '（证监会每周公布，滞后约两周）。</p></div>')
    out += '<nav class="lp-jump"><a href="#l2t-status">结论</a><a href="#l2t-go">买点名单</a><a href="#l2t-wait">等待名单</a><a href="#l2t-rules">规则</a><a href="#l2t-bt">回测</a><a href="#l2t-old">旧版为何放弃</a></nav>'
    out += ('<section id="l2t-status"><h2>结论</h2><div class="l2t-box"><p><b>状态：</b>' + E(R['status']) + '</p><p><b>名单构成：</b>' + E(R['note']) +
            '</p><p><b>当前：</b>' + str(len(L['list'])) + '只入选，其中' + str(len(G['go'])) + '只在买点（高于12周均线0%—8%），' + str(len(G['pull'])) + '只等回调，' + str(len(G['back'])) + '只等站回均线。</p></div></section>')
    out += ('<section id="l2t-go"><h2>买点名单（' + str(len(G['go'])) + '只）</h2><p class="note">按港股市值排序。优势来自分散，回测中单只股票跑赢的比例只有56%左右，不要集中押一两只。</p>' + table(G['go']) + '</section>')
    out += ('<section id="l2t-wait"><h2>等待名单（' + str(len(G['pull']) + len(G['back'])) + '只）</h2><p class="note">满足“离高点近＋空头条件”，价格还不在买点。</p>' + table(G['pull'] + G['back']))
    ex = '；'.join(E(n) + '（' + c + '，' + E(w) + '）' for c, n, w in L['excluded'])
    out += '<p class="note"><b>离高点近但因空头条件剔除：</b>' + ex + '。</p></section>'
    out += ('<section id="l2t-rules"><h2>规则</h2><dl class="pr-dl">' + ''.join('<dt>' + k + '</dt><dd>' + E(R[key]) + '</dd>' for k, key in
            (('候选范围', 'universe'), ('趋势', 'trend'), ('空头', 'short'), ('买点', 'entry'), ('卖出与止损', 'exit'), ('业绩上修', 'earnings'))) + '</dl></section>')
    out += ('<section id="l2t-bt"><h2>回测</h2><p class="note">' + E(B['setup']) + '</p>' + bt_table(B['cols'], B['rows']) +
            '<h3>买点组逐个检验日</h3>' + bt_table(B['by_date_cols'], B['by_date']) + '<p class="note"><b>回测说明了什么：</b>' + E(B['read']) + '</p></section>')
    O = L['reversal']
    out += ('<section id="l2t-old"><h2>' + E(O['title']) + '</h2><p class="note">' + E(O['read']) + '</p>' + bt_table(B['cols'], O['rows']) + '<p class="note">' + E(L['source']) + '</p></section>')
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
    (site/'stocks/hk-turn.html').write_text(ctx['page']('港股 · 动量＋空头下降 | A 股框架笔记', 'gg', page2(root), '../'), encoding='utf-8')
    (site/'stocks/hk-ah.html').write_text(ctx['page']('港股 · 两地比价 | A 股框架笔记', 'gg', page3(root), '../'), encoding='utf-8')


CSS = """
.l2t-box{background:#f3f6f9;border-radius:10px;padding:14px 18px;margin:10px 0}.l2t-box p{font-size:14.5px;line-height:1.9;margin:4px 0}
.l2t-table{min-width:1100px}.l2t-table td,.l2t-table th{vertical-align:top;font-size:13.5px}
"""
