"""Decision invariants: reasons, financial comparability, vetoes and issuer cap."""
import sys,json,unittest,copy
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import stock_decisions as s
class DecisionsTest(unittest.TestCase):
 def setUp(self):
  self.policy=s.read(ROOT,'stock_selection_policy.json');self.pool=copy.deepcopy(next(p for p in self.policy['subpools'] if p['id']=='a-semiconductor'))
  self.review={'gate':{'reason':self.pool['reason'],**{k:{'status':'yes','evidence_ids':[k],'source':'source','date':'2026-11-12'} for k in 'ABC'}}}
  self.gate=s.gate_decision(self.pool,self.review)
  self.pack=dict(id='pack1',reviewed=True,period=self.pool['peer_period'],basis=self.pool['financial_basis'],currency='CNY',source='report',normalization_notes='No adjustments required after review',evidence_ids=['financial'],metrics=dict(normalized_profit=130,normalized_profit_previous=100,normalized_fcf=130,normalized_fcf_previous=100,cash_coverage=1.1,gross_margin_delta_pp=1,receivable_days_delta=0,inventory_days_delta=0),checks={name:dict(op='lt' if name in ['现金覆盖','毛利变化'] else 'gt',limit=0 if name in ['现金覆盖','毛利变化'] else 30,source='documented policy',rationale='synthetic test') for name in s.CHECK_METRICS})
  self.quality=s.quality_decision(self.pool,self.pack,self.gate)
  self.pricing=dict(reviewed=True,metric=self.pool['primary_valuation'],date='2026-11-13',valid_until='2026-11-13',source='quote',basis='same pack',range_source='predeclared',range_date='2026-11-12',evidence_ids=['pricing'],financial_pack_id='pack1',value=2,pursue_max=3,avoid_above=5,execution_confirmed=True,secondary_review_complete=True,secondary_vetoes=[dict(metric=self.pool['secondary_valuation'],kind='historical_percentile',op='gt',limit=95,value=60,source='historical',basis='same',date='2026-11-13',observations=300,window='fixed')])
 def price(self):return s.price_decision(self.pool,self.pricing,self.gate,self.quality)
 def rec(self,key,value,pool=None,issuer=None):
  p=pool or self.pool
  return dict(key=key,issuer_id=issuer or key,pool_id=p['id'],gate={'status':'yes'},quality={'status':'ready','value':value,'rank':None,'comparison_key':[p['id'],'2026-09-30','same','CNY']},price={'status':'wait'},shortlisted=False)
 def test_gate_missing_and_wrong_reason(self):
  self.assertEqual(self.gate['status'],'yes');self.assertEqual(s.gate_decision(self.pool,{})['status'],'pending')
  self.review['gate']['reason']='低估值';self.assertEqual(s.gate_decision(self.pool,self.review)['status'],'no')
  self.review['gate']['reason']=self.pool['reason'];self.review['gate']['C']['status']='no';self.assertEqual(s.gate_decision(self.pool,self.review)['status'],'no')
 def test_quality_nonpositive_base_and_basis(self):
  self.assertEqual(self.quality['status'],'ready');self.assertAlmostEqual(self.quality['value'],30)
  self.pack['metrics']['normalized_profit_previous']=0;self.assertEqual(s.quality_decision(self.pool,self.pack,self.gate)['status'],'pending')
  self.pack['basis']='different';self.assertEqual(s.quality_decision(self.pool,self.pack,self.gate)['status'],'pending')
 def test_quality_veto_cannot_be_offset(self):
  self.pack['metrics']['receivable_days_delta']=60
  q=s.quality_decision(self.pool,self.pack,self.gate);self.assertEqual(q['status'],'downgraded');self.assertEqual(s.price_decision(self.pool,self.pricing,self.gate,q)['status'],'avoid')
 def test_revision_year_and_sample(self):
  self.pack['earnings_revision']=dict(verified=True,target_year=2026,same_institutions=True,source='survey',change_pct=30,downgrade_below_pct=-10)
  self.assertEqual(s.quality_decision(self.pool,self.pack,self.gate)['status'],'pending')
  self.pack['earnings_revision'].update(target_year=2027,change_pct=-20)
  self.assertEqual(s.quality_decision(self.pool,self.pack,self.gate)['status'],'downgraded')
 def test_price_single_metric_and_veto(self):
  self.assertEqual(self.price()['status'],'pursue')
  self.pricing['secondary_vetoes'][0]['value']=96;self.assertEqual(self.price()['status'],'avoid');self.assertAlmostEqual(self.quality['value'],30)
  self.pricing['metric']='PE';self.assertEqual(self.price()['status'],'wait')
 def test_price_validity_and_no_future_threshold(self):
  for k,v in [('date','2026-11-14'),('valid_until','2026-11-12'),('range_date','2026-11-14')]:
   old=self.pricing[k];self.pricing[k]=v;self.assertEqual(self.price()['status'],'wait');self.pricing[k]=old
  self.pricing['secondary_vetoes'][0]['date']='2026-11-14';self.assertEqual(self.price()['status'],'wait')
 def test_missing_secondary_not_pass(self):
  self.pricing['secondary_vetoes'][0]['observations']=20;self.assertEqual(self.price()['status'],'wait')
  self.pricing['secondary_vetoes']=[];self.assertEqual(self.price()['status'],'wait')
 def test_tied_cutoff_not_arbitrary(self):
  self.pool['slots']=2;rows=[self.rec('one',40),self.rec('two',30),self.rec('three',30)]
  picked,_=s.rank_and_select(rows,{'subpools':[self.pool],'convergence':{'max_issuers':10}},{'issuers':{}})
  self.assertEqual([r['key'] for r in picked],['one']);self.assertEqual([r['quality']['rank'] for r in rows],[1,2,2])
 def test_separate_pool_no_global_rank_and_issuer_dedup(self):
  p2=copy.deepcopy(self.pool);p2['id']='other';p2['slots']=2
  rows=[self.rec('a',40,issuer='company'),self.rec('b',80,p2,'company'),self.rec('c',20,p2)]
  policy={'subpools':[self.pool,p2],'convergence':{'max_issuers':10}}
  selected,conflicts=s.rank_and_select(rows,policy,{'issuers':{'company':{'primary_subpool':p2['id']}}})
  self.assertEqual({r['key'] for r in selected},{'b','c'});self.assertEqual(rows[0]['quality']['rank'],1);self.assertIn('a',conflicts)
 def test_incompatible_basis_no_rank(self):
  rows=[self.rec('a',40),self.rec('b',30)];rows[1]['quality']['comparison_key'][-1]='USD'
  selected,_=s.rank_and_select(rows,{'subpools':[self.pool],'convergence':{'max_issuers':10}},{'issuers':{}})
  self.assertEqual(selected,[]);self.assertTrue(all(r['quality']['rank'] is None for r in rows))
 def test_ownership_rejects_double_use(self):
  reviews={'securities':{'a':self.review},'issuers':{'a':{'financial_pack':self.pack}}};s.validate(self.policy,reviews)
  self.pack['evidence_ids']=['A']
  with self.assertRaises(AssertionError):s.validate(self.policy,reviews)
 def test_actual_preserved_candidates_and_one_issuer_pack(self):
  model=s.prepare(ROOT);self.assertEqual(len([r for r in model['records'] if not r['legacy']]),61)
  self.assertEqual(s.issuer_id('a:601088'),s.issuer_id('hk:01088'))
  self.assertEqual(len(model['packs']),len({r['issuer_id'] for r in model['records']}))
  self.assertLessEqual(len(model['selected']),10)
  self.assertTrue(all(r['quality']['rank'] is None for r in model['records'] if r['gate']['status']!='yes'))
  self.assertTrue(all('scores' not in r for r in model['records']))
if __name__=='__main__':unittest.main()
