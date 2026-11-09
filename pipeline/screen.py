"""全市场行业板块初筛：按东方财富行业分类（财报里的 BOARD_CODE）汇总全部 A 股。
用法（分步，避免单次超时）：
  python3 -I pipeline/screen.py <根目录> fin 2026-09-30   # 依次抓 4 个报告期
  python3 -I pipeline/screen.py <根目录> val 2026-11-09   # 今天和一年前的估值
  python3 -I pipeline/screen.py <根目录> kline
  python3 -I pipeline/screen.py <根目录> score
"""
import json, os, sys, time

ROOT, MODE = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from fetch import dc, kline  # noqa: E402

OUT = os.path.join(ROOT, "data", "raw", "screen")
os.makedirs(OUT, exist_ok=True)


def save(name, obj):
    json.dump(obj, open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False)


def load(name):
    return json.load(open(os.path.join(OUT, name + ".json"), encoding="utf-8"))


if MODE == "fin":
    p = sys.argv[3]
    cols = "SECURITY_CODE,SECURITY_NAME_ABBR,BOARD_CODE,BOARD_NAME,PARENT_NETPROFIT,TOTAL_OPERATE_INCOME,NOTICE_DATE"
    rows = {}
    # 接口单次最多翻 20 页（1 万行），按股票代码分段查询
    segs = ["000000", "002000", "300000", "301000", "600000", "603000", "688000", "999999"]
    for lo, hi in zip(segs, segs[1:]):
        for r in dc("RPT_LICO_FN_CPD", "SECURITY_CODE", cols, 500, 20, f'(REPORTDATE=\'{p}\')(SECURITY_CODE>="{lo}")(SECURITY_CODE<"{hi}")'):
            rows[r["SECURITY_CODE"]] = r
    save("fin_" + p, list(rows.values())); print(p, len(rows))

elif MODE == "val":
    d = sys.argv[3]
    rows = dc("RPT_VALUEANALYSIS_DET", "SECURITY_CODE", "SECURITY_CODE,ORIG_BOARD_CODE,BOARD_NAME,PE_TTM,TOTAL_MARKET_CAP", 500, 20, f"(TRADE_DATE='{d}')")
    save("val_" + d, rows); print(d, len(rows))

elif MODE == "kline":
    fin = load("fin_2026-09-30")
    boards = sorted({r["BOARD_CODE"] for r in fin if r.get("BOARD_CODE")})
    have = load("klines") if os.path.exists(os.path.join(OUT, "klines.json")) else {}
    t0 = time.time()
    for b in boards:
        if b in have: continue
        try:
            have[b] = kline("90." + b, 300)["rows"]
        except Exception as e:
            print(b, "err", e)
        if time.time() - t0 > 140: break
    save("klines", have); print(len(have), "/", len(boards))

elif MODE == "score":
    import analyze as A
    D = A.Data(os.path.join(ROOT, "data", "raw"))
    F = {k: {r["SECURITY_CODE"]: r for r in load("fin_" + k)} for k in ("2026-09-30", "2026-06-30", "2025-09-30", "2025-06-30")}
    V = {k: {r["SECURITY_CODE"]: r for r in load("val_" + k)} for k in ("2026-11-09", "2025-11-10")}
    K = load("klines")
    hs = {r["date"]: r["close"] for r in D.idx["idx_hs300"]["rows"]}
    allamt = dict(D.turnover)
    boards = {}
    for c, r in F["2026-09-30"].items():
        if r.get("BOARD_CODE"):
            boards.setdefault(r["BOARD_CODE"], {"name": r["BOARD_NAME"], "codes": []})["codes"].append(c)
    clip = lambda x: max(-2, min(2, int(x + 0.5) if x >= 0 else -int(-x + 0.5)))
    g = lambda a, b: (a / b - 1) * 100 if b > 0 and a >= 0 else None
    out = []
    for bk, b in boards.items():
        cs = [c for c in b["codes"] if all(c in F[k] for k in F)]
        if len(cs) < 6 or bk not in K:
            continue
        S = lambda k, f: sum(F[k][c][f] or 0 for c in cs)
        q = S("2026-09-30", "PARENT_NETPROFIT") - S("2026-06-30", "PARENT_NETPROFIT")
        qly = S("2025-09-30", "PARENT_NETPROFIT") - S("2025-06-30", "PARENT_NETPROFIT")
        rv = S("2026-09-30", "TOTAL_OPERATE_INCOME") - S("2026-06-30", "TOTAL_OPERATE_INCOME")
        rvly = S("2025-09-30", "TOTAL_OPERATE_INCOME") - S("2025-06-30", "TOTAL_OPERATE_INCOME")
        m = {"rev_yoy": g(rv, rvly), "np_yoy": g(q, qly), "h1_yoy": g(S("2026-06-30", "PARENT_NETPROFIT"), S("2025-06-30", "PARENT_NETPROFIT")),
             "cum_yoy": g(S("2026-09-30", "PARENT_NETPROFIT"), S("2025-09-30", "PARENT_NETPROFIT")), "q_np": q, "n": len(cs),
             "loss_n": sum(1 for c in cs if (F["2026-09-30"][c]["PARENT_NETPROFIT"] or 0) < 0)}

        def wpe(vd):
            rows = [vd[c] for c in b["codes"] if c in vd and vd[c]["PE_TTM"]]
            mc = sum(r["TOTAL_MARKET_CAP"] or 0 for r in rows); pr = sum((r["TOTAL_MARKET_CAP"] or 0) / r["PE_TTM"] for r in rows)
            return (mc / pr if pr > 0 else None), mc
        pe, mc = wpe(V["2026-11-09"]); pe1, _ = wpe(V["2025-11-10"])
        peg = pe / m["cum_yoy"] if pe and m["cum_yoy"] and m["cum_yoy"] > 0 else None
        k = K[bk]; bc = [x["close"] for x in k]; ds = [x["date"] for x in k]
        if len(bc) < 260 or ds[-1] not in hs: continue
        rs = lambda n: (bc[-1] / bc[-1 - n] - hs[ds[-1]] / hs[ds[-1 - n]]) * 100
        share = [x["amount"] / 1e8 / allamt[x["date"]] * 100 for x in k if x["date"] in allamt and allamt[x["date"]]]
        s5 = [sum(share[i - 4:i + 1]) / 5 for i in range(4, len(share))]
        sh_pct = 100 * sum(1 for x in s5 if x < s5[-1]) / len(s5)
        sc = {}
        ry = m["rev_yoy"]; sc["A"] = 0 if ry is None else (1 if ry >= 20 else 0.5 if ry >= 5 else -1 if ry < 0 else 0)
        ny = m["np_yoy"]
        sc["C"] = -1 if q <= 0 else (0 if ny is None else 1 if ny >= 20 else 0.5 if ny >= 0 else -1)
        if m["loss_n"] >= m["n"] / 2: sc["C"] -= 0.5
        e = 0
        if ny is not None and m["h1_yoy"] is not None:
            e = 1 if ny - m["h1_yoy"] >= 10 else -1 if ny - m["h1_yoy"] <= -10 else 0
        sc["E"] = e
        if pe is None: sc["F"] = -1
        elif peg is not None: sc["F"] = 1 if peg < 1 else -1 if peg > 2 else 0
        else: sc["F"] = -1 if pe > 25 else 0
        sc["G"] = -1 if sh_pct >= 85 else 0
        sc = {kk: clip(v) for kk, v in sc.items()}
        out.append({"bk": bk, "name": b["name"], **m, "pe": pe, "pe1": pe1, "peg": peg, "mc": mc, "rs20": rs(20), "rs60": rs(60), "rs250": rs(250),
                    "dd": (bc[-1] / max(bc[-250:]) - 1) * 100, "sh5": s5[-1], "sh_pct": sh_pct, "sc": sc, "total": sum(sc.values())})
    save("result", out)
    f = lambda x, p="+.0f": "—" if x is None else format(x, p)
    for r in sorted(out, key=lambda r: (-r["total"], -(r["np_yoy"] or -999))):
        print(f'{r["bk"]} {r["name"]:<8} 合计{r["total"]:+d} {"".join(f"{k}{v:+d}" for k, v in r["sc"].items())} 营收{f(r["rev_yoy"])} 利润{f(r["np_yoy"])} H1{f(r["h1_yoy"])} '
              f'PE{f(r["pe"], ".0f")}/{f(r["pe1"], ".0f")} PEG{f(r["peg"], ".2f")} 市值{r["mc"] / 1e12:.1f}万亿 n{r["n"]} rs60{r["rs60"]:+.0f} rs250{r["rs250"]:+.0f} 回撤{r["dd"]:.0f} 拥挤{r["sh_pct"]:.0f}')
