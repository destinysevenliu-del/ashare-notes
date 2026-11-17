"""判断链与煤炭、石油复核的验收（2026-11-17）。用法：python3 -I pipeline/test_chain.py <根目录>"""
import json,sys,unittest
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve();sys.argv=sys.argv[:1]
sys.path.insert(0,str(ROOT/'pipeline'))
import stockpick,logic1_rules
S={s['id']:s for s in json.loads((ROOT/'data/sector_selection.json').read_text())['sectors']}
def pl(c,buy=(10,11),sell=14,stop=9):
    return {'close':c,'buy':buy,'sell':sell,'stop':stop,'where':'在买入区' if buy[0]<=c<=buy[1] else ('高于买入区' if c>buy[1] else '低于买入区'),'rr':1.0}
X=lambda c,**k:{'code':'X','pl':pl(c,**k),'chip':'中'}
V_OK={'X':{'sub':'动力煤','fcf_div':2,'ocf_np':2,'fcf_ttm':10,'div':5,'np_ttm':10,'np_avg5':10,'pb':1,'pb95':2,'pbpct5':50,'pe_ttm':8,'pe_norm':15,'mix':''}}
class ChainTest(unittest.TestCase):
 def test1_price_in_zone_but_unverified_is_not_buy(self):
  ch=stockpick.chain('a-tanker',S['a-tanker'],'upstream',X(10.5),{})
  self.assertEqual(ch['view'],'价格到位·待核')
  ch=stockpick.chain('a-coal',S['a-coal'],'upstream',X(10.5),V_OK)
  self.assertNotEqual(ch['view'],'可执行')   # 估值仍待核
 def test2_yoy_decline_does_not_downgrade(self):
  for sid in ('a-coal','a-oil'):
   s=S[sid];self.assertEqual(s['rating'],'前半段')
   for r in s['tracking']:
    if '同比' in r[0]:self.assertNotIn('降级',r[3])
   self.assertIn('不单独',s['switch']+s['why'])
 def test3_oil_drop_does_not_carry_to_refining(self):
  s=json.loads(json.dumps(S['a-oil']))
  for b in s['subs']:b['state']='逆风' if b['name']=='上游开采' else '前半段'
  self.assertEqual(stockpick.sub_state(s,{'sub':'炼化及贸易'})[0],'通过')
  self.assertEqual(stockpick.sub_state(S['a-oil'],{'sub':'一体化（上游＋炼化）'})[0],'待核')
 def test4_low_ttm_pe_is_not_cheap(self):
  ch=stockpick.chain('a-coal',S['a-coal'],'upstream',X(10.5),V_OK)
  self.assertEqual(dict((a,b) for a,b,_ in ch['steps'])['估值'],'待核')
  self.assertIn('正常化估值待验证',S['a-oil']['parts']['den']['text'])
 def test5_single_day_85_is_warning(self):
  row=[r for r in S['a-oil']['tracking'] if '单日' in r[3]][0]
  self.assertEqual(row[5],'预警');self.assertIn('不等于命题证伪',row[3])
  self.assertIn('不是EIA给出的投资阈值',S['a-oil']['note85'])
 def test6_plan_vs_current_rr(self):
  e={'close':12.0,'dd':-20.0,'pos52':0.5,'vsMA60':0.0}
  p=logic1_rules.price_levels('upstream',{'en':e})
  mid=sum(p['buy'])/2
  self.assertAlmostEqual(p['rr'],round((p['sell']-mid)/(mid-p['stop']),1))
  self.assertAlmostEqual(p['rr_now'],round((p['sell']-12.0)/(12.0-p['stop']),1))
 def test7_pages_consistent_after_build(self):
  idx=(ROOT/'docs/stocks/index.html').read_text();rules=(ROOT/'docs/stocks/selection-rules.html').read_text()
  self.assertIn('class="ch"',idx);self.assertIn('现价盈亏比',idx);self.assertIn('价格到位·待核',idx)
  self.assertIn('当前生效',rules);self.assertNotIn('子池合同与研究席位</h2>',rules)
  for sid in ('a-coal','a-oil'):
   b=(ROOT/'docs/boards'/(sid+'.html')).read_text();self.assertIn('id="subs"',b);self.assertIn('性质',b)
  self.assertNotIn('利润是真金白银',idx);self.assertNotIn('不预期创新高',idx)
  self.assertNotIn('说明部分风险已反映',idx)
 def test8_all_sectors_rules(self):
  D=json.loads((ROOT/'data/sector_selection.json').read_text())
  for x in D['sectors']:
   self.assertNotIn('PPI环比连续两个月≤0',x['switch'],x['id'])
   for r in x['tracking']:
    self.assertEqual(len(r),6,(x['id'],r[0]));self.assertTrue(r[5],(x['id'],r[0]))
    if 'PPI' in r[0] and '同比' in r[0]:self.assertNotIn('降级',r[3],(x['id'],r[0]))
    if r[0]=='美国10年期国债':self.assertIn('5.15',r[2],x['id'])
   for c in x['checks']:
    for t in c[3:5]:
     if '降为逆风' in t or '升为顺风' in t:self.assertTrue(any(k in t for k in ('且','同时','复核','决定')),(x['id'],t))
 def test9_all_candidates_verified(self):
  V=json.loads((ROOT/'data/raw/stock_pick/verify.json').read_text())
  L=json.loads((ROOT/'data/stock_pick.json').read_text())['logic1_list']['sectors']
  for sid,cs in L.items():
   for c in cs:self.assertIn(c,V,(sid,c))
 def test10_crowding_pause(self):
  s=dict(S['a-bank']);s['no_new']='测试'
  ch=stockpick.chain('a-bank',s,'crowded',X(10.5),{})
  self.assertTrue(ch['view'].startswith('不买'))
if __name__=='__main__':unittest.main()
