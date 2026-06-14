"""PIPELINE_LOG.md 唯一写入口（append-only）。

格式: [YYYY-MM-DD HH:MM] <cli> <op> <object> [k=v ...] → <state>
op: ingest|promote|update|lint|adjudicate|archive|reject
是多 CLI 的协调底座 + 「错了能回滚/可审计」的依据。任何状态翻转都要落这一条。
"""
import datetime

import common


def append(op, obj, cli="cc", state=None, **kw):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    extra = " ".join(f"{k}={v}" for k, v in kw.items() if v is not None)
    arrow = f" → {state}" if state else ""
    line = f"[{ts}] {cli} {op} {obj}" + (f" {extra}" if extra else "") + arrow
    path = common.vault_path("PIPELINE_LOG.md")
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


if __name__ == "__main__":
    import sys
    print(append(*sys.argv[1:3], **dict(kv.split("=") for kv in sys.argv[3:] if "=" in kv)))
