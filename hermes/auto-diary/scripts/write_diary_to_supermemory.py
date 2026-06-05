#!/usr/bin/env python3
"""日记 → Supermemory `hermes` 池（auto-diary Workflow A 收尾步骤）。

为什么需要它：memory provider 的自动 capture 在 cron session 被关闭
（`_write_enabled = agent_context not in {"cron","flush","subagent"}`），
所以日记 cron 的内容从不进 supermemory。本脚本在日记校验 PASS 后，
**直接用 SDK 幂等写入**，让小黄（default/hermes 池）能检索每天的日记。

设计原则：
- **幂等**：`custom_id=hermes-diary-<date>`，同一天重跑覆盖而非重复。
- **非阻塞**：任何失败只打印 warning 并 return 0，绝不影响日记交付。
- **走代理**：默认 `HTTPS_PROXY=127.0.0.1:6152` 避开 Surge fake-ip。

用法：python3 write_diary_to_supermemory.py <diary.md>
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# 兜底：cron 可能用系统 python3（无 supermemory SDK），把 hermes venv 的
# site-packages 加进来，确保能 import。
_VENV_SP = "~/.hermes/hermes-agent/venv/lib/python3.11/site-packages"
if os.path.isdir(_VENV_SP) and _VENV_SP not in sys.path:
    sys.path.insert(0, _VENV_SP)


def _load_key() -> str:
    key = os.environ.get("SUPERMEMORY_API_KEY", "").strip()
    if key:
        return key
    for env in (
        "~/.hermes/profiles/cron-worker/.env",
        "~/.hermes/.env",
    ):
        try:
            for line in Path(env).read_text(encoding="utf-8").splitlines():
                if line.startswith("SUPERMEMORY_API_KEY="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return ""


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: write_diary_to_supermemory.py <diary.md>")
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"[supermemory] diary not found: {path} — skip")
        return 0
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(content) < 50:
        print("[supermemory] diary too short — skip")
        return 0

    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    date = m.group(1) if m else path.stem

    os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:6152")
    os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:6152")

    key = _load_key()
    if not key:
        print("[supermemory] no SUPERMEMORY_API_KEY — skip")
        return 0

    try:
        from supermemory import Supermemory
    except Exception as exc:  # SDK 缺失，非阻塞
        print(f"[supermemory] SDK unavailable ({exc}) — skip")
        return 0

    try:
        client = Supermemory(
            api_key=key,
            timeout=20,
            max_retries=1,
            default_headers={"x-sm-source": "hermes"},
        )
        result = client.documents.add(
            content=content,
            container_tags=["hermes"],
            custom_id=f"hermes-diary-{date}",
            metadata={"sm_source": "hermes", "type": "diary", "date": date},
        )
        print(f"[supermemory] ✓ diary {date} → hermes 池 (id={getattr(result, 'id', '')})")
    except Exception as exc:  # 写入失败，非阻塞
        print(f"[supermemory] ⚠ write failed (non-blocking): {type(exc).__name__}: {str(exc)[:140]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
