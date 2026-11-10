"""半年名单页 /picks/：半年记分卡 + 持有卡 + 变更记录。
数据全部来自 data/halfyear.json（决策记录，季报后重算），日度信号仍看大盘/板块/个股页。
由 build.py 调用：picks.build(ctx)。
"""
import json, os, html

E = html.escape

GROUPS = [("resource", "上游资源", "#8A5A2B"), ("export", "外需", "#27408B"),
          ("pharma", "医药", "#15804E"), ("tech", "科技", "#6B3FA0"), ("cash", "现金", "#B0B6C0")]
BOARD_GROUP = {"工业金属": "resource", "煤炭开采": "resource", "化学原料": "resource", "化学纤维": "resource",
               "航运港口": "export", "化学制药": "pharma", "医疗服务": "pharma",
               "半导体": "tech", "计算机设备": "tech"}
TIER_NAME = {"A": "A 低波", "B": "B 中波", "C": "C 高波"}


def f(x, n=0, suffix=""):
    if x is None:
        return "—"
    return f"{x:,.{n}f}{suffix}"


def sg(x, suffix="%"):
    if x is None:
        return "—"
    return f"{x:+,.0f}{suffix}"


def structure_svg(h):
    w, hh = 920, 40
    pf, stocks = h["portfolio"], h["stocks"]
    tot = {g: 0 for g, _, _ in GROUPS}
    for s in stocks:
        tot[BOARD_GROUP[s["board"]]] += s["weight"]
    tot["cash"] = pf["cash"]
    x, out = 0.0, []
    scale = w / 100.0
    for key, label, color in GROUPS:
        v = tot[key]
        if not v:
            continue
        bw = v * scale
        out.append(f'<rect x="{x:.1f}" y="0" width="{max(bw - 2, 1):.1f}" height="{hh}" rx="3" fill="{color}"/>')
        if bw > 52:
            out.append(f'<text x="{x + bw / 2 - 1:.1f}" y="{hh / 2 + 5}" text-anchor="middle" class="pkb">{v}%</text>')
        out.append(f'<text x="{x + bw / 2 - 1:.1f}" y="{hh + 17}" text-anchor="middle" class="pkbl">{E(label)}</text>')
        x += bw
    legend = "".join(f'<span class="pkleg"><i style="background:{c}"></i>{E(l)} {tot[k]}%</span>' for k, l, c in GROUPS)
    return f'<svg viewBox="0 0 {w} {hh + 26}" class="pkbar" role="img" aria-label="组合结构">{"".join(out)}</svg><p class="pklegend">{legend}</p>'


def board_table(h):
    rows = ""
    for b in h["boards"]:
        act = b["action"]
        cls = "tag flat" if act == "保留" else "tag up"
        pe_cls = "down" if b["pe"] and b["pe"] > 35 else "flat"
        rows += (f'<tr><td><a href="../boards/{E(b["slug"])}.html">{E(b["name"])}</a></td>'
                 f'<td><span class="{cls}">{E(act)}</span></td><td>{E(b["style"])}</td>'
                 f'<td class="num">{sg(b["np_q"])}</td><td class="num">{f(b["pe"], 1)}</td>'
                 f'<td class="num {pe_cls}">{sg(b["rs60"])}</td><td class="num">{b["crowd"]}%</td>'
                 f'<td class="num">{sg(b["dd"])}</td><td class="pkjudge">{E(b["judge"])}</td></tr>')
    return ('<div class="tblwrap"><table class="mt pk"><thead><tr><th>板块</th><th>动作</th><th>风格</th>'
            '<th>单季利润</th><th>板块 PE</th><th>RS60</th><th>拥挤度</th><th>距一年高</th><th>判断</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def stock_card(s, h):
    g = BOARD_GROUP[s["board"]]
    label = dict((k, l) for k, l, _ in GROUPS)[g]
    fals = "".join(f"<li>{E(x)}</li>" for x in s["falsify"])
    div = f'<b>{s["div"]:.2f}%</b>' if s.get("div") else "<b>—</b>"
    note = f'<p class="pknote">{E(s["div_note"])}</p>' if s.get("div_note") else ""
    return f"""<article class="pkcard t{s['tier']}">
<div class="pkh"><a href="../stocks/{E(s['code'])}.html">{E(s['name'])}</a>
<span class="pkw">{s['weight']}%</span></div>
<p class="pkmeta">{E(s['board'])} · {E(role_text(s, label))} · {TIER_NAME[s['tier']]}</p>
<div class="pkmini"><span>PE <b>{f(s['pe'], 1)}</b></span><span>2027E <b>{f(s['fpe27'], 1)}</b></span>
<span>现金/利润 <b>{f(s['ocf'], 2)}</b></span><span>股息 {div}</span></div>
<p class="pkass"><span class="pklab">假设</span>{E(s['assumption'])}</p>
<p class="pklab pklab2">证伪条件</p><ul class="pkfals">{fals}</ul>{note}</article>"""


def role_text(s, label):
    return s.get("role", label)


def build(ctx):
    root = ctx["ROOT"]
    h = json.load(open(os.path.join(root, "data", "halfyear.json"), encoding="utf-8"))
    out = os.path.join(ctx["SITE"], "picks")
    os.makedirs(out, exist_ok=True)
    pf, stocks = h["portfolio"], h["stocks"]
    held = sum(s["weight"] for s in stocks)
    tiers = {t: [s for s in stocks if s["tier"] == t] for t in "ABC"}
    reviews = "、".join(r[5:].replace("-", "/") for r in h["window"]["reviews"])

    cards = ""
    for t in "ABC":
        cards += f'<h3 class="pkh3">{TIER_NAME[t]}<span>合计 {sum(s["weight"] for s in tiers[t])}%</span></h3><div class="pkgrid">'
        cards += "".join(stock_card(s, h) for s in tiers[t]) + "</div>"

    changes = "".join(f'<tr><td>{E(c["date"])}</td><td><span class="tag flat">{E(c["action"])}</span></td>'
                      f'<td>{E(c["target"])}</td><td class="pkjudge">{E(c["why"])}</td></tr>'
                      for c in h["changes"])
    rules = "".join(f"<li>{E(r)}</li>" for r in h["rules"])
    verify = "".join(f'<tr><td>{E(v["pri"])}</td><td>{E(v["item"])}</td><td>{E(v["impact"])}</td></tr>'
                     for v in h["verify"])

    body = f"""
<div class="hero"><p class="date">{E(h['window']['start'])} → {E(h['window']['end'])} · 半年名单</p>
<h1>这半年我打算拿什么，以及什么情况下认错</h1>
<p class="sum">20 只股票、9 个板块。上游涨价链做主力，科技压到 12%，医药和外需各做一块，现金留 {pf['cash']}%。</p>
<p class="stamp">数字为 {E(h['as_of'])} 收盘快照，每季报后重算；日度信号请看大盘、板块、个股三页。名单更新时间 {E(h['updated'])}。</p></div>

<section class="block" id="structure"><h2>组合结构</h2>
<p class="sub">总仓位 {held}%，现金 {pf['cash']}%。单只上限 {pf['max_single']}%，单板块上限 {pf['max_board']}%，C 档合计上限 {pf['tier_c_max']}%。</p>
{structure_svg(h)}</section>

<section class="block" id="boards"><h2>板块记分卡</h2>
<p class="sub">用三把尺子分别量：成长看 2027E PE 与增速，周期看商品价格位置，红利看股息率减国债利差。“拥挤度”是成交额占全市场的分位，越高越容易被踩踏。</p>
{board_table(h)}</section>

<section class="block" id="holdings"><h2>20 张持有卡</h2>
<p class="sub">按波动分三档：A 低波（股息率 >3.5%、回撤 &lt;15%）、B 中波（现金流 >1.0）、C 高波（估值最低或成长最快，但趋势已破坏）。每张卡都必须写得出“什么情况下我认错”。</p>
{cards}</section>

<section class="block" id="changes"><h2>变更记录</h2>
<p class="sub">每次换进换出都留痕。6 个月后回看，先看这些判断对不对，而不是看赚了多少。</p>
<div class="tblwrap"><table class="mt pk"><thead><tr><th>日期</th><th>动作</th><th>对象</th><th>原因</th></tr></thead><tbody>{changes}</tbody></table></div></section>

<section class="block" id="rules"><h2>组合级风控</h2>
<p class="sub">这些是硬规则，触发就执行，不在盘中重新讨论。</p>
<ol class="pkrules">{rules}</ol>
<p class="note">下次复核：{E(reviews)}。任一证伪条件触发，当天移出名单并记进“变更记录”。</p></section>

<section class="block" id="todo"><h2>还没核验完的</h2>
<p class="sub">没查到就写没查到，不填数。</p>
<div class="tblwrap"><table class="mt pk"><thead><tr><th>优先级</th><th>事项</th><th>影响</th></tr></thead><tbody>{verify}</tbody></table></div></section>

<section class="block"><h2>怎么读这一页</h2>
<p class="note">这一页是<b>决策记录</b>，不是行情页。它回答的是“我为什么买、什么情况下我错了”，所以数字固定在 {E(h['as_of'])}，只在季报后重算。
想看今天发生了什么，回<a href="../index.html">大盘页</a>、<a href="../boards/index.html">板块页</a>或<a href="../stocks/index.html">个股页</a>。
页面只呈现假设与条件，不构成投资建议；仓位是风险预算上限，不是推荐买入。</p></section>
"""
    html_ = ctx["page"]("半年名单 | A 股框架笔记", "pk", body, "../")
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html_)
    return {"count": len(stocks), "held": held}
