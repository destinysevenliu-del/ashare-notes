# -*- coding: utf-8 -*-
"""用 GitHub Git Data API 发布（github.com 的 git 通道不可达时的替代方案）。
用法：python3 publish_api.py <项目根目录> <提交说明> [--dry]
"""
import base64, hashlib, json, os, sys, time, urllib.request, urllib.error

ROOT, MSG = sys.argv[1], sys.argv[2]
DRY = "--dry" in sys.argv
OWNER, REPO = "destinysevenliu-del", "ashare-notes"
TOKEN = open(os.path.join(ROOT, "github_token.txt")).read().strip()
SKIP = {"github_token.txt", "site", "__pycache__", ".DS_Store", ".git"}
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
     "Content-Type": "application/json", "User-Agent": "ashare-notes-publisher"}


def call(method, url, body=None, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                         headers=H, method=method)
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            if e.code in (401, 403, 404):
                raise SystemExit(f"{method} {url} -> {e.code} {detail}")
            last = f"{e.code} {detail}"
        except Exception as e:
            last = str(e)[:200]
        time.sleep(1.5 * (i + 1))
    raise SystemExit(f"{method} {url} failed: {last}")


def blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# 1) 远端当前 tree
ref = call("GET", f"{API}/git/ref/heads/main")
head = ref["object"]["sha"]
tree = call("GET", f"{API}/git/trees/{head}?recursive=1")
remote = {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}

# 2) 本地文件
local, blobs = {}, {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP]
    for fn in filenames:
        if fn in SKIP or fn.endswith(".pyc"):
            continue
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        data = open(p, "rb").read()
        sha = blob_sha(data)
        local[rel] = sha
        blobs[rel] = data

added = [p for p in local if p not in remote]
modified = [p for p in local if p in remote and remote[p] != local[p]]
deleted = [p for p in remote if p not in local]
print(f"head {head[:8]} | 远端 {len(remote)} 文件 | 新增 {len(added)} 修改 {len(modified)} 删除 {len(deleted)}")
for p in sorted(deleted)[:20]:
    print("  删除", p)
if DRY:
    print("DRY RUN，不写入")
    raise SystemExit(0)

# 3) 上传 blob（只传变更）
entries = []
from concurrent.futures import ThreadPoolExecutor
def _up(p):
    r = call("POST", f"{API}/git/blobs", {"content": base64.b64encode(blobs[p]).decode(), "encoding": "base64"})
    return {"path": p, "mode": "100644", "type": "blob", "sha": r["sha"]}
with ThreadPoolExecutor(12) as ex:
    entries.extend(ex.map(_up, added + modified))
for p in deleted:
    entries.append({"path": p, "mode": "100644", "type": "blob", "sha": None})
print(f"blobs 上传完成 {len(added) + len(modified)} 个")
if not entries:
    print("no changes")
    raise SystemExit(0)

# 4) tree → commit → ref
new_tree = call("POST", f"{API}/git/trees", {"base_tree": tree["sha"], "tree": entries})
commit = call("POST", f"{API}/git/commits", {"message": MSG, "tree": new_tree["sha"], "parents": [head]})
call("PATCH", f"{API}/git/refs/heads/main", {"sha": commit["sha"], "force": False})
print("pushed:", commit["sha"][:8], MSG)
