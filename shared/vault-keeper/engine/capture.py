"""捕获：源落 00-Inbox，生成 id+hash（不可变 raw）。

源记录一旦写入永不删（00-Inbox 是永久溯源层）。多了按 归档/YYYY-MM/ 滚动。
用法：
  python3 capture.py --type url --origin "https://..." --file 粘贴.txt
  echo "正文" | python3 capture.py --type paste
  python3 capture.py --backfill [--dry]   # 给 00-Inbox 旧笔记原地补溯源锚
"""
import os
import sys
import glob
import argparse
import datetime

import common


def next_id(date):
    n = len(glob.glob(common.vault_path(common.INBOX, f"SRC-{date}-*.md"))) + 1
    return f"SRC-{date}-{n:03d}"


def capture(stype, origin, content):
    date = datetime.date.today().strftime("%Y%m%d")
    sid = next_id(date)
    fm = {
        "id": sid,
        "type": stype,
        "origin": origin,
        "hash": common.sha12(content),
        "captured": datetime.date.today().isoformat(),
        "lifecycle_state": "raw",
    }
    path = common.vault_path(common.INBOX, f"{sid}.md")
    common.dump(path, fm, f"\n{content}\n")
    print("captured →", path)
    return sid, path


def backfill(dry=False):
    """给 00-Inbox 现存旧笔记原地补溯源锚（id/hash/captured/lifecycle_state: raw）。
    不改文件名（避免断链）、不覆盖已有字段、幂等（已有 id+hash 跳过）。"""
    today = datetime.date.today().strftime("%Y%m%d")
    seq = len(glob.glob(common.vault_path(common.INBOX, f"SRC-{today}-*.md")))
    done = []
    for p in sorted(glob.glob(common.vault_path(common.INBOX, "*.md"))):
        name = os.path.basename(p)
        if name.startswith("SRC-"):                  # 已是 SRC 命名记录
            continue
        fm, body = common.load(p)
        if fm.get("id") and fm.get("hash"):          # 已有溯源锚，幂等跳过
            continue
        if not body.strip():                          # 空文件跳过
            continue
        seq += 1
        fm.setdefault("id", f"SRC-{today}-{seq:03d}")
        fm["hash"] = common.sha12(body)
        fm.setdefault("captured", str(fm.get("created", ""))[:10] or datetime.date.today().isoformat())
        fm["lifecycle_state"] = "raw"
        fm.setdefault("origin", f"{common.INBOX}/{name}")
        if not dry:
            common.dump(p, fm, body)
        done.append((fm["id"], name))
    print(f"{'[dry] 将' if dry else '已'}backfill {len(done)} 个源（补 id+hash+raw，原地不改名）")
    for sid, name in done:
        print(f"  {sid}  ←  {name}")
    return len(done)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true",
                    help="给 00-Inbox 旧笔记原地补溯源锚（id/hash/raw）")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--type", default="paste",
                    choices=["url", "pdf", "paste", "conversation", "gbrain"])
    ap.add_argument("--origin", default="")
    ap.add_argument("--file")
    a = ap.parse_args()
    if a.backfill:
        backfill(a.dry)
    else:
        text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
        capture(a.type, a.origin, text)
