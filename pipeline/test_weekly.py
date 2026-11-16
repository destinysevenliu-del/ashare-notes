"""每周更新流程的回归：JS 与 Python 指标口径一致、状态标签、开关读取。用法：python3 -I pipeline/test_weekly.py <根目录>"""
import json, sys, os, random, shutil, subprocess, unittest, tempfile
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from weekly import metrics as M
import logic1_rules

def sample(seed):
    rnd = random.Random(seed); px = []; c = 20.0; d0 = __import__("datetime").date(2025, 9, 1)
    for i in range(300):
        d = d0 + __import__("datetime").timedelta(days=i * 7 // 5)
        ch = rnd.uniform(-6, 6); c = round(c * (1 + ch / 100), 2); px.append([d.isoformat(), c, ch])
    mg = [[px[-30 + i][0], rnd.uniform(1e8, 2e8), rnd.uniform(0.5, 6)] for i in range(30)]
    hd = [["2026-06-30", -5.25, "较分散", 47.5, "2026-08-25"], ["2026-09-30", 3.15, "较集中", 52.49, "2026-10-28"], ["2026-12-31", 9.9, "x", 1, "2027-03-01"]]
    lf = [["2027-01-05", 0.0123], ["2027-03-01", 0.04]]
    return {"px": px, "mg": mg, "hd": hd, "lf": lf}

class WeeklyTest(unittest.TestCase):
    def test_js_python_same(self):
        node = shutil.which("node")
        if not node: self.skipTest("本机没有 node，跳过 JS 口径核对")
        raws = {str(i): sample(i) for i in range(5)}; asof = "2026-11-13"; y1 = "2025-11-13"
        py = {k: M.compute(v, asof, y1) for k, v in raws.items()}
        with tempfile.TemporaryDirectory() as t:
            Path(t, "in.json").write_text(json.dumps(raws))
            js = "const {compute}=require(%s);const r=require(%s);const o={};for(const k in r)o[k]=compute(r[k],%s,%s);console.log(JSON.stringify(o))" % (json.dumps(str(ROOT / "pipeline/weekly/metrics.js")), json.dumps(str(Path(t, "in.json"))), json.dumps(asof), json.dumps(y1))
            out = json.loads(subprocess.run([node, "-e", js], capture_output=True, text=True, check=True).stdout)
        for k in raws:
            self.assertEqual(set(py[k]), set(out[k]), k)
            for f in py[k]:
                a, b = py[k][f], out[k][f]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)): self.assertAlmostEqual(a, b, 6, (k, f))
                else: self.assertEqual(a, b, (k, f))
        self.assertEqual(py["0"]["hdate"], "2026-09-30")  # 公告日晚于截止日的一期不能用

    def test_stop_label(self):
        x = {"en": {"close": 10, "dd": -50, "pos52": 0.0, "vsMA60": -10}}
        p = logic1_rules.price_levels("upstream", x)
        self.assertIn("跌破止损", p["where"]) if p and p["stop"] and p["close"] <= p["stop"] else None
        b = logic1_rules.box_levels({"close": 8.0, "pos": -0.4, "W": 0.5})
        self.assertIn("跌破止损", b["where"])

    def test_csi_rows_dedupe(self):
        d = {"data": [{"tradeDate": "20261101", "close": 1, "tradingVol": 5}, {"tradeDate": "20261102", "close": 1, "tradingVol": 5}, {"tradeDate": "20261103", "close": 2, "tradingVol": 6}]}
        self.assertEqual([r["date"] for r in M.csi_rows(d)], ["2026-11-02", "2026-11-03"])

    def test_snapshot_files(self):
        for p in sorted((ROOT / "data/snapshots/prices").glob("*.json"))[-2:]:
            s = json.loads(p.read_text())
            self.assertTrue(s["logic1"] and s["logic2"], p.name)
            for x in s["logic1"].values():
                if x.get("buy"): self.assertLessEqual(x["buy"][0], x["buy"][1])

if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
