"""港股顺势选股：候选通过门槛、判断链六格齐全、价格规则与A股同一套、逆风板块不选股、行业表可复算。"""
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

    def test_logic2_list_follows_rules(self):
        import hk_turn
        L = hk_turn.load(ROOT)
        for x in L['list']:
            self.assertLessEqual(x[5], -40); self.assertGreaterEqual(x[3], 100)
            self.assertTrue(x[8] or x[9])
            self.assertLess(x[15][0] - x[15][2], hk_turn.SHORT_RISE, x[1])
        for c, n, s in L['excluded_short_rising']:
            self.assertGreaterEqual(s[0] - s[2], hk_turn.SHORT_RISE, n)
        self.assertIn('不买', L['rules']['enable'] + L['rules']['status'])

    def test_industry_table(self):
        R, asof = H.industry_rows(ROOT)
        self.assertTrue(R)
        for r in R:
            g = [x for x in H.rows(self.D) if x['ind'] == r['ind'] and x.get('mc')]
            self.assertEqual(r['n'], len(g))

if __name__ == '__main__':
    unittest.main()
