#!/usr/bin/env python3
"""XHS-Downloader 薄 runner —— 由 .xhs-downloader/.venv (Python 3.12) 执行。

这是子进程边界的「内侧」：被 xhs_backend.py 以
  PYTHONPATH=<clone> <clone>/.venv/bin/python xhs_downloader_runner.py <url> [cookie]
调用，把单行 JSON 写到 stdout，错误细节写 stderr（供 backend 分类）。

用法: python xhs_downloader_runner.py <url> [cookie]
输出: {"ok": bool, "data": dict|null}

注意：本文件运行在 3.12 venv 里，可用 3.12 语法；与 skill 胶水层的 3.9 约束无关。
"""

import asyncio
import contextlib
import json
import sys

from source import XHS  # 由 PYTHONPATH=<clone> 提供


async def _run(url: str, cookie: str) -> dict | None:
    # 只读提取：关掉一切文件/记录副作用，cookie 由 backend 传入（默认 ""）
    async with XHS(
        cookie=cookie,
        image_download=False,
        video_download=False,
        live_download=False,
        record_data=False,
        download_record=False,
        script_server=False,
    ) as xhs:
        results = await xhs.extract(url, download=False)
    # extract() 返回 list[dict]；取首条，必须含作品ID 才算成功
    if not results:
        return None
    data = results[0]
    if not isinstance(data, dict) or not data.get("作品ID"):
        return None
    return data


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "data": None, "error": "missing url"}))
        return 2
    url = sys.argv[1]
    cookie = sys.argv[2] if len(sys.argv) > 2 else ""
    # 库会把进度信息 rich.print 到 stdout；重定向到 stderr，保证 stdout 只有我们的 JSON
    real_stdout = sys.stdout
    try:
        with contextlib.redirect_stdout(sys.stderr):
            data = asyncio.run(_run(url, cookie))
    except Exception as exc:  # 兜底：错误进 stderr，backend 据此分类（含 IP 风控）
        print(json.dumps({"ok": False, "data": None, "error": repr(exc)}), file=real_stdout)
        print(repr(exc), file=sys.stderr)
        return 1
    print(json.dumps({"ok": bool(data), "data": data}, ensure_ascii=False), file=real_stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
