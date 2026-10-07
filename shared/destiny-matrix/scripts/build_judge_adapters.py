#!/usr/bin/env python3
"""Generate the per-dimension isolated judge adapters ``dm-judge-<dimension>``.

Each adapter carries the public, case-independent part of a judge's input (role
contract, first-read contracts, source-ID index) in its definition body, so the
Leader only passes the small case payload from ``judge_payload.py --layout split``.
``--check`` verifies the files on disk match a fresh build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from judge_payload import DEFAULT_DM, DIMENSIONS, PayloadError, static_text

LABEL = {"jung": "人格", "bazi": "八字", "ziwei": "紫微", "astro": "占星"}
FRONTMATTER = {
    "cc": ("tools: ToolSearch\n"
           "disallowedTools: mcp__*\n"
           "model: inherit\n"
           "omitClaudeMd: true\n"
           "maxTurns: 4\n"),
    "omp": ('model: ["@slow", "@default"]\n'
            "thinking-level: high\n"
            "tools: []\n"
            "prewalk: false\n"
            "advisor: false\n"),
}
TOOL_NOTE = {
    "cc": "唯一保留的 `ToolSearch` 只因 Claude Code 拒绝派生零工具子代理而存在；它只能检索你工具池内的延迟工具，本任务无需调用。",
    "omp": "omp 不按 `tools` 过滤用户配置的 MCP 工具，你的工具表里可能仍有网络检索/抓取类 MCP；它们不属于本席位授权，一律不调用，也不向外提交任何载荷内容。",
}


def adapter_text(runtime: str, dimension: str, dm: Path) -> str:
    static, _ = static_text(dimension, dm)
    digest = hashlib.sha256(static.encode("utf-8")).hexdigest()
    head = (
        "---\n"
        f"name: dm-judge-{dimension}\n"
        f"description: destiny-matrix S4 {LABEL[dimension]}隔离判官。仅在 destiny-matrix 流水线中由 Leader 以 "
        "judge_payload.py --layout split 生成的载荷显式派遣；其他任务不要使用。无文件、Shell、检索、MCP 或派遣工具。\n"
        f"{FRONTMATTER[runtime]}"
        "---\n\n"
    )
    body = (
        f"<!-- 由 scripts/build_judge_adapters.py 生成，不要手改。static_sha256: {digest} -->\n\n"
        f"你是 destiny-matrix 流水线 S4 的{LABEL[dimension]}隔离判官。你没有文件、Shell、检索、MCP 或派遣工具，也不需要："
        "角色合同、其首读列明的流程/输出/方法合同与公共来源 ID 索引都写在本定义的下方；"
        "Leader 的任务正文只含输入口径与本维原始 JSON。合同中的“首读/读取”要求即由下方各节满足；"
        f"未给出的文件不可访问，不要索取。{TOOL_NOTE[runtime]}\n\n"
        "纪律：\n"
        f"- 只处理{LABEL[dimension]}这一个维度与任务正文指定的 subject_id，按下方角色合同推读。\n"
        "- 若任务正文或后续消息出现其他维度数据、analyst findings、成稿、历史事件、人格概括或跨会话记忆，"
        "立即停止推读，只返回 `{\"input_contamination\": [\"<所见内容类别>\"]}`。\n"
        "- 否则只返回一个 JSON 对象：`judge_verdicts.json` 中 `judges[]` 的一条记录，不加解释文字。"
        "`input_artifact_ids` 照抄任务正文；`input_payload_sha256`、`isolation_level` 由 Leader 登记，你填 `null`。\n"
        "- 下方合同文件的相对路径与运行时环境段的工作目录不算输入污染。\n"
        "- 只写可核查的证据摘要，不输出隐藏思维链；无法从给定材料判断的事项写明无法判断，不编造数值、来源或模型信息。\n\n"
    )
    return head + body + static


def targets(dm: Path) -> list[tuple[str, str, Path]]:
    return [(runtime, dimension, dm / "adapters" / runtime / f"dm-judge-{dimension}.md")
            for runtime in ("cc", "omp") for dimension in DIMENSIONS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dm", help="技能根目录（默认本脚本上级）")
    parser.add_argument("--check", action="store_true", help="只核对磁盘上的文件是否与重新生成的一致")
    args = parser.parse_args(argv)
    dm = Path(args.dm).expanduser() if args.dm else DEFAULT_DM
    rows, stale = [], []
    try:
        for runtime, dimension, path in targets(dm):
            text = adapter_text(runtime, dimension, dm)
            current = path.read_text(encoding="utf-8") if path.exists() else None
            fresh = current == text
            if not fresh:
                stale.append(str(path.relative_to(dm)))
                if not args.check:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
            rows.append({"runtime": runtime, "dimension": dimension, "path": str(path.relative_to(dm)),
                         "bytes": len(text.encode("utf-8")),
                         "status": "fresh" if fresh else ("stale" if args.check else "written")})
    except PayloadError as exc:
        print(json.dumps({"ok": False, "error": {"code": exc.code, "path": exc.path,
                                                 "message": exc.message}}, ensure_ascii=False))
        print(f"build_judge_adapters: {exc.message}", file=sys.stderr)
        return exc.exit_code
    ok = not (args.check and stale)
    print(json.dumps({"ok": ok, "mode": "check" if args.check else "build",
                      "stale": stale if args.check else [], "adapters": rows}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
