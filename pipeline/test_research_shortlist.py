"""Decision concentration and current/legacy boundary regression."""
import copy,json,sys,unittest,re
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve();sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import research_shortlist as R,hk_pick as H
D,SEC=R.load(ROOT)
class ShortlistTests(unittest.TestCase):
 def test_issuer_limit_not_security_limit(self):
  self.assertLessEqual(len(D['companies']),10)
  x=copy.deepcopy(D);x['companies'].append(copy.deepcopy(x['companies'][0]))
  with self.assertRaises(ValueError):R.validate(x,SEC)
  x=copy.deepcopy(D)
  for i in range(11):
   c=copy.deepcopy(D['companies'][0]);c.update(issuer_id=str(i),code=str(i),refcode=None)
   if i==0:x['companies']=[]
   x['companies'].append(c)
  with self.assertRaises(ValueError):R.validate(x,SEC)
 def test_aliases_cannot_count_as_separate_companies(self):
  x=copy.deepcopy(D);x['companies'][1]['code']=x['companies'][0]['refcode']
  with self.assertRaises(ValueError):R.validate(x,SEC)
 def test_upstream_downgrade_requires_review(self):
  s=copy.deepcopy(SEC);s[D['companies'][0]['sector_id']]['rating']='逆风'
  with self.assertRaises(ValueError):R.validate(D,s)
 def test_comparison_and_sustainability_required(self):
  x=copy.deepcopy(D);x['companies'][0]['peer_decision']=''
  with self.assertRaises(ValueError):R.validate(x,SEC)
  self.assertEqual({x['sector_id'] for x in D['sector_decisions']},set(SEC))
  self.assertTrue(all(x['sustainability'] and x['next'] for x in D['sector_decisions']))
 def test_primary_pages_contain_only_reviewed_issuers(self):
  for market,path in [(None,'index.html'),('hk','hk.html')]:
   h=(ROOT/'docs/stocks'/path).read_text()
   codes=re.findall(r'<article class="sc" id="s-([0-9]+)"',h)
   expected=[x['code'] for x in D['companies'] if market is None or x['market']==market]
   self.assertCountEqual(codes,expected);self.assertIn('id="library"',h)
   self.assertNotIn('class="lp-view go"',h)
 def test_legacy_pages_collapsed(self):
  for fn in ['coverage-a.html','coverage-hk.html','box.html','a-turn.html','hk-turn.html','dividend.html','hk-dividend.html','hk-event.html']:
   h=(ROOT/'docs/stocks'/fn).read_text()
   self.assertIn('data-shortlist-archive="true"',h)
   self.assertIn('id="archived-coverage"><summary>',h)
   self.assertNotIn('id="archived-coverage" open',h)
 def test_dossiers_and_sources(self):
  for x in D['companies']:
   self.assertTrue((ROOT/'docs/stocks'/('research-'+x['issuer_id']+'.html')).exists())
   self.assertGreaterEqual(len(x['sections']),5)
   for section in x['sections']:
    self.assertTrue(section['refs'])
    for k in section['refs']:self.assertIn(k,D['sources'])
 def test_hk_pb_converts_cny_financials(self):
  rows={x['code']:x for x in H.rows(H.load(ROOT))}
  self.assertAlmostEqual(rows['00883']['pb'],1.028,delta=.01)
 def test_corrected_bank_dividend_waits(self):
  l=json.loads((ROOT/'data/raw/stock_pick/hk_dividend.json').read_text())
  x=next(x for x in l['cand'] if x[0]=='01398')
  self.assertAlmostEqual(x[5],.32/.8558,places=4)
  net=x[5]*(1-l['tax'])/x[4]*100
  self.assertAlmostEqual(net,3.923,delta=.01);self.assertLess(net,l['cn10y']+2.5)
  c=next(x for x in D['companies'] if x['issuer_id']=='icbc')
  self.assertAlmostEqual(R.plans(ROOT,c)['buy'][1],7.31,places=2)
 def test_market_constraint_overrides_price(self):
  for x in D['companies']:
   self.assertNotEqual(R.action(ROOT,x),'可执行')
   if x['market']=='a':self.assertIn('暂停新增',R.action(ROOT,x))
 def test_rule_page_matches_new_selection(self):
  h=(ROOT/'docs/stocks/selection-rules.html').read_text()
  for key in ['最多10家','A/H同发行人','D/G','当前生效','同业取舍']:self.assertIn(key,h)
  self.assertNotIn('主指标排序',h)
if __name__=='__main__':unittest.main()
