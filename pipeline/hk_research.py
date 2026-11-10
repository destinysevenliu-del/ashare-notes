"""Render sourced HK research with explicit dates, coverage and inference labels."""
import copy
import html
import json
from pathlib import Path


def load(root, asof):
    path = Path(root) / 'data/hk_research.json'
    if not path.exists():
        return {'sections': {}}
    research = json.loads(path.read_text())
    sections = research['sections']
    context_path = Path(root) / 'data/raw/hk/context.json'
    context = json.loads(context_path.read_text()) if context_path.exists() else {'series': {}}
    for key, series in context['series'].items():
        rows = [row for row in series['rows'] if row['date'] <= asof]
        if not rows:
            continue
        latest = rows[-1]
        description = f"{latest['value']:.4f} {series['unit']}"
        if len(rows) > 20:
            old = rows[-21]
            delta = latest['value'] - old['value']
            if key in ('us10', 'us_hy_oas'):
                change = f'{delta * 100:+.1f}bp'
            elif key == 'usd_broad':
                change = f"{(latest['value'] / old['value'] - 1) * 100:+.2f}%"
            else:
                change = f'{delta:+.2f} 点'
            description += f"，较 {old['date']}（20 个有效观测间隔前）{change}"
        fact = {'label': series['name'], 'value': description, 'date': latest['date'],
                'source': series['source'], 'scope': '日数据。美国市场／全球环境代理'}
        sections['D']['facts'].append(fact)
        if key == 'usd_broad':
            sections['A']['facts'].append(copy.deepcopy(fact))
    valuation_path = Path(root) / 'data/raw/hk/valuations.json'
    if valuation_path.exists():
        valuations = json.loads(valuation_path.read_text())
        names = {'hsi': '恒生指数', 'hscei': '恒生国企指数'}
        for key, name in names.items():
            rows = [row for row in valuations.get('indices', {}).get(key, []) if row['date'] <= asof and row.get('pe_ratio')]
            if rows:
                latest = rows[-1]
                value = f"PE {latest['pe_ratio']:.2f} 倍，股息率 {latest['dividend_yield_pct']:.2f}%。"
                first = rows[0]
                value += f"公开可得 {len(rows)} 个日观测，{first['date']} PE {first['pe_ratio']:.2f} 倍。"
                sections['F']['facts'].insert(0, {'label': name, 'value': value, 'date': latest['date'], 'source': latest['source'], 'scope': '恒生指数公司公开日报，保留真实短窗历史'})
    return research


def render(entry, reviewed_at):
    escape = html.escape
    rows = []
    for fact in entry.get('facts', []):
        scope = '<small class="hk-scope">' + escape(fact.get('scope', '')) + '</small>'
        rows.append('<tr><th scope="row">' + escape(fact['label']) + '</th><td>'
                    + escape(str(fact['value'])) + scope + '</td><td>' + escape(fact['date'])
                    + '</td><td><a href="' + escape(fact['source'], quote=True)
                    + '" target="_blank" rel="noopener noreferrer">原始材料</a></td></tr>')
    body = '<div class="hk-evidence"><div class="hk-call"><span class="tag">研究判断</span><b>'
    body += escape(entry['headline']) + '</b><small>复核于 ' + escape(reviewed_at) + '</small></div>'
    body += '<p class="hk-mobilehint">表格可左右滑动查看完整日期和原始来源。</p>'
    body += '<div class="tblwrap"><table class="mt"><thead><tr><th>已核验事实</th><th>数值与口径</th><th>统计期／日期</th><th>来源</th></tr></thead><tbody>'
    body += ''.join(rows) + '</tbody></table></div>'
    for key, label in [('analysis', '影响分析'), ('counter', '相反证据'), ('monitor', '验证条件'), ('boundary', '覆盖范围')]:
        if entry.get(key):
            body += '<p><b>' + label + '</b>　' + escape(entry[key]) + '</p>'
    body += '</div>'
    return body
