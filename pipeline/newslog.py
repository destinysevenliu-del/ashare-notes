"""新闻归类：把每周新闻归到分子、分母、水龙头，并用固定规则判断它是否需要跟踪。

原则：判断只跟读数走。新闻本身不直接改结论；改结论的只有跟踪单上的读数越过阈值。
新闻分级只有三档，由本文件的 grade() 计算，不手填：
  B 进入跟踪：来源已确认、对应到跟踪读数，并且（官方决定或数据改变了预期路径，或市场当日反应≥2倍日常波动）。
  C 不改变判断：来源未核实、对应不到跟踪读数、只是确认已知读数，或市场反应在日常波动以内。
  待数据：需要看市场反应、但反应日的数据还没有进站。
同一读数、同一方向，4周内出现2条B，列入“需复核”，在月度复核时决定是否改判断。
"""
import json, math, datetime
from pathlib import Path
from html import escape as E

CONFIRMED = ('官方', '公司公告', '权威媒体')
PATH_OK = ('官方', '公司公告')
INDICATORS = {  # 指标：数据来源、口径、名称、对应跟踪单
    'idx_all': ('idx', 'pct', '中证全指', 'a_idx_all'), 'idx_hs300': ('idx', 'pct', '沪深300', None),
    'idx_cyb': ('idx', 'pct', '创业板指', None), 'idx_kc50': ('idx', 'pct', '科创50', 'a_kc50'),
    'idx_sh': ('idx', 'pct', '上证指数', None),
    'hsi': ('hk', 'pct', '恒生指数', 'hk_hsi'), 'hstech': ('hk', 'pct', '恒生科技', 'hk_hstech'),
    'cn10y': ('bond', 'bp', '中国10年国债', 'cn10y'), 'us10y': ('bond', 'bp', '美国10年国债', 'us10y'),
}
Z_LINE = 2.0
WINDOW = 60
GRADE_LABEL = {'B': 'B 进入跟踪', 'C': 'C 不改变判断', '待数据': '待数据'}


def series(root, ind):
    kind = INDICATORS[ind][0]
    if kind == 'idx':
        rows = json.loads((root/'data/raw'/(ind+'.json')).read_text())['rows']
        return [(r['date'], r['close']) for r in rows]
    if kind == 'hk':
        rows = json.loads((root/'data/raw/hk'/(ind+'.json')).read_text())['rows']
        return [(r['date'], r['close']) for r in rows]
    col = 'EMM00166466' if ind == 'cn10y' else 'EMG00001310'
    rows = json.loads((root/'data/raw/bond.json').read_text())
    return sorted((r['SOLAR_DATE'][:10], r[col]) for r in rows if r.get(col) is not None)


def reaction(root, ind, date):
    """当日变动与此前60个交易日日变动标准差之比；日期不在序列里返回 None（待数据）。"""
    s = series(root, ind); unit = INDICATORS[ind][1]
    pos = {d: i for i, (d, _) in enumerate(s)}
    if date not in pos or pos[date] < WINDOW + 1:
        return None
    i = pos[date]

    def chg(k):
        return (s[k][1]/s[k-1][1]-1)*100 if unit == 'pct' else (s[k][1]-s[k-1][1])*100
    hist = [chg(k) for k in range(i-WINDOW, i)]
    m = sum(hist)/len(hist); sd = math.sqrt(sum((x-m)**2 for x in hist)/(len(hist)-1))
    move = chg(i)
    return {'ind': ind, 'date': date, 'move': round(move, 2), 'unit': '%' if unit == 'pct' else '个基点',
            'sd': round(sd, 2), 'z': round(move/sd, 1) if sd else None, 'close': s[i][1]}


def grade(item, rx):
    lvl = item['source_level']
    if lvl not in CONFIRMED:
        return 'C', '来源未核实（' + lvl + '），先记录，等原始公告或官方数据'
    if not item.get('links'):
        return 'C', '对应不到任何跟踪读数'
    if item.get('path_change'):
        return 'B', '官方决定或数据改变了跟踪变量的预期路径'
    if item.get('react') is None:
        return 'C', item.get('no_react_reason') or '只是确认已知读数，没有新增信息'
    if rx is None:
        return '待数据', '反应日数据尚未进站，下次更新自动计算'
    if rx['z'] is not None and abs(rx['z']) >= Z_LINE:
        return 'B', '市场当日反应达到日常波动的%.1f倍' % abs(rx['z'])
    return 'C', '市场当日反应在日常波动以内（%.1f倍）' % abs(rx['z'] or 0)


def thresholds(root, start, end):
    """本周跟踪单阈值：以收盘计越过的，以及周末距阈值很近的（指数2%以内、利率10个基点以内）。"""
    t = json.loads((root/'data/market_thesis.json').read_text())['macro_regime']['markets']
    rows = {r['src']: (mk, r) for mk, m in t.items() for r in m['tracking']}
    crossed, near = [], []
    for ind, (_, unit, name, src) in INDICATORS.items():
        if not src or src not in rows:
            continue
        mk, r = rows[src]; s = series(root, ind)
        wk = [(i, d, v) for i, (d, v) in enumerate(s) if start <= d <= end]
        if not wk:
            continue
        for side in ('lo', 'hi'):
            line = r.get(side); lab = r.get(side+'_label')
            if line is None:
                continue
            hit = False
            for i, d, v in wk:
                p = s[i-1][1]
                if (side == 'lo' and p >= line > v) or (side == 'hi' and p <= line < v):
                    crossed.append({'date': d, 'name': name, 'line': line, 'close': v, 'prev': p, 'label': lab, 'market': mk}); hit = True
            last = wk[-1][2]
            gap = (last/line-1)*100 if unit == 'pct' else (last-line)*100
            if not hit and abs(gap) <= (2 if unit == 'pct' else 10):
                near.append({'date': wk[-1][1], 'name': name, 'line': line, 'close': last, 'gap': round(gap, 1), 'past': (side == 'lo' and last < line) or (side == 'hi' and last > line),
                             'unit': '%' if unit == 'pct' else '个基点', 'label': lab})
    return crossed, near


def evaluate(root):
    root = Path(root); d = json.loads((root/'data/news_log.json').read_text())
    weeks = []
    for w in d['weeks']:
        same = {}
        for it in w['items']:
            if it.get('react'):
                k = (it['react']['ind'], it['react']['date']); same[k] = same.get(k, 0)+1
        items = []
        for it in w['items']:
            rx = reaction(root, it['react']['ind'], it['react']['date']) if it.get('react') else None
            g, why = grade(it, rx)
            shared = bool(it.get('react')) and same[(it['react']['ind'], it['react']['date'])] > 1
            items.append({**it, 'rx': rx, 'grade': g, 'grade_why': why, 'shared': shared})
        crossed, near = thresholds(root, w['start'], w['end'])
        weeks.append({**w, 'items': items, 'crossed': crossed, 'near': near})
    flags = []  # 需复核：同一跟踪项、同一方向，4周内2条B
    allb = [(w['end'], it) for w in weeks for it in w['items'] if it['grade'] == 'B']
    for end, it in allb:
        for link in it['links']:
            hits = [x for e, x in allb if link in x['links'] and x.get('direction') == it.get('direction')
                    and 0 <= (datetime.date.fromisoformat(end)-datetime.date.fromisoformat(e)).days < 28]
            key = (link, it.get('direction'))
            if len(hits) >= 2 and key not in [(f[0], f[1]) for f in flags]:
                flags.append((link, it.get('direction'), [h['title'] for h in hits]))
    return d, weeks, flags


def fmt_rx(rx):
    sign = '+' if rx['move'] > 0 else ''
    return '%s %s %s%s%s（日常波动的%.1f倍）' % (rx['date'][5:], INDICATORS[rx['ind']][2], sign, rx['move'], rx['unit'], abs(rx['z'] or 0))


CSS = """
.nw-rule{background:#f3f6f9;border-radius:10px;padding:16px 20px;margin:16px 0}.nw-rule p,.nw-rule li{font-size:14.5px;line-height:1.9}
.nw-week{border:1px solid #d4dfeb;border-radius:10px;padding:16px 20px;margin:18px 0;background:#fff}
.nw-week h3{margin:0 0 6px}.nw-sum{font-size:15px;line-height:1.9}
.nw-alert{border-left:4px solid #C8312B;background:#fbecea;padding:10px 14px;margin:10px 0;font-size:14.5px;line-height:1.85}
.nw-near{border-left:4px solid #D88B1F;background:#fdf4e7;padding:10px 14px;margin:10px 0;font-size:14.5px;line-height:1.85}
.nw-tbl td,.nw-tbl th{vertical-align:top;font-size:13.5px;line-height:1.75}.nw-tbl td:nth-child(1),.nw-tbl th:nth-child(1),.nw-tbl td:nth-child(3),.nw-tbl th:nth-child(3){white-space:nowrap}.nw-tbl td:nth-child(2){min-width:240px}
.nw-g{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12.5px;font-weight:600;white-space:nowrap}
.nw-B{background:#fde6d8;color:#9a3d12}.nw-C{background:#eef1f4;color:#55687a}.nw-待数据{background:#fff4d6;color:#7a5a00}
.nw-home{border:1px solid #d4dfeb;border-left:4px solid #3d6b8f;border-radius:8px;padding:12px 16px;margin:16px 0;background:#fff}.nw-home p{margin:4px 0;font-size:14.5px;line-height:1.85}
"""


def rules_html(d):
    r = d['rules']
    return ('<div class="nw-rule"><p><b>判断只跟读数走。</b>' + E(r['principle']) + '</p><ol>' +
            ''.join('<li>' + E(x) + '</li>' for x in r['steps']) + '</ol><p class="note">' + E(r['limits']) + '</p></div>')


def week_html(w):
    md = lambda s: str(int(s[5:7])) + '月' + str(int(s[8:10])) + '日'
    out = '<section class="nw-week" id="w' + w['start'] + '"><h3>' + md(w['start']) + '—' + md(w['end']) + '</h3>'
    out += '<p class="nw-sum">' + E(w['summary']) + '</p>'
    for c in w['crossed']:
        act = w.get('crossed_action', {}).get(c['name'], '按跟踪单规则执行。')
        out += ('<div class="nw-alert"><b>读数越过阈值：</b>' + md(c['date']) + E(c['name']) + '收盘' + format(c['close'], ',') +
                '，越过' + format(c['line'], ',') + '（' + E(c['label'] or '') + '）。' + E(act) + '</div>')
    for n in w['near']:
        if n['past']:
            out += ('<div class="nw-near"><b>仍在阈值另一侧：</b>' + md(n['date']) + E(n['name']) + '收于' + format(n['close'], ',') + '，仍在' +
                    format(n['line'], ',') + '另一侧（' + E(n['label'] or '') + '，已触发并执行；恢复条件见大盘页）。</div>')
        else:
            out += ('<div class="nw-near"><b>接近阈值：</b>' + md(n['date']) + E(n['name']) + '收于' + format(n['close'], ',') + '，距' +
                    format(n['line'], ',') + '（' + E(n['label'] or '') + '）' + ('%+.1f' % n['gap']) + n['unit'] + '。</div>')
    out += ('<div class="tbl-wrap"><table class="nw-tbl"><thead><tr><th>日期</th><th>新闻与归类理由</th><th>归到</th><th>对应读数</th>'
            '<th>来源</th><th>当日反应</th><th>分级</th></tr></thead><tbody>')
    order = {'B': 0, '待数据': 1, 'C': 2}
    for it in sorted(w['items'], key=lambda x: (order[x['grade']], x['date'])):
        src = '<a href="' + E(it['url']) + '">' + E(it['source_name']) + '</a><br>（' + E(it['source_level']) + '）'
        if not it.get('react'):
            rx = '不适用'
        elif not it['rx']:
            rx = '待数据（' + E(it['react']['date'][5:]) + ' ' + E(INDICATORS[it['react']['ind']][2]) + '）'
        else:
            rx = E(fmt_rx(it['rx']))
        if it['shared']:
            rx += '；同日多条新闻，反应不单独归因'
        out += ('<tr><td>' + E(it['date'][5:]) + '</td><td><b>' + E(it['title']) + '</b><br><span class="note">' + E(it['why']) +
                '</span></td><td>' + E(it['part']) + '</td><td>' + E('、'.join(it['links_label'])) + '</td><td>' + src + '</td><td>' + rx +
                '</td><td><span class="nw-g nw-' + it['grade'] + '">' + GRADE_LABEL[it['grade']] + '</span><br>' + E(it['grade_why']) +
                ('。' + E(it['path_note']) if it.get('path_note') else '') + '</td></tr>')
    return out + '</tbody></table></div></section>'


def home_card(root, prefix=''):
    d, weeks, flags = evaluate(root)
    if not weeks:
        return ''
    w = weeks[-1]; nb = sum(1 for x in w['items'] if x['grade'] == 'B')
    out = ('<style>' + CSS + '</style><div class="nw-home"><p><b>本周新闻归类（' + E(w['start'][5:]) + '至' + E(w['end'][5:]) + '）：</b>' +
           str(len(w['items'])) + '条新闻，' + str(nb) + '条进入跟踪，' + str(sum(1 for x in w['items'] if x['grade'] == '待数据')) + '条待数据，其余不改变判断。')
    for c in w['crossed']:
        out += '读数越过阈值：' + E(c['name']) + '收盘' + format(c['close'], ',') + '（' + E(c['label'] or '') + '）。'
    for n in w['near']:
        out += (E(n['name']) + '仍在' + format(n['line'], ',') + '另一侧（已触发）。') if n['past'] else ('接近阈值：' + E(n['name']) + '距' + format(n['line'], ',') + ('%+.1f' % n['gap']) + n['unit'] + '。')
    return out + '<a href="' + prefix + 'news.html">看归类与理由</a></p></div>'


def build(ctx):
    root = Path(ctx['ROOT']); d, weeks, flags = evaluate(root)
    body = ('<div class="hero"><p class="date">每周更新 · 最近一周 ' + E(weeks[-1]['start']) + ' 至 ' + E(weeks[-1]['end']) +
            '</p><h1>新闻归类</h1><p class="sum">' + E(d['intro']) + '</p></div>')
    body += '<style>' + CSS + '</style>' + rules_html(d)
    if flags:
        body += ('<div class="nw-alert"><b>需复核（同一读数、同一方向，4周内2条进入跟踪）：</b>' +
                 '；'.join(E(f[0]) + '：' + E('、'.join(f[2])) for f in flags) + '</div>')
    for w in reversed(weeks):
        body += week_html(w)
    (root/'docs/news.html').write_text(ctx['page']('新闻归类 | A 股框架笔记', 'nw', body), encoding='utf-8')
