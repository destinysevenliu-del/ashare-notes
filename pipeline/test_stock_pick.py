"""Stock pick page: logic 1 follows sector rules; logic 2 rules are quantified and reproducible."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import logic1_rules,logic2_box
class PickTest(unittest.TestCase):
 def test_logic1_rules_cover_selected_a_sectors(self):
  S=json.loads((ROOT/'data/sector_selection.json').read_text())['sectors']
  ids={s['id'] for s in S if s['market']=='a'}
  self.assertEqual(ids,set(logic1_rules.RULES))
  r=logic1_rules.select(ROOT,S)
  for k,v in r.items():
   self.assertTrue(v['picks'],k)
   for x in v['picks']:self.assertTrue(logic1_rules.RULES[k]['filter'](x),(k,x['code']))
 def test_logic2_reference_and_candidates(self):
  P=json.loads((ROOT/'data/stock_pick.json').read_text())['logic2']
  for x in P['top']+[P['reference']]:
   self.assertTrue(logic2_box.qualifies(x),x['code'])
   self.assertTrue(-1<=x['pos']<=2)
   if 'boxL' in x:self.assertAlmostEqual(x['pos'],(x['close']-x['boxL'])/(x['boxH']-x['boxL']),1)
  counts=[n for _,n in P['funnel']];self.assertEqual(counts,sorted(counts,reverse=True))
 def test_page(self):
  body=(ROOT/'docs/stocks/index.html').read_text();box=(ROOT/'docs/stocks/box.html').read_text()
  self.assertIn('id="overview"',body);self.assertIn('id="logic1"',body);self.assertIn('href="box.html"',body)
  self.assertIn('id="logic2"',box);self.assertIn('乐凯胶片',box);self.assertIn('按真实规则做组合回测',box)
 def test_price_levels_are_ordered(self):
  S=json.loads((ROOT/'data/sector_selection.json').read_text())['sectors']
  r=logic1_rules.select_v2(ROOT,S)
  for k,v in r.items():
   for x in v['picks']:
    pl=logic1_rules.price_levels(v['type'],x);self.assertTrue(pl,(k,x['code']))
    self.assertLessEqual(pl['buy'][0],pl['buy'][1]);self.assertGreater(pl['sell'],pl['buy'][1])
    if pl.get('stop'):self.assertLess(pl['stop'],pl['buy'][0])
  P=json.loads((ROOT/'data/stock_pick.json').read_text())['logic2']
  for x in P['top']:
   b=logic1_rules.box_levels(x);self.assertTrue(b['stop']<b['buy'][0]<=b['buy'][1]<b['sell'])
 def test_three_layers(self):
  S=json.loads((ROOT/'data/sector_selection.json').read_text())['sectors']
  r=logic1_rules.select_v2(ROOT,S)
  for k,v in r.items():
   for x in v['picks']:
    for layer in ['fund','pos','chip']:self.assertIn(x[layer],['好','中','差'],(k,x['code']))
    self.assertTrue(x['en'],(k,x['code']))
 def test_price_rules_documented(self):
  D=logic1_rules.PRICE_DOC
  self.assertEqual({r['t'] for r in D['types']},set(logic1_rules.PRICE_RULES))
  self.assertEqual(set(logic1_rules.TYPE.values()),set(logic1_rules.PRICE_RULES))
  b=logic1_rules.box_levels({'close':12.5,'pos':0.5,'W':0.5})
  L=12.5/1.25;H=L*1.5
  self.assertAlmostEqual(b['buy'][1],round(L+0.25*(H-L),2));self.assertAlmostEqual(b['sell'],round(L+0.8*(H-L),2))
  for f,i in [('docs/stocks/index.html','id="price-rules"'),('docs/stocks/box.html','id="box-rules"')]:self.assertIn(i,(ROOT/f).read_text())
 def test_logic2_judge(self):
  import stockpick
  P=json.loads((ROOT/'data/stock_pick.json').read_text())['logic2'];F=stockpick.l2_fund(ROOT)
  rows=stockpick.l2_judged(P,{'on':True},F)
  self.assertEqual(len(rows),len(P['top'])+1)
  for x,j,_ in rows:self.assertIn(j['view'],stockpick.VORD,x['code'])
  bad={'code':'x','pos':0.1,'W':0.5,'swings':2,'sp':1}
  j=logic2_box.judge(bad,{'pb':1,'q3':{'rev_m':150,'np_m':-10,'bps':2,'cfps':0,'roe':-3}},{},True)
  self.assertEqual(j['view'],'剔除：地板不牢')
  j=logic2_box.judge({**bad,'pos':-0.4},{'pb':1,'q3':{'rev_m':900,'np_m':10,'bps':2,'cfps':0,'roe':3}},{},True)
  self.assertEqual(j['view'],'已破位，不接')
  self.assertEqual(logic2_box.judge(bad,None,{},False)['view'],'暂停开新仓')
  self.assertIn('id="l2-judge"',(ROOT/'docs/stocks/box.html').read_text())
if __name__=='__main__':unittest.main()
