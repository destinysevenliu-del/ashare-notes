"""Run: python3 -I pipeline/test_sectorpage.py <project root>."""
import json,sys,unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
import sectorpage
DATA=json.loads((ROOT/'data/sector_research.json').read_text())
class Parsed(HTMLParser):
 def __init__(self,text):super().__init__();self.graphs=0;self.rects=0;self.arrows=0;self.ids=[];self.links=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='svg' and a.get('class')=='sector-diagram':self.graphs+=1
  if tag=='rect':self.rects+=1
  if tag=='path' and a.get('marker-end'):self.arrows+=1
  if a.get('id'):self.ids.append(a['id'])
  if tag=='a' and a.get('href'):self.links.append(a['href'])
class SectorPageTest(unittest.TestCase):
 def test_scopes_match_outlooks(self):
  for market,file in [('a','outlook.json'),('hk','hk_outlook.json')]:
   outlook=json.loads((ROOT/'data'/file).read_text())
   expected={(t['name'],s['name']) for t in outlook['tiers'] if t['name'] in ['主要方向','条件看好'] for s in t['items']}
   self.assertEqual(expected,{(s['tier'],s['outlook_name']) for s in DATA['sectors'] if s['market']==market})
 def test_each_sector_has_complete_clickable_graph(self):
  for s in DATA['sectors']:
   with self.subTest(sector=s['id']):
    page=Parsed(sectorpage.detail(DATA,s))
    self.assertEqual((page.graphs,page.rects,page.arrows),(1,8,11))
    self.assertEqual(len(page.ids),len(set(page.ids)))
    for key in 'ABCDEFGH':
     self.assertIn('node-'+key,page.ids);self.assertIn('#node-'+key,page.links)
     self.assertEqual(len(s['diagram'][key]),2)
 def test_hubs_have_each_market_graph(self):
  for market in ['a','hk']:
   page=Parsed(sectorpage.hub(DATA,market))
   self.assertEqual(page.graphs,len([s for s in DATA['sectors'] if s['market']==market]))
   self.assertEqual(len(page.ids),len(set(page.ids)))
   self.assertFalse(any('picks/' in link for link in page.links))
 def test_leader_observations_have_evidence(self):
  for s in DATA['sectors']:
   body=sectorpage.detail(DATA,s)
   self.assertIn('最终可以选择龙头，也可以选择其他公司',body)
   for stock in s['stocks']:
    self.assertTrue(stock['watch_reason'] and stock['watch_role'] and stock['watch_nodes'])
    self.assertIn(stock['observation']['source'],DATA['sources'])
    self.assertIn(stock['leader_source'],DATA['sources'])
if __name__=='__main__':unittest.main()
