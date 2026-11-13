"""Prevent stale rankings, broken causal links and cross-market data substitutions."""
import json,sys,unittest,re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class Links(HTMLParser):
 def __init__(self,s):super().__init__();self.ids=[];self.anchors=[];self.markers=[];self.feed(s)
 def handle_starttag(self,t,a):
  a=dict(a)
  if 'id' in a:self.ids.append(a['id'])
  if a.get('href','').startswith('#'):self.anchors.append(a['href'][1:])
  if a.get('marker-end'):self.markers.append(a['marker-end'][5:-1])
class ThesisTest(unittest.TestCase):
 def test_all_rankings_agree(self):
  d=json.loads((ROOT/'data/market_thesis.json').read_text());sectors=json.loads((ROOT/'data/industry_research.json').read_text())['sectors']
  for market,filename in [('a','outlook.json'),('hk','hk_outlook.json')]:
   m=d['markets'][market];o=json.loads((ROOT/'data'/filename).read_text())
   self.assertEqual(m['headline'],o['headline'])
   self.assertEqual({(s['id'],s['group']) for s in m['sectors']},{(s['id'],s['review']['group']) for s in sectors if s['market']==market})
   self.assertEqual(set('ABCDEFGH'),{n['key'] for n in m['nodes']})
 def test_anchor_and_marker_targets(self):
  for f in ['docs/index.html','docs/hk/index.html']:
   body=(ROOT/f).read_text();p=Links(body)
   self.assertEqual(len(p.ids),len(set(p.ids)),f)
   self.assertFalse(set(p.anchors+p.markers)-set(p.ids),f)
   self.assertNotIn('上方保留宏观判断与原推导方向',body)
   self.assertNotIn('能源和油运保留主线地位',body)
 def test_sources_exist_and_dates_are_bounded(self):
  d=json.loads((ROOT/'data/market_thesis.json').read_text())
  for s in d['sources'].values():
   self.assertLessEqual(s['date'],d['overview_reviewed_at'])
   if not s['url'].startswith('https://'):self.assertTrue((ROOT/'docs'/s['url']).exists())
  for m in d['markets'].values():
   for obj in m['nodes']+m['sectors']:
    self.assertTrue(obj['refs']);self.assertFalse(set(obj['refs'])-set(d['sources']))
 def test_no_company_analysis_and_no_date_relabeling(self):
  d=json.loads((ROOT/'data/market_thesis.json').read_text());pool=json.loads((ROOT/'data/sector_research.json').read_text())
  names={x['name'] for s in pool['sectors'] for x in s['stocks']+s['candidates']}
  visible=json.dumps(d['markets'],ensure_ascii=False)
  for name in names:self.assertNotIn(name,visible)
  self.assertIn('2026-10-30',json.dumps(d,ensure_ascii=False))
  self.assertIn('11月9日',visible);self.assertIn('固定2027',visible)
  hk=d['markets']['hk'];self.assertTrue(any('不是半导体指数' in s['priced'] for s in hk['sectors']))
if __name__=='__main__':unittest.main()
