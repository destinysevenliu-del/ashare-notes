"""Guard numerical evidence, dated windows, and current conclusion ownership."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(sys.argv[1]);sys.argv=sys.argv[:1]
class VerdictTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/'data/market_thesis.json').read_text());self.audit=json.loads((ROOT/'docs/data/market-verdict-evidence.json').read_text())
 def test_recomputed_a_values(self):
  x=self.audit['inputs'];a=self.audit['observations']['a'];p=x['a_pe'];v=p[-1]['pe']
  self.assertAlmostEqual(a['pe_percentile'],sum(r['pe']<v for r in p)/len(p)*100)
  for n in [5,20]:self.assertAlmostEqual(a[f'margin{n}_pct'],(x['a_margin'][-1]['RZRQYE']/x['a_margin'][-n-1]['RZRQYE']-1)*100)
  self.assertAlmostEqual(a['ma60'],sum(r['close'] for r in x['a_index'][-60:])/60)
  self.assertEqual(a['pe_date'],'2026-11-06');self.assertEqual(a['index_date'],'2026-11-09')
 def test_hk_windows_have_no_missing_or_future_rows(self):
  x=self.audit['inputs'];h=self.audit['observations']['hk'];dates=x['hk_trade_dates'];rows={r['date']:r for r in x['hk_southbound']}
  self.assertEqual(len(dates),20);self.assertEqual(dates[-1],'2026-11-09');self.assertEqual(set(rows),set(dates))
  for n in [5,20]:self.assertAlmostEqual(h[f'south{n}'],sum(rows[d]['net'] for d in dates[-n:]))
  self.assertGreater(h['south5'],0);self.assertLess(h['south20'],0)
  self.assertAlmostEqual(h['hibor20_bp'],(x['hk_liquidity'][-1]['hibor_fixing_1m']-x['hk_liquidity'][-21]['hibor_fixing_1m'])*100)
 def test_no_empty_cautions_replace_decisions(self):
  for market in ['a','hk']:
   m=self.data['markets'][market];v=m['macro_overview']
   self.assertTrue(v['verdict']);self.assertTrue(v['synthesis']);self.assertEqual(len(v['evidence']),3)
   for item in v['evidence']+m['macro_nodes']:self.assertFalse(set(item['refs'])-self.data['sources'].keys())
   top=json.dumps(v,ensure_ascii=False)
   for stale in ['不对每只股票重复扣分','当前没有已核定的目标仓位','缺口不补成利好']:self.assertNotIn(stale,top)
  self.assertIn('低利率',self.data['markets']['a']['macro_overview']['verdict'])
  self.assertIn('HIBOR',self.data['markets']['hk']['macro_overview']['valuation']['text'])
 def test_portfolio_reads_current_nodes(self):
  page=(ROOT/'docs/stocks/portfolio.html').read_text()
  for m in self.data['markets'].values():
   self.assertIn(m['macro_overview']['constraint']['title'],page)
   for n in m['macro_nodes']:
    if n['key'] in 'DG':self.assertIn(n['fact'],page)
if __name__=='__main__':unittest.main()
