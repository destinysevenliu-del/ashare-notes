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
   self.assertTrue(0<=x['pos']<=0.25)
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
if __name__=='__main__':unittest.main()
