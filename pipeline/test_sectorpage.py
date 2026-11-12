"""Regression: industry pages must never embed company research."""
import json,sys,unittest,re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import sectorpage
DATA=json.loads((ROOT/'data/industry_research.json').read_text());STOCKS=json.loads((ROOT/'data/sector_research.json').read_text())
class Text(HTMLParser):
 def __init__(self,s):super().__init__();self.parts=[];self.feed(s)
 def handle_data(self,s):self.parts.append(s)
class SectorPageTest(unittest.TestCase):
 def test_scope(self):
  for market,file in [('a','outlook.json'),('hk','hk_outlook.json')]:
   o=json.loads((ROOT/'data'/file).read_text());expected={(t['name'],s['name']) for t in o['tiers'] for s in t['items']}
   self.assertEqual(expected,{(s['review']['group'],s['title']) for s in DATA['sectors'] if s['market']==market})
 def test_final_judgment_is_not_inherited_macro_tier(self):
  for s in DATA['sectors']:
   v=s['review'];self.assertEqual(s['summary_takeaway'],v['headline']);self.assertEqual(s['conclusion']['base'],v['headline'])
   self.assertEqual(set(v['factors']),set('ABCDEFGH'));self.assertEqual(len(v['decisive']),3)
   body=sectorpage.detail(DATA,s);self.assertIn(v['synthesis'],body);self.assertIn(v['change'],body)
   for x in v['decisive']:self.assertIn(x['source'],DATA['sources'])
  coal=next(s for s in DATA['sectors'] if s['id']=='a-coal')
  self.assertEqual(coal['macro_tier'],'主要方向');self.assertEqual(coal['review']['group'],'防御观察')
 def test_market_summary_and_final_rows(self):
  for market in ['a','hk']:
   body=sectorpage.hub(DATA,market);self.assertIn(DATA['market_synthesis'][market]['body'],body)
   for s in DATA['sectors']:
    if s['market']==market:self.assertIn('data-sector="'+s['id']+'"',body);self.assertIn(s['review']['headline'],body)
 def test_no_company_material(self):
  names={x['name'] for s in STOCKS['sectors'] for x in s['stocks']+s['candidates']}|{'澜起','长电','兆易','腾讯','阿里','许继','南瑞','联想','中芯','华虹','Frontline'}
  bodies=[sectorpage.detail(DATA,s) for s in DATA['sectors']]+[sectorpage.hub(DATA,m) for m in ['a','hk']]
  for body in bodies:
   visible=' '.join(Text(body).parts)
   for name in names:self.assertNotIn(name,visible)
   self.assertNotIn('id="leaders"',body);self.assertNotIn('id="candidates"',body)
  for s in DATA['sectors']:
   self.assertNotIn('stocks',s);self.assertNotIn('candidates',s)
 def test_complete_graph_and_nodes(self):
  for s in DATA['sectors']:
   body=sectorpage.detail(DATA,s)
   self.assertEqual(body.count('<svg class="sector-diagram"'),1)
   for k in 'ABCDEFGH':self.assertIn('id="node-'+k+'"',body)
 def test_stock_pools_retained_separately(self):
  for s in STOCKS['sectors']:
   body=sectorpage.stock_pool(STOCKS,s)
   self.assertIn('id="leaders"',body);self.assertIn('id="candidates"',body)
   for x in s['stocks']:self.assertIn(x['code'],body)
if __name__=='__main__':unittest.main()
