"""Downstream regression: evidence gate, financial ordering, and layout contract."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(sys.argv[1]).resolve();sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import logic1_rules as L,stockpick as SP,hk_pick as H,downstream as D,dividend
S=json.loads((ROOT/'data/sector_selection.json').read_text());SEC={s['id']:s for s in S['sectors']}
V=SP.verify_data(ROOT)
class Downstream(unittest.TestCase):
 def test_contracts_cover_both_markets(self):
  self.assertEqual(len(SEC),16)
  for s in SEC.values():
   c=s['stock_contract'];self.assertTrue(c['reason']);self.assertTrue(c['primary_rank']);self.assertIn(c['primary_valuation'],['PB','正常化PE','股息率','税后股息率'])
 def test_missing_business_never_passes(self):
  self.assertEqual(D.admission(SEC['a-coal'],{})[0],'待核')
  for c in ['600985','600256','600188']:self.assertEqual(D.admission(SEC['a-coal'],V[c])[0],'待核')
  self.assertEqual(D.admission(SEC['a-coal'],V['601101'])[0],'通过')
 def test_position_and_funding_do_not_reorder(self):
  a=L.select_v2(ROOT,S['sectors'])
  def reverse(t,x):return {'fund':'中','pos':'好' if x['code'][-1]<'5' else '差','chip':'差','notes':[]}
  with patch.object(L,'_layers',reverse):b=L.select_v2(ROOT,S['sectors'])
  for k in a:self.assertEqual([x['code'] for x in a[k]['picks']],[x['code'] for x in b[k]['picks']])
 def test_no_valuation_admission_or_composite(self):
  self.assertTrue(L.RULES['a-semiconductor']['filter']({'mc':500,'q_np':10,'np_yoy':50,'pe':1000}))
  for r in L.select_v2(ROOT,S['sectors']).values():
   for x in r['picks']:self.assertNotIn('total',x);self.assertNotIn('score',x)
 def test_legacy_whitelist_no_longer_excludes_upstream(self):
  r=L.select_v2(ROOT,S['sectors'])['a-oil'];self.assertIn('600938',[x['code'] for x in r['picks']])
  petro=[x for x in r['picks'] if x['code']=='600028'][0];self.assertEqual(petro['admission'],'待核');self.assertIsNone(petro['rank_value'])
 def test_cash_failure_cannot_head_quality_ranking(self):
  rows=L.select_v2(ROOT,S['sectors'])['a-tanker']['picks'];self.assertEqual(rows[0]['code'],'601872');self.assertIsNone(next(x['rank_value'] for x in rows if x['code']=='600026'))
 def test_hk_comparison_cohort_includes_report_and_business(self):
  rows,_=H.select(ROOT,S)
  for r in rows.values():
   for x in r['picks']:
    self.assertIn(x.get('rpt','报告期缺失'),x['cohort']);self.assertNotIn('total',x)
 def test_uncovered_dividend_not_admitted(self):
  self.assertEqual(D.income_gate('hk','黄金及贵金属',SEC)[0],'待核')
 def test_existing_structure_and_new_roles_render(self):
  for f in ['stocks/index.html','stocks/hk.html']:
   h=(ROOT/'docs'/f).read_text()
   for t in ['class="sc-grid"','class="ch"','赛道归属','兑现质量','价格反映','D/G']:self.assertIn(t,h)
   for t in ['三分之一','三层合成排序','综合排名＝']:self.assertNotIn(t,h)
   self.assertEqual(h.count('id="l1-a-oil"'),0) # broad sector lists moved to coverage archive
   self.assertEqual(h.count('<article class="sc"'),4 if f=='stocks/index.html' else 2)
  for sid in SEC:
   h=(ROOT/'docs/boards'/(sid+'.html')).read_text()
   self.assertIn('id="parts"',h);self.assertIn('id="tracking"',h);self.assertIn('id="handoff"',h)
   self.assertNotIn('<b>相关公司：</b>',h)
if __name__=='__main__':unittest.main()
