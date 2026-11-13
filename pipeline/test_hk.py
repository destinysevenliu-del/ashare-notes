"""Run: python3 -I pipeline/test_hk.py <project root>."""
import datetime,json,sys,unittest
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'pipeline'))
from hk_fetch import parse_connect,completed_rows
from hkpage import aligned_series,flow_window,funding_score,change
class HKTest(unittest.TestCase):
 def records(self):
  def record(m,b,s):
   return {'market':m,'date':'2026-11-09','tradingDay':1,'content':[{'table':{'classname':'tradingTable','schema':[['Buy Turnover','Sell Turnover']],'tr':[{'td':[[b]]},{'td':[[s]]}]}}]}
  return [record('SSE Northbound','9,000','0'),record('SSE Southbound','2,000','1,500'),record('SZSE Southbound','1,000','800')]
 def test_units_and_direction(self):
  r=parse_connect('tabData = '+json.dumps(self.records())+';','2026-11-09')
  self.assertEqual(r['buy'],30);self.assertEqual(r['sell'],23);self.assertEqual(r['net'],7)
 def test_incomplete_connect_rejected(self):
  records=self.records()
  with self.assertRaises(ValueError):parse_connect(json.dumps(records[:-1]),'2026-11-09')
  records[-1]['date']='2026-11-06'
  with self.assertRaises(ValueError):parse_connect(json.dumps(records),'2026-11-09')
 def test_intraday_excluded(self):
  data={'rows':[{'date':'2026-11-09'},{'date':'2026-11-10'},{'date':'2026-11-11'}]}
  self.assertEqual(len(completed_rows(data,datetime.datetime(2026,11,10,16,30))),1)
  self.assertEqual(len(completed_rows(data,datetime.datetime(2026,11,10,17))),2)
 def test_intraday_cache_never_becomes_close_without_refresh(self):
  data={'observed_at':'2026-11-10T10:00:00+08:00','rows':[{'date':'2026-11-09'},{'date':'2026-11-10'}]}
  self.assertEqual(len(completed_rows(data,datetime.datetime(2026,11,11,17))),1)
 def test_missing_flow_not_zero(self):
  rows=[{'date':'2026-11-06','net':3},{'date':'2026-11-09','net':-5}]
  self.assertEqual(flow_window(rows,['2026-11-06','2026-11-09'],2),-2)
  self.assertIsNone(flow_window(rows,['2026-11-05','2026-11-06','2026-11-09'],3))
 def test_chart_common_dates_and_returns(self):
  values={'hsi':[{'date':'a','close':10},{'date':'b','close':20},{'date':'c','close':30}],'hstech':[{'date':'b','close':40},{'date':'c','close':20}]}
  aligned=aligned_series(values)
  self.assertEqual(aligned[0][2],[('b',100),('c',150)])
  self.assertEqual(aligned[1][2],[('b',100),('c',50)])
  self.assertAlmostEqual(change(values['hsi'],1),50)
 def test_funding_staleness(self):
  rows=[{'end_of_date':(datetime.date(2026,10,1)+datetime.timedelta(days=i)).isoformat(),'hibor_fixing_1m':3-i*.02} for i in range(21)]
  self.assertEqual(funding_score(rows,'2026-10-21')[0],1)
  self.assertIsNone(funding_score(rows,'2026-11-09')[0])
  self.assertIsNone(funding_score(rows[:20],'2026-10-21')[0])
 def test_page_links_and_unknowns(self):
  hk=(ROOT/'docs/hk/index.html').read_text();a=(ROOT/'docs/index.html').read_text()
  self.assertIn('href="hk/index.html"',a)
  self.assertIn('href="../index.html"',hk)
  self.assertIn('id="tracking"',hk);self.assertNotIn('id="today"',hk)
  for p in (ROOT/'data/snapshots/hk_v1').glob('*.json'):
   s=json.loads(p.read_text())
   for k in ['external','economy','policy','valuation']:self.assertIsNone(s['scores'][k])
 def test_full_nodes_remain_unknown_when_only_proxies_available(self):
  snapshots=list((ROOT/'data/snapshots/hk_v2').glob('*.json'))
  self.assertTrue(snapshots)
  for p in snapshots:
   data=json.loads(p.read_text())
   self.assertEqual(set(data['scores']),set('ABCDEFGX'))
   self.assertTrue(all(value is None for value in data['scores'].values()))
   self.assertEqual(set(data['proxy_signals']),{'hibor','southbound'})
 def test_completed_research_has_evidence_for_all_nodes(self):
  from hk_research import load
  r=load(ROOT,'2026-11-09')
  self.assertEqual(set(r['sections']),set('ABCDEFGX'))
  for entry in r['sections'].values():
   for field in ('facts','analysis','counter','monitor','boundary'):
    self.assertTrue(entry[field])
   self.assertTrue(all(fact['source'].startswith('https://') for fact in entry['facts']))
  self.assertTrue(r['gaps'])
 def test_official_index_csv_encodings_and_missing_pe(self):
  from hsi_public_data import parse_daily
  text='日期\t指數\nTrade Date\tIndex\tIndex Currency\tIndex Close\tPE Ratio (times)\tDividend Yield (%)\n20261109\tHang Seng Index\tHKD\t24448.95\t13.69\t2.99\n'
  row=parse_daily(text.encode('utf-16'),'hsi','source')
  self.assertEqual(row['pe_ratio'],13.69)
  text=text.replace('Hang Seng Index','Hang Seng TECH Index').replace('13.69','')
  row=parse_daily(text.encode('utf-16'),'hstech','source')
  self.assertIsNone(row['pe_ratio'])
if __name__=='__main__':unittest.main()
