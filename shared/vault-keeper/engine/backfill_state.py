"""冷启动：给现有 core 区笔记批量补 lifecycle_state: core（幂等）。

只处理 10/20/30/02 区已有 frontmatter 的页。跳过：已含 lifecycle_state、
区内归档子目录（由 iter_pages 排除）、status 已为 归档/archived 的页。
用法：python3 backfill_state.py [--dry]
"""
import os
import re
import argparse
import datetime

import common


def run(dry=False):
    changed = []
    for p in common.iter_pages():                       # iter_pages 已跳过区内归档子目录
        txt = open(p, encoding="utf-8").read()
        if "lifecycle_state:" in txt or not txt.startswith("---"):
            continue
        if re.search(r"^status:\s*(归档|archived)\s*$", txt[:800], re.M):  # 双保险：已归档不补 core
            continue
        if not dry:
            txt = re.sub(r"^(---\n)", r"\1lifecycle_state: core\n", txt, count=1)
            open(p, "w", encoding="utf-8").write(txt)
        changed.append(os.path.relpath(p, common.VAULT))
    out = _write_manifest(changed) if not dry else None
    tail = f"，清单 → {os.path.relpath(out, common.VAULT)}" if out else ""
    print(f"{'[dry] 将' if dry else '已'}backfill {len(changed)} 页{tail}")
    return len(changed)


def _write_manifest(changed):
    """落变更清单，供精准撤销（按清单逐文件删 lifecycle_state: core 行，独立于 git/Obsidian Sync）。"""
    today = datetime.date.today()
    out = common.vault_path(common.AUDIT, f"backfill-{today}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    head = [
        "---", "status: 常青", "type: 系统",
        "tags: [type/系统, status/常青, src/原创, topic/治理]",
        f"created: {today}", f"modified: {today}", "---", "",
        f"# backfill 变更清单 {today}", "",
        f"> 给 {len(changed)} 个 core 页补了 `lifecycle_state: core`（additive·幂等）。",
        "> **撤销**：对下列每个文件删除其 frontmatter 的 `lifecycle_state: core` 行即可。",
        "",
    ]
    body = "\n".join(f"- [ ] {rel}" for rel in changed)
    open(out, "w", encoding="utf-8").write("\n".join(head) + body + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    run(a.dry)
