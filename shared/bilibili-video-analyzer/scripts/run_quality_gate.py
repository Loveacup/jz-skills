#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2-E/P2-F quality gate harness: fetch_all JSON → report → gates.

This script is deliberately deterministic by default (`--writer-provider fixture`):
it exercises the same generate_report/render/verify/coherence pipeline without
network calls or LLM tokens. Use `--writer-provider cli` for a real model-backed
sample smoke. P2-F adds fallback-warning detection so real sample runs can fail
when the LLM writer silently falls back to skeleton output.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Callable, Dict, Any, Optional, Tuple

# Allow running as `python scripts/run_quality_gate.py` from repo root.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_report
import verify_report
import verify_publishable_report
from video_analysis_engine import check_report_coherence

WriterProvider = Callable[[str, str], str]


def _repeat_sentence(seed: str, citation: str, min_chars: int) -> str:
    """Create citation-bearing Chinese prose long enough for static gates."""
    sentence = (
        f"{seed}这段分析严格基于现有证据{citation}，先说明现象，再解释机制，"
        "最后落到对观看者可验证的启发；它不补写视频没有给出的事实，只把证据中已经出现的"
        "时间、行动、角色和因果关系组织成清晰段落。"
    )
    out = []
    while len("".join(out)) < min_chars:
        out.append(sentence)
    return "".join(out)


def fixture_writer_provider(system: str, user: str) -> str:
    """Deterministic provider that returns verify_report-compatible sections.

    It is not a content-quality substitute for real LLM output. Its job is to
    catch pipeline regressions: prompt routing, section formatting, static gates,
    and coherence validation.
    """
    if "洞察" in system and "💡" in system:
        parts = []
        for i in range(1, 4):
            parts.append(f"### 💡 洞察 {i}：证据驱动的关键判断 [E{i}]")
            parts.append(_repeat_sentence(f"第{i}个洞察指出，", f"[E{i}]", 230))
        return "\n".join(parts) + "\n"

    if "模块" in system and ("Deep Dive" in user or "深度" in system or "模块 N" in system):
        parts = []
        for i in range(1, 4):
            parts.append(f"### 模块 {i}：结构化拆解层 {i} [E{i}]")
            parts.append(_repeat_sentence(f"模块{i}从叙事结构、证据链和行动后果三个角度展开，", f"[E{i}]", 560))
        return "\n".join(parts) + "\n"

    if "独特价值" in system and "可行动" in system:
        return """### 独特价值 [E1]
- 这份内容把分散现象压缩成可追踪的问题链，让观看者能从证据而不是情绪出发理解主题 [E1]
- 它把历史事实、商业动机和用户后果放在同一张图里，适合转化为后续知识笔记 [E2]
- 它保留了足够多的原文锚点，方便复核关键判断是否真的来自视频内容 [E3]

### 局限与偏见 [E2]
- 从现有证据只能看出视频自身的叙事重点，不能自动证明所有背景事实都完整无误 [E2]
- 评论和弹幕样本数量有限，观众反馈只能作为辅助信号，不能替代事实核查 [E3]

### 可行动项 [E3]
1. 先把核心概念拆成可复查的 claim 清单，再逐条补外部资料验证 [E1]
2. 把高光引文与时间戳保留到 Obsidian，作为后续主题研究入口 [E2]
3. 对商业动机、技术演化、用户影响分别建立链接，避免只留下单线故事 [E3]
"""

    # Fail closed: an unknown prompt should make validation fail, not hide routing bugs.
    return "fixture provider received an unknown writer prompt without valid section format"


def resolve_quality_provider(name: str) -> Optional[WriterProvider]:
    if name == "none":
        return None
    if name == "fixture":
        return fixture_writer_provider
    args = argparse.Namespace(writer_provider=name)
    return generate_report.resolve_writer_provider(args)


def _load_results(input_path: str) -> Dict[str, Any]:
    text = Path(input_path).read_text(encoding="utf-8")
    parsed = generate_report.parse_result_json(text)
    if parsed is None:
        raise ValueError(f"无法解析 fetch_all JSON: {input_path}")
    return parsed


def run_quality_gate(
    input_path: str,
    output_path: str,
    *,
    writer_provider: str = "fixture",
    mode: str = "full",
    run_fact_check: bool = False,
    fail_on_fallback_warning: bool = False,
    publishable_gate: bool = False,
    section_qa_gate: bool = False,  # Phase 4: 可选 section QA gate
) -> Tuple[bool, Dict[str, Any]]:
    """Run the report quality gate and return (passed, summary)."""
    results = _load_results(input_path)
    provider = resolve_quality_provider(writer_provider)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        markdown, report = generate_report.report_markdown(
            results,
            run_fact_check=run_fact_check,
            provider=provider,
        )
    warning_messages = [str(w.message) for w in caught]
    fallback_warnings = [
        msg for msg in warning_messages
        if "falling back to skeleton" in msg
        or ("LLM writer" in msg and "fallback" in msg.lower())
    ]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(markdown, encoding="utf-8")

    verify_results, verify_passed = verify_report.evaluate(markdown, mode)
    coherence = check_report_coherence(markdown)
    publishable_results = None
    publishable_passed = None
    publishable_failed_codes = []
    if publishable_gate:
        publishable_results, publishable_passed = verify_publishable_report.evaluate(markdown)
        publishable_failed_codes = [
            code for code, gate in publishable_results.items()
            if not gate.get("pass")
        ]
    failed_due_to_fallback_warning = bool(fail_on_fallback_warning and fallback_warnings)
    failed_due_to_publishable_gate = bool(publishable_gate and not publishable_passed)

    # Phase 4: section QA gate 逻辑
    section_qa = report.get("section_qa", {})
    section_qa_failed = False
    if section_qa_gate:
        # 检查所有 section QA 是否有 P0 blockers
        for sid, qa in section_qa.items():
            if qa.get("blockers"):
                section_qa_failed = True
                break
    section_qa_gate_passed = not section_qa_failed
    failed_due_to_section_qa_gate = bool(section_qa_gate and section_qa_failed)

    passed = bool(
        verify_passed
        and coherence.passed
        and not failed_due_to_fallback_warning
        and not failed_due_to_publishable_gate
        and not failed_due_to_section_qa_gate
    )
    summary = {
        "passed": passed,
        "input_path": input_path,
        "output_path": output_path,
        "writer_provider": writer_provider,
        "mode": mode,
        "markdown_chars": len(markdown),
        "video_id": report.get("frontmatter", {}).get("video_id"),
        "fail_on_fallback_warning": fail_on_fallback_warning,
        "warnings": warning_messages,
        "fallback_warnings": fallback_warnings,
        "fallback_warning_count": len(fallback_warnings),
        "failed_due_to_fallback_warning": failed_due_to_fallback_warning,
        "publishable_gate": publishable_gate,
        "publishable_passed": publishable_passed,
        "publishable_failed_codes": publishable_failed_codes,
        "publishable_gates": publishable_results,
        "failed_due_to_publishable_gate": failed_due_to_publishable_gate,
        "section_qa_gate": section_qa_gate,  # Phase 4: section QA gate 开关
        "section_qa_gate_passed": section_qa_gate_passed,  # Phase 4: section QA gate 是否通过
        "failed_due_to_section_qa_gate": failed_due_to_section_qa_gate,  # Phase 4: 是否因 section QA gate 失败
        "verify_passed": verify_passed,
        "verify_gates": verify_results,
        "coherence_passed": coherence.passed,
        "coherence_issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "section_id": issue.section_id,
                "message": issue.message,
            }
            for issue in coherence.issues
        ],
        "section_qa": section_qa,  # Phase 3: QA 元数据暴露
    }
    return passed, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Bilibili report quality gates end-to-end."
    )
    parser.add_argument("--input", required=True, help="fetch_all JSON path")
    parser.add_argument("--output", help="report output path")
    parser.add_argument(
        "--writer-provider",
        choices=("fixture", "none", "cli", "deepseek"),
        default="fixture",
        help="fixture is deterministic/no-token; cli/deepseek exercise real LLM writer providers",
    )
    parser.add_argument("--mode", choices=("full", "condensed"), default="full")
    parser.add_argument(
        "--run-fact-check",
        action="store_true",
        help="Allow generate_report to run fact_check_wrr extraction; default is off for deterministic CI",
    )
    parser.add_argument(
        "--fail-on-fallback-warning",
        action="store_true",
        help="Fail if LLM writer validation/error warnings show fallback to skeleton; recommended for real sample smoke",
    )
    parser.add_argument(
        "--publishable",
        action="store_true",
        help="Run the stricter publishable Obsidian note gate. This is opt-in; default gate is engineering-only.",
    )
    parser.add_argument(
        "--section-qa-gate",
        action="store_true",
        help="Phase 4: Enable section-level content quality gate (P0 blockers fail the report).",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    output = args.output
    if not output:
        stem = Path(args.input).stem.replace("_fetch_all", "")
        output = f"/tmp/{stem}_quality_gate_report.md"

    try:
        passed, summary = run_quality_gate(
            args.input,
            output,
            writer_provider=args.writer_provider,
            mode=args.mode,
            run_fact_check=args.run_fact_check,
            fail_on_fallback_warning=args.fail_on_fallback_warning,
            publishable_gate=args.publishable,
            section_qa_gate=args.section_qa_gate,  # Phase 4
        )
    except Exception as exc:
        print(f"❌ quality gate failed before evaluation: {exc}", file=sys.stderr)
        if args.as_json:
            print("RESULT_JSON_START")
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
            print("RESULT_JSON_END")
        sys.exit(2)

    mark = "✅" if passed else "❌"
    print(f"{mark} quality gate {'PASS' if passed else 'FAIL'}")
    print(f"   input : {summary['input_path']}")
    print(f"   output: {summary['output_path']} ({summary['markdown_chars']} chars)")
    print(f"   verify_report: {summary['verify_passed']}")
    print(f"   coherence    : {summary['coherence_passed']} ({len(summary['coherence_issues'])} issues)")
    if summary["publishable_gate"]:
        print(
            f"   publishable  : {summary['publishable_passed']}"
            f" ({len(summary['publishable_failed_codes'])} failed gates)"
        )
    print(
        f"   fallback warn: {summary['fallback_warning_count']}"
        + (" (fail-on-fallback enabled)" if summary["fail_on_fallback_warning"] else "")
    )
    for gid, gate in summary["verify_gates"].items():
        status = "PASS" if gate["pass"] else "FAIL"
        print(f"   {gid}: {status} — {gate['measured']}")
    if summary["coherence_issues"]:
        for issue in summary["coherence_issues"]:
            print(f"   coherence {issue['severity']} {issue['code']}: {issue['message']}")
    if summary["fallback_warnings"]:
        for msg in summary["fallback_warnings"]:
            print(f"   fallback warning: {msg}")

    if args.as_json:
        print("RESULT_JSON_START")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
