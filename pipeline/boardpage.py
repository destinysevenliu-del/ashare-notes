"""板块页：行业层 A–H。由 build.py 调用：boardpage.build(ctx) → 返回 {secid: 分析结果}。"""
import json, os, html
import scorecard

E = html.escape


def st(x):
    return "up" if x > 0 else ("down" if x < 0 else "flat")


def rnd(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def clip(x):
    return max(-2, min(2, x))


def yi(x):
    return f"{x / 1e8:,.0f} 亿" if abs(x) >= 1e9 else f"{x / 1e8:,.2f} 亿"


def sg(x):
    return f"{x:+d}" if x else "0"


NODE_NAMES = {"A": "下游需求", "B": "政策与地缘", "C": "量 × 价 × 毛利率 → 行业利润", "D": "宏观环境：利率与风险偏好",
              "E": "景气预期：增速的方向", "F": "行业估值：PE 配得上增速吗", "G": "拥挤度：成交集中", "H": "板块走势"}


def analyze_board(cfg, raw, ctx):
    R, D = ctx["R"], ctx["D"]
    fin = {k: {r["SECURITY_CODE"]: r for r in v} for k, v in raw["fin"].items()}
    common = set.intersection(*[set(v) for v in fin.values()])
    S = lambda k, f: sum((fin[k][c][f] or 0) for c in common)
    agg = {k: {"np": S(k, "PARENT_NETPROFIT"), "rev": S(k, "TOTAL_OPERATE_INCOME")} for k in fin}
    q = {"np": agg["cur"]["np"] - agg["prev"]["np"], "rev": agg["cur"]["rev"] - agg["prev"]["rev"]}
    q_ly = {"np": agg["cur_ly"]["np"] - agg["prev_ly"]["np"], "rev": agg["cur_ly"]["rev"] - agg["prev_ly"]["rev"]}
    qp = {"np": agg["prev"]["np"] - agg["prev2"]["np"]} if "prev2" in agg else None
    g = lambda a, b: (a / b - 1) * 100 if b > 0 and a >= 0 else None
    per = raw["periods"]
    ql = f"{per['cur'][2:4]}Q{int(per['cur'][5:7]) // 3}"
    m = {"n": len(common), "q_label": ql, "q_np": q["np"], "q_rev": q["rev"],
         "rev_yoy": g(q["rev"], q_ly["rev"]), "np_yoy": g(q["np"], q_ly["np"]),
         "h_np_yoy": g(agg["prev"]["np"], agg["prev_ly"]["np"]), "h_rev_yoy": g(agg["prev"]["rev"], agg["prev_ly"]["rev"]),
         "qoq": g(q["np"], qp["np"]) if qp else None, "cum_np": agg["cur"]["np"], "cum_np_yoy": g(agg["cur"]["np"], agg["cur_ly"]["np"]),
         "loss_n": sum(1 for c in common if (fin["cur"][c]["PARENT_NETPROFIT"] or 0) < 0),
         "turn_loss": q["np"] < 0 < q_ly["np"]}
    names = {c["f12"]: c["f14"] for c in raw["cons"]}
    qnp = {c: (fin["cur"][c]["PARENT_NETPROFIT"] or 0) - (fin["prev"][c]["PARENT_NETPROFIT"] or 0) for c in common}
    tot_pos = sum(v for v in qnp.values() if v > 0) or 1
    m["top"] = [(names.get(c, c), v, v / tot_pos * 100) for c, v in sorted(qnp.items(), key=lambda x: -x[1])[:3] if v > 0]

    def wpe(rows):
        mc = sum(r["TOTAL_MARKET_CAP"] or 0 for r in rows if r["PE_TTM"])
        prof = sum((r["TOTAL_MARKET_CAP"] or 0) / r["PE_TTM"] for r in rows if r["PE_TTM"])
        return (mc / prof if prof > 0 else None), mc
    pe_now, mc_now = wpe(raw["val_now"])
    pe_1y, _ = wpe(raw["val_1y"])
    peg = pe_now / m["cum_np_yoy"] if pe_now and m["cum_np_yoy"] and m["cum_np_yoy"] > 0 else None

    k = raw["kline"]["rows"]
    bc = [r["close"] for r in k]; ba = {r["date"]: r["amount"] for r in k}
    hs = {r["date"]: r["close"] for r in D.idx["idx_hs300"]["rows"]}
    allamt = dict(D.turnover)  # 亿元
    share = [(r["date"], r["amount"] / 1e8 / allamt[r["date"]] * 100) for r in k if r["date"] in allamt and allamt[r["date"]]]
    sh5 = sum(v for _, v in share[-5:]) / 5
    sh_hist = [sum(v for _, v in share[i - 4:i + 1]) / 5 for i in range(4, len(share))]
    sh_pct = 100 * sum(1 for x in sh_hist if x < sh5) / len(sh_hist)
    dts = [r["date"] for r in k]
    rs = lambda n: (bc[-1] / bc[-1 - n] - hs[dts[-1]] / hs[dts[-1 - n]]) * 100
    t = {"close": bc[-1], "d1": (bc[-1] / bc[-2] - 1) * 100, "d20": (bc[-1] / bc[-21] - 1) * 100, "d60": (bc[-1] / bc[-61] - 1) * 100,
         "rs20": rs(20), "rs60": rs(60), "rs250": rs(250) if len(bc) > 250 else None,
         "ma60": sum(bc[-60:]) / 60, "ma250": sum(bc[-250:]) / 250 if len(bc) >= 250 else None,
         "hi": max(bc[-250:]), "dd": (bc[-1] / max(bc[-250:]) - 1) * 100}

    N = {}
    h = []
    ry = m["rev_yoy"]
    if ry is not None:
        if ry >= 20: h.append((f"{ql} 成分股合计单季营收同比 {ry:+.0f}%，已实现收入增长", 1))
        elif ry >= 5: h.append((f"{ql} 成分股合计单季营收同比 {ry:+.0f}%", 0.5))
        elif ry < 0: h.append((f"{ql} 成分股合计单季营收同比 {ry:+.0f}%，已实现收入下降", -1))
        else: h.append((f"{ql} 成分股合计单季营收同比 {ry:+.0f}%，增长平缓", 0))
    N["A"] = h
    N["B"] = [(cfg["b_note"], cfg["b_score"])] if cfg.get("evidence_verified") else []
    h = []
    if q["np"] <= 0:
        h.append((f"{ql} 成分股合计单季亏损 {yi(-q['np'])}", -1))
    elif m["np_yoy"] is not None:
        if m["np_yoy"] >= 20: h.append((f"{ql} 合计单季净利润 {yi(q['np'])}，同比 {m['np_yoy']:+.0f}%", 1))
        elif m["np_yoy"] >= 0: h.append((f"{ql} 合计单季净利润 {yi(q['np'])}，同比 {m['np_yoy']:+.0f}%", 0.5))
        else: h.append((f"{ql} 合计单季净利润 {yi(q['np'])}，同比 {m['np_yoy']:+.0f}%，利润在下滑", -1))
    if m["loss_n"] >= m["n"] / 2:
        h.append((f"{m['n']} 家成分股里 {m['loss_n']} 家前三季度亏损", -0.5))
    N["C"] = h
    sr = {r["key"]: r for r in R["score_rows"]}
    N["D"] = [(f"引用大盘 D 节点：{'；'.join(x[0] for x in sr['liq']['hits']) or '各项变化不大'}", sr["liq"]["score"])]
    h = []
    if m["np_yoy"] is not None and m["h_np_yoy"] is not None:
        dd = m["np_yoy"] - m["h_np_yoy"]
        if dd >= 10: h.append((f"利润增速在加快：{ql} 单季同比 {m['np_yoy']:+.0f}%，上半年累计同比 {m['h_np_yoy']:+.0f}%", 1))
        elif dd <= -10: h.append((f"利润增速在放缓：{ql} 单季同比 {m['np_yoy']:+.0f}%，上半年累计同比 {m['h_np_yoy']:+.0f}%", -1))
        else: h.append((f"利润增速大致持平：{ql} 单季同比 {m['np_yoy']:+.0f}%，上半年累计同比 {m['h_np_yoy']:+.0f}%", 0))
    if m["qoq"] is not None:
        if m["qoq"] >= 5: h.append((f"单季净利润环比 {m['qoq']:+.0f}%", 0.5))
        elif m["qoq"] <= -5: h.append((f"单季净利润环比 {m['qoq']:+.0f}%", -0.5))
    N["E"] = []  # 实际利润增速保留展示，不能替代机构预期修订。
    h = []
    if pe_now is None:
        h.append(("成分股合计滚动利润为负，无法计算板块 PE", -1))
    else:
        cy = m["cum_np_yoy"]
        if peg is not None:
            if peg < 1: h.append((f"板块 PE {pe_now:.0f} 倍，前三季度利润增速 {cy:+.0f}%，PEG {peg:.2f}，静态 PEG 较低，需验证增长持续性", 1))
            elif peg > 2: h.append((f"板块 PE {pe_now:.0f} 倍，利润增速 {cy:+.0f}%，PEG {peg:.2f}，静态 PEG 较高，需结合周期判断", -1))
            else: h.append((f"板块 PE {pe_now:.0f} 倍，利润增速 {cy:+.0f}%，PEG {peg:.2f}，仅为静态比较", 0))
        else:
            h.append((f"板块 PE {pe_now:.0f} 倍，但利润在下滑（{cy:+.0f}%），估值缺少增速支撑" if cy is not None else f"板块 PE {pe_now:.0f} 倍", -1 if pe_now > 25 else 0))
        if pe_1y:
            h.append((f"一年前板块 PE {pe_1y:.0f} 倍，现在 {pe_now:.0f} 倍", 0))
    N["F"] = h
    h = []
    if sh_pct >= 85: h.append((f"近 5 日成交额占全 A {sh5:.2f}%，处在近一年 {sh_pct:.0f}% 分位，交易拥挤", -1))
    elif sh_pct <= 15: h.append((f"近 5 日成交额占全 A {sh5:.2f}%，处在近一年 {sh_pct:.0f}% 分位，交易冷清", 0))
    else: h.append((f"近 5 日成交额占全 A {sh5:.2f}%，处在近一年 {sh_pct:.0f}% 分位", 0))
    N["G"] = h
    scores = {kk: clip(rnd(sum(p for _, p in hh))) if hh else None for kk, hh in N.items()}
    total = sum(v for kk, v in scores.items() if v is not None and kk != "D")
    return {"cfg": cfg, "m": m, "t": t, "pe_now": pe_now, "pe_1y": pe_1y, "peg": peg, "mc": mc_now, "share": share, "sh5": sh5,
            "sh_pct": sh_pct, "nodes": N, "scores": scores, "total": total, "cons": raw["cons"], "kline": k, "d_now": raw["d_now"],
            "d_1y": raw["d_1y"], "periods": per}


def render(a, ctx, stocks_in):
    spark, line_chart, verdict, rules = ctx["spark"], ctx["line_chart"], ctx["verdict"], ctx["rules"]
    cfg, m, t, sc = a["cfg"], a["m"], a["t"], a["scores"]
    D = ctx["D"]

    def ns(k):
        if k == "H": return "price"
        s = sc.get(k)
        return "na" if s is None else st(s)

    def sub(k):
        if k == "H": return f"近 20 日 {t['d20']:+.1f}%，相对沪深 300 {t['rs20']:+.1f} 个点"
        s = sc.get(k)
        if s is None: return "暂缺"
        return {"up": "利好", "down": "利空", "flat": "中性"}[st(s)] + " " + sg(s) + ("（人工）" if k == "B" else "")
    P = {"A": (20, 20), "B": (370, 20), "C": (35, 120), "D": (370, 120), "E": (50, 220), "F": (370, 220), "G": (700, 220), "H": (640, 330)}
    NW, NH = 290, 62
    o = ['<svg class="fw" viewBox="0 0 1000 410" role="img" aria-label="行业层传导图">',
         '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9AA2AF"/></marker>'
         '<marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#D88B1F"/></marker></defs>']
    for ed in [f"M{P['A'][0] + 90},{P['A'][1] + NH} V{P['C'][1]}",
               f"M{P['B'][0] + 90},{P['B'][1] + NH} V{P['B'][1] + NH + 18} H{P['C'][0] + 200} V{P['C'][1]}",
               f"M{P['B'][0] + 160},{P['B'][1] + NH} V{P['D'][1]}",
               f"M{P['C'][0] + 90},{P['C'][1] + NH} V{P['E'][1]}",
               f"M{P['D'][0] + 110},{P['D'][1] + NH} V{P['F'][1]}",
               f"M{P['E'][0] + 90},{P['E'][1] + NH} V{P['H'][1] - 14} H{P['H'][0] + 30} V{P['H'][1]}",
               f"M{P['F'][0] + 150},{P['F'][1] + NH} V{P['H'][1] - 26} H{P['H'][0] + 70} V{P['H'][1]}",
               f"M{P['G'][0] + 70},{P['G'][1] + NH} V{P['H'][1]}"]:
        o.append(f'<path d="{ed}" class="edge" marker-end="url(#ar)"/>')
    o.append(f'<path d="M{P["H"][0] + 160},{P["H"][1]} V{P["H"][1] - 24} H{P["G"][0] + 170} V{P["G"][1] + NH}" class="edge fb" marker-end="url(#ar2)"/>')
    for k, (x, y) in P.items():
        w = NW if k != "H" else 330
        o.append(f'<a href="#n-{k}" class="node {ns(k)}"><rect x="{x}" y="{y}" width="{w}" height="{NH}" rx="10"/>'
                 f'<circle cx="{x + 22}" cy="{y + 31}" r="12" class="lc"/><text x="{x + 22}" y="{y + 36}" class="lt" text-anchor="middle">{k}</text>'
                 f'<text x="{x + 44}" y="{y + 27}" class="n">{E(NODE_NAMES[k])}</text><text x="{x + 44}" y="{y + 48}" class="s">{E(sub(k))}</text></a>')
    o.append("</svg>")
    chips = "".join(f'<a href="#n-{k}" class="chip {ns(k)}"><b>{k}</b>{E(NODE_NAMES[k])}<span>{E(sub(k))}</span></a>' for k in "ABCDEFGH")

    def sec(k, q, body):
        hits = a["nodes"].get(k) or []
        vd = verdict(ns(k), sc.get(k), hits) if hits and k != "H" else ""
        return (f'<section class="nd" id="n-{k}"><div class="ndh"><span class="lc2 {ns(k)}">{k}</span><div><h3>{E(NODE_NAMES[k])}</h3>'
                f'<p class="q">{E(q)}</p></div></div>{vd}{body}</section>')

    pf = lambda x: "—" if x is None else f"{x:+.0f}%"
    if m["turn_loss"]:
        pf_np = "由盈转亏"
    else:
        pf_np = pf(m["np_yoy"])
    ftab = ('<div class="tblwrap"><table class="mt"><thead><tr><th>口径</th><th>营收</th><th>营收同比</th><th>净利润</th><th>净利润同比</th></tr></thead><tbody>'
            f'<tr><th scope="row">{m["q_label"]} 单季</th><td>{yi(m["q_rev"])}</td><td class="{st(m["rev_yoy"] or 0)}">{pf(m["rev_yoy"])}</td><td>{yi(m["q_np"])}</td><td class="{"down" if m["turn_loss"] else st(m["np_yoy"] or 0)}">{pf_np}</td></tr>'
            f'<tr><th scope="row">上半年累计</th><td></td><td class="{st(m["h_rev_yoy"] or 0)}">{pf(m["h_rev_yoy"])}</td><td></td><td class="{st(m["h_np_yoy"] or 0)}">{pf(m["h_np_yoy"])}</td></tr>'
            f'<tr><th scope="row">前三季度累计</th><td></td><td></td><td>{yi(m["cum_np"])}</td><td class="{st(m["cum_np_yoy"] or 0)}">{pf(m["cum_np_yoy"])}</td></tr>'
            '</tbody></table></div>'
            f'<p class="note">口径：板块 {m["n"]} 家成分股的合计数，由累计值相减得到单季。龙头公司权重很大，合计数往往由少数几家决定。'
            + ("单季利润贡献最大的是" + "、".join(f"{n}（{yi(v)}，占盈利公司合计的 {p:.0f}%）" for n, v, p in m["top"]) + "。" if m["top"] else "") + '</p>')
    share = a["share"][-250:]
    g_chart = line_chart([("成交额占全 A 比例（%）", "#C8312B", share)], ylabel="板块成交额占比", fmt="{:.2f}")
    k = a["kline"]
    base = k[-250]["date"] if len(k) >= 250 else k[0]["date"]
    hsr = {r["date"]: r["close"] for r in D.idx["idx_hs300"]["rows"]}
    h_chart = line_chart([(cfg["name"], "#C8312B", [(r["date"], r["close"] / [x for x in k if x["date"] == base][0]["close"] * 100) for r in k if r["date"] >= base]),
                          ("沪深 300", "#18202B", [(r["date"], hsr[r["date"]] / hsr[base] * 100) for r in k if r["date"] >= base and r["date"] in hsr])],
                         ylabel="板块和沪深 300 近一年走势，一年前 = 100", fmt="{:.0f}")
    cons = sorted(a["cons"], key=lambda c: -(c.get("f20") or 0))[:15]
    cand_codes = {s["cfg"]["code"] for s in stocks_in}
    num = lambda x, f: "—" if x in (None, "-") else f.format(x)

    def cname(c):
        if c["f12"] in cand_codes:
            return f'<a href="../stocks/{c["f12"]}.html">{E(c["f14"])}</a>'
        return E(c["f14"])
    crow = "".join(
        f'<tr><th scope="row">{cname(c)}<span class="hint">{c["f12"]}</span></th>'
        f'<td>{num(c["f2"], "{:.2f}")}</td><td class="{st(c["f3"] if isinstance(c["f3"], (int, float)) else 0)}">{num(c["f3"], "{:+.2f}%")}</td>'
        f'<td>{num((c["f20"] or 0) / 1e8, "{:,.0f}")} 亿</td><td>{num(c["f9"], "{:.1f}")}</td>'
        f'<td class="{st(c["f24"] if isinstance(c["f24"], (int, float)) else 0)}">{num(c["f24"], "{:+.1f}%")}</td>'
        f'<td class="{st(c["f25"] if isinstance(c["f25"], (int, float)) else 0)}">{num(c["f25"], "{:+.1f}%")}</td></tr>' for c in cons)
    ctab = ('<div class="tblwrap"><table class="mt"><thead><tr><th>成分股（按市值）</th><th>现价</th><th>今日</th><th>总市值</th><th>动态 PE</th><th>60 日</th><th>年初至今</th></tr></thead>'
            f'<tbody>{crow}</tbody></table></div>')

    nodes_html = (
        sec("A", "谁在买这个行业的产品，买得多不多？", f'<p class="note">{E(cfg["a_note"])}</p>'
            + rules("用成分股合计单季营收同比代替观察：≥ 20% 加 1，5–20% 加 0.5，0–5% 为 0，负增长减 1。具体的下游指标（如云厂商资本开支、汽车销量）需要人工跟踪。"))
        + sec("B", "政策和外部环境是顺风还是逆风？", '<p class="mnote">人工判定，' + ("你已确认。" if cfg.get("confirmed_by_user") else "待核验原始政策来源，暂不计分。") + '</p>'
              + rules("人工打分：明显顺风 +2，偏顺风 +1，中性 0，偏逆风 −1，明显逆风 −2。"))
        + sec("C", "行业整体还在多赚钱吗？", ftab
              + rules("成分股合计单季净利润同比 ≥ 20% 加 1，0–20% 加 0.5，负增长减 1；合计亏损减 1；一半以上成分股亏损再减 0.5。"))
        + sec("D", "利率和风险偏好对这个行业是压力还是支撑？", '<p class="note">直接引用大盘页的 D 节点，不计入板块合计。不同行业对利率的敏感度不同，具体看个股页的因子影响地图。</p>')
        + sec("E", "利润增速在加快还是放缓？", '<p class="note">机构对行业的一致预期暂未接入，本项暂不计分；下表仅描述实际利润同比与环比，不代表预期修订。</p>'
              + rules("最新单季利润同比比上半年累计同比高 10 个点以上加 1，低 10 个点以上减 1；单季环比 ≥ +5% 加 0.5，≤ −5% 减 0.5。"))
        + sec("F", "市场给的估值，增速撑得住吗？",
              f'<p class="note">板块 PE = 成分股总市值 ÷ 成分股滚动利润之和（截至 {a["d_now"]}），总市值 {yi(a["mc"])}。PEG = PE ÷ 前三季度利润增速。</p>'
              + rules("PEG < 1 加 1，1–2 为 0，> 2 减 1；利润下滑且 PE 高于 25 倍减 1；合计亏损无法计算时减 1。"))
        + sec("G", "资金是不是都挤在这里？", g_chart
              + '<p class="note">基金持仓和板块融资余额暂未接入，先看成交集中度。占比越高，说明越多资金在这里交易，一旦反向也越容易踩踏。</p>'
              + rules("近 5 日成交额占全 A 的比例处在近一年 85% 分位以上减 1；其余为 0。"))
        + sec("H", "板块实际走成了什么样？",
              f'<p class="note">板块指数 {t["close"]:.2f}，今日 {t["d1"]:+.2f}%；近 20 日 {t["d20"]:+.1f}%、近 60 日 {t["d60"]:+.1f}%；'
              f'相对沪深 300：20 日 {t["rs20"]:+.1f}、60 日 {t["rs60"]:+.1f}' + (f'、一年 {t["rs250"]:+.1f}' if t["rs250"] is not None else "") + ' 个点；'
              f'在 60 日线{"上方" if t["close"] > t["ma60"] else "下方"}' + (f'、250 日线{"上方" if t["close"] > t["ma250"] else "下方"}' if t["ma250"] else "") +
              f'；距一年高点 {t["dd"]:.1f}%。</p>' + h_chart)
    )
    rows = [{"key": k2, "name": NODE_NAMES[k2].split("：")[0] if k2 != "C" else "行业利润", "score": sc.get(k2),
             "hits": a["nodes"].get(k2) or [], "manual": k2 == "B", "href": f"#n-{k2}"} for k2 in "ABCEFG"]
    card_html = scorecard.card(rows, "板块合计", "合计只作变化提醒，不用于跨行业排名；人工草稿待核验。", a["hist"], ("B",))
    cand = "".join(f'<a class="chip2" href="../stocks/{s["cfg"]["slug"]}.html">{E(s["cfg"]["name"])}</a>' for s in stocks_in)
    tot = a["total"]
    om = (ctx.get("OUTLOOK_MAP") or {}).get(cfg["slug"])
    reason_html = ""
    if om:
        it, fill = om["item"], ctx["ofill"]
        hz = it.get("horizon", "")
        hz_html = f'<span class="hz-badge {"hz-struct" if "结构" in hz else "hz-cycle"}">{E(hz)}</span>' if hz and hz != "—" else ""
        line = lambda lab, txt: f'<p class="ol-p"><span class="ol-lab">{lab}</span>{E(fill(txt))}</p>' if txt else ""
        reason_html = (f'<section class="block reason-block">'
                       f'<p class="reason-label">大盘推断分档<span class="tag {om["cls"]}" style="margin-left:8px">{E(om["tier"])}</span>{hz_html}</p>'
                       + line("依据", it["why"]) + line("风险", it.get("risk")) + line("证伪 / 触发", it.get("falsify"))
                       + f'<p class="reason-link"><a href="../index.html#horizon">← 回到大盘推断</a>&emsp;<a href="../picks/index.html">查看半年名单 →</a></p>'
                       f'</section>')
    body = f"""
<div class="crumb"><a href="index.html">板块</a> ／ {E(cfg['name'])}</div>
<div class="hero shero"><div><h1>{E(cfg['name'])}<small>{cfg['slug']}</small></h1>
<div class="tags2"><span>{a['m']['n']} 家成分股</span><span>追踪股：</span>{cand}</div></div>
<div class="px"><b>{t['close']:.2f}</b><span class="{st(t['d1'])}">{t['d1']:+.2f}%</span><small>板块指数</small></div></div>
{reason_html}<section class="block" id="score"><h2>板块打分卡</h2><p class="sub">行业层六个维度各打 −2 到 +2 分，点任意一项跳到下面的展开分析。D（利率与风险偏好）直接引用大盘页，不计入板块合计。</p>{card_html}</section>
<section class="block" id="nodes"><h2>行业层传导图</h2><p class="sub">和大盘页、个股页同一套 A–H 骨架，换成了行业的变量。</p>
<div class="fwbox">{"".join(o)}</div><div class="chips">{chips}</div><div class="ndlist">{nodes_html}</div></section>
<section class="block"><h2>主要成分股</h2><p class="sub">按总市值排前 15。带链接的是追踪股。</p>{ctab}</section>"""
    return body


def index(analyses, ctx, by_board):
    rows = ""
    for a in analyses:
        cfg, t, sc = a["cfg"], a["t"], a["scores"]
        chips = "".join(f'<span class="tag {"na" if sc.get(k) is None else st(sc[k])}" title="{NODE_NAMES[k]}">{k}</span>' for k in "ABCEFG")
        names = "、".join(s["cfg"]["name"] for s in by_board.get(cfg["secid"], []))
        om = (ctx.get("OUTLOOK_MAP") or {}).get(cfg["slug"])
        tier = f'<span class="tag {om["cls"]}">{E(om["tier"])}</span>' if om else ""
        rows += (f'<a class="srow brow" href="{cfg["slug"]}.html"><span class="nm">{tier}{E(cfg["name"])}<small>{E(cfg.get("style", ""))}{"｜" + E(names) if names else ""}</small></span>'
                 f'<span class="kv">合计 <b class="{st(a["total"])}">{sg(a["total"])}</b></span>'
                 f'<span class="kv">20 日相对 <b class="{st(t["rs20"])}">{t["rs20"]:+.1f}</b></span>'
                 f'<span class="kv">利润同比 <b class="{st(a["m"]["np_yoy"] or 0)}">{("转亏" if a["m"]["turn_loss"] else "亏损" if a["m"]["q_np"] < 0 else "—") if a["m"]["np_yoy"] is None else format(a["m"]["np_yoy"], "+.0f") + "%"}</b></span>'
                 f'<span class="kv">PE / PEG <b>{"亏损" if a["pe_now"] is None else format(a["pe_now"], ".0f")}{"" if a["peg"] is None else " / " + format(a["peg"], ".2f")}</b></span>'
                 f'<span class="lys">{chips}</span></a>')
    return f"""<div class="hero"><h1>板块</h1><p class="sum">当前追踪的 {len(analyses)} 个板块。每个板块前面的标签是<a href="../index.html#horizon">大盘半年推断</a>给它的分档（核心配置 / 条件配置 / 观察）；下面用行业层 A–H 拆开看，合计分不含引用大盘的 D。</p>
<p class="stamp">色块依次是 A 下游需求、B 政策、C 行业利润、E 盈利预期（待数据）、F 估值、G 拥挤度：红色利好，绿色利空，灰色中性。“20 日相对”是板块近 20 日涨幅减去沪深 300，单位是百分点。</p></div>
<section class="block"><div class="slist">{rows}</div></section>
<section class="block"><h2>板块从哪里来</h2><p class="note">先在<a href="../index.html#horizon">大盘页</a>从 A–H 推出方向和分档，再用板块自己的利润、估值、拥挤度验证。早期的全市场初筛留档在 <a href="screen.html">全市场行业初筛</a>，已不作为当前依据。</p></section>"""


def build(ctx, stock_cfgs):
    root = ctx["ROOT"]
    cfgs = json.load(open(os.path.join(root, "data", "boards.json"), encoding="utf-8"))["boards"]
    out = os.path.join(ctx["SITE"], "boards")
    os.makedirs(out, exist_ok=True)
    res, analyses = {}, []
    by_board = {}
    for s in stock_cfgs:
        by_board.setdefault(s["board"]["secid"], []).append({"cfg": s})
    for cfg in cfgs:
        p = os.path.join(root, "data", "raw", "boards", cfg["slug"] + ".json")
        if not os.path.exists(p):
            continue
        a = analyze_board(cfg, json.load(open(p, encoding="utf-8")), ctx)
        a["hist"] = scorecard.record(root, "boards", cfg["slug"], ctx["TODAY"], {k: v for k, v in a["scores"].items() if k != "D"})
        analyses.append(a)
        res[cfg["secid"]] = a
        html_ = ctx["page"](f"{cfg['name']} | 板块 | A 股框架笔记", "bk", render(a, ctx, by_board.get(cfg["secid"], [])), "../")
        open(os.path.join(out, cfg["slug"] + ".html"), "w", encoding="utf-8").write(html_)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(ctx["page"]("板块 | A 股框架笔记", "bk", index(analyses, ctx, by_board), "../"))
    screen_page(ctx)
    return res


def screen_page(ctx):
    root = ctx["ROOT"]
    rp = os.path.join(root, "data", "raw", "screen", "result.json")
    lp = os.path.join(root, "data", "screen_longlist.json")
    if not (os.path.exists(rp) and os.path.exists(lp)):
        return
    res = {r["bk"]: r for r in json.load(open(rp, encoding="utf-8"))}
    ll = json.load(open(lp, encoding="utf-8"))
    prop = set(ll["proposal"])
    f = lambda x, p="+.0f", suf="%": "—" if x is None else format(x, p) + suf
    cards = ""
    for style in ("成长", "周期", "防守"):
        items = [i for i in ll["items"] if i["style"] == style]
        lis = ""
        for i in items:
            r = res[i["bk"]]
            star = f'<span class="star">{"已选定" if ll.get("final") else "首轮提议"}</span>' if i["bk"] in prop else ""
            lis += (f'<div class="ll"><div class="llh"><b>{E(r["name"])}</b>{star}<span class="v {st(r["total"])}">{sg(r["total"])}</span></div>'
                    f'<p class="kv2">单季利润 {f(r["np_yoy"])}　营收 {f(r["rev_yoy"])}　PE {f(r["pe"], ".0f", " 倍")}　PEG {f(r["peg"], ".2f", "")}　'
                    f'近一年相对沪深 300 {f(r["rs250"], "+.0f", " 点")}　拥挤度 {r["sh_pct"]:.0f}% 分位</p>'
                    f'<p><span class="tag up">理由</span>{E(i["why"])}</p><p><span class="tag down">风险</span>{E(i["risk"])}</p></div>')
        cards += f'<h3 class="h3s">{style}（{len(items)} 个）</h3><div class="lls">{lis}</div>'
    rows = ""
    in_ll = {i["bk"] for i in ll["items"]}
    for r in sorted(res.values(), key=lambda r: (-r["total"], -(r["np_yoy"] or -999))):
        mark = "★" if r["bk"] in prop else ("○" if r["bk"] in in_ll else "")
        rows += (f'<tr class="{"hl" if mark else ""}"><th scope="row">{mark} {E(r["name"])}<span class="hint">{r["bk"]}，{r["n"]} 家</span></th>'
                 f'<td class="{st(r["total"])}"><b>{sg(r["total"])}</b></td>'
                 + "".join(f'<td class="{st(r["sc"][k])}">{sg(r["sc"][k])}</td>' for k in "ACEFG")
                 + f'<td class="{st(r["np_yoy"] or 0)}">{f(r["np_yoy"])}</td><td>{f(r["pe"], ".0f", "")}</td><td>{f(r["peg"], ".2f", "")}</td>'
                 f'<td class="{st(r["rs60"])}">{r["rs60"]:+.0f}</td><td class="{st(r["rs250"])}">{r["rs250"]:+.0f}</td><td>{r["sh_pct"]:.0f}%</td></tr>')
    body = f"""<div class="crumb"><a href="index.html">板块</a> ／ 全市场初筛</div>
<div class="hero"><h1>全市场行业初筛（旧版留档）</h1><p class="mnote">此页沿用 v1 初筛方法，仅保留历史研究过程；不与 v2 分数比较，当前名单以个股页为准。</p><p class="sum">把东方财富 {len(res)} 个行业，全部按行业层的 A、C、E、F、G 五项打分，用来一起挑出未来半年值得追踪的 6 个板块。</p>
<p class="stamp">数据截至 {ll['date']}：利润用 2026 年三季报（单季 = 前三季度 − 上半年），估值为当日市值加权 PE。B（政策）是人工项，这里没有打。</p></div>
<section class="block"><h2>入围名单</h2><p class="sub">按“攻守平衡”的偏好，从成长、周期、防守三类里各挑出几个。{"标“已选定”的是最终确认的 6 个。" + ll.get("final_note", "") if ll.get("final") else "标“首轮提议”的是我建议的 6 个，等你删改。"}</p>{cards}</section>
<section class="block"><h2>全部行业</h2><p class="sub">★ 首轮提议，○ 入围。“60 日 / 一年”是相对沪深 300 的超额涨幅（百分点）；拥挤度是近 5 日成交额占全 A 比例在近一年的分位。</p>
<div class="tblwrap"><table class="mt scr"><thead><tr><th>行业</th><th>合计</th><th>A</th><th>C</th><th>E</th><th>F</th><th>G</th><th>单季利润</th><th>PE</th><th>PEG</th><th>60 日</th><th>一年</th><th>拥挤</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>"""
    open(os.path.join(ctx["SITE"], "boards", "screen.html"), "w", encoding="utf-8").write(ctx["page"]("全市场行业初筛 | A 股框架笔记", "bk", body, "../"))
