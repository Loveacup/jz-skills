"""Lint 巡检（🟢扫描）：孤立页 / 断链 / 缺溯源 core / 陈旧 / frontmatter 合规。

输出报告到 88-审计/lint-YYYY-MM-DD.md，人确认后修复（🟡）。纯标准库 + pyyaml。
用法：python3 lint.py
"""
import os
import datetime

import common
import config as C


def run():
    cfg = C.load()
    pages = list(common.iter_pages())
    titles = {os.path.basename(p)[:-3]: p for p in pages}
    inlinks = {t: set() for t in titles}
    broken, nosrc, stale, badfm = [], [], [], []
    today = datetime.date.today()

    for p in pages:
        fm, body = common.load(p)
        name = os.path.basename(p)[:-3]
        for link in common.wikilinks(body):
            if link in inlinks:
                inlinks[link].add(name)
            elif link not in titles:
                broken.append((name, link))
        if fm.get("lifecycle_state") == "core" and not fm.get("sources"):
            nosrc.append(name)
        for k in ("lifecycle_state", "status", "type"):
            if k not in fm:
                badfm.append((name, k))
        mod = str(fm.get("modified", ""))[:10]
        if mod and fm.get("status") != "归档":
            try:
                days = (today - datetime.date.fromisoformat(mod)).days
                if days > cfg["stale_days"]:
                    stale.append((name, days))
            except ValueError:
                pass

    orphans = [t for t in titles if not inlinks[t]]
    out = common.vault_path(common.AUDIT, f"lint-{today}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# Lint 报告 {today}\n\n")
        _sec(f, f"孤立页（入链=0）", [f"[[{o}]]" for o in orphans])
        _sec(f, "断链", [f"`{a}` → [[{b}]]" for a, b in broken])
        _sec(f, "缺溯源的 core 页", [f"[[{n}]]" for n in nosrc])
        _sec(f, f"陈旧（>{cfg['stale_days']}天）", [f"[[{n}]]（{d}d）" for n, d in stale])
        _sec(f, "frontmatter 缺字段", [f"`{n}`: 缺 {k}" for n, k in badfm])
    print(f"lint → {out}  (孤立{len(orphans)} 断链{len(broken)} 缺源{len(nosrc)} 陈旧{len(stale)})")
    return out


def _sec(f, title, items):
    f.write(f"## {title}（{len(items)}）\n")
    f.write("\n".join(f"- [ ] {it}" for it in items) if items else "_无_")
    f.write("\n\n")


if __name__ == "__main__":
    run()
