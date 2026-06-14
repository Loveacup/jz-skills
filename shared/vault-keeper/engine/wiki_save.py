"""Query 回填：把高价值对话产出存为 conversation 源 → 走正常 ingest 管道。

这是 v2.0 相比 v1.7 的最大复利增量：探索也复利入库，不沉入聊天历史。
用法：python3 wiki_save.py --title "RAG vs 长上下文对比" --file 对话产出.md
之后由 agent 对该源跑 ingest（评分→过滤→抽取→建 candidate）。
"""
import argparse

import capture as CAP
import log as L


def save(title, content):
    sid, path = CAP.capture("conversation", f"query:{title}", content)
    L.append("query", title, state="raw")
    print(f"回填源 {sid} → {path}（接着对其跑 ingest）")
    return sid, path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--file", required=True)
    a = ap.parse_args()
    save(a.title, open(a.file, encoding="utf-8").read())
