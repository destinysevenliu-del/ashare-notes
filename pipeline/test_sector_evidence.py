"""Evidence regression: prevent mixed valuation windows and fabricated price/flow labels."""
import json,sys,unittest,math
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1]
d=json.loads((ROOT/'data/industry_research.json').read_text())
class EvidenceTest(unittest.TestCase):
 def test_sources_and_windows(self):
  for s in d['sectors']:
   self.assertEqual(set(s['node_detail']),set('ABCDEFGH'))
   for n in s['node_detail'].values():
    for r in n['rows']:
     self.assertTrue(r['date']);self.assertTrue(r['scope'])
     if r['source']:self.assertIn(r['source'],d['sources'])
   for v in s['valuation']['items']:
    if v['percentile'] is not None:
     self.assertLessEqual(v['percentile'],100);self.assertGreaterEqual(v['percentile'],0)
     self.assertTrue(any(x in v['window'] for x in ['年','2002']))
 def test_price_metrics_recompute(self):
  for s in d['sectors']:
   if not s.get('position'):continue
   p=s['position'];vals=[x['value'] for x in p['series']]
   self.assertAlmostEqual(vals[-1]/vals[-21]*100-100,p['d20'],delta=.002)
   if p['d60'] is not None:self.assertAlmostEqual(vals[-1]/vals[-61]*100-100,p['d60'],delta=.002)
   if p['drawdown'] is not None:self.assertAlmostEqual(vals[-1]/max(vals[-250:])*100-100,p['drawdown'],delta=.002)
 def test_distinct_hk_and_a_valuations(self):
  s={x['id']:x for x in d['sectors']}
  self.assertEqual(s['a-semiconductor']['valuation']['items'][0]['percentile'],23.51)
  self.assertTrue(all(i['percentile'] is None for i in s['hk-hardware']['valuation']['items']))
  self.assertIn('剔除负值',s['a-coal']['valuation']['items'][0]['metric'])
 def test_public_evidence_no_company_research(self):
  e=json.loads((ROOT/'docs/data/industry_evidence.json').read_text())
  for x in e['sectors'].values():self.assertNotIn('top',x['financials']);self.assertNotIn('cfg',x)
 def test_local_source_links(self):
  for u in d['sources'].values():
   if u.startswith('../'):self.assertTrue((ROOT/'docs/boards'/u).resolve().exists(),u)
if __name__=='__main__':unittest.main()
