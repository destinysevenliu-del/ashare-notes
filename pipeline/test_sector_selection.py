"""Sector selection must follow the macro tailwind map, cite sources, and give executable tracking."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1]
D=json.loads((ROOT/'data/sector_selection.json').read_text())
class SelTest(unittest.TestCase):
 def test_fields(self):
  for s in D['sectors']:
   self.assertIn(s['rating'],['顺风','前半段','等开关','逆风'])
   self.assertEqual(set(s['parts']),{'num','den','tap'})
   for p in s['parts'].values():self.assertFalse(set(p['refs'])-set(D['sources']))
   self.assertTrue(s['tracking']);self.assertTrue(s['checks']);self.assertTrue(s['handoff'])
   for r in s['tracking']:self.assertEqual(len(r),5)
   for r in s['checks']:self.assertEqual(len(r),5)
 def test_screen_numbers_match(self):
  rows={r['bk']:r for r in json.loads((ROOT/'docs/data/sector-screen.json').read_text())['rows']}
  self.assertAlmostEqual(rows['BK0457']['np_yoy'],-24,delta=1);self.assertAlmostEqual(rows['BK1250']['np_yoy'],27,delta=1)
  for s in D['sectors']:
   for b in s['bks']:self.assertIn(b,rows)
 def test_pages_and_macro_consistency(self):
  for s in D['sectors']:
   body=(ROOT/'docs/boards'/(s['id']+'.html')).read_text();self.assertIn(s['verdict'],body)
  hub=(ROOT/'docs/boards/index.html').read_text()
  for s in D['sectors']:
   if s['market']=='a':self.assertIn('data-sector="'+s['id']+'"',hub)
  macro=json.loads((ROOT/'data/market_thesis.json').read_text())['macro_regime']['markets']
  for m in ['a','hk']:
   text=json.dumps(macro[m]['sectors'],ensure_ascii=False)
   for s in D['sectors']:
    if s['market']==m:self.assertIn(s['rating'],text)
  self.assertIn('已移出',(ROOT/'docs/boards/a-copper.html').read_text())
if __name__=='__main__':unittest.main()
