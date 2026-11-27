"""Shared admission contracts: sector reason first; no price/fund weighted score."""
from html import escape as E

def admission(s,v):
    sid=s['id'];v=v or {};sub=v.get('sub','');mix=v.get('mix','')
    if s['rating']=='逆风':return '未通过','板块逆风，当前不进入景气候选'
    if sid in ('a-coal','hk-energy') and ('煤种结构' in mix or '煤种结构' in sub):return '待核','动力煤与焦煤的利润贡献尚未分清'
    if sid=='a-coal' and '煤炭41%' in mix:return '待核','煤炭毛利占41%，煤化工与天然气合计更大；不能直接套动力煤理由'
    if sub.startswith('一体化'):return '待核','需要按上游、炼化与贸易分部核对主利润来源'
    subs={b['name']:b['state'] for b in s.get('subs',[])}
    if sub in subs:
        if subs[sub] in ('顺风','前半段'):return '通过',sub+'业务与本窗口理由匹配；'+mix
        return '待核',sub+'：行业证据'+subs[sub]+'，先放观察'
    if sid=='a-bank' and v:return '通过','银行独立分红子池；资本与拨备在财务核验中验收'
    if sid=='hk-tanker' and sub=='油轮':return '通过','油轮业务匹配；分部利润与现金仍需核验'
    review=v.get('business_review') or {}
    if review.get('status')=='verified' and review.get('source') and review.get('reason')==s['stock_contract']['reason']:
        return '通过',review['basis']
    return '待核',s.get('stock_contract',{}).get('admission','业务归属尚未验证')+'；行业分类和财务初筛不代替业务证据'

def contract_text(s):
    c=s['stock_contract']
    return ('赛道归属｜'+c['reason']+'：'+c['admission']+'。兑现质量｜'+c['primary_rank']+'，同理由、同报告期比较；现金流、毛利与周转异常单独降级。价格反映｜主估值'+c['primary_valuation']+'，决定追、等或不追。D/G只约束组合仓位与节奏，H只做价格验证。')

def contract_html(s):
    return '<p class="note"><b>本窗口个股规则：</b>'+E(contract_text(s))+'</p>'

def remaining_html(r):
    rows=r.get('remaining',[])
    if not rows:return ''
    return '<details class="more"><summary>其余财务初筛对象（'+str(len(rows))+'只，未进入已验证排序）</summary><p class="note">'+E('；'.join(x['name']+'（'+x['code']+'）：'+x.get('admission_reason','业务待核') for x in rows))+'</p></details>'

def income_gate(market,industry,sectors):
    """Only researched stable-income directions enter this independent reason pool."""
    sid='a-bank' if market=='a' and '银行' in industry else 'hk-telecom' if market=='hk' and any(k in industry for k in ('银行','电讯','电信')) else None
    if not sid:return '待核',industry+'尚未完成稳定分红的板块传导；保留为数据观察，不进正式红利池'
    s=sectors.get(sid,{})
    if s.get('no_new'):return '暂停',s['no_new']
    if s.get('rating') not in ('顺风','前半段'):return '待核','所属板块尚未通过'
    return '通过','大盘利率条件 → '+s['title']+' → 稳定现金分红子池；资本与现金覆盖仍须核验'
