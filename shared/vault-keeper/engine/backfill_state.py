"""冷启动：给现有 core 区笔记批量补 lifecycle_state: core（幂等）。

只处理 10/20/30/02 区已有 frontmatter 的页；已含 lifecycle_state 的跳过。
用法：python3 backfill_state.py [--dry]
"""
import re
import argparse

import common


def run(dry=False):
    n = 0
    for p in common.iter_pages():
        txt = open(p, encoding="utf-8").read()
        if "lifecycle_state:" in txt or not txt.startswith("---"):
            continue
        if not dry:
            txt = re.sub(r"^(---\n)", r"\1lifecycle_state: core\n", txt, count=1)
            open(p, "w", encoding="utf-8").write(txt)
        n += 1
    print(f"{'[dry] 将' if dry else '已'}backfill {n} 页")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    run(a.dry)
