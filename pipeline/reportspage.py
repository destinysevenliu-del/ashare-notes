"""报告归档页：把「旧报告/」文件夹里的 HTML 复盘报告原样发布到 docs/reports/，并生成目录页。
以后有新报告，直接放进「旧报告/」再运行 build.py 即可。
"""
import os, re, shutil, html, urllib.parse

E = html.escape
MISSING = [
    ("A 股 2024–2026 分阶段复盘", "8 节点传导图逐阶段上色，10 个阶段，从 9·24 到 2026-11 的“政策底？”", "2026-11-07"),
    ("港股 2024–2026 分阶段复盘", "恒指、恒生科技、国企指数 10 个阶段，每阶段对照 A 股同期", "2026-11-07"),
    ("A 股下钻：光模块（阶段 8–9）", "中际旭创、新易盛、寒武纪；市值 = 利润 × PE 拆解；7 步下钻清单", "2026-11-08"),
    ("方法论验证：恒瑞医药、比亚迪", "估值杀、叙事降温、业绩杀三种类型；下钻清单升级为 9 步", "2026-11-09"),
]


def meta(path):
    s = open(path, encoding="utf-8").read()
    strip = lambda x: re.sub(r"\s+", " ", re.sub("<[^>]+>", "", x)).strip()
    t = re.search(r"<title>([^<]*)", s)
    h = re.findall(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    p = re.findall(r"<p[^>]*>(.*?)</p>", s, re.S)
    return (strip(t.group(1)) if t else os.path.basename(path)), (strip(h[0]) if h else ""), (strip(p[0])[:120] if p else "")


def build(ctx):
    root, site, page = ctx["ROOT"], ctx["SITE"], ctx["page"]
    src = os.path.join(root, "旧报告")
    out = os.path.join(site, "reports")
    os.makedirs(out, exist_ok=True)
    items = []
    if os.path.isdir(src):
        for fn in sorted(os.listdir(src)):
            if fn.lower().endswith(".html"):
                shutil.copy2(os.path.join(src, fn), os.path.join(out, fn))
                title, h1, p = meta(os.path.join(src, fn))
                items.append((fn, title, h1, p))
    lis = "".join(f'<a class="rp" href="{urllib.parse.quote(fn)}"><b>{E(title)}</b><span class="rh">{E(h1)}</span><span class="rd">{E(p)}</span></a>'
                  for fn, title, h1, p in items)
    miss = "".join(f'<li><b>{E(t)}</b><span class="evd">{d}</span><p>{E(x)}</p></li>' for t, x, d in MISSING)
    body = f"""<div class="hero"><h1>报告</h1><p class="sum">之前做过的复盘和验证报告，原样保存在这里，方便回头对照框架。</p></div>
<section class="block"><h2>已收录</h2><div class="rplist">{lis}</div></section>
<section class="block"><h2>待补</h2><p class="sub">这几份是在之前的对话里生成的，文件留在那次对话的工作区里，网站这边读不到。
把它们保存到电脑的“文稿 → A股网站 → 旧报告”文件夹，下次更新时会自动收录。</p><ul class="ev">{miss}</ul></section>"""
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page("报告 | A 股框架笔记", "bg", body, "../"))
