"""计算大盘层各节点的指标、判定、打分、关注条件和今日变化。
被 build.py 调用；所有规则都写在这里，方便以后调整。
"""
import json, os, datetime

RULES_VERSION = "2026-11-09 v1"


# ---------- 读数据 ----------
def _load(raw, name):
    with open(os.path.join(raw, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def _add_months(d, n, extra_days=0):
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    return (datetime.date(y, m, 1) + datetime.timedelta(days=extra_days)).isoformat()


class Data:
    def __init__(self, raw):
        L = lambda n: _load(raw, n)
        self.idx = {}
        for key, name in [("idx_all", "中证全指"), ("idx_sh", "上证指数"), ("idx_hs300", "沪深 300"),
                          ("idx_cyb", "创业板指"), ("idx_kc50", "科创 50")]:
            self.idx[key] = {"name": name, "rows": L(key)["rows"]}
        rows = self.idx["idx_all"]["rows"]
        self.dates = [r["date"] for r in rows]
        self.all_close = [(r["date"], r["close"]) for r in rows]
        self.turnover = [(r["date"], r["amount"] / 1e8) for r in rows]  # 亿元
        bond = sorted(L("bond"), key=lambda r: r["SOLAR_DATE"])
        self.cn10 = [(r["SOLAR_DATE"][:10], r["EMM00166466"]) for r in bond if r["EMM00166466"] is not None]
        self.us10 = [(r["SOLAR_DATE"][:10], r["EMG00001310"]) for r in bond if r["EMG00001310"] is not None]
        self.cnh = [(r["date"], r["close"]) for r in L("usdcnh")["rows"]]
        mg = sorted(L("margin"), key=lambda r: r["DIM_DATE"])
        self.mbal = [(r["DIM_DATE"][:10], r["RZRQYE"] / 1e8) for r in mg]
        self.mnet = [(r["DIM_DATE"][:10], (r["RZJME"] or 0) / 1e8) for r in mg]
        self.mlev = [(r["DIM_DATE"][:10], r["RZYEZB"]) for r in mg]
        pe = L("pe_all")
        self.pe_all = [(r["date"], r["pe"]) for r in pe]
        self.eps_all = [(r["date"], r["close"] / r["pe"]) for r in pe if r["pe"]]
        self.pe_300 = [(r["date"], r["pe"]) for r in L("pe_hs300")]
        lpr = sorted(L("lpr"), key=lambda r: r["TRADE_DATE"])
        self.lpr1 = [(r["TRADE_DATE"][:10], r["LPR1Y"]) for r in lpr]
        self.lpr5 = [(r["TRADE_DATE"][:10], r["LPR5Y"]) for r in lpr]

        def mser(name, field, lag_months, lag_days):
            out = []
            for r in sorted(L(name), key=lambda r: r["REPORT_DATE"]):
                if r.get(field) is None:
                    continue
                rd = datetime.date.fromisoformat(r["REPORT_DATE"][:10])
                out.append({"period": r["TIME"], "rdate": rd.isoformat(),
                            "avail": _add_months(rd, lag_months, lag_days), "v": r[field]})
            return out
        # avail = 大致的发布日期（用于回看历史时，不提前用到当时还没公布的数据）
        self.pmi = mser("pmi", "MAKE_INDEX", 1, 0)
        self.pmi_n = mser("pmi", "NMAKE_INDEX", 1, 0)
        self.cpi = mser("cpi", "NATIONAL_SAME", 1, 9)
        self.ppi = mser("ppi", "BASE_SAME", 1, 9)
        self.exports = mser("exports", "EXIT_BASE_SAME", 1, 9)
        self.indus = mser("indus", "BASE_SAME", 1, 16)
        self.retail = mser("retail", "RETAIL_TOTAL_SAME", 1, 16)
        self.m1 = mser("money", "CURRENCY_SAME", 1, 14)
        self.m2 = mser("money", "BASIC_CURRENCY_SAME", 1, 14)
        self.gdp = mser("gdp", "SUM_SAME", 1, 18)
        self.status = L("_status")
        LATEST["d"] = self.dates[-1]


# ---------- 工具 ----------
def upto(s, d):
    return [x for x in s if x[0] <= d]


LATEST = {"d": None}


def mupto(m, d):
    # 最新一天：凡是已经抓到的数据都已公布，全部可用；回看历史时才按估计的发布日过滤
    if LATEST["d"] and d >= LATEST["d"]:
        return m
    return [x for x in m if x["avail"] <= d]


def back(s, n):
    """倒数第 n+1 个值（n=0 为最新）"""
    return s[-1 - n] if len(s) > n else s[0]


def pct_rank(vals, x):
    return 100.0 * sum(1 for v in vals if v < x) / len(vals)


def rnd(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def clip(x, lo=-2, hi=2):
    return max(lo, min(hi, x))


def value_at(s, d):
    u = upto(s, d)
    return u[-1][1] if u else None


# ---------- 四个自动维度 ----------
def dim_econ(D, d):
    hits = []
    pmi = mupto(D.pmi, d)
    p, pp = pmi[-1]["v"], pmi[-2]["v"]
    if p >= 50.5: hits.append((f"制造业 PMI {p} 明显站上 50，经济在扩张", 1))
    elif p >= 50: hits.append((f"制造业 PMI {p} 在 50 以上", 0.5))
    elif p < 49.5: hits.append((f"制造业 PMI {p} 低于 49.5，经济在收缩", -1))
    else: hits.append((f"制造业 PMI {p} 略低于 50", -0.5))
    if p - pp >= 0.5: hits.append((f"PMI 比上月回升 {p - pp:.1f}", 0.5))
    elif p - pp <= -0.5: hits.append((f"PMI 比上月回落 {pp - p:.1f}", -0.5))
    r = mupto(D.retail, d)[-1]["v"]
    if r >= 5: hits.append((f"社零同比 {r}%，消费不错", 0.5))
    elif r < 3: hits.append((f"社零同比只有 {r}%，消费偏弱", -0.5))
    i = mupto(D.indus, d)[-1]["v"]
    if i >= 6: hits.append((f"工业增加值同比 {i}%，生产偏强", 0.5))
    elif i < 4: hits.append((f"工业增加值同比 {i}%，生产偏弱", -0.5))
    e = mupto(D.exports, d)[-1]["v"]
    if e >= 5: hits.append((f"出口同比 {e}%，外需支撑", 0.5))
    elif e < 0: hits.append((f"出口同比 {e}%，外需拖累", -0.5))
    return {"score": clip(rnd(sum(h[1] for h in hits))), "hits": hits}


def dim_liquidity(D, d):
    hits = []
    cn = upto(D.cn10, d); us = upto(D.us10, d); fx = upto(D.cnh, d)
    c20 = (cn[-1][1] - back(cn, 20)[1]) * 100
    if c20 <= -10: hits.append((f"中国 10 年国债收益率近 20 日下行 {abs(c20):.0f}bp，资金变便宜", 1))
    elif c20 >= 10: hits.append((f"中国 10 年国债收益率近 20 日上行 {c20:.0f}bp", -1))
    u20 = (us[-1][1] - back(us, 20)[1]) * 100
    if u20 <= -20: hits.append((f"美国 10 年国债收益率近 20 日回落 {abs(u20):.0f}bp", 0.5))
    elif u20 >= 20: hits.append((f"美国 10 年国债收益率近 20 日上行 {u20:.0f}bp", -0.5))
    if us[-1][1] >= 4.5: hits.append((f"美国 10 年国债收益率 {us[-1][1]:.2f}%，处在高位", -0.5))
    f20 = (fx[-1][1] / back(fx, 20)[1] - 1) * 100
    if f20 <= -1: hits.append((f"人民币近 20 日升值 {abs(f20):.1f}%", 0.5))
    elif f20 >= 1: hits.append((f"人民币近 20 日贬值 {f20:.1f}%", -0.5))
    m1 = mupto(D.m1, d)
    dm = m1[-1]["v"] - back([(0, x) for x in m1], 3)[1]["v"]
    if dm >= 1: hits.append((f"M1 同比 {m1[-1]['v']}%，比 3 个月前高 {dm:.1f} 个点，企业活钱在变多", 0.5))
    elif dm <= -1: hits.append((f"M1 同比 {m1[-1]['v']}%，比 3 个月前低 {abs(dm):.1f} 个点", -0.5))
    l = upto(D.lpr1, d)
    d90 = (datetime.date.fromisoformat(d) - datetime.timedelta(days=90)).isoformat()
    old = value_at(D.lpr1, d90)
    if old is not None and l[-1][1] < old: hits.append((f"近 3 个月 LPR 下调到 {l[-1][1]}%", 0.5))
    elif old is not None and l[-1][1] > old: hits.append((f"近 3 个月 LPR 上调到 {l[-1][1]}%", -0.5))
    return {"score": clip(rnd(sum(h[1] for h in hits))), "hits": hits,
            "c20": c20, "u20": u20, "f20": f20}


def erp_series(D, d):
    out = []
    for dt, pe in upto(D.pe_all, d):
        y = value_at(D.cn10, dt)
        if y is not None:
            out.append((dt, 100.0 / pe - y))
    return out


def dim_valuation(D, d):
    hits = []
    pes = upto(D.pe_all, d)
    pe = pes[-1][1]
    pct = pct_rank([v for _, v in pes], pe)
    if pct < 15: hits.append((f"全 A 市盈率 {pe:.1f} 倍，处在 2019 年以来 {pct:.0f}% 分位，很便宜", 2))
    elif pct < 35: hits.append((f"全 A 市盈率 {pe:.1f} 倍，处在 2019 年以来 {pct:.0f}% 分位，偏便宜", 1))
    elif pct > 85: hits.append((f"全 A 市盈率 {pe:.1f} 倍，处在 2019 年以来 {pct:.0f}% 分位，很贵", -2))
    elif pct > 65: hits.append((f"全 A 市盈率 {pe:.1f} 倍，处在 2019 年以来 {pct:.0f}% 分位，偏贵", -1))
    else: hits.append((f"全 A 市盈率 {pe:.1f} 倍，处在 2019 年以来 {pct:.0f}% 分位，不贵不便宜", 0))
    es = erp_series(D, d)
    epct = pct_rank([v for _, v in es], es[-1][1])
    if epct >= 80: hits.append((f"股债性价比 {es[-1][1]:.2f}%，历史 {epct:.0f}% 分位，股票相对债券有吸引力", 0.5))
    elif epct <= 20: hits.append((f"股债性价比 {es[-1][1]:.2f}%，历史 {epct:.0f}% 分位，股票相对债券不划算", -0.5))
    return {"score": clip(rnd(sum(h[1] for h in hits))), "hits": hits,
            "pe": pe, "pct": pct, "erp": es[-1][1], "epct": epct, "pe_date": pes[-1][0]}


def dim_funds(D, d):
    hits = []
    mb = upto(D.mbal, d)
    m5 = (mb[-1][1] / back(mb, 5)[1] - 1) * 100
    m20 = (mb[-1][1] / back(mb, 20)[1] - 1) * 100
    if m5 >= 2: hits.append((f"两融余额 5 日增加 {m5:.1f}%，杠杆资金在进场", 1))
    elif m5 <= -2: hits.append((f"两融余额 5 日减少 {abs(m5):.1f}%，杠杆资金在撤", -1))
    if m20 >= 5: hits.append((f"两融余额 20 日增加 {m20:.1f}%", 0.5))
    elif m20 <= -5: hits.append((f"两融余额 20 日减少 {abs(m20):.1f}%，还在去杠杆", -0.5))
    to = upto(D.turnover, d)
    r = (sum(v for _, v in to[-5:]) / 5) / (sum(v for _, v in to[-60:]) / 60)
    if r >= 1.2: hits.append((f"近 5 日成交额是 60 日均值的 {r:.2f} 倍，交投放大", 0.5))
    elif r <= 0.8: hits.append((f"近 5 日成交额只有 60 日均值的 {r:.2f} 倍，交投萎缩", -0.5))
    return {"score": clip(rnd(sum(h[1] for h in hits))), "hits": hits, "m5": m5, "m20": m20, "to_ratio": r,
            "m_date": mb[-1][0]}


def node_earnings(D, d):
    hits = []
    eps = upto(D.eps_all, d)
    e60 = (eps[-1][1] / back(eps, 60)[1] - 1) * 100
    e250 = (eps[-1][1] / back(eps, 250)[1] - 1) * 100
    if e60 >= 3: hits.append((f"全 A 滚动盈利近 60 个交易日增长 {e60:.1f}%", 1))
    elif e60 <= -3: hits.append((f"全 A 滚动盈利近 60 个交易日下降 {abs(e60):.1f}%", -1))
    else: hits.append((f"全 A 滚动盈利近 60 个交易日变化 {e60:+.1f}%，基本持平", 0))
    ppi = mupto(D.ppi, d)[-1]["v"]
    if ppi > 0: hits.append((f"PPI 同比 {ppi:+.1f}%，出厂价格在涨，利好上游和制造业利润", 0.5))
    else: hits.append((f"PPI 同比 {ppi:+.1f}%，出厂价格在跌，压制企业利润", -0.5))
    return {"score": clip(rnd(sum(h[1] for h in hits))), "hits": hits, "e60": e60, "e250": e250}


def auto_dims(D, d):
    return {"econ": dim_econ(D, d), "liq": dim_liquidity(D, d), "val": dim_valuation(D, d), "funds": dim_funds(D, d)}


# ---------- 关注条件（大盘层） ----------
def conditions(D, d, dims_now, dims_5ago):
    out = []
    flips = []
    names = {"econ": "国内经济", "liq": "利率与流动性", "val": "估值", "funds": "资金"}
    for k in names:
        a, b = dims_5ago[k]["score"], dims_now[k]["score"]
        if (a > 0 and b < 0) or (a < 0 and b > 0) or (a == 0 and b != 0 and abs(b) == 2):
            flips.append(f"{names[k]} {a:+d} → {b:+d}")
    tot_now = sum(dims_now[k]["score"] for k in names); tot_5 = sum(dims_5ago[k]["score"] for k in names)
    hit = bool(flips) or abs(tot_now - tot_5) >= 2
    out.append({"id": "score", "name": "打分卡有维度翻转正负，或一周内合计变化 ≥ 2 分",
                "hit": hit, "now": ("；".join(flips) if flips else f"自动维度合计 5 日前 {tot_5:+d}，现在 {tot_now:+d}")})
    m5 = dims_now["funds"]["m5"]
    out.append({"id": "margin5", "name": "两融余额 5 个交易日变化超过 ±2%", "hit": abs(m5) > 2,
                "now": f"{m5:+.2f}%（截至 {dims_now['funds']['m_date'][5:]}）"})
    us = upto(D.us10, d)
    u5 = (us[-1][1] - back(us, 5)[1]) * 100
    out.append({"id": "us10", "name": "美国 10 年国债收益率一周内变化超过 ±20bp", "hit": abs(u5) >= 20,
                "now": f"{u5:+.0f}bp，现在 {us[-1][1]:.2f}%"})
    cn = upto(D.cn10, d)[-250:]
    v = cn[-1][1]; hi = max(x for _, x in cn); lo = min(x for _, x in cn)
    out.append({"id": "cn10", "name": "中国 10 年国债收益率创近一年新高或新低", "hit": v >= hi or v <= lo,
                "now": f"{v:.3f}%，近一年区间 {lo:.3f}%–{hi:.3f}%"})
    pct = dims_now["val"]["pct"]
    out.append({"id": "pe", "name": "全 A 估值分位跌破 20% 或升破 80%", "hit": pct < 20 or pct > 80,
                "now": f"{pct:.0f}% 分位"})
    pm = mupto(D.pmi, d)
    a, b = pm[-2]["v"], pm[-1]["v"]
    out.append({"id": "pmi", "name": "制造业 PMI 穿越 50（由下到上或由上到下）",
                "hit": (a < 50 <= b) or (a >= 50 > b), "now": f"{pm[-2]['period'][-4:]} {a} → {pm[-1]['period'][-4:]} {b}"})
    return out


# ---------- 汇总 ----------
def analyze(D, manual):
    d = D.dates[-1]
    prev = D.dates[-2]
    d5 = D.dates[-6]
    dims = auto_dims(D, d)
    dims_prev = auto_dims(D, prev)
    dims_5 = auto_dims(D, d5)
    earn = node_earnings(D, d)
    earn_prev = node_earnings(D, prev)

    # 30 个交易日打分历史（只算自动维度，人工维度没有历史）
    hist = []
    for dt in D.dates[-30:]:
        a = auto_dims(D, dt)
        hist.append({"date": dt, **{k: a[k]["score"] for k in a}})

    ext, pol = manual["external"], manual["policy"]
    score_rows = [
        {"key": "ext", "name": "外部环境", "score": ext["score"], "manual": True,
         "hits": [(ext["reason"], ext["score"])], "node": "A"},
        {"key": "econ", "name": "国内经济", "score": dims["econ"]["score"], "hits": dims["econ"]["hits"], "node": "A",
         "prev": dims_prev["econ"]["score"]},
        {"key": "pol", "name": "政策", "score": pol["score"], "manual": True,
         "hits": [(pol["reason"], pol["score"])], "node": "B"},
        {"key": "liq", "name": "利率与流动性", "score": dims["liq"]["score"], "hits": dims["liq"]["hits"], "node": "D",
         "prev": dims_prev["liq"]["score"]},
        {"key": "val", "name": "估值", "score": dims["val"]["score"], "hits": dims["val"]["hits"], "node": "F",
         "prev": dims_prev["val"]["score"]},
        {"key": "funds", "name": "资金", "score": dims["funds"]["score"], "hits": dims["funds"]["hits"], "node": "G",
         "prev": dims_prev["funds"]["score"]},
    ]
    total = sum(r["score"] for r in score_rows)

    def st(x):
        return "up" if x > 0 else ("down" if x < 0 else "flat")

    nodes = {
        "A": {"state": st(ext["score"] + dims["econ"]["score"]), "score": ext["score"] + dims["econ"]["score"]},
        "B": {"state": st(pol["score"]), "score": pol["score"]},
        "C": {"state": st(earn["score"]), "score": earn["score"], "hits": earn["hits"]},
        "D": {"state": st(dims["liq"]["score"]), "score": dims["liq"]["score"]},
        "E": {"state": "na", "score": None},
        "F": {"state": st(dims["val"]["score"]), "score": dims["val"]["score"]},
        "G": {"state": st(dims["funds"]["score"]), "score": dims["funds"]["score"]},
        "H": {"state": "price", "score": None},
    }
    conds = conditions(D, d, dims, dims_5)
    conds_prev = conditions(D, prev, dims_prev, auto_dims(D, D.dates[-7]))
    for c, p in zip(conds, conds_prev):
        c["new"] = c["hit"] and not p["hit"]

    # 今日变化
    changes = []
    for r in score_rows:
        if "prev" in r and r["prev"] != r["score"]:
            changes.append({"dir": st(r["score"] - r["prev"]), "text": f"打分卡「{r['name']}」从 {r['prev']:+d} 变为 {r['score']:+d}", "node": r["node"]})
    if earn["score"] != earn_prev["score"]:
        changes.append({"dir": st(earn["score"] - earn_prev["score"]), "text": f"C 盈利判定从 {earn_prev['score']:+d} 变为 {earn['score']:+d}", "node": "C"})

    def dchg(series, label, unit, thr, node, good, scale=1.0, fmt="{:.2f}"):
        s = series
        a, b = s[-2][1], s[-1][1]
        diff = (b - a) * scale
        if abs(diff) >= thr:
            dirn = st(diff * good)
            changes.append({"dir": dirn, "node": node,
                            "text": f"{label} {fmt.format(b)}{unit if unit != 'bp' else '%'}，较上一交易日 {diff:+.0f}{'bp' if unit == 'bp' else unit}（{s[-1][0][5:]}）"})
    dchg(D.cn10, "中国 10 年国债收益率", "bp", 3, "D", -1, 100, "{:.3f}")
    dchg(D.us10, "美国 10 年国债收益率", "bp", 8, "D", -1, 100, "{:.2f}")
    fx = D.cnh
    fchg = (fx[-1][1] / fx[-2][1] - 1) * 100
    if abs(fchg) >= 0.3:
        changes.append({"dir": st(-fchg), "node": "D", "text": f"离岸人民币 {fx[-1][1]:.4f}，{'贬值' if fchg > 0 else '升值'} {abs(fchg):.2f}%"})
    mn = D.mnet[-1]
    if abs(mn[1]) >= 150:
        changes.append({"dir": st(mn[1]), "node": "G",
                        "text": f"两融单日{'净买入' if mn[1] > 0 else '净偿还'} {abs(mn[1]):.0f} 亿元（{mn[0][5:]}）"})
    pp = pct_rank([v for _, v in D.pe_all[:-1]], D.pe_all[-2][1])
    if abs(dims["val"]["pct"] - pp) >= 3:
        changes.append({"dir": st(-(dims["val"]["pct"] - pp)), "node": "F", "text": f"全 A 估值分位从 {pp:.0f}% 变为 {dims['val']['pct']:.0f}%"})
    for name, ms, node, good in [("制造业 PMI", D.pmi, "A", 1), ("CPI 同比", D.cpi, "A", 0), ("PPI 同比", D.ppi, "C", 1),
                                 ("出口同比", D.exports, "A", 1), ("工业增加值同比", D.indus, "A", 1),
                                 ("社零同比", D.retail, "A", 1), ("M1 同比", D.m1, "D", 1)]:
        for x in ms:
            if x["avail"] > prev:
                changes.append({"dir": "flat", "node": node, "text": f"{x['period']} {name}：{x['v']}"})
    for c in conds:
        if c["new"]:
            changes.append({"dir": "alert", "node": "", "text": f"关注条件触发：{c['name']}（{c['now']}）"})

    return {"date": d, "prev": prev, "dims": dims, "earn": earn, "score_rows": score_rows, "total": total,
            "hist": hist, "nodes": nodes, "conds": conds, "changes": changes, "rules_version": RULES_VERSION}
