"""捕获：源落 00-Inbox，生成 id+hash（不可变 raw）。

源记录一旦写入永不删（00-Inbox 是永久溯源层）。多了按 归档/YYYY-MM/ 滚动。
用法：
  python3 capture.py --type url --origin "https://..." --file 粘贴.txt
  echo "正文" | python3 capture.py --type paste
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", default="paste",
                    choices=["url", "pdf", "paste", "conversation", "gbrain"])
    ap.add_argument("--origin", default="")
    ap.add_argument("--file")
    a = ap.parse_args()
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    capture(a.type, a.origin, text)
