"""个股页的卡片式展现：行动看板 + 每只股票一张卡片（结论、价格计划、分层判断、位置条）。
只负责展现；判断与价格全部来自 logic1_rules / logic2_box / stockpick 中已有的函数。"""
from html import escape as E

def f(x, p='.1f', suf=''):
    return '—' if x is None else format(x, p) + suf

def money(v):
    return '—' if v is None else format(v, '.2f')

LY = {'好': 'g', '中': 'm', '差': 'b'}
def pill(v, lab=None): return '<span class="ly ly-' + LY[v] + '">' + ((lab or {}).get(v, v)) + '</span>'

def status(pl):
    """价格状态 → (类别, 显示文字, 颜色类)"""
    if not pl: return ('无', '价格数据不足', 'st-na')
    w = pl['where']; c = pl['close']
    if '未确认' in w: return ('未确认', w.split('（')[0], 'st-wait')
    if '跌破止损' in w or (pl.get('stop') and c <= pl['stop']): return ('止损', '已跌破止损价', 'st-stop')
    if '卖出区' in w or c >= pl['sell']: return ('卖出', '已到卖出价', 'st-sell')
    if '在买入区' in w: return ('买入', '在买入区', 'st-buy')
    if '低于' in w: return ('低于', w.split('（')[0], 'st-low')
    return ('高于', w.replace('等待：', '').replace('价格已确认，', ''), 'st-high')

def bar(lo, hi, buy, sell, stop, cur, lab_lo='一年低点', lab_hi='一年高点'):
    """横向位置条：止损—低点—买入区—卖出—高点，标出现价。"""
    pts = [v for v in (lo, hi, sell, stop, cur, buy[0], buy[1]) if v is not None]
    a, b = min(pts), max(pts)
    if b <= a: return ''
    a -= (b - a) * 0.04; b += (b - a) * 0.04
    X = lambda v: (v - a) / (b - a) * 100
    out = '<div class="pb" aria-hidden="true"><div class="pb-track">'
    if lo is not None and hi is not None: out += '<i class="pb-rng" style="left:%.1f%%;width:%.1f%%"></i>' % (X(lo), X(hi) - X(lo))
    out += '<i class="pb-buy" style="left:%.1f%%;width:%.1f%%"></i>' % (X(buy[0]), max(X(buy[1]) - X(buy[0]), 1.2))
    if sell is not None: out += '<i class="pb-sell" style="left:%.1f%%"></i>' % X(sell)
    if stop is not None: out += '<i class="pb-stop" style="left:%.1f%%"></i>' % X(stop)
    out += '<b class="pb-cur" style="left:%.1f%%"></b></div><div class="pb-lab"><span>' % X(cur)
    out += ('止损 ' + money(stop)) if stop is not None else ((lab_lo + ' ' + money(lo)) if lo is not None else ('买入 ' + money(buy[0])))
    out += '</span><span>现价 ' + money(cur) + '</span><span>' + ((lab_hi + ' ' + money(hi)) if hi is not None else ('卖出 ' + money(sell))) + '</span></div></div>'
    return out

def plan(pl, rr_note=True):
    """价格计划：一行写完买入、卖出、止损、盈亏比（原来五个格子信息重复、占地大）。"""
    if not pl: return '<p class="sc-na">价格数据不足</p>'
    rr = '—' if pl.get('rr') is None else format(pl['rr'], '.1f')
    if pl.get('rr_now') is not None: rr += '<small>（现价 ' + format(pl['rr_now'], '.1f') + '）</small>'
    cells = [('买入', money(pl['buy'][0]) + '–' + money(pl['buy'][1])),
             ('参考上沿', money(pl['sell']) + ((' / ' + money(pl['sell2'])) if pl.get('sell2') else '')),
             ('止损', money(pl.get('stop')) if pl.get('stop') is not None else '看分红'),
             ('盈亏比', rr)]
    return '<p class="sc-plan">' + ''.join('<span><em>' + a + '</em>' + b + '</span>' for a, b in cells) + '</p>'

def final_action(view):
    if view.startswith('剔除') or view=='移出关注':return '移出关注','bad'
    if view.startswith('不买') or '暂停' in view or '已破位' in view:return '暂停新增','bad'
    if '待核' in view:return '待核','wait'
    if view=='可执行':return '条件满足','go'
    return '等待','wait'

def card(cid, name, sub, view, vcls, pl, layers, bar_html='', note='', chain=''):
    """个股卡片：首屏只留结论、现价、位置条、价格计划和判断链；判断依据与分层指标折叠。"""
    st = status(pl)
    action, action_cls = final_action(view)
    chips, _, det = chain.partition('<dl class="ch-d">')
    det = ('<dl class="ch-d">' + det) if det else ''
    out = '<article class="sc' + (' sc-dim' if vcls == 'bad' else '') + '" id="' + cid + '"><header><div><b>' + E(name) + '</b><small>' + E(sub) + '</small></div><span class="lp-view ' + action_cls + '">' + E(action) + '</span></header><p class="sc-decision-reason">' + E(view) + '</p>'
    out += '<div class="sc-px"><span>现价 <b>' + money(pl['close'] if pl else None) + '</b></span><span class="sc-position">价格位置：' + E(st[1].replace('在买入区','落在参考区间').replace('价格已确认，','')) + '</span></div>'
    out += bar_html + plan(pl) + chips
    if note: out += '<p class="sc-note">' + E(note) + '</p>'
    out += '<details class="sc-more"><summary>判断依据</summary>' + det
    out += '<ul class="sc-ly">' + ''.join('<li><span class="sc-k">' + E(L[0]) + '</span>' + pill(L[1], L[3] if len(L) > 3 else None) + '<span class="sc-v">' + L[2] + '</span></li>' for L in layers) + '</ul></details>'
    return out + '</article>'

def board(buckets, order, hint, wide=()):
    """行动看板：按“现在该做什么”分组；buckets={组名:[(锚点,名称,小字)]}。空组不单独占一列，合并成一行。"""
    out = '<div class="ab">'; empty = []
    for k, cls, desc in order:
        xs = buckets.get(k) or []
        if not xs:
            empty.append(k); continue
        out += '<section class="ab-col ' + cls + (' ab-wide' if k in wide or len(xs) > 8 else '') + '"><h3>' + E(k) + '<span>' + str(len(xs)) + '</span></h3><p>' + E(desc) + '</p><ul>'
        out += ''.join('<li><a href="#' + a + '">' + E(n) + '</a><small>' + E(s) + '</small></li>' for a, n, s in xs)
        out += '</ul></section>'
    out += '</div>'
    if empty: out += '<p class="ab-none">暂无：' + '、'.join(E(k) for k in empty) + '</p>'
    return out + '<p class="note">' + E(hint) + '</p>'

CSS = """
.ab{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:12px 0 6px}
.ab-col{background:#fff;border:1px solid #dfe6ee;border-radius:10px;padding:12px 14px;border-top:4px solid #c8d3df}
.ab-col h3{font-size:15px;margin:0 0 2px;display:flex;justify-content:space-between;align-items:center}.ab-col h3 span{font-size:13px;color:#64798d;font-weight:600}
.ab-col p{font-size:12px;color:#6b7c8c;margin:0 0 8px;line-height:1.5}.ab-col ul{list-style:none;margin:0;padding:0}
.ab-col li{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-top:1px solid #eef2f6;font-size:13.5px}.ab-col li small{color:#6b7c8c;font-size:12px;text-align:right}
.ab-col a{text-decoration:none;color:#1f3b57;font-weight:600}.ab-empty{color:#9aa8b5}
.ab-wide{grid-column:1/-1}.ab-wide ul{display:flex;flex-wrap:wrap;gap:6px}.ab-wide li{border:none;background:#f3f6f9;border-radius:8px;padding:4px 10px;gap:6px}.ab-wide li small{text-align:left}.sc-dim{opacity:.72}
.ab-buy{border-top-color:#3f8a64}.ab-high{border-top-color:#d1a23d}.ab-low{border-top-color:#9aa8b5}.ab-sell{border-top-color:#c4572a}.ab-wait{border-top-color:#5a7ea6}.ab-bad{border-top-color:#8c8c8c}
.sc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,380px),1fr));gap:12px;margin:12px 0}
.sc{background:#fff;border:1px solid #dfe6ee;border-radius:12px;padding:14px 16px;scroll-margin-top:90px;align-self:start}
.sc header{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.sc header b{font-size:16.5px;color:#1b324a}.sc header small{display:block;color:#6b7c8c;font-size:12px;margin-top:2px}
.sc-decision-reason{font-size:13px;color:#52687b;margin:6px 0}.sc-position{font-size:12px;color:#62788b}.sc-px{display:flex;align-items:center;gap:10px;margin:10px 0 6px;font-size:13.5px;color:#455a6e}.sc-px b{font-size:17px;color:#1b324a}
.st{font-size:12.5px;padding:2px 9px;border-radius:10px;font-weight:600}.st-buy{background:#e3f3ea;color:#2f6f53}.st-high{background:#fff3d9;color:#8a5a00}.st-sell{background:#fbe3dc;color:#9b3d27}.st-low,.st-na{background:#eef1f4;color:#5b6b7a}.st-stop{background:#ececec;color:#555}.st-wait{background:#e6eef7;color:#2f4f6f}
.sc-plan span{display:inline-block;margin-right:18px}.sc-plan{display:block;margin:8px 0;font-size:13.5px;font-weight:600;color:#1b324a;font-variant-numeric:tabular-nums}.sc-plan em{font-style:normal;font-weight:400;color:#6b7c8c;font-size:12px;margin-right:5px}.sc-plan small{font-weight:400;color:#6b7c8c;font-size:11.5px}
.sc-more{margin-top:6px;border-top:1px solid #eef2f6;padding-top:6px}.sc-more>summary{cursor:pointer;font-size:12.5px;color:#52687b;list-style:none}.sc-more>summary::before{content:"▸ ";color:#8a9aab}.sc-more[open]>summary::before{content:"▾ "}.sc-more[open]>summary{margin-bottom:6px}
.ab-none{font-size:12.5px;color:#7a8794;margin:2px 0 0}
.ch{list-style:none;display:flex;flex-wrap:wrap;gap:4px;margin:4px 0 6px;padding:0}.ch li{display:flex;align-items:center;gap:4px;font-size:12px;border-radius:7px;padding:3px 7px;background:#eef1f4;color:#5b6b7a}.ch li span{opacity:.8}.ch li b{font-weight:600}
.ch-ok{background:#e3f3ea!important;color:#2f6f53!important}.ch-no{background:#fbe3dc!important;color:#9b3d27!important}.ch-tip{background:#f3f0e6!important;color:#6b5a2e!important}
.ch-d{margin:0 0 8px;font-size:12.5px;line-height:1.65;color:#3a4c5e}.ch-d div{display:grid;grid-template-columns:2.6em minmax(0,1fr);gap:6px;padding:2px 0}.ch-d dt{color:#6b7c8c}.ch-d dd{margin:0}
.sc-ly{list-style:none;margin:0;padding:0}.sc-ly li{display:grid;grid-template-columns:4.6em 3.1em minmax(0,1fr);align-items:baseline;gap:6px;padding:5px 0;border-top:1px solid #f0f3f6;font-size:13px;line-height:1.6}
.sc-k{color:#455a6e;font-weight:600}.sc-v{color:#3a4c5e}.sc-note{font-size:12.5px;color:#6b5a2e;background:#fbf6e9;border-radius:8px;padding:6px 10px;margin:8px 0 0;line-height:1.6}.sc-na{color:#7a8794;font-size:13px}
.pb{margin:6px 0 2px}.pb-track{position:relative;height:10px;background:#eef1f4;border-radius:5px}
.pb-track i,.pb-track b{position:absolute;top:0;height:10px}.pb-rng{background:#dde5ee;border-radius:5px}.pb-buy{background:#7cc19a;border-radius:3px}
.pb-sell{width:3px;background:#c4572a}.pb-stop{width:3px;background:#555}.pb-cur{width:4px;margin-left:-2px;top:-4px!important;height:18px!important;background:#1b324a;border-radius:2px}
.pb-lab{display:flex;justify-content:space-between;font-size:11.5px;color:#6b7c8c;margin-top:4px}
.sec-h{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.sec-meta{font-size:13px;color:#52687b}
.sec-lens{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0}.sec-lens div{background:#f6f8fa;border-radius:8px;padding:8px 10px;font-size:12.5px;line-height:1.6;color:#3a4c5e}.sec-lens b{display:block;color:#1f3b57;font-size:13px}
.sec-rule{font-size:12.5px;color:#455a6e;background:#f9fafb;border:1px dashed #cfd9e3;border-radius:8px;padding:8px 12px;line-height:1.7}
details.more{margin:8px 0}details.more>summary{cursor:pointer;font-size:13px;color:#2f4f6f}
.wk{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}.wk-i{background:#fff;border:1px solid #dfe6ee;border-radius:8px;padding:6px 10px;font-size:13px}.wk-i a{font-weight:600;text-decoration:none;color:#1f3b57}.wk-i em{font-style:normal;color:#6b7c8c}
.wk-sum{display:flex;flex-wrap:wrap;gap:6px;font-size:12.5px;color:#52687b}.wk-sum span{background:#eef2f6;border-radius:10px;padding:2px 9px}
@media(max-width:760px){.sec-lens{grid-template-columns:1fr}}
"""
