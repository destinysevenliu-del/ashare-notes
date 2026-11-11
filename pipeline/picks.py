"""Sector-only six-month study; historical stock/weight input is not rendered."""
from pathlib import Path
import framework_review

def build(ctx):
    body='<div class="hero"><h1>未来半年：先从A–H选择板块</h1><p class="sum">个股及仓位尚未确定。旧20股方案仅保留历史数据，不作为当前方案。</p></div>'
    for market,label in [('a','A股'),('hk','港股')]:
        body+='<details class="l1" open><summary><h2>'+label+'半年板块研究</h2></summary>'+framework_review.render(ctx,market)+'</details>'
    out=Path(ctx['SITE'])/'picks';out.mkdir(exist_ok=True)
    (out/'index.html').write_text(ctx['page']('半年板块 | A股框架笔记','pk',body,'../'))
    return {'count':0,'held':0}
