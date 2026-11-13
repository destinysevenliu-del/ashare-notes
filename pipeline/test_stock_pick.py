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
  body=(ROOT/'docs/stocks/index.html').read_text()
  self.assertIn('id="logic1"',body);self.assertIn('id="logic2"',body);self.assertIn('乐凯胶片',body)
if __name__=='__main__':unittest.main()
