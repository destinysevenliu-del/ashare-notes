"""港股顺势选股（与A股逻辑一同一格式：板块 → 初筛 → 核验 → 估值 → 价格 → 筹码）。
数据：data/raw/stock_pick/hk_enrich.json（浏览器执行 pipeline/weekly/hk_pick.js 取得，口径见该文件头）。
页面：docs/stocks/hk.html（个股页第三个标签）。
"""
import json
from pathlib import Path
from html import escape as E
import logic1_rules as LR
import stockcards as SC
import stockpick as SP

TAX = 0.20  # 港股通个人投资者H股、红筹股红利税，按20%计
FOREIGN = {'00005', '02888', '00023', '00440', '02356'}
# 能源公司利润主要来自哪项业务（决定“板块”一格是否适用前半段；与A股同一做法）
HK_SUB = {'00883': '上游原油', '00857': '一体化（上游为主）', '00386': '一体化（炼化为主）', '01088': '动力煤', '01898': '煤种结构待核', '01171': '煤种结构待核', '03668': '煤种结构待核'}
RULES = {
 'hk-energy': {'type': 'upstream', 'inds': ['石油及天然气', '煤炭'], 'n': 4,
   'gate': '港股通可买的石油与煤炭股；港股市值≥300亿港元；最近一期归母利润同比>0；市盈率（TTM）0—20倍（与A股煤炭门槛一致）',
   'filter': lambda x: (x.get('mc') or 0) >= 300 and (x.get('np_yoy') or -1) > 0 and 0 < (x.get('pe') or 99) <= 20, 'factors': ['np', 'dy', 'cheap']},
 'hk-tanker': {'type': 'upstream', 'inds': ['工用运输'], 'n': 2,
   'gate': '只保留纯油运公司（港股通行业“工用运输”中名称含油运或能源运输的公司）',
   'filter': lambda x: any(k in x['name'] for k in ('油运', '能源运输', '远海能')), 'factors': ['np', 'cheap']},
 'hk-hardware': {'type': 'growth', 'inds': ['半导体'], 'n': 4,
   'gate': '港股通可买的半导体股；港股市值≥300亿港元；最近一期归母利润同比≥30%；市盈率（TTM）0—100倍（港股半导体以晶圆代工为主，估值普遍高于A股门槛，单独设定）',
   'filter': lambda x: (x.get('mc') or 0) >= 300 and (x.get('np_yoy') or 0) >= 30 and 0 < (x.get('pe') or 999) <= 100, 'factors': ['np', 'rev', 'cheap']},
}
FAC = {'np': ('最近一期利润同比', lambda x: x.get('np_yoy') or 0), 'rev': ('营收同比', lambda x: x.get('rev_yoy') or 0),
       'cheap': ('估值低（PE）', lambda x: -(x.get('pe') or 999)), 'dy': ('税后股息率', lambda x: x.get('dy_net') or 0)}
SB_LINE = 2.0  # 南向持股占比20日上升≥2个百分点视为资金快速涌入（本站设定）


def load(root):
    p = Path(root)/'data/raw/stock_pick/hk_enrich.json'
    return json.loads(p.read_text()) if p.exists() else None


def rows(D):
    out = []
    for c, s in D['stocks'].items():
        if not s.get('close'):
            continue
        x = {'code': c, **s}
        x['pe'] = round(s['close']/s['eps_ttm'], 1) if s.get('eps_ttm') and s['eps_ttm'] > 0 else None
        x['pb'] = round(s['close']/s['bps'], 2) if s.get('bps') and s['bps'] > 0 else None
        x['dy'] = round(s['dps']/s['close']*100, 2) if s.get('dps') else None
        x['dy_net'] = round(x['dy']*(1-TAX), 2) if x['dy'] else None
        x['cash'] = round(s['ocfps']/s['beps'], 2) if s.get('ocfps') is not None and s.get('beps') and s['beps'] > 0 else None
        out.append(x)
    return out


def layers(t, x, score):
    e = x['en']
    L = LR._layers(t, {'en': e, 'score': score})
    chg = x.get('sb20')
    if chg is not None and chg >= SB_LINE:
        L['chip'] = '差'; L['notes'].append('南向持股20日+%.1f个百分点' % chg)
    elif chg is not None and chg <= -SB_LINE:
        L['chip'] = '中'; L['notes'].append('南向持股20日%.1f个百分点' % chg)
    else:
        L['chip'] = '中'
    return L


def select(root, S):
    D = load(root)
    if not D:
        return {}, None
    sec = {s['id']: s for s in S['sectors']}
    allr = rows(D); res = {}
    LR.CN10Y = LR.cn10y(root)['value']
    for sid, R in RULES.items():
        s = sec[sid]
        pool = [x for x in allr if x['ind'] in R['inds']]
        ok = [x for x in pool if R['filter'](x)]
        for k in R['factors']:
            vals = sorted(FAC[k][1](x) for x in ok)
            for x in ok:
                v = FAC[k][1](x); x['pct_'+k] = (sum(a < v for a in vals)+0.5*sum(a == v for a in vals))/len(vals)
        t = R['type']; V = {'好': 1, '中': .5, '差': 0}
        for x in ok:
            x['score'] = round(sum(x['pct_'+k] for k in R['factors'])/len(R['factors']), 2)
            x['en'] = {'close': x['close'], 'pos52': x.get('pos52'), 'dd': x.get('dd'), 'vsMA60': x.get('vsMA60'), 'ret60': x.get('ret60'),
                       'dy': x['dy_net'] if t == 'crowded' else x.get('dy'), 'cashEps': x.get('cash')}
            L = layers(t, x, x['score']); x.update(L)
            x['total'] = round((x['score']+V[L['pos']]+V[L['chip']])/3*(0.5 if L['fund'] == '差' else 1), 2)
            x['flag'] = ''
        ok.sort(key=lambda x: -x['total'])
        picks = ok[:R['n']] if s['rating'] != '逆风' else []
        for x in picks:
            x['pl'] = LR.price_levels(t, x)
            ch = SP.chain(sid, s, t, x, {})
            if x['code'] in HK_SUB and s['rating'] != '等开关':
                st, stx = SP.sub_state(s, {'sub': HK_SUB[x['code']]})
                ch['steps'][0] = ('板块', st, stx)
                if st == '待核' and ch['view'].startswith('等回落') and '业务待核' not in ch['view']:
                    ch['view'] += '（业务待核）'
            ch['steps'] = [(a, b, hk_text(a, b, tx, t, x)) for a, b, tx in ch['steps']]
            x['chain'] = ch
        res[sid] = {'gate': R['gate'], 'type': t, 'lens': LR.LENS[t], 'pool': len(pool), 'passed': len(ok), 'picks': picks,
                    'rank': '综合排名＝以下各项在通过门槛的公司中的百分位平均：'+'、'.join(FAC[k][0] for k in R['factors'])+'。市值只用作门槛。'}
    return res, D


def hk_text(step, state, txt, t, x):
    if step == '核验':
        cv = '经营现金流覆盖约%.1f倍（%s每股经营现金流÷基本每股收益）' % (x['cash'], x.get('rpt', '')) if x.get('cash') is not None else '经营现金流覆盖：数据缺'
        if t == 'crowded':
            return '港股核验未接入资本充足率、拨备覆盖率与不良率；' + cv + '；分红为2025年度合计每股' + format(x['dps'], '.3f') + '港元'
        return '港股核验未接入资本开支与自由现金流；' + cv
    if step == '估值' and t != 'crowded':
        return '市盈率（TTM）%s倍、市净率%s倍；港股五年估值分位未接入，正常化估值待验证' % ('—' if x.get('pe') is None else format(x['pe'], '.1f'), '—' if x.get('pb') is None else format(x['pb'], '.2f'))
    if step == '估值' and t == 'crowded':
        return txt + '（按港股通个人投资者20%红利税后的股息率计算）'
    if step == '筹码':
        return '南向持股占比%s%%，20日变化%s个百分点' % ('—' if x.get('sb') is None else format(x['sb'], '.1f'), '—' if x.get('sb20') is None else format(x['sb20'], '+.1f'))
    return txt


def fund_text(t, x):
    f = SP.f
    base = '最近一期（' + x.get('rpt', '—') + '）利润同比 ' + f(x.get('np_yoy'), '+.0f', '%') + ' · 营收同比 ' + f(x.get('rev_yoy'), '+.0f', '%')
    if t == 'crowded':
        return '税后股息率 ' + f(x.get('dy_net'), '.2f', '%') + '（税前' + f(x.get('dy'), '.2f', '%') + '） · ' + base + ' · 市净率 ' + f(x.get('pb'), '.2f') + ' · ROE ' + f(x.get('roe'), '.1f', '%')
    if t == 'upstream':
        return base + ' · 股息率 ' + f(x.get('dy'), '.2f', '%') + ' · 经营现金流覆盖 ' + f(x.get('cash'), '.2f') + ' · 市盈率 ' + f(x.get('pe'), '.1f')
    return base + ' · 经营现金流覆盖 ' + f(x.get('cash'), '.2f') + ' · 市盈率 ' + f(x.get('pe'), '.1f')


def card(sid, s, r, x, i):
    t = r['type']; v, c = SP.view_of(s['rating'], sid, x, i); f = SP.f
    pos = '一年位置 ' + f(x.get('pos52'), '.2f') + ' · 距一年高点 ' + f(x.get('dd'), '.0f', '%') + ' · 相对60日线 ' + f(x.get('vsMA60'), '+.0f', '%')
    chip = '南向持股 ' + f(x.get('sb'), '.1f', '%') + ' · 20日变化 ' + f(x.get('sb20'), '+.1f') + '个百分点'
    note = '；'.join(n for n in x.get('notes', []) if not n.startswith('南向'))
    posk = '回撤条件' if t == 'upstream' else '位置'
    plab = {'好': '达标', '中': '一般', '差': '未达标'} if t == 'upstream' else None
    return SC.card('s-'+x['code'], x['name'], x['code'] + ' · ' + SP.short(s['title']), v, c, x.get('pl'),
                   [('初筛指标', x['fund'], E(fund_text(t, x))), (posk, x['pos'], E(pos), plab), ('筹码', x['chip'], E(chip))], SP.l1_bar(t, x), note, SP.chain_html(x['chain']))


def sector_html(sid, s, r):
    t = r['type']; Lz = r['lens']; R = LR.PRICE_RULES[t]
    nb = sum(1 for x in r['picks'] if SC.status(x.get('pl'))[0] == '买入')
    out = ('<details class="lp-sec" id="l1-' + sid + '"' + ('' if s['rating'] == '等开关' else ' open') + '><summary><span class="sec-h"><h3>' + E(s['title']) +
           '</h3><span class="lp-badge lp-' + SP.BADGE[s['rating']] + '">' + E(s['rating']) + '</span><span class="sec-meta">' + str(len(r['picks'])) + '只 · 在买入区' + str(nb) + '只 · ' + E(Lz['name']) + '</span></span></summary>')
    out += '<div class="sec-lens">' + ''.join('<div><b>' + k + '看什么</b>' + E(Lz[key]) + '</div>' for k, key in (('基本面', 'fund'), ('位置', 'pos'))) + '<div><b>筹码看什么</b>南向持股占比（港股通持股占港股股本）及其20日变化：20日上升≥2个百分点视为资金快速涌入（本站设定，未回测）。</div></div>'
    buy = R['buy'] if t != 'crowded' else '税后股息率达到“中国10年国债+2.5个百分点”对应的价格及以下（每股分红×(1−20%)÷(10年国债+2.5%)）'
    sell = R['sell'] if t != 'crowded' else '税后股息率降到“10年国债+2.0个百分点”对应的价格'
    out += ('<p class="sec-rule"><b>价格规则：</b>买入 ' + E(buy) + '；卖出 ' + E(sell) + '；止损 ' + E(R['stop']) + '。<a href="index.html#price-rules">为什么这样定 →</a><br><b>门槛：</b>' + E(r['gate']) +
            '（通过' + str(r['passed']) + ' / ' + str(r['pool']) + '家）　<a href="../boards/' + sid + '.html">板块依据 →</a></p>')
    out += '<div class="sc-grid">' + ''.join(card(sid, s, r, x, i) for i, x in enumerate(r['picks'])) + '</div>'
    return out + '<p class="note">进入个股研究时还要比较：' + E('；'.join(s['handoff'])) + '</p></details>'


def page(ctx):
    root = Path(ctx['ROOT']); S = json.loads((root/'data/sector_selection.json').read_text())
    sec = {s['id']: s for s in S['sectors']}; L, D = select(root, S)
    head = SP.head(3)
    if not L:
        return head + '<div class="hero"><h1>个股 · 港股</h1><p>港股数据尚未取得。</p></div>'
    out = ('<style>' + SP.CSS + SC.CSS + '</style>' + head + '<div class="hero"><h1>港股 · 逻辑一 · 顺势选股</h1><p class="sum">港股有三条选股逻辑：顺势选股（本页）、业绩拐点（观察）、两地比价（只保留逻辑；原高息资产板块归入这条）。国资箱体利用的是A股国资股的特征，不适用港股。格式与A股逻辑一相同：大盘 → 板块 → 个股，判断链为板块、初筛、核验、估值、价格、筹码。价格截至' + E(D['asof']) +
           '（每周更新）。港股按事先写明的规则已下调为偏弱；互联网为逆风，不研究个股。</p><p class="sum"><b>需要复核：</b>业绩拐点页的回测显示，过去一年港股离一年高点越近的股票越强、回撤越深越弱；本页能源、油运沿用A股“一年区间下部买入”的规则，与这一结论相反，买入前要先复核。</p></div>')
    out += '<nav class="lp-jump"><a href="hk-ah.html">高息资产 → 逻辑三</a><a href="#overview">行动看板</a><a href="#logic1">按板块展开</a><a href="#hk-data">数据口径</a></nav>'
    B = {}
    for sid, r in L.items():
        for x in r['picks']:
            k = SP.l1_bucket(sec[sid]['rating'], x); sm = SP.short(sec[sid]['title'])
            if k == '等开关': sm += ' · ' + ('价格已确认' if SC.status(x.get('pl'))[0] != '未确认' else '未确认')
            elif k == '不买': sm += ' · ' + x['chain']['view'].replace('不买：', '')
            B.setdefault(k, []).append(('s-'+x['code'], x['name'], sm))
    out += ('<section id="overview"><h2>行动看板</h2><p class="note">按“现在该做什么”把候选分组。港股的核验（资本开支、资本充足率）与五年估值分位尚未接入，所以价格到了买入区也只到“价格到位·待核”，不直接买。</p>' +
            SC.board(B, SP.L1_ORDER, '价格截至' + D['asof'] + '；规则见A股个股页“价格规则”。', wide=('等开关',)) + '</section>')
    order = ['顺风', '前半段', '等开关', '逆风']
    out += '<section id="logic1"><h2>按板块展开</h2><p class="note">每个板块按自己的类型看三层：基本面、位置、筹码。卡片结构与A股相同。</p>'
    for sid in sorted(L, key=lambda k: order.index(sec[k]['rating'])):
        out += sector_html(sid, sec[sid], L[sid])
    si = sec['hk-internet']
    out += ('<article class="lp-sec" id="l1-hk-internet"><h3>' + E(si['title']) + ' <span class="lp-badge lp-wait">' + E(si['rating']) + '</span></h3><p>' + E(si['verdict']) +
            '</p><p class="note">逆风板块本轮不研究个股；恢复为等开关后再按成长类规则选股。<a href="../boards/hk-internet.html">板块依据 →</a></p></article></section>')
    out += ('<section id="hk-data"><h2>数据口径</h2><ul class="lens-ul"><li>候选范围：截止日港股通（南向）可买股票，按东方财富港股行业分组。</li>'
            '<li>价格与一年区间：东方财富南向持股日表的每日收盘价与涨跌幅，复权方法与A股相同。</li>'
            '<li>财务：东方财富港股主要指标最新一期（港元口径），利润与营收同比为报告期累计，不是单季。</li>'
            '<li>分红：2025年度（中期＋末期）每股分红合计，港元；股息率＝分红÷现价。高息资产的买卖价用税后股息率（港股通个人投资者H股、红筹股红利税按20%计；机构与A+H差异需另算）。</li>'
            '<li>筹码：南向持股占港股股本比例及20日变化；港股没有融资余额与股东户数的同口径数据。</li>'
            '<li>尚未接入：银行资本充足率与不良率、资本开支与自由现金流、五年估值分位。这些都影响“核验”和“估值”，所以港股候选目前最多到“价格到位·待核”。</li></ul></section>')
    return out


def build(ctx):
    site = Path(ctx['SITE'])
    (site/'stocks/hk.html').write_text(ctx['page']('港股 · 顺势选股 | A 股框架笔记', 'gg', page(ctx), '../'), encoding='utf-8')


SECTOR_INDS = {'hk-telecom': ['银行', '电讯'], 'hk-energy': ['石油及天然气', '煤炭'], 'hk-tanker': ['工用运输'], 'hk-internet': ['软件服务', '媒体及娱乐'], 'hk-hardware': ['半导体']}


def industry_rows(root):
    """港股同口径行业数据（港股通可买股票，按东方财富港股行业汇总）。"""
    D = load(root)
    if not D:
        return [], None
    allr = rows(D); out = []
    med = lambda v: sorted(v)[len(v)//2] if v else None
    for sid, inds in SECTOR_INDS.items():
        for ind in inds:
            g = [x for x in allr if x['ind'] == ind and x.get('mc')]
            if not g:
                continue
            mc = sum(x['mc'] for x in g)
            ep = sum(x['mc']/x['pe'] for x in g if x.get('eps_ttm') and x['eps_ttm'] > 0 and x.get('pe'))
            neg = sum(x['mc'] for x in g if x.get('eps_ttm') is not None and x['eps_ttm'] <= 0)
            dyw = sum(x['mc']*(x.get('dy') or 0) for x in g)/mc
            out.append({'sid': sid, 'ind': ind, 'n': len(g), 'mc': mc, 'pe': (mc-neg)/ep if ep else None, 'loss_mc': neg/mc*100,
                        'np': med([x['np_yoy'] for x in g if x.get('np_yoy') is not None]), 'rev': med([x['rev_yoy'] for x in g if x.get('rev_yoy') is not None]),
                        'dy': dyw, 'dd': med([x['dd'] for x in g if x.get('dd') is not None]), 'pos': med([x['pos52'] for x in g if x.get('pos52') is not None]),
                        'sb20': med([x['sb20'] for x in g if x.get('sb20') is not None])})
    return out, D['asof']


def industry_table(root, sec):
    R, asof = industry_rows(root)
    if not R:
        return ''
    f = SP.f
    out = ('<h3>入选板块的同口径行业数据（港股）</h3><div class="tblwrap"><table class="mt ss-table"><thead><tr><th>板块</th><th>行业（东方财富港股）</th><th>样本</th><th>港股市值（亿港元）</th>'
           '<th>市盈率（市值加权，剔除亏损）</th><th>亏损公司市值占比</th><th>利润同比（中位数，最近一期累计）</th><th>营收同比（中位数）</th><th>股息率（市值加权，税前）</th><th>距一年高点（中位数）</th><th>南向持股20日变化（中位数，百分点）</th></tr></thead><tbody>')
    for r in R:
        out += ('<tr><td><a href="' + r['sid'] + '.html">' + E(sec[r['sid']]['title']) + '</a></td><td>' + E(r['ind']) + '</td><td>' + str(r['n']) + '</td><td>' + format(r['mc'], ',.0f') + '</td><td>' + f(r['pe'], '.1f') +
                '</td><td>' + f(r['loss_mc'], '.0f', '%') + '</td><td>' + f(r['np'], '+.0f', '%') + '</td><td>' + f(r['rev'], '+.0f', '%') + '</td><td>' + f(r['dy'], '.2f', '%') + '</td><td>' + f(r['dd'], '.0f', '%') + '</td><td>' + f(r['sb20'], '+.2f') + '</td></tr>')
    return out + '</tbody></table></div><p class="note">样本为' + E(asof) + '港股通可买的股票；财务为各公司最新一期（中报或三季报）累计同比，不是单季；股息率为2025年度分红÷现价。数据与个股页同源（' + E(load(root)['source']) + '）。</p>'
