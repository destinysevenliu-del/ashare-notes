"""生成静态网站：site/index.html（大盘）和 site/trades.html（我的操作）。
用法：python3 -I pipeline/build.py <项目根目录>
"""
import json, os, sys, html, datetime

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import analyze as A  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
SITE = os.path.join(ROOT, "docs")
SNAP = os.path.join(ROOT, "data", "snapshots")
os.makedirs(SITE, exist_ok=True)
os.makedirs(SNAP, exist_ok=True)
E = html.escape
WEEK = "一二三四五六日"

D = A.Data(RAW)
manual = json.load(open(os.path.join(ROOT, "data", "manual.json"), encoding="utf-8"))
for item in (manual['external'], manual['policy']):
    if not item.get('evidence_verified', False):
        item['score'] = 0
        item['reason'] = '待核验，暂不计分。草稿：' + item['reason']
trades = json.load(open(os.path.join(ROOT, "data", "trades.json"), encoding="utf-8"))["trades"]
R = A.analyze(D, manual)
TODAY = R["date"]


def cn_date(s, week=False):
    d = datetime.date.fromisoformat(s[:10])
    t = f"{d.month} 月 {d.day} 日"
    return t + (f" 周{WEEK[d.weekday()]}" if week else "")


def short(s):
    d = datetime.date.fromisoformat(s[:10])
    return f"{d.month}/{d.day}"


# ---------- 小图 ----------
def spark(vals, w=120, h=30, color="#4B5565"):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = [(i * (w - 4) / (len(vals) - 1) + 2, h - 3 - (v - lo) / rng * (h - 6)) for i, v in enumerate(vals)]
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true">'
            f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="1.4"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{color}"/></svg>')


def line_chart(series_list, w=900, h=240, bands=None, ylabel="", fmt="{:.1f}"):
    """series_list: [(label, color, [(date, v)])]，共用横轴（按第一条的日期）"""
    padl, padr, padt, padb = 48, 16, 14, 28
    allv = [v for _, _, s in series_list for _, v in s]
    if bands:
        allv += [b[0] for b in bands]
    lo, hi = min(allv), max(allv)
    span = (hi - lo) or 1
    lo -= span * 0.06; hi += span * 0.06
    dates = [d for d, _ in series_list[0][2]]
    n = len(dates)
    X = lambda i: padl + i * (w - padl - padr) / max(n - 1, 1)
    Y = lambda v: padt + (hi - v) / (hi - lo) * (h - padt - padb)
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{E(ylabel)}">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        out.append(f'<line x1="{padl}" x2="{w - padr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                   f'<text x="{padl - 6}" y="{Y(v) + 4:.1f}" class="ax" text-anchor="end">{fmt.format(v)}</text>')
    if bands:
        for v, lab in bands:
            out.append(f'<line x1="{padl}" x2="{w - padr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="band"/>'
                       f'<text x="{w - padr - 4}" y="{Y(v) - 5:.1f}" class="bandlab" text-anchor="end">{E(lab)}</text>')
    for i in [0, n // 3, 2 * n // 3, n - 1]:
        out.append(f'<text x="{X(i):.1f}" y="{h - 8}" class="ax" text-anchor="{"start" if i == 0 else "end" if i == n - 1 else "middle"}">{dates[i][:7]}</text>')
    idx = {d: i for i, d in enumerate(dates)}
    for label, color, s in series_list:
        pts = [(X(idx[d]), Y(v)) for d, v in s if d in idx]
        out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{color}" stroke-width="1.8"/>')
        x, y = pts[-1]
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"/>')
    out.append("</svg>")
    leg = "".join(f'<span><i style="background:{c}"></i>{E(l)}</span>' for l, c, _ in series_list)
    return f'<div class="chartbox">{"".join(out)}<div class="cleg">{leg}</div></div>'


# ---------- 指标行 ----------
def cls(diff, good):
    if diff is None or good == 0 or abs(diff) < 1e-9:
        return "flat"
    return "up" if diff * good > 0 else "down"


def row(name, hint, val, diff_txt, diff_cls, sp, date, freq):
    return (f'<tr><th scope="row">{E(name)}<span class="hint">{E(hint)}</span></th>'
            f'<td class="v">{val}</td><td class="chg {diff_cls}">{diff_txt}</td>'
            f'<td class="sp">{sp}</td><td class="dt">{E(date)}<span class="freq">{E(freq)}</span></td></tr>')


def drow(name, hint, s, fmt="{:.2f}", unit="", good=0, mode="abs", n=120, freq="每日"):
    a, b = s[-2][1], s[-1][1]
    if mode == "bp":
        diff = (b - a) * 100; dt = f"{diff:+.1f}bp"
    elif mode == "pct":
        diff = (b / a - 1) * 100; dt = f"{diff:+.2f}%"
    else:
        diff = b - a; dt = (fmt if "{:+" in fmt else fmt.replace("{:", "{:+")).format(diff) + unit
    return row(name, hint, fmt.format(b) + unit, dt, cls(diff, good), spark([v for _, v in s[-n:]]), short(s[-1][0]), freq)


def mrow(name, hint, m, unit="%", good=0, freq="每月"):
    a, b = m[-2]["v"], m[-1]["v"]
    diff = b - a
    return row(name, hint, f"{b:g}{unit}", f"{diff:+.1f}", cls(diff, good), spark([x["v"] for x in m[-24:]]),
               m[-1]["period"].replace("年", "-").replace("月份", "").replace("第1-", "Q1-").replace("季度", ""), freq)


def table(rows):
    return ('<div class="tblwrap"><table class="mt"><thead><tr><th>指标</th><th>最新</th><th>较上期</th>'
            '<th>走势</th><th>数据日期</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


STATE_TXT = {"up": "利好", "down": "利空", "flat": "中性", "na": "暂缺", "price": "结果"}


def verdict(state, score, hits, manual_note=None):
    lis = "".join(f'<li><span class="pt {"up" if p > 0 else "down" if p < 0 else "flat"}">{p:+g}</span>{E(t)}</li>' for t, p in hits)
    sc = "" if score is None else f"<b>{(f'{score:+d}' if score else '0')}</b>"
    note = f'<p class="mnote">{manual_note}</p>' if manual_note else ""
    return (f'<div class="verdict {state}"><div class="vh"><span class="tag {state}">{STATE_TXT[state]}</span>{sc}'
            f'<span class="vwhy">判定依据</span></div><ul>{lis}</ul>{note}</div>')


def rules(text):
    return f'<details class="rules"><summary>怎么判的</summary>{text}</details>'


def events(layer):
    ev = [e for e in manual["events"] if e["layer"] == layer]
    if not ev:
        return ""
    lis = "".join(f'<li><span class="tag {"up" if e["dir"] == "up" else "flat"}">{E(e.get("status", "利好" if e["dir"] == "up" else "待核验"))}</span>'
                  f'<b>{E(e["title"])}</b><span class="evd">{E(e["date"])}</span><p>{E(e["note"])}<span class="src">来源：{E(e["source"])}</span></p></li>'
                  for e in ev)
    return f'<h4>相关事件</h4><ul class="ev">{lis}</ul>'


# ---------- 各节点内容 ----------
sr = {r["key"]: r for r in R["score_rows"]}
dims = R["dims"]
N = R["nodes"]
spread = [(d, v - (A.value_at(D.us10, d) or 0)) for d, v in D.cn10 if A.value_at(D.us10, d) is not None]
eps_idx = [(d, v / D.eps_all[-250][1] * 100) for d, v in D.eps_all]
pe_pct_hist = A.pct_rank([v for _, v in D.pe_all], D.pe_all[-1][1])
pe300_pct = A.pct_rank([v for _, v in D.pe_300], D.pe_300[-1][1])
erp = A.erp_series(D, TODAY)

sec = {}
manual_flag = lambda m: ("人工判定，" + ("证据已核验" if m.get("evidence_verified") else "证据待核验，暂不计分") + f"，更新于 {cn_date(m['updated'])}。")

sec["A"] = dict(
    title="全球环境与国内经济",
    q="经济在扩张还是收缩？外部有没有大的冲击？",
    body=verdict(N["A"]["state"], N["A"]["score"],
                 dims["glob"]["hits"] + [("外部事件：" + manual["external"]["reason"], manual["external"]["score"])]
                 + dims["econ"]["hits"],
                 "全球环境（VIX、美元、信用利差）自动判定；外部事件这一条是" + manual_flag(manual["external"]))
    + '<h4>全球环境</h4><p class="sub">A 股与港股的共同外部变量：美元流动性、全球风险偏好、信用条件。三项都来自 FRED 日频序列。</p>'
    + table([
        drow("VIX 波动率", "越高越恐慌，全球风险偏好在收缩", D.glob.get("vix", []), "{:.1f}", "", -1, "pct", 120),
        drow("广义美元指数", "美元走强通常压制新兴市场资金", D.glob.get("usd_broad", []), "{:.1f}", "", -1, "pct", 120),
        drow("美国高收益信用利差", "走阔说明信用环境在收紧", D.glob.get("us_hy_oas", []), "{:.2f}", "%", -1, "bp", 120),
    ])
    + '<h4>国内基本面</h4>'
    + table([
        mrow("制造业 PMI", "50 以上是扩张，以下是收缩", D.pmi, "", 1),
        mrow("非制造业 PMI", "服务业和建筑业的景气", D.pmi_n, "", 1),
        mrow("工业增加值同比", "生产端", D.indus, "%", 1),
        mrow("社会消费品零售同比", "消费端", D.retail, "%", 1),
        mrow("出口同比", "外需", D.exports, "%", 1),
        mrow("CPI 同比", "居民物价，太高太低都不好", D.cpi, "%", 0),
        mrow("GDP 累计同比", "按季度公布", D.gdp, "%", 1, "每季度"),
    ])
    + events("A")
    + rules("国内经济分：制造业 PMI ≥ 50.5 加 1，50–50.5 加 0.5，49.5–50 减 0.5，低于 49.5 减 1；比上月变动 ±0.5 以上再加减 0.5；"
            "社零同比 ≥ 5% 加 0.5、低于 3% 减 0.5；工业增加值 ≥ 6% 加 0.5、低于 4% 减 0.5；出口 ≥ 5% 加 0.5、负增长减 0.5。合计四舍五入，限定在 −2 到 +2。"
            "全球环境分：VIX ≥30 减 1、22–30 减 0.5、≤14 加 0.5，20 日变动 ±30% 再加减 0.5；广义美元 20 日 ±1.5% 减／加 0.5；"
            "美国高收益信用利差 ≥5% 减 0.5，20 日走阔或收窄 50bp 再加减 0.5。外部事件分由人工判断。A 节点的颜色看三者之和。"),
)

lp1, lp5 = D.lpr1, D.lpr5
sec["B"] = dict(
    title="货币、财政与产业政策",
    q="政策是在托底、加码，还是收紧？",
    body=verdict(N["B"]["state"], N["B"]["score"], [(manual["policy"]["reason"], manual["policy"]["score"])],
                 "这一项是" + manual_flag(manual["policy"]) + "政策没有稳定的自动数据，靠整理新闻和公告，可能滞后或遗漏。")
    + table([
        row("1 年期 LPR", "贷款利率基准，下调代表货币宽松", f"{lp1[-1][1]:g}%", f"{lp1[-1][1] - lp1[-2][1]:+.2f}",
            cls(lp1[-1][1] - lp1[-2][1], -1), spark([v for _, v in lp1]), short(lp1[-1][0]), "每月 20 日"),
        row("5 年期 LPR", "房贷利率基准", f"{lp5[-1][1]:g}%", f"{lp5[-1][1] - lp5[-2][1]:+.2f}",
            cls(lp5[-1][1] - lp5[-2][1], -1), spark([v for _, v in lp5]), short(lp5[-1][0]), "每月 20 日"),
    ])
    + events("B")
    + rules("政策分由人工判断：方向明确托底且力度大 +2；方向托底但力度待观察 +1；中性 0；边际收紧 −1；明显收紧 −2。"),
)

sec["C"] = dict(
    title="需求、成本与企业盈利",
    q="上市公司整体还在多赚钱吗？",
    body=verdict(N["C"]["state"], N["C"]["score"], R["earn"]["hits"])
    + table([
        row("全 A 滚动盈利（推算）", "指数点位 ÷ 市盈率，近似全市场过去 12 个月利润，一年前 = 100",
            f"{eps_idx[-1][1]:.1f}", f"近 60 日 {R['earn']['e60']:+.1f}%", cls(R['earn']['e60'], 1),
            spark([v for _, v in eps_idx[-250:]]), short(eps_idx[-1][0]), "每日（随财报跳变）"),
        mrow("PPI 同比", "工业品出厂价格；对利润需结合成本与需求判断", D.ppi, "%", 1),
        mrow("CPI 同比", "居民端物价，与 PPI 一起看利润分配", D.cpi, "%", 0),
    ])
    + '<h4>利润分配：涨价落在哪个环节</h4><p class="sub">这一项只做结构提示，不进入打分——上游涨价对中下游是成本，正负相抵后没有总和信号，但对选板块最关键。</p>'
    + table([
        row("PPI − CPI 剪刀差", "大于 0 表示涨价集中在上游，利润向资源端转移",
            f"{R['earn']['split']:+.1f}pp",
            (f"3 个月 {R['earn']['split'] - R['earn']['split_old']:+.1f}pp" if R['earn'].get('split_old') is not None else ""),
            cls(R['earn']['split'] - (R['earn']['split_old'] if R['earn'].get('split_old') is not None else R['earn']['split']), 1),
            "", short(TODAY), "每月（随 PPI／CPI）"),
    ])
    + rules("全 A 滚动盈利近 60 个交易日增长 ≥ 3% 加 1，下降 ≥ 3% 减 1；PPI 与 CPI 的剪刀差只做结构展示，不进入总分。"
            "注意：盈利数据主要在财报季（4、8、10 月底）跳变，其余时间变化不大。"),
)

sec["D"] = dict(
    title="利率、融资条件与风险偏好",
    q="钱是变便宜了还是变贵了？外资和风险偏好的压力大不大？",
    body=verdict(N["D"]["state"], N["D"]["score"], dims["liq"]["hits"] or [("各项变化都不大，没有触发加减分", 0)])
    + table([
        drow("中国 10 年国债收益率", "越低，股票相对越有吸引力", D.cn10, "{:.3f}", "%", -1, "bp"),
        drow("美国 10 年国债收益率", "越高，全球成长股估值压力越大", D.us10, "{:.2f}", "%", -1, "bp"),
        drow("中美利差", "中国减美国，越负外资流出压力越大", spread, "{:.2f}", "%", 1, "bp"),
        drow("离岸人民币", "数字变小代表人民币升值", D.cnh, "{:.4f}", "", -1, "pct"),
        row("实际利率（10Y − PPI）", "扣掉通胀后的真实融资成本，越低对风险资产越有利",
            (f"{dims['liq']['rr']:+.1f}%" if dims['liq'].get('rr') is not None else "待数据"),
            (f"3 个月 {dims['liq']['drr']:+.1f}pp" if dims['liq'].get('drr') is not None else ""),
            cls(dims['liq'].get('drr') or 0, -1), "", short(TODAY), "每月（随 PPI）"),
        mrow("M1 同比", "企业活期存款，回升代表资金在活跃", D.m1, "%", 1),
        mrow("M2 同比", "广义货币", D.m2, "%", 0),
        row("M1 − M2 剪刀差", "扩大代表资金从定期活化到活期，是风险偏好的领先指标",
            (f"{dims['liq']['sky']:+.1f}pp" if dims['liq'].get('sky') is not None else "待数据"),
            (f"3 个月 {dims['liq']['sky_chg']:+.1f}pp" if dims['liq'].get('sky_chg') is not None else ""),
            cls(dims['liq'].get('sky_chg') or 0, 1), "", short(TODAY), "每月"),
    ])
    + rules("中国 10 年国债近 20 日下行 ≥ 10bp 加 1，上行 ≥ 10bp 减 1；美国 10 年国债近 20 日回落 ≥ 20bp 加 0.5，上行 ≥ 20bp 减 0.5，"
            "且水平 ≥ 4.5% 再减 0.5；人民币近 20 日升值 ≥ 1% 加 0.5，贬值 ≥ 1% 减 0.5；M1 同比比 3 个月前高 1 个点以上加 0.5，低 1 个点以上减 0.5；"
            "近 3 个月 LPR 下调加 0.5，上调减 0.5；"
            "实际利率（10 年国债 − PPI 同比）3 个月下降 ≥ 0.5 个百分点加 1，上升 ≥ 0.5 个百分点减 1；"
            "M1−M2 剪刀差比 3 个月前扩大 1 个点以上加 0.5，收窄 1 个点以上减 0.5。社融暂未接入（数据源未找到）。"),
)

sec["E"] = dict(
    title="未来收益预期",
    q="机构预期未来的利润会上调还是下调？",
    body='<div class="verdict na"><div class="vh"><span class="tag na">暂缺</span></div>'
         '<p class="mnote">全市场的机构盈利一致预期，目前没有找到稳定的免费数据源，这一环暂时空着，也不参与打分。'
         '可以先看 C 节点的实际盈利变化做参考。到第三期做个股时，会接入个股层面的一致预期。</p></div>',
)

val_chart = line_chart([("全 A 市盈率（倍）", "#27408B", D.pe_all)],
                       bands=[(sorted(v for _, v in D.pe_all)[int(len(D.pe_all) * 0.2)], "20% 分位"),
                              (sorted(v for _, v in D.pe_all)[int(len(D.pe_all) * 0.8)], "80% 分位")],
                       ylabel="全 A 市盈率 2019 年以来走势")
sec["F"] = dict(
    title="投资者愿意支付的估值",
    q="现在的价格贵不贵？股票和债券比哪个更划算？",
    body=verdict(N["F"]["state"], N["F"]["score"], dims["val"]["hits"])
    + table([
        row("全 A 市盈率", "中证全指 PE-TTM", f"{D.pe_all[-1][1]:.2f} 倍", f"{D.pe_all[-1][1] - D.pe_all[-2][1]:+.2f}",
            cls(D.pe_all[-1][1] - D.pe_all[-2][1], 0), spark([v for _, v in D.pe_all[-250:]]), short(D.pe_all[-1][0]), "每日"),
        row("全 A 估值分位", "2019 年以来，越低越便宜", f"{pe_pct_hist:.0f}%", "", "flat", "", short(D.pe_all[-1][0]), "每日"),
        row("沪深 300 市盈率", "大盘蓝筹", f"{D.pe_300[-1][1]:.2f} 倍", f"分位 {pe300_pct:.0f}%",
            "flat", spark([v for _, v in D.pe_300[-250:]]), short(D.pe_300[-1][0]), "每日（2016 年以来分位）"),
        row("全 A 盈利分位", "滚动盈利在 2019 年以来的位置，和估值分位配对看",
            f"{dims['val']['eps_pct']:.0f}%", f"估值分位 {dims['val']['pct']:.0f}%", "flat",
            "", short(D.pe_all[-1][0]), "每日"),
        row("股债性价比", "全 A 盈利收益率减中国 10 年国债，越高股票越划算", f"{erp[-1][1]:.2f}%",
            f"分位 {dims['val']['epct']:.0f}%", cls(dims['val']['epct'] - 50, 1),
            spark([v for _, v in erp[-250:]]), short(erp[-1][0]), "每日"),
    ])
    + f'<p class="note"><b>估值分位与盈利分位要配对读：</b>{E(dims["val"]["quad"])}。盈利分位高说明当前利润处在历史高位，这时 PE 分位低往往意味着「市场认为这个利润不可持续」，不是便宜。</p>'
    + val_chart
    + rules("全 A 市盈率在 2019 年以来的分位：低于 15% 加 2，15–35% 加 1，35–65% 为 0，65–85% 减 1，高于 85% 减 2；"
            "股债性价比分位 ≥ 80% 再加 0.5，≤ 20% 再减 0.5。"),
)

mb = D.mbal
lev_pct = dims["funds"].get("lev_pct")
lev_pct = lev_pct if lev_pct is not None else A.pct_rank([v for _, v in D.mlev[-250:]], D.mlev[-1][1])
g_chart = line_chart([("两融余额（一年前 = 100）", "#C8312B", [(d, v / mb[-250][1] * 100) for d, v in mb[-250:]]),
                      ("中证全指（一年前 = 100）", "#4B5565",
                       [(d, v / A.value_at(D.all_close, mb[-250][0]) * 100) for d, v in D.all_close if d >= mb[-250][0]])],
                     ylabel="两融余额与指数近一年走势", fmt="{:.0f}")
sec["G"] = dict(
    title="参与者的仓位、申赎与交易约束",
    q="增量资金在进还是在出？杠杆是过热还是在出清？",
    body=verdict(N["G"]["state"], N["G"]["score"], dims["funds"]["hits"] or [("变化不大，没有触发加减分", 0)])
    + table([
        drow("两融余额", "杠杆资金的总量", [(d, v / 1e4) for d, v in mb], "{:.3f}", " 万亿", 1, "pct", 250),
        drow("两融单日净买入", "正数是加杠杆，负数是还钱", D.mnet, "{:+.0f}", " 亿", 1, "abs", 60),
        row("两融占流通市值", "杠杆拥挤度：比例比绝对额更可比，过高容易踩踏",
            f"{D.mlev[-1][1]:.2f}%", f"一年 {lev_pct:.0f}% 分位", "flat", "", short(D.mlev[-1][0]), "每日（T+1）"),
        drow("全 A 成交额", "交易活跃度", D.turnover, "{:,.0f}", " 亿", 1, "pct", 120),
    ])
    + '<p class="note">图里两条线一起看：两融和指数同向下跌是去杠杆的踩踏；指数涨而两融不涨，说明上涨不是靠杠杆推的。股价反过来也会影响这一环（图中 H 指向 G 的虚线），比如下跌触发平仓，平仓又加剧下跌。</p>'
    + g_chart
    + '<p class="note">两融数据由交易所在收盘后统计公布，比行情晚一个交易日左右。股票 ETF 申赎和新发基金数据暂未接入。</p>'
    + rules("两融余额 5 日变化 ≥ +2% 加 1，≤ −2% 减 1；20 日变化 ≥ +5% 加 0.5，≤ −5% 减 0.5；"
            "两融占流通市值在近一年 90% 分位以上减 0.5（拥挤），10% 分位以下加 0.5（杠杆已出清）；"
            "近 5 日成交额是 60 日均值的 1.2 倍以上加 0.5，0.8 倍以下减 0.5。"),
)


# H：指数表
def idx_stats(rows):
    c = [r["close"] for r in rows]
    ds = [r["date"] for r in rows]
    y0 = [r["close"] for r in rows if r["date"] < TODAY[:4] + "-01-01"][-1]
    ma = lambda n: sum(c[-n:]) / n
    hi250 = max(c[-250:])
    return dict(close=c[-1], d1=(c[-1] / c[-2] - 1) * 100, d5=(c[-1] / c[-6] - 1) * 100, d20=(c[-1] / c[-21] - 1) * 100,
                ytd=(c[-1] / y0 - 1) * 100, dd=(c[-1] / hi250 - 1) * 100, ma60=c[-1] > ma(60), ma250=c[-1] > ma(250))


def pc(x):
    return f'<td class="{"up" if x > 0 else "down" if x < 0 else "flat"}">{x:+.2f}%</td>'


hrows = ""
for key in ["idx_sh", "idx_hs300", "idx_cyb", "idx_kc50", "idx_all"]:
    s = idx_stats(D.idx[key]["rows"])
    hrows += (f'<tr><th scope="row">{E(D.idx[key]["name"])}</th><td class="v">{s["close"]:,.2f}</td>{pc(s["d1"])}{pc(s["d5"])}{pc(s["d20"])}{pc(s["ytd"])}'
              f'<td class="down">{s["dd"]:.1f}%</td><td>{"上方" if s["ma60"] else "下方"}</td><td>{"上方" if s["ma250"] else "下方"}</td></tr>')
base_d = D.idx["idx_all"]["rows"][-250]["date"]
h_chart = line_chart([(D.idx[k]["name"], col, [(r["date"], r["close"] / A.value_at([(x["date"], x["close"]) for x in D.idx[k]["rows"]], base_d) * 100)
                                              for r in D.idx[k]["rows"] if r["date"] >= base_d])
                      for k, col in [("idx_hs300", "#18202B"), ("idx_cyb", "#C8312B"), ("idx_kc50", "#D88B1F"), ("idx_sh", "#7C8696")]],
                     ylabel="主要指数近一年走势，一年前 = 100", fmt="{:.0f}")
sec["H"] = dict(
    title="股价与市场走势",
    q="前面七环作用之后，市场实际走成了什么样？",
    body='<p class="note">这一环是结果，不打分。用它来对照：前面的判断和实际走势是否一致，不一致的地方往往最值得研究。</p>'
         '<div class="tblwrap"><table class="mt it"><thead><tr><th>指数</th><th>收盘</th><th>今日</th><th>5 日</th><th>20 日</th><th>年内</th>'
         '<th>距一年高点</th><th>60 日线</th><th>250 日线</th></tr></thead><tbody>' + hrows + '</tbody></table></div>' + h_chart,
)


# ---------- 框架图 ----------
NODE_POS = {"A": (20, 20), "B": (370, 20), "C": (35, 120), "D": (370, 120), "E": (50, 220), "F": (370, 220), "G": (700, 220), "H": (640, 330)}
NODE_NAME = {"A": "全球环境与国内经济", "B": "货币、财政与产业政策", "C": "需求、成本与企业盈利", "D": "利率、融资条件与风险偏好",
             "E": "未来收益预期", "F": "投资者愿意支付的估值", "G": "参与者的仓位、申赎与交易约束", "H": "股价与市场走势"}
NW, NH = 290, 62


def node_sub(k):
    n = N[k]
    if k == "H":
        s = idx_stats(D.idx["idx_hs300"]["rows"])
        return f"沪深 300 今日 {s['d1']:+.2f}%，年内 {s['ytd']:+.1f}%"
    if n["state"] == "na":
        return "暂缺：没有可靠数据源"
    return f"{STATE_TXT[n['state']]} {n['score']:+d}" if n["score"] else STATE_TXT[n["state"]] + " 0"


def diagram(states=None, subs=None, idp="", label="大盘层传导图，节点颜色表示今日判定"):
    states = states or {k: N[k]["state"] for k in NODE_POS}
    subs = subs or {k: node_sub(k) for k in NODE_POS}
    o = [f'<svg class="fw" viewBox="0 0 1000 410" role="img" aria-label="{E(label)}">',
         f'<defs><marker id="{idp}ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9AA2AF"/></marker>'
         f'<marker id="{idp}ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#D88B1F"/></marker></defs>']
    P = NODE_POS
    def bx(k): x, y = P[k]; return x, y, x + NW, y + NH
    edges = [
        f"M{P['A'][0] + 90},{P['A'][1] + NH} V{P['C'][1]}",
        f"M{P['B'][0] + 90},{P['B'][1] + NH} V{P['B'][1] + NH + 18} H{P['C'][0] + 200} V{P['C'][1]}",
        f"M{P['B'][0] + 160},{P['B'][1] + NH} V{P['D'][1]}",
        f"M{P['C'][0] + 90},{P['C'][1] + NH} V{P['E'][1]}",
        f"M{P['D'][0] + 110},{P['D'][1] + NH} V{P['F'][1]}",
        f"M{P['E'][0] + 90},{P['E'][1] + NH} V{P['H'][1] - 14} H{P['H'][0] + 30} V{P['H'][1]}",
        f"M{P['F'][0] + 150},{P['F'][1] + NH} V{P['H'][1] - 26} H{P['H'][0] + 70} V{P['H'][1]}",
        f"M{P['G'][0] + 70},{P['G'][1] + NH} V{P['H'][1]}",
    ]
    for e in edges:
        o.append(f'<path d="{e}" class="edge" marker-end="url(#{idp}ar)"/>')
    o.append(f'<path d="M{P["H"][0] + 160},{P["H"][1]} V{P["H"][1] - 24} H{P["G"][0] + 170} V{P["G"][1] + NH}" class="edge fb" marker-end="url(#{idp}ar2)"/>')
    for k, (x, y) in P.items():
        st = states[k]
        w = NW if k != "H" else 330
        o.append(f'<a href="#node-{k}" class="node {st}"><rect x="{x}" y="{y}" width="{w}" height="{NH}" rx="10"/>'
                 f'<circle cx="{x + 22}" cy="{y + 31}" r="12" class="lc"/><text x="{x + 22}" y="{y + 36}" class="lt" text-anchor="middle">{k}</text>'
                 f'<text x="{x + 44}" y="{y + 27}" class="n">{E(NODE_NAME[k])}</text>'
                 f'<text x="{x + 44}" y="{y + 48}" class="s">{E(subs[k])}</text></a>')
    o.append("</svg>")
    return "".join(o)


# ---------- 打分卡 ----------
def scale(s):
    cells = []
    for v in (-2, -1, 0, 1, 2):
        c = ""
        if v == 0: c = "mid"
        if s < 0 and s <= v < 0: c = "d"
        if s > 0 and 0 < v <= s: c = "u"
        cells.append(f'<span class="{c}"></span>')
    return '<div class="scale">' + "".join(cells) + "</div>"


def scorecard():
    cells = ""
    for r in R["score_rows"]:
        s = r["score"]
        c = "up" if s > 0 else "down" if s < 0 else "flat"
        first = E(r["hits"][0][0]) if r["hits"] else "没有触发加减分"
        if not r.get("manual") and len(r["hits"]) > 1:
            first = "；".join(E(h[0]) for h in r["hits"][:2])
        lab = '<span class="man">人工</span>' if r.get("manual") else ""
        cells += (f'<a class="sc" href="#node-{r["node"]}"><div class="lbl">{E(r["name"])}{lab}<span class="v {c}">{("待核验" if r.get("manual") and not manual["external" if r["key"] == "ext" else "policy"].get("evidence_verified") else (f"{s:+d}" if s else "0"))}</span></div>'
                  f'{scale(s)}<p>{first}</p></a>')
    t = R["total"]
    auto_keys = ("glob", "econ", "liq", "val", "funds")
    n_scored = len(auto_keys) + sum(1 for m in (manual["external"], manual["policy"]) if m.get("evidence_verified"))
    lim = 2 * n_scored
    # 30 日自动维度合计走势（与上面同一口径：只含自动维度）
    hs = [sum(h[k] for k in auto_keys) for h in R["hist"]]
    w, h = 300, 64
    bars = ""
    bw = w / len(hs)
    for i, v in enumerate(hs):
        y0 = h / 2
        hh = abs(v) * (h / 2 - 4) / max(4, max(abs(x) for x in hs))
        y = y0 - hh if v > 0 else y0
        bars += f'<rect x="{i * bw + 1:.1f}" y="{y:.1f}" width="{bw - 2:.1f}" height="{max(hh, 1):.1f}" class="{"u" if v > 0 else "d" if v < 0 else "z"}"/>'
    trend = (f'<svg viewBox="0 0 {w} {h}" class="trend" aria-label="近 30 个交易日自动维度合计">{bars}'
             f'<line x1="0" x2="{w}" y1="{h / 2}" y2="{h / 2}" stroke="#7C8696" stroke-width=".6"/></svg>')
    return (f'<div class="score">{cells}<div class="sc total"><div class="lbl">合计（{n_scored} 项已计分，满分 ±{lim}）<span class="v">{t:+d}</span></div>'
            f'<p>人工两项未核验时记为 0，<b>不等于中性</b>，只是没有证据。下面是近 30 个交易日五个自动维度的合计（{short(R["hist"][0]["date"])}–{short(R["hist"][-1]["date"])}，'
            f'从 {hs[0]:+d} 到 {hs[-1]:+d}），人工维度待核验。历史宏观发布日期部分为估计，只供学习观察，不作严格回测。</p>{trend}</div></div>')


# ---------- 今日变化 ----------
def changes():
    items = R["changes"]
    if not items:
        return '<p class="note">和上一交易日相比，没有指标出现值得注意的变化。</p>'
    lis = ""
    for c in items:
        k = c["dir"]
        badge = {"up": "利好", "down": "利空", "flat": "新数据", "alert": "提醒"}[k]
        link = f' <a href="#node-{c["node"]}">看 {c["node"]} 节点</a>' if c["node"] else ""
        lis += f'<li><span class="tag {k}">{badge}</span>{E(c["text"])}{link}</li>'
    return f'<ul class="chg-list">{lis}</ul>'


def conds_html():
    lis = ""
    for c in R["conds"]:
        st = "hit" if c["hit"] else "ok"
        lab = ("今天新触发" if c.get("new") else "触发中") if c["hit"] else "未触发"
        lis += f'<li class="{st}"><span class="cs">{lab}</span><b>{E(c["name"])}</b><span class="cn">{E(c["now"])}</span></li>'
    return f'<ul class="conds">{lis}</ul>'


def today_lead():
    """今天变了什么：先给结论，再展开明细。"""
    rows = R["score_rows"]
    valid = [r for r in rows if r["score"] is not None]
    neg = sorted([r for r in valid if r["score"] < 0], key=lambda r: r["score"])
    pos = sorted([r for r in valid if r["score"] > 0], key=lambda r: -r["score"])
    sig = [c for c in R["changes"] if c["dir"] in ("up", "down")]
    neut = [c for c in R["changes"] if c["dir"] == "flat"]
    newc = [c for c in R["conds"] if c.get("new")]
    n = sum(1 for r in rows if not r.get("manual")) + sum(
        1 for m in (manual["external"], manual["policy"]) if m.get("evidence_verified"))
    main = f"合计 {R['total']:+d} 分（{n} 项已计分，满分 ±{2 * n}）。"
    if neg: main += "最弱的是" + "、".join(f"{r['name']} {r['score']:+d}" for r in neg[:2]) + "；"
    if pos: main += "支撑来自" + "、".join(f"{r['name']} {r['score']:+d}" for r in pos[:2]) + "。"
    if not neg and not pos: main += "各项都接近中性。"
    main = main.rstrip("；") if main.endswith("；") else main
    pts = []
    if sig:
        pts.append(f'<li><b>今天有 {len(sig)} 条会改变判断：</b>' + "；".join(E(c["text"]) for c in sig[:3]) + "。</li>")
    else:
        pts.append("<li><b>今天没有出现会改变判断的新信号</b>，分数和上一交易日一致。</li>")
    if neut:
        pts.append(f'<li>另有 {len(neut)} 条是月度数据公布，不改变分数：'
                   + "、".join(E(c["text"].split("：")[0]) for c in neut[:4]) + "。</li>")
    if newc:
        pts.append("<li><b>新触发关注条件：</b>" + "；".join(E(c["name"]) for c in newc) + "。</li>")
    else:
        pts.append("<li>关注条件今天没有新增触发。</li>")
    if neg:
        pts.append(f'<li>最该盯的是 <a href="#node-{neg[0]["node"]}">{E(neg[0]["name"])}</a>，它是当前最大的拖累。</li>')
    return (f'<div class="lead"><p class="lead-k">结论</p><p class="lead-main">{E(main)}</p>'
            f'<ul class="lead-points">{"".join(pts)}</ul></div>')


def summary():
    rows = R["score_rows"]
    neg = [r["name"] for r in sorted(rows, key=lambda r: r["score"]) if r["score"] < 0]
    pos = [r["name"] for r in sorted(rows, key=lambda r: -r["score"]) if r["score"] > 0]
    n_auto = sum(1 for r in rows if not r.get("manual"))
    n_scored = n_auto + sum(1 for m in (manual["external"], manual["policy"]) if m.get("evidence_verified"))
    s = f"{n_scored} 项已计分，合计 {R['total']:+d} 分（满分 ±{2 * n_scored}）。"
    if neg: s += "拖累来自" + "、".join(neg) + "；"
    if pos: s += "支撑来自" + "、".join(pos) + "。"
    return s.rstrip("；") + ("" if s.endswith("。") else "。")


# ---------- 半年板块推断（判断在 data/outlook.json，数字实时填入） ----------
import re as _re
OUTLOOK = json.load(open(os.path.join(ROOT, "data", "outlook.json"), encoding="utf-8"))
_SCREEN_P = os.path.join(RAW, "screen", "result.json")
SCREEN = {r["bk"]: r for r in json.load(open(_SCREEN_P, encoding="utf-8"))} if os.path.exists(_SCREEN_P) else {}


def _live():
    liq, val, fu = dims["liq"], dims["val"], dims["funds"]
    yr = TODAY[:4]
    ppi_m = {x["period"][:8]: x["v"] for x in D.ppi}
    vix = D.glob.get("vix", []); hy = D.glob.get("us_hy_oas", [])
    cyb = idx_stats(D.idx["idx_cyb"]["rows"])
    cpi = D.cpi[-1]["v"]; lpr1 = D.lpr1[-1][1]
    lev = dims["funds"].get("lev_pct")
    g = lambda x, f: "—" if x is None else format(x, f)
    return {
        "ppi": f"{D.ppi[-1]['v']:g}", "cpi": f"{cpi:g}", "split": f"{R['earn']['split']:+.1f}",
        "ppi_m3": g(ppi_m.get(f"{yr}年03月"), "+.1f"), "ppi_m4": g(ppi_m.get(f"{yr}年04月"), "+.1f"),
        "cn10": f"{D.cn10[-1][1]:.2f}", "cn10_20": f"{liq['c20']:+.0f}", "erp_pct": f"{val['epct']:.0f}",
        "lpr1": f"{lpr1:g}", "lpr5": f"{D.lpr5[-1][1]:g}", "lpr_real": f"{lpr1 - cpi:+.1f}",
        "m1": f"{D.m1[-1]['v']:g}", "m1_drop": f"{D.m1[-6]['v'] - D.m1[-1]['v']:.1f}", "sky": f"{liq['sky']:+.1f}",
        "vix": g(vix[-1][1] if vix else None, ".1f"),
        "vix_20": g((vix[-1][1] / vix[-21][1] - 1) * 100 if len(vix) > 21 else None, "+.0f"),
        "hy_20": g((hy[-1][1] - hy[-21][1]) * 100 if len(hy) > 21 else None, "+.0f"),
        "us10": f"{D.us10[-1][1]:.2f}", "us10_peak": f"{max(v for _, v in D.us10[-60:]):.2f}",
        "cyb_ytd": f"{cyb['ytd']:+.1f}", "exports": f"{D.exports[-1]['v']:g}",
        "exp6": f"{sum(x['v'] for x in D.exports[-6:]) / 6:.1f}", "cnh": f"{D.cnh[-1][1]:.2f}",
        "m20": f"{fu['m20']:+.1f}", "m5": f"{fu['m5']:+.1f}", "pmi": f"{D.pmi[-1]['v']:g}",
        "retail": f"{D.retail[-1]['v']:g}", "e60": f"{R['earn']['e60']:+.1f}",
        "pe_all": f"{D.pe_all[-1][1]:.1f}", "hs300_ytd": f"{idx_stats(D.idx['idx_hs300']['rows'])['ytd']:+.1f}", "pe_pct": f"{val['pct']:.0f}", "lev_pct": g(lev, ".0f"),
    }


LIVE = _live()


def ofill(s):
    """把 outlook.json 里的 {key} 换成当日数据；未知 key 原样保留，方便发现。"""
    return _re.sub(r"\{(\w+)\}", lambda m: LIVE.get(m.group(1), m.group(0)), s or "")


def sector_stat(bk):
    r = SCREEN.get(bk)
    if not r:
        return ""
    np_ = "亏损/不可比" if r["np_yoy"] is None else f"{r['np_yoy']:+.0f}%"
    pe = "—" if r["pe"] is None else f"{r['pe']:.0f} 倍"
    return f"{r['name']}：三季度单季利润同比 {np_} · PE {pe} · 拥挤度 {r['sh_pct']:.0f}% 分位 · 60 日相对沪深 300 {r['rs60']:+.0f} 点"


# bk → 分档，供板块页使用
OUTLOOK_MAP = {}
for _t in OUTLOOK["tiers"]:
    for _it in _t["items"]:
        for _bk in ([_it["bk"]] if _it.get("bk") else _it.get("bks", [])):
            OUTLOOK_MAP[_bk] = {"tier": _t["name"], "cls": _t["cls"], "item": _it}


def outlook_card(it, prefix=""):
    bks = [it["bk"]] if it.get("bk") else it.get("bks", [])
    name = E(it["name"])
    if it.get("tracked") and it.get("bk"):
        name = f'<a href="{prefix}boards/{it["bk"]}.html">{name}</a>'
    flag = "" if it.get("tracked") else '<span class="ol-new">未追踪</span>'
    hz = f'<span class="ol-hz">{E(it["horizon"])}</span>' if it.get("horizon") and it["horizon"] != "—" else ""
    stats = "".join(f'<p class="ol-stat">{E(sector_stat(b))}</p>' for b in bks if sector_stat(b))
    line = lambda lab, txt: f'<p class="ol-p"><span class="ol-lab">{lab}</span>{E(ofill(txt))}</p>' if txt else ""
    return (f'<article class="ol-card"><div class="ol-ch"><b>{name}</b>{hz}{flag}</div>{stats}'
            + line("依据", it["why"]) + line("风险", it.get("risk")) + line("证伪 / 触发", it.get("falsify")) + "</article>")


def outlook_section():
    import framework_review
    return framework_review.render(globals(), 'a')


# ---------- 页面骨架 ----------
CSS = open(os.path.join(ROOT, "pipeline", "style.css"), encoding="utf-8").read()


def page(title, active, body, prefix=""):
    if active == "gg":
        body = '<p class="hk-notice">历史个股资料：当前先按A–H判断半年并选择板块，尚未确定个股或仓位。旧名单不是当前方案。</p>' + body
    nav = [("index.html", "大盘", "dp"), ("boards/index.html", "板块", "bk"), ("stocks/index.html", "个股", "gg"),
           ("reports/index.html", "报告", "bg"), ("trades.html", "我的操作", "tr")]
    links = ""
    for href, lab, key in nav:
        if not href:
            links += f'<span class="soon">{lab}<small>{key}</small></span>'
        else:
            cur = ' aria-current="page"' if key == active or (key == 'dp' and active == 'hk') else ""
            links += f'<a href="{prefix}{href}"{cur}>{lab}</a>'
    switch = ''
    if active in ('dp', 'hk'):
        switch = ('<nav class="market-switch" aria-label="大盘市场">'
                  f'<a href="{prefix}index.html"' + (' aria-current="page"' if active == 'dp' else '') + '>A 股</a>'
                  f'<a href="{prefix}hk/index.html"' + (' aria-current="page"' if active == 'hk' else '') + '>港股</a></nav>')
    sources = ('行情来自东方财富，估值来自恒生指数公司，利率与宏观数据来自金管局、FRED及统计机关，市场及参与者资料来自港交所、证监会和基金／公司官网。规则 HK v3，日期、口径与原始链接见各节。'
               if active == 'hk' else f"数据来自东方财富、中证指数公司的公开数据，外部环境和政策为人工整理。判定规则版本 {R['rules_version']}，每节的“怎么判的”里有完整规则。")
    if active == "bk":
        sources = "当前板块研究依据公司财报、交易所披露及宏观行业资料；每条证据保留报告期和原始链接。旧宽行业页面仅为历史统计资料。"
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(title)}</title><style>{CSS}</style></head><body>
<header class="top"><div class="wrap"><a class="brand" href="{prefix}index.html">A 股框架笔记</a><nav aria-label="主导航">{links}</nav></div></header>
<main class="wrap">{switch}{body}</main>
<footer><div class="wrap"><p>{sources}</p>
<p>本站只呈现框架下各项信号的状态和理由，是个人学习用的辅助判断工具，不构成投资建议。</p></div></footer></body></html>"""


def index():
    st = D.status
    mdate = D.mbal[-1][0]; pdate = D.pe_all[-1][0]
    stamp = (f"行情截至 {cn_date(TODAY)}收盘；两融截至 {cn_date(mdate)}；估值截至 {cn_date(pdate)}。"
             f"页面生成于 {st.get('_fetched_at', '')}。")
    nodes_html = ""
    for k in "ABCDEFGH":
        s = sec[k]
        state = N[k]["state"]
        nodes_html += (f'<section class="nd" id="node-{k}"><div class="ndh"><span class="lc2 {state}">{k}</span>'
                       f'<div><h3>{E(s["title"])}</h3><p class="q">{E(s["q"])}</p></div></div>{s["body"]}</section>')
    chips = "".join(f'<a href="#node-{k}" class="chip {N[k]["state"]}"><b>{k}</b>{E(NODE_NAME[k])}<span>{E(node_sub(k))}</span></a>' for k in "ABCDEFGH")
    body = f"""
<div class="hero"><p class="date">{cn_date(TODAY, True)}</p><h1>大盘今天处在什么状态</h1>
<p class="sum">{E(summary())}</p><p class="stamp">{E(stamp)}</p></div>

<nav class="l1nav"><a href="#horizon">六个月的判断</a><a href="#today">今日分析</a><a href="#conds">大盘关注条件</a></nav>

<details class="l1" id="horizon" open><summary><h2>六个月的判断</h2><span class="l1hint">传导图 · 结论 · 板块分档</span></summary>
{outlook_section()}</details>

<details class="l1" id="today" open><summary><h2>今日分析</h2><span class="l1hint">传导图 · 结论 · 展开分析（{cn_date(TODAY)}）</span></summary>
<h3 class="h3s" id="map">今日传导图</h3><p class="sub">红色利好，绿色利空，灰色中性。点任意一环跳到下面的展开分析。</p>
<div class="fwbox">{diagram()}</div><div class="chips">{chips}</div>
<h3 class="h3s">结论：今天变了什么</h3>{today_lead()}
<details class="sub2"><summary>和上一交易日（{cn_date(R['prev'])}）相比的逐条明细</summary>{changes()}</details>
<h3 class="h3s" id="score">展开分析</h3><p class="sub">信号观察卡沿用独立日度规则，只作变化提醒；人工综合方向未量化时不计分，不能据总分选择半年板块。</p>{scorecard()}
<details class="sub2" id="nodes"><summary>A–H 逐项展开（看什么指标、现在多少、怎么判的）</summary>{nodes_html}</details>
</details>

<details class="l1" id="conds"><summary><h2>大盘关注条件</h2><span class="l1hint">触发只是提醒你去看一眼，不是买卖信号</span></summary>
{conds_html()}</details>

<script>
/* 点站内锚点时自动展开所在的折叠块；没有 JS 时折叠块仍可手动展开 */
function openTo(id){{var el=document.getElementById(id);for(;el;el=el.parentElement)if(el.tagName==="DETAILS")el.open=true;}}
document.addEventListener("click",function(e){{var a=e.target.closest&&e.target.closest('a[href^="#"]');if(a)openTo(a.getAttribute("href").slice(1));}});
if(location.hash)openTo(location.hash.slice(1));
</script>
"""
    return page("大盘 | A 股框架笔记", "dp", body)


def trades_page():
    if not trades:
        lst = ('<div class="empty"><h3>还没有记录</h3><p>在和 Claude 的对话里说一句就行，例如：</p>'
               '<blockquote>今天 450 元买入中际旭创，仓位加到 20%。理由：估值到了近 3 年 20% 分位，融资余额止跌。计划：跌破 400 元离场。</blockquote>'
               '<p>Claude 会整理成一条记录，自动附上当天大盘、板块、个股、股价四层的信号快照，并在 1、3、6 个月后补上回看。</p></div>')
    else:
        rows = ""
        for t in sorted(trades, key=lambda t: t["date"], reverse=True):
            rows += (f'<tr><td>{E(t["date"])}</td><td>{E(t["stock"])}</td><td class="{"up" if t["side"] == "买入" else "down"}">{E(t["side"])}</td>'
                     f'<td>{E(str(t["price"]))}</td><td>{E(str(t.get("position", "")))}</td><td>{E(t.get("reason", ""))}</td>'
                     f'<td>{E(t.get("plan", ""))}</td><td>{E(t.get("snapshot_text", ""))}</td><td>{E(t.get("review", "待回看"))}</td></tr>')
        lst = ('<div class="tblwrap"><table class="mt"><thead><tr><th>日期</th><th>股票</th><th>方向</th><th>价格</th><th>仓位</th>'
               '<th>理由</th><th>计划</th><th>当时四层信号</th><th>事后回看</th></tr></thead><tbody>' + rows + "</tbody></table></div>")
    body = f"""<div class="hero"><h1>我的操作</h1><p class="sum">每一笔买卖都记下当时看到了什么，6 个月后回头检验判断，找出问题出在哪一层。</p>
<p class="stamp">仓位只记占总资金的比例。本页公开可见。</p></div>
<section class="block">{lst}</section>
<section class="block"><h2>每条记录包含什么</h2><div class="tblwrap"><table class="mt"><thead><tr><th>字段</th><th>谁来填</th><th>说明</th></tr></thead><tbody>
<tr><th scope="row">日期、股票、方向、价格</th><td>你</td><td></td></tr>
<tr><th scope="row">仓位</th><td>你</td><td>占总资金的比例</td></tr>
<tr><th scope="row">理由</th><td>你</td><td>看到了什么，为什么是现在</td></tr>
<tr><th scope="row">计划（可选）</th><td>你</td><td>什么情况下加仓、减仓或离场；会加入这只股票的关注条件</td></tr>
<tr><th scope="row">当时四层信号</th><td>自动</td><td>记录当天大盘、板块、个股、股价的状态</td></tr>
<tr><th scope="row">事后回看</th><td>自动</td><td>1、3、6 个月后的涨跌，对比沪深 300 和所属板块</td></tr>
</tbody></table></div></section>"""
    return page("我的操作 | A 股框架笔记", "tr", body)


with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
    f.write(index())
with open(os.path.join(SITE, "trades.html"), "w", encoding="utf-8") as f:
    f.write(trades_page())

import hkpage
hkpage.build(globals())

import stockpage, reportspage, boardpage, sectorpage  # noqa: E402
BOARDS = boardpage.build(globals(), json.load(open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))["stocks"])
stock_analyses = stockpage.build(globals())
reportspage.build(globals())
sectorpage.build(globals())

snap = {"date": TODAY, "total": R["total"], "scores": {r["key"]: r["score"] for r in R["score_rows"]},
        "nodes": {k: v["state"] for k, v in N.items()}, "conds": {c["id"]: c["hit"] for c in R["conds"]},
        "changes": R["changes"], "rules_version": R["rules_version"]}
with open(os.path.join(SNAP, TODAY + "_v2.json"), "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False, indent=1)
print("built", TODAY, "total", R["total"])
