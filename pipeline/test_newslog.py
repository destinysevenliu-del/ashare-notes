"""新闻归类：字段齐全、对应项存在、分级由规则计算且可复现、阈值检测与原始数据一致。"""
import json, sys, unittest
from pathlib import Path
ROOT = Path(sys.argv[1]); sys.argv = sys.argv[:1]
sys.path.insert(0, str(ROOT/'pipeline'))
import newslog as N

class NewsTests(unittest.TestCase):
    def setUp(self):
        self.d, self.weeks, self.flags = N.evaluate(ROOT)
        t = json.loads((ROOT/'data/market_thesis.json').read_text())['macro_regime']['markets']
        s = json.loads((ROOT/'data/sector_selection.json').read_text())['sectors']
        self.valid = {r['src'] for m in t.values() for r in m['tracking']} | {c[0] for m in t.values() for c in m['checks']} | {x['id'] for x in s}

    def test_fields_and_links(self):
        need = ['date', 'title', 'why', 'part', 'links', 'links_label', 'source_name', 'url', 'source_level', 'path_change', 'react', 'direction']
        for w in self.d['weeks']:
            self.assertLessEqual(w['start'], w['end'])
            for it in w['items']:
                for k in need: self.assertIn(k, it, it['title'])
                self.assertIn(it['part'], ('分子', '分母', '水龙头'))
                self.assertIn(it['direction'], ('有利', '不利', '中性'))
                self.assertEqual(len(it['links']), len(it['links_label']))
                self.assertFalse(set(it['links']) - self.valid, it['title'])
                self.assertTrue(it['url'].startswith('http'))
                self.assertTrue(w['start'] <= it['date'] <= w['end'], it['title'])
                if it['path_change']:
                    self.assertIn(it['source_level'], N.PATH_OK, '只有官方或公司公告能算改变路径')
                if it['react']:
                    self.assertIn(it['react']['ind'], N.INDICATORS)
                    self.assertGreaterEqual(it['react']['date'], it['date'])

    def test_grade_is_rule_output(self):
        for w in self.weeks:
            for it in w['items']:
                g, _ = N.grade(it, it['rx'])
                self.assertEqual(g, it['grade'])
                if it['source_level'] not in N.CONFIRMED: self.assertEqual(g, 'C')
                if it['rx'] and not it['path_change'] and it['source_level'] in N.CONFIRMED and it['links']:
                    self.assertEqual(g, 'B' if abs(it['rx']['z']) >= N.Z_LINE else 'C')

    def test_reaction_recomputes(self):
        s = N.series(ROOT, 'hsi'); i = [d for d, _ in s].index('2026-11-20')
        rx = N.reaction(ROOT, 'hsi', '2026-11-20')
        self.assertAlmostEqual(rx['move'], round((s[i][1]/s[i-1][1]-1)*100, 2))
        self.assertIsNone(N.reaction(ROOT, 'hsi', '2099-01-01'))

    def test_threshold_detection(self):
        w = [x for x in self.weeks if x['start'] == '2026-11-16'][0]
        names = {(c['name'], c['line']) for c in w['crossed']}
        self.assertIn(('恒生指数', 22500), names)
        self.assertIn('中证全指', {n['name'] for n in w['near']})

if __name__ == '__main__':
    unittest.main()
