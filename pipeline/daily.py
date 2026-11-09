"""每日运行入口：抓数据 → 判断两融是否已更新 → 生成页面 → 推送。
用法：python3 -I pipeline/daily.py <项目根目录> [--force]
退出说明（打印在最后一行）：
  SKIP_ALREADY_DONE   今天这批数据已经发布过
  WAIT_MARGIN         两融还没更新到最新交易日，且还没到 09:00，等下一次运行
  PUBLISHED ...       已发布
"""
import json, os, sys, subprocess, datetime

ROOT = sys.argv[1]
FORCE = "--force" in sys.argv
PY = sys.executable
now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)  # 北京时间
state_p = os.path.join(ROOT, "data", "last_publish.json")
last = json.load(open(state_p)) if os.path.exists(state_p) else {}


def run(script, *args):
    r = subprocess.run([PY, "-I", os.path.join(ROOT, "pipeline", script), ROOT, *args], capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-1500:])
    if r.returncode:
        raise SystemExit(f"FAILED {script}")


run("fetch.py")
run("stocks.py")
raw = os.path.join(ROOT, "data", "raw")
idx_date = json.load(open(os.path.join(raw, "idx_all.json")))["rows"][-1]["date"]
m_date = max(r["DIM_DATE"][:10] for r in json.load(open(os.path.join(raw, "margin.json"))))
margin_ok = m_date >= idx_date
print("latest trading day", idx_date, "margin", m_date, "status", json.load(open(os.path.join(raw, "_status.json"))))

if not FORCE and last.get("idx_date") == idx_date and (last.get("margin_date") == m_date or not margin_ok):
    print("SKIP_ALREADY_DONE"); sys.exit(0)
if not FORCE and not margin_ok and now.hour < 9:
    print("WAIT_MARGIN"); sys.exit(0)

run("build.py")
run("publish.py", f"每日更新：行情 {idx_date}，两融 {m_date}")
json.dump({"idx_date": idx_date, "margin_date": m_date, "at": now.strftime("%Y-%m-%d %H:%M")}, open(state_p, "w"))
print("PUBLISHED", idx_date, "margin", m_date, "(margin late)" if not margin_ok else "")
