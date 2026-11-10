"""Run with: python3 -I pipeline/test_framework_v2.py <project root>."""
import sys,json,unittest,tempfile,runpy,contextlib,io
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1]
sys.path.insert(0,str(ROOT/'pipeline'))
import research,stockpage
class FrameworkTest(unittest.TestCase):
 def test_same_target_year(self):
  h=[{'date':'2026-10-09','eps':{'2027':4,'2026':3}}]
  self.assertAlmostEqual(research.revision(h,'2026-11-09',2027,4.4)['change'],10)
  self.assertIsNone(research.revision(h,'2026-11-09',2028,5))
  self.assertIsNone(research.revision(h,'2026-10-19',2027,5))
  self.assertIsNone(research.revision(h,'2026-12-09',2027,5))
 def test_no_fabricated_observation(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'data/snapshots').mkdir(parents=True)
   e=dict(y1=2026,e1=3,y2=2027,e2=4,orgs=12)
   research.record_consensus(d,'1',{},e)
   self.assertFalse(Path(d,'data/snapshots/consensus.json').exists())
   raw={'consensus_observed_at':'2026-11-09T16:00:00+08:00'}
   research.record_consensus(d,'1',raw,e);research.record_consensus(d,'1',raw,e)
   self.assertEqual(len(json.loads(Path(d,'data/snapshots/consensus.json').read_text())['1']),1)
 def test_growth_not_acceleration(self):
  text=research.growth_description([dict(yoy=81,qoq=36),dict(yoy=162,qoq=8)])
  self.assertIn('同比增速较上一季提高 81.0',text)
  self.assertIn('环比增速较上一季降低 28.0',text)
 def test_pool_and_pages(self):
  stocks=json.loads((ROOT/'data/stocks.json').read_text())['stocks']
  cards=research.load_cards(ROOT)
  self.assertEqual(len(stocks),20)
  self.assertEqual(set(cards),{x['code'] for x in stocks})
  for stock in stocks:
   html=(ROOT/'docs/stocks'/f"{stock['code']}.html").read_text()
   self.assertIn('未来半年验证卡',html)
   self.assertNotIn('二阶导向上',html)
   self.assertNotIn('订单旺盛',html)
   self.assertIn('不据此给目标价',html)
 def test_actual_analysis(self):
  sys.argv=['build.py',str(ROOT)]
  with contextlib.redirect_stdout(io.StringIO()): ctx=runpy.run_path(str(ROOT/'pipeline/build.py'))
  for a in ctx['stock_analyses']:
   self.assertIsNone(a['scores']['B'])
   if a['revision'] is None: self.assertIsNone(a['scores']['E'])
   self.assertTrue(all(score==0 for txt,score in a['nodes']['C'] if '环比' in txt))
  for a in ctx['BOARDS'].values():
   self.assertIsNone(a['scores']['B']);self.assertIsNone(a['scores']['E'])
  self.assertEqual(ctx['R']['score_rows'][0]['score'],0)
if __name__=='__main__':unittest.main()
