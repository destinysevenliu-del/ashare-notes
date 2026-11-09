"""通用打分卡：大盘页已有自己的版本，这里给板块页、个股页用。
每次 build 把当天各板块、个股的分数写进 data/snapshots/scores.json，用来画走势。
"""
import json, os, html

E = html.escape


def _scale(s):
    cells = []
    for v in (-2, -1, 0, 1, 2):
        c = "mid" if v == 0 else ""
        if s is not None and s < 0 and s <= v < 0: c = "d"
        if s is not None and s > 0 and 0 < v <= s: c = "u"
        cells.append(f'<span class="{c}"></span>')
    return '<div class="scale">' + "".join(cells) + "</div>"


def record(root, kind, key, date, scores):
    p = os.path.join(root, "data", "snapshots", "scores.json")
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    d.setdefault(kind, {}).setdefault(key, {})[date] = scores
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return sorted(d[kind][key].items())  # [(date, scores)]


def _trend(hist, keys):
    pts = [(dt, sum(v for k, v in sc.items() if k in keys and v is not None)) for dt, sc in hist][-30:]
    if len(pts) < 2:
        return f'<p>打分从 {pts[-1][0][5:].replace("-", "/")} 开始记录，之后每次更新都会在这里画出合计分的走势。</p>'
    w, h = 300, 64
    bw = w / len(pts)
    mx = max(4, max(abs(v) for _, v in pts))
    bars = ""
    for i, (_, v) in enumerate(pts):
        hh = abs(v) * (h / 2 - 4) / mx
        y = h / 2 - hh if v > 0 else h / 2
        bars += f'<rect x="{i * bw + 1:.1f}" y="{y:.1f}" width="{bw - 2:.1f}" height="{max(hh, 1):.1f}" class="{"u" if v > 0 else "d" if v < 0 else "z"}"/>'
    return (f'<p>近 {len(pts)} 次更新的合计分（{pts[0][0][5:]}–{pts[-1][0][5:]}，从 {pts[0][1]:+d} 到 {pts[-1][1]:+d}）。</p>'
            f'<svg viewBox="0 0 {w} {h}" class="trend">{bars}<line x1="0" x2="{w}" y1="{h / 2}" y2="{h / 2}" stroke="#7C8696" stroke-width=".6"/></svg>')


def card(rows, total_label, note, hist):
    """rows: [{"key","name","score"(None=暂缺),"hits":[(text,pt)],"manual":bool,"href"}]"""
    cells = ""
    for r in rows:
        s = r["score"]
        c = "flat" if not s else ("up" if s > 0 else "down")
        if s is None:
            txt, val = "暂缺：没有可用数据，不参与合计", "—"
        else:
            txt = "；".join(E(h[0]) for h in r["hits"][:2]) or "没有触发加减分"
            val = f"{s:+d}" if s else "0"
        lab = '<span class="man">人工</span>' if r.get("manual") else ""
        cells += (f'<a class="sc" href="{r["href"]}"><div class="lbl"><span class="sk">{r["key"]}</span>{E(r["name"])}{lab}'
                  f'<span class="v {c}">{val}</span></div>{_scale(s)}<p>{txt}</p></a>')
    valid = [r for r in rows if r["score"] is not None]
    t = sum(r["score"] for r in valid)
    n = len(rows)
    span = 3 - n % 3 if n % 3 else 3
    return (f'<div class="score">{cells}<div class="sc total" style="grid-column:span {span}"><div class="lbl">{E(total_label)}'
            f'<span class="v">{(f"{t:+d}" if t else "0")}</span></div><p>满分 ±{2 * len(valid)}（{len(valid)} 项有数据）。{E(note)}</p>'
            f'{_trend(hist, {r["key"] for r in rows})}</div></div>')
