"""Ingest 归档助手（确定性部分）。

分工：评分→过滤→实体抽取 由 **agent** 按 SKILL.md 完成（AI 判断）；
本脚本只做确定性归档——把 agent 给定的 (标题, 摘要, sources) 写成/更新 01-Staging 的 candidate 页。
这正是「闸是代码、AI 判断在 agent」的体现。
用法：
  python3 ingest.py --title "检索增强生成(RAG)" --summary "RAG 的定义与原理" \\
                    --sources SRC-20260614-001 SRC-20260520-014 --ai-self 0.7
"""
import os
import argparse
import datetime

import common
import log as L


def upsert(title, summary, sources, ai_self=0.6, cli="cc"):
    path = common.vault_path(common.STAGING, f"{title}.md")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if os.path.exists(path):                                  # 已有 → 追加源（additive）
        fm, body = common.load(path)
        srcs = fm.get("sources") or []
        for s in sources:
            if s not in srcs:
                srcs.append(s)
        fm["sources"] = srcs
        fm["modified"] = now
        body = body.rstrip() + f"\n- {summary}（来源 {', '.join(sources)}）\n"
    else:                                                     # 新建 candidate
        fm = {
            "lifecycle_state": "candidate",
            "status": "种子",
            "sources": list(sources),
            "confidence": None,           # 由 gate.py 计算
            "risk": None,                 # 由 risk.py 标注
            "_ai_self": ai_self,
            "type": "概念",
            "priority": "正常",
            "aliases": [],
            "tags": ["status/种子", "src/原创"],
            "created": now,
            "modified": now,
        }
        body = (f"\n# {title}\n\n{summary}\n\n"
                f"## 来源\n" + "\n".join(f"- {s}" for s in sources) + "\n")

    common.dump(path, fm, body)
    L.append("ingest", title, cli=cli, state="candidate")
    print("candidate →", path)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", default="")
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--ai-self", type=float, default=0.6)
    a = ap.parse_args()
    upsert(a.title, a.summary, a.sources, a.ai_self)
