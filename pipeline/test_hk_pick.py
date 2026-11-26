"""港股顺势选股：候选通过门槛、判断链六格齐全、港股价格规则为动量买点、逆风板块不选股、行业表可复算。"""
import json, sys, unittest
from pathlib import Path
ROOT = Path(sys.argv[1]); sys.argv = sys.argv[:1]
sys.path.insert(0, str(ROOT/'pipeline'))
import hk_pick as H

class HKPick(unittest.TestCase):
    def setUp(self):
        self.S = json.loads((ROOT/'data/sector_selection.json').read_text())
        self.sec = {s['id']: s for s in self.S['sectors']}
        self.L, self.D = H.select(ROOT, self.S)

    def test_picks_pass_gate(self):
        for sid, r in self.L.items():
            for x in r['picks']:
                self.assertTrue(H.RULES[sid]['filter'](x), (sid, x['code']))
                self.assertIn(x['ind'], H.RULES[sid]['inds'])

    def test_chain_and_views(self):
        for sid, r in self.L.items():
            for x in r['picks']:
                self.assertEqual([a for a, _, _ in x['chain']['steps']], ['板块', '初筛', '核验', '估值', '价格', '筹码'])
                self.assertNotEqual(x['chain']['view'], '可执行', '港股核验未接入，不能出现可执行')
                if self.sec[sid]['rating'] == '等开关':
                    self.assertTrue(x['chain']['view'].startswith('等开关'))

    def test_headwind_no_picks(self):
        for sid in self.L:
            self.assertNotEqual(self.sec[sid]['rating'], '逆风') if self.L[sid]['picks'] else None
        self.assertNotIn('hk-internet', [sid for sid, r in self.L.items() if r['picks']])

    def test_high_yield_moved_to_logic3(self):
        self.assertNotIn('hk-telecom', self.L)

    def test_hk_price_rule_is_momentum(self):
        """港股买点＝上升趋势中回调到12周均线附近；趋势未确认时不能出现“在买入区”。"""
        T = H.load_trend(ROOT)
        for sid, r in self.L.items():
            for x in r['picks']:
                pl = x.get('pl')
                if not pl or r['type'] == 'crowded':
                    continue
                _, m12, m26, r26 = T['stocks'][x['code']]
                self.assertAlmostEqual(pl['buy'][0], round(m12*0.97, 2)); self.assertAlmostEqual(pl['buy'][1], round(m12*1.05, 2))
                if not (pl['close'] > m26 and r26 and r26 > 0):
                    self.assertTrue(pl['where'].startswith('未确认'), x['code'])
                    self.assertNotIn(x['chain']['view'][:2], ('可执', '价格'), x['code'])

    def test_logic2_list_follows_rules(self):
        import hk_turn
        L = hk_turn.load(ROOT)
        self.assertEqual(L['version'], 'revision')
        for x in L['list']:
            self.assertGreaterEqual(x[hk_turn.MC], hk_turn.MC_MIN, x[1])
            self.assertGreaterEqual(x[hk_turn.REV], hk_turn.REV_MIN, x[1])
            self.assertGreaterEqual(x[hk_turn.ORGS], hk_turn.MIN_ORGS, x[1])
            r = L['research'][x[hk_turn.C]]
            for _, k in hk_turn.RES_KEYS:
                self.assertTrue(r.get(k), (x[1], k))
            self.assertNotEqual(hk_turn.verdict(x, L['research'])[0], '可买', '高频指标未验证前不能可买')
        codes = {x[0] for x in L['list']}
        self.assertFalse(codes & {c for c, _, _ in L['excluded']})
        self.assertNotIn('银行', {x[hk_turn.IND] for x in L['list']})

    def test_industry_table(self):
        R, asof = H.industry_rows(ROOT)
        self.assertTrue(R)
        for r in R:
            g = [x for x in H.rows(self.D) if x['ind'] == r['ind'] and x.get('mc')]
            self.assertEqual(r['n'], len(g))

if __name__ == '__main__':
    unittest.main()
