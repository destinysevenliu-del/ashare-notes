"""2026-11-26新增的选股逻辑：A股业绩反转、A股与港股红利高股息、港股回购与私有化；导航按上涨动力分类。"""
import json, sys, unittest
from pathlib import Path
ROOT = Path(sys.argv[1]); sys.argv = sys.argv[:1]
sys.path.insert(0, str(ROOT/'pipeline'))
import a_turn as T, dividend as D, hk_event as V, stockpick as SP, logic_map as LM


class NewLogics(unittest.TestCase):
    def test_nav_named_by_driver(self):
        for m in SP.MARKETS.values():
            for n, h, t, d in m['sub']:
                self.assertTrue(t.split(' · ')[0] in ('分子', '分母', '事件'), t)
                self.assertTrue((ROOT/'docs/stocks'/h).exists(), h)

    def test_a_turn_rules(self):
        L = T.load(ROOT)
        for x in L['cand']:
            self.assertGreater(x[T.G0], 0); self.assertLess(x[T.G1], 0)
            self.assertLessEqual(x[T.V26], 0, x[1]); self.assertGreater(x[T.DD], -25, x[1]); self.assertGreaterEqual(x[T.MC], 100)
            pl = T.levels(x); self.assertLess(pl['stop'], pl['buy'][0]); self.assertNotEqual(T.view(x, pl), '可执行')

    def test_dividend_rules(self):
        for f, mkt in (('a_dividend.json', 'a'), ('hk_dividend.json', 'hk')):
            L = D.load(ROOT, f); self.assertEqual(L['market'], mkt)
            for x in L['cand']:
                pl = D.levels(L, x); v = D.view(L, x, pl)
                if x[D.FLAG] == 'pause':
                    self.assertTrue(v.startswith('不买'), x[1])
                if D.verify(x)[0] == '未通过':
                    self.assertTrue(v.startswith('不买'), x[1])
                if v == '可执行':
                    self.assertEqual(D.verify(x)[0], '通过'); self.assertLessEqual(x[D.PX], pl['buy'][1])
            self.assertTrue(all(str(x[D.IND]).startswith('银行') <= (x[D.FLAG] == 'pause') for x in L['cand']) if mkt == 'a' else True)

    def test_hk_event_rules(self):
        L = V.load(ROOT)
        for x in L['cand']:
            self.assertGreaterEqual(x[V.PCT], 0.5); self.assertLessEqual(x[V.PCT], 5)
            pl = V.levels(x); v = V.view(x, pl)
            if x[V.V26] <= 0:
                self.assertFalse(v.startswith('价格到位'), x[1])
            if x[V.SHORT] in ('rise', 'high'):
                self.assertTrue(v.startswith('不买'), x[1])

    def test_logic_map_consistent(self):
        st = {x['id']: x['status'] for x in LM.LOGICS}
        self.assertEqual(st['revision'], '已覆盖'); self.assertEqual(st['dividend'], '已覆盖')
        self.assertIn(st['buyback'], ('已覆盖', '部分覆盖'))


if __name__ == '__main__':
    unittest.main()
