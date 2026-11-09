"""把项目推送到 GitHub（GitHub Pages 从 main 分支的 docs/ 发布）。
在临时目录里做 git 操作，避免在你的文件夹里产生 .git。
用法：python3 -I pipeline/publish.py <项目根目录> [提交说明]
"""
import os, sys, shutil, subprocess, tempfile, datetime, json, urllib.request

OWNER, REPO = "destinysevenliu-del", "ashare-notes"
ROOT = sys.argv[1]
MSG = sys.argv[2] if len(sys.argv) > 2 else "每日更新 " + datetime.date.today().isoformat()
TOKEN = open(os.path.join(ROOT, "github_token.txt")).read().strip()
SKIP = {"github_token.txt", "site", "__pycache__", ".DS_Store", ".git"}
URL = f"https://x-access-token:{TOKEN}@github.com/{OWNER}/{REPO}.git"


def run(*a, cwd=None):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit((r.stdout + r.stderr).replace(TOKEN, "***"))
    return r.stdout


work = tempfile.mkdtemp()
repo = os.path.join(work, "repo")
try:
    run("git", "clone", "-q", URL, repo)
except SystemExit:
    os.makedirs(repo); run("git", "init", "-q", "-b", "main", cwd=repo)
    run("git", "remote", "add", "origin", URL, cwd=repo)
# 用项目文件夹的内容整体替换仓库内容
for name in os.listdir(repo):
    if name != ".git":
        p = os.path.join(repo, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
ign = shutil.ignore_patterns(*SKIP, "*.pyc")
for name in os.listdir(ROOT):
    if name in SKIP:
        continue
    s, d = os.path.join(ROOT, name), os.path.join(repo, name)
    shutil.copytree(s, d, ignore=ign) if os.path.isdir(s) else shutil.copy2(s, d)
run("git", "-c", "user.name=claude-daily", "-c", f"user.email={OWNER}@users.noreply.github.com", "add", "-A", cwd=repo)
if run("git", "status", "--porcelain", cwd=repo).strip():
    run("git", "-c", "user.name=claude-daily", "-c", f"user.email={OWNER}@users.noreply.github.com",
        "commit", "-q", "-m", MSG, cwd=repo)
    run("git", "push", "-q", "origin", "HEAD:main", cwd=repo)
    print("pushed:", MSG)
else:
    print("no changes")

# 确保 GitHub Pages 已开启（main 分支 /docs）
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
api = f"https://api.github.com/repos/{OWNER}/{REPO}/pages"
try:
    urllib.request.urlopen(urllib.request.Request(api, headers=H), timeout=20)
except urllib.error.HTTPError as e:
    if e.code == 404:
        body = json.dumps({"source": {"branch": "main", "path": "/docs"}}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(api, data=body, headers=H, method="POST"), timeout=20)
            print("pages enabled")
        except urllib.error.HTTPError:
            print("PAGES_NOT_ENABLED: 请在仓库 Settings → Pages 里选 main 分支 /docs 并保存")
    else:
        print("pages check skipped:", e.code)
shutil.rmtree(work, ignore_errors=True)
print(f"https://{OWNER}.github.io/{REPO}/")
