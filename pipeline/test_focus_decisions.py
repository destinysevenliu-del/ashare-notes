import sys,unittest,json
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import focus_decisions as F
import logic1_rules as L
import stockcards as C
import stockpick as S
class FocusTests(unittest.TestCase):
 def test_precedence(self):
  x={'thesis_valid':True,'missing':['缺估值'],'entry_met':False,'next':'补齐数据'}
  self.assertEqual(F.decide(x,{'paused':True,'reason':'恢复未完成'})['status'],'暂停新增')
  self.assertEqual(F.decide(x,{'paused':False})['status'],'待核')
  self.assertEqual(F.decide({**x,'missing':[]},{'paused':False})['status'],'等待')
  self.assertEqual(F.decide({**x,'missing':[],'entry_met':True},{'paused':False})['status'],'条件满足')
  self.assertEqual(F.decide({**x,'thesis_valid':False},{'paused':True})['status'],'移出关注')
 def test_position_missing_and_cutoff(self):
  self.assertIsNone(F.position([], '2026-11-27'))
  rows=[{'date':'2026-11-26','close':10,'amount':100},{'date':'2026-11-27','close':11,'amount':100},{'date':'2026-11-30','close':99,'amount':100}]
  x=F.position(rows,'2026-11-27');self.assertEqual(x['close'],11);self.assertEqual(x['event_return'],10)
  self.assertIsNone(x['ma60']);self.assertIsNone(x['range_52'])
 def test_growth_target_not_forced_to_two_r(self):
  e={'close':95,'dd':-5,'pos52':.9,'vsMA60':-5}
  p=L.price_levels('growth',{'en':e});self.assertLess(p['rr'],2);self.assertFalse(p['opportunity_valid'])
 def test_pending_valuation_can_finish_with_documented_review(self):
  v={'pb':1,'pb95':2,'pbpct5':20,'pe_ttm':12,'pe_norm':10,'valuation_window':'近五年','val_date':'2026-11-27','current_price':10}
  self.assertEqual(S.value_step('growth',v,'买入')[0],'待核')
  v['valuation_review']={'status':'approved','metric':'正常化PE','denominator':1,'buy_max':12,'avoid_above':18,'as_of':'2026-11-27','valid_until':'2026-12-27','source':'https://example.com/report','basis':'正常化每股利润，剔除一次性收益','reviewer':'人工复核'}
  self.assertEqual(S.value_step('growth',v,'买入')[0],'通过')
  v['current_price']=20;self.assertEqual(S.value_step('growth',v,'买入')[0],'否决')
  v['valuation_review']['valid_until']='2026-11-26';self.assertEqual(S.value_step('growth',v,'买入')[0],'待核')
 def test_blocked_card_no_green_price_badge(self):
  p={'close':10,'buy':(9,11),'sell':12,'stop':8,'rr':1,'where':'在买入区'}
  h=C.card('test','测试','','不买：核验未通过','bad',p,[])
  self.assertNotIn('class="st st-buy"',h);self.assertIn('暂停新增',h)
 def test_focus_outputs(self):
  d=F.prepare(ROOT);self.assertEqual(len(d['items']),3)
  for x in d['items']:
   self.assertTrue(x['missing']);self.assertTrue(x['next']);self.assertTrue(x['invalidate']);self.assertNotEqual(x['decision']['status'],'条件满足')
  a=(ROOT/'docs/index.html').read_text();self.assertLess(a.index('id="focus"'),a.index('id="horizon"'))
  self.assertIn('id="horizon"',a);self.assertNotIn('id="horizon" open',a)
if __name__=='__main__':unittest.main()
