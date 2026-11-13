"""Regime framework (分子/分母/水龙头): numbers must recompute, checks must be falsifiable, sector notes must agree."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import macro_regime_calc
class RegimeTest(unittest.TestCase):
 def setUp(self):
  self.d=json.loads((ROOT/'data/market_thesis.json').read_text());self.g=self.d['macro_regime']
 def test_evidence_recomputes(self):
  self.assertEqual(macro_regime_calc.compute(ROOT),json.loads((ROOT/'docs/data/macro-regime-evidence.json').read_text()))
 def test_structure_and_refs(self):
  for k in ['a','hk']:
   x=self.g['markets'][k];self.assertEqual([p['key'] for p in x['parts']],['num','den','tap'])
   for p in x['parts']:self.assertFalse(set(p['refs'])-set(self.d['sources']))
   self.assertEqual(len(x['scenarios']),3)
   for c in x['checks']:
    self.assertEqual(len(c),6);self.assertTrue(all(c))
 def test_pages(self):
  for f,k in [('docs/index.html','a'),('docs/hk/index.html','hk')]:
   body=(ROOT/f).read_text();self.assertIn(self.g['markets'][k]['verdict'],body);self.assertIn('id="macro-legacy"',body)
 def test_sector_groups(self):
  s={x['id']:x for x in json.loads((ROOT/'data/industry_research.json').read_text())['sectors']}
  self.assertEqual(s['hk-internet']['review']['group'],'等待开关')
  for i in ['a-coal','a-tanker','hk-tanker','hk-energy']:self.assertIn('PPI',s[i]['review']['downgrade'])
if __name__=='__main__':unittest.main()
