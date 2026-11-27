"""Market-specific derivation; sector verdicts are read from the sector source of truth."""
import json
from pathlib import Path
from html import escape as E

def load(root,market):
    d=json.loads((Path(root)/'data/market_thesis.json').read_text())
    sectors=json.loads((Path(root)/'data/sector_selection.json').read_text())['sectors']
    by={s['id']:s for s in sectors if s['market']==market}
    routes=d['macro_regime']['markets'][market]['routes']
    referenced={i for r in routes for i in r['sector_ids']}
    if referenced!=set(by):raise ValueError('Macro routes must cover exactly this market: '+market)
    return d,by,routes

def flow(market):
    labels=['中国需求与上市盈利','中国利率与风险补偿','国内资金与稳市政策'] if market=='a' else ['中国经营与港股盈利','美元、港元与风险补偿','南向、外资与股票供给']
    out='<svg class="mp-flow" viewBox="0 0 1200 240" role="img" aria-label="先分析大盘三个部件，再推导风向，经行业验证得出板块结论"><defs><marker id="mp-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0L8,4L0,8" fill="#6d8295"/></marker></defs>'
    for i,(title,label) in enumerate(zip(['分子 · A/B/C/E','分母 · D/E/F','水龙头 · B/G/H'],labels)):
        y=10+i*76
        out+=f'<rect x="5" y="{y}" width="290" height="62" rx="7" fill="#f0f5f9" stroke="#c9d6e2"/><text x="20" y="{y+24}" font-size="15" fill="#39536a">{title}</text><text x="20" y="{y+47}" font-size="15" fill="#233d54">{label}</text><path d="M295 {y+31} H325 V117 H350" stroke="#6d8295" fill="none" marker-end="url(#mp-arrow)"/>'
    for x,title,lines in [(350,'① 大盘结论',['半年基准与上／下行情景','形成顺风、逆风与待验证条件']),(640,'② 行业逐项验收',['利润现金 · 估值位置 · 资金','对照反证、开关与失效条件']),(930,'③ 板块结论',['顺风 / 前半段 / 等开关 / 逆风','再交给个股；执行纪律单独约束'])]:
        out+=f'<rect x="{x}" y="66" width="260" height="105" rx="8" fill="#fff" stroke="#7390a9"/><text x="{x+14}" y="95" font-size="18" fill="#223d54">{title}</text>'
        for j,line in enumerate(lines):out+=f'<text x="{x+14}" y="{125+j*22}" font-size="13" fill="#526a80">{line}</text>'
        if x<930:out+=f'<path d="M{x+260} 117 H{x+287}" stroke="#6d8295" marker-end="url(#mp-arrow)"/>'
    return out+'</svg>'

def policy(x):
    p=x['policy_assessment']
    return '<section class="mp-policy"><h4>政策先改变哪一环，力度和持续性怎么验收</h4><div class="mp-grid">'+''.join('<article><b>'+name+'</b><p>'+E(p[k])+'</p></article>' for k,name in [('force','作用与力度'),('duration','持续性'),('next','下一次验收')])+'</div></section>'

def mapping(root,market,prefix):
    d,sectors,routes=load(root,market);name='A股' if market=='a' else '港股';board=prefix+('boards/index.html' if market=='a' else 'boards/hk.html')
    out='<section id="regime-sectors" data-market="'+market+'"><h3>从'+name+'大盘到行业筛选：证据通过后才确定板块</h3>'+flow(market)+'<div class="tblwrap"><table class="mt regime-table mp-table"><thead><tr><th>大盘风向与来源</th><th>行业必须证明什么</th><th>验收结果与板块档位</th></tr></thead><tbody>'
    for r in routes:
        out+='<tr><th><b>'+E(r['name'])+'</b><small>'+E(r['part'])+'</small><p>'+E(r['wind'])+'</p></th><td>'+E(r['verify'])+'</td><td><p>'+E(r['result'])+'</p>'
        for sid in r['sector_ids']:
            s=sectors[sid];out+='<a class="mp-sector" data-derived-sector="'+sid+'" href="'+prefix+'boards/'+sid+'.html">'+E(s['title'])+' · '+E(s['rating'])+'</a>'
        out+='</td></tr>'
    return out+'</tbody></table></div><p class="regime-next"><a href="'+board+'">进入'+name+'板块：查看逐行业的利润、估值、位置与改判条件 →</a></p></section>'

def upstream(root,market):
    d,_,_=load(root,market);x=d['macro_regime']['markets'][market];home='../index.html' if market=='a' else '../hk/index.html'
    return '<section class="mp-upstream" id="upstream"><h2>第一步：本市场大盘给出的条件</h2><p><b>'+E(x['verdict'])+'</b></p><div class="mp-grid">'+''.join('<article><b>'+E(p['name'])+'</b><p>'+E(p['implication'])+'</p></article>' for p in x['parts'])+'</div><p><a href="'+home+'#regime">返回完整大盘分析与传导 →</a></p><p>第二步：下面按行业自身的盈利、估值与资金证据验收；档位是研究结论，新增仍受市场执行条件约束。</p></section>'

CSS='''
.mp-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.mp-grid article{padding:14px;background:#f3f6f9;border-radius:8px}.mp-grid p{margin:6px 0;font-size:14px;line-height:1.8}.mp-policy,.mp-upstream{margin:20px 0;padding:18px;border:1px solid #d5e0e9;border-radius:10px}.mp-flow{display:block;width:100%;height:auto;margin:16px 0}.mp-table th{width:30%;vertical-align:top;font-weight:400}.mp-table th small{display:block;color:#5c7184}.mp-table p{margin:4px 0 8px;font-size:13.5px;line-height:1.8}.mp-table td{width:35%}.mp-sector{display:inline-block;margin:4px 8px 4px 0;background:#eef3f7;padding:4px 8px;border-radius:5px;text-decoration:none;font-size:13px}.mp-execution{border-left:3px solid #9a7154;background:#faf5ef;padding:12px 16px;margin:18px 0}.mp-execution p{margin:5px 0;font-size:14px}.mp-order{display:flex;gap:16px;flex-wrap:wrap;font-size:14px;padding:12px 16px;background:#edf3f8;border-radius:8px;margin:12px 0}.mp-withdrawn{padding:18px;border-left:4px solid #9a7154;background:#faf5ef;line-height:1.9}
@media(max-width:850px){.mp-grid{grid-template-columns:1fr}.mp-flow{min-width:850px}.mp-flow-wrap{overflow:auto}}
'''
