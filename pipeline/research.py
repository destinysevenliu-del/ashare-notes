"""Research v2: explicit hypotheses, evidence boundaries and forecast vintages."""
import datetime
import json
from pathlib import Path
from html import escape as E

VERSION = '2026-11-09 v2'

def revision(history, date, year, eps):
    """Compare the same target year against a 30–45 day old observed snapshot."""
    day = datetime.date.fromisoformat(date)
    candidates = []
    for row in history:
        age = (day - datetime.date.fromisoformat(row['date'])).days
        prior = row['eps'].get(str(year))
        if 30 <= age <= 45 and prior is not None and prior > 0:
            candidates.append(row)
    if not candidates or eps is None or eps <= 0:
        return None
    old = max(candidates, key=lambda x: x['date'])
    return {'date': old['date'], 'year': year, 'change': (eps / old['eps'][str(year)] - 1) * 100}

def consensus_change(root, code, raw, e):
    stamp = raw.get('consensus_observed_at')
    if not stamp or not e:
        return None
    path = Path(root) / 'data/snapshots/consensus.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    return revision(data.get(code, []), stamp[:10], e['y2'], e['e2'])

def record_consensus(root, code, raw, e):
    # A rebuild must not manufacture a new observation from an old raw file.
    stamp = raw.get('consensus_observed_at')
    if not stamp or not e:
        return
    path = Path(root) / 'data/snapshots/consensus.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    history = data.setdefault(code, [])
    row = {'date': stamp[:10], 'observed_at': stamp,
           'eps': {str(e['y1']): e['e1'], str(e['y2']): e['e2']}, 'orgs': e['orgs']}
    history[:] = [x for x in history if x['date'] != row['date']] + [row]
    history.sort(key=lambda x: x['date'])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def growth_description(qs):
    now = qs[-1]
    def pct(v): return '暂缺' if v is None else f'{v:+.1f}%'
    text = f"利润同比 {pct(now['yoy'])}，环比 {pct(now['qoq'])}。"
    if len(qs) > 1:
        prev = qs[-2]
        for key, title in [('yoy', '同比增速'), ('qoq', '环比增速')]:
            if now[key] is not None and prev[key] is not None:
                delta = now[key] - prev[key]
                text += f"{title}较上一季{'提高' if delta >= 0 else '降低'} {abs(delta):.1f} 个百分点。"
    return text + '同比受基数影响，环比未经季节调整；两种变化分别观察，不直接推断未来加速。'

def load_cards(root):
    p = Path(root) / 'data/research_cards.json'
    return json.loads(p.read_text())['stocks'] if p.exists() else {}

def render(a, root):
    card = load_cards(root).get(a['cfg']['code'])
    if not card: return ''
    q = a['f']['qs'][-1]
    evidence = f"财务接口记录：{q['label']} 收入 {q['rev']/1e8:.2f} 亿元，归母净利润 {q['np']/1e8:.2f} 亿元；报告披露日期 {a['f']['notice']}。接口数据尚未逐项与公告原文核对。"
    risks = []
    if q['np'] <= 0: risks.append('最新单季亏损，需独立验证持续经营改善。')
    if a['f']['cash_ratio'] is not None and a['f']['cash_ratio'] < .5: risks.append('累计经营现金流与利润的比值偏低，需检查应收、存货及季节性。')
    if a['m']['lev'] >= 4: risks.append('融资余额占比较高，需单独观察杠杆收缩。')
    risks.append('扣非利润、存货与应收明细尚未接入，风险清单并不完整。')
    rows = ''.join('<tr>'+''.join(f'<td>{E(v)}</td>' for v in [f['name'],f['direction'],f['lag'],f['metric'],f['source'],'待核验：'+f['failure']])+'</tr>' for f in card['factors'])
    return f'''<section class="block" id="research"><h2>未来半年验证卡</h2>
<p class="sub">研究窗口：2026-11 至 2027-05。以下为研究假设，更新于 {E(card['updated'])}；尚未完成全部事实核验。</p>
<div class="nd"><h3>核心假设</h3><p>{E(card['thesis'])}</p><p><b>共同驱动：</b>{E('、'.join(card['drivers']))}</p></div>
<div class="nd"><h3>已有数据与证据边界</h3><p>{E(evidence)}</p><p><b>经营变化：</b>{E(growth_description(a['f']['qs']))}</p><p><b>价格反映了多少改善：</b>历史 PE 分位仅显示相对位置。未来利润、合理估值区间和悲观情景尚未验证，不据此给目标价。</p></div>
<div class="tblwrap"><table class="mt"><thead><tr><th>核心因子</th><th>方向与条件</th><th>传导时间</th><th>验证指标</th><th>待查来源</th><th>降级条件</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><b>下次验证：</b>{E(card['next_check'])}</p>
<div class="nd"><h3>独立风险提示</h3><ul>{''.join('<li>'+E(r)+'</li>' for r in risks)}</ul><p>风险不与正分相抵；总分不代表收益率、胜率或仓位。</p></div></section>'''

def exposure_html(analyses, root):
    cards = load_cards(root); groups = {}
    for a in analyses:
        for driver in cards.get(a['cfg']['code'], {}).get('drivers', []):
            groups.setdefault(driver, []).append(a['cfg']['name'])
    rows = ''.join(f'<tr><th>{E(k)}</th><td>{len(v)}</td><td>{E("、".join(v))}</td></tr>' for k,v in groups.items())
    return '<section class="block"><h2>共同驱动因素</h2><p class="sub">研究标签可重叠，数量不是持仓权重，也不是统计相关系数；用于发现多个行业背后的共同风险。</p><div class="tblwrap"><table class="mt"><thead><tr><th>驱动因素</th><th>股票数</th><th>股票</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>'
