"""Hermes JSON 输出格式化（success/content/details）+ doctor 报告。

保持 v3 兼容（含 banner、details 主键），新增 highlights 与 backup_hint。
fallback_chain 统一 snake_case（v3 web_fetch 曾用 camel 的 fallbackChain，此处归一）。
v5.1: doctor 人类可读报告 + JSON 输出。
"""
import json
from typing import List, Optional

from . import config
from .schemas import FallbackStep, RouterResult, EngineCheckResult


def _chain_dicts(steps: List[FallbackStep]):
    return [s.to_dict() for s in steps]


def _banner(result: RouterResult, primary: str) -> str:
    if result.actual_provider == primary:
        return ""
    failed = [s.provider for s in result.fallback_chain if not s.ok]
    return (f"> ⚠️ fallback: {' → '.join(failed)} 失败，"
            f"已降级到 **{result.actual_provider}**\n\n")


def format_search(result: RouterResult, query: str) -> str:
    primary = config.SEARCH_FALLBACK_ORDER[0]
    items = result.payload
    formatted = "\n\n".join(
        f"**{i + 1}. {r.title}**\n   {r.url}\n   {r.snippet}"
        + (("\n   ↳ " + " · ".join(r.highlights[:2])) if r.highlights else "")
        for i, r in enumerate(items)
    )
    details = {
        "provider": result.actual_provider,
        "query": query,
        "result_count": len(items),
        "results": [r.to_dict() for r in items],
        "fallback_chain": _chain_dicts(result.fallback_chain),
        "backup_hint": config.BACKUP_HINT,
    }
    # v5：mode 路由 + RRF 融合诊断（仅 v5 路径有值）
    if result.mode is not None:
        details["mode"] = result.mode
        details["fusion_method"] = result.fusion_method
        details["weights"] = result.weights
    banner = "" if result.mode is not None else _banner(result, primary)
    return json.dumps({
        "success": True,
        "content": f'## web_search (provider: {result.actual_provider}, query: "{query}")\n\n'
                   f"{banner}{formatted}",
        "details": details,
    }, ensure_ascii=False)


def format_extract(result: RouterResult, url: str) -> str:
    primary = config.EXTRACT_FALLBACK_ORDER[0]
    ex = result.payload
    hl = ("\n\n**Highlights:**\n" + "\n".join(f"- {h}" for h in ex.highlights)
          ) if ex.highlights else ""
    return json.dumps({
        "success": True,
        "content": f"## web_fetch (provider: {result.actual_provider}, url: {url})\n\n"
                   f"{_banner(result, primary)}{ex.text}{hl}",
        "details": {
            "url": url,
            "provider": result.actual_provider,
            "actualProvider": result.actual_provider,
            "chars": len(ex.text),
            "highlights": ex.highlights,
            "fallback_chain": _chain_dicts(result.fallback_chain),
            "backup_hint": config.BACKUP_HINT,
        },
    }, ensure_ascii=False)


def format_similar(result: RouterResult, url: str) -> str:
    items = result.payload
    formatted = "\n\n".join(
        f"**{i + 1}. {r.title}**\n   {r.url}\n   {r.snippet}"
        for i, r in enumerate(items)
    )
    return json.dumps({
        "success": True,
        "content": f"## web_similar (provider: {result.actual_provider}, url: {url})\n\n{formatted}",
        "details": {
            "url": url,
            "provider": result.actual_provider,
            "result_count": len(items),
            "results": [r.to_dict() for r in items],
            "fallback_chain": _chain_dicts(result.fallback_chain),
            "backup_hint": config.BACKUP_HINT,
        },
    }, ensure_ascii=False)


def format_error(operation: str, identifier: str, error: Exception,
                 fallback_chain: Optional[List[FallbackStep]] = None) -> str:
    payload = {
        "error": f"{operation} failed: {str(error)}",
        "details": {"identifier": identifier},
    }
    if fallback_chain is not None:
        payload["details"]["fallback_chain"] = _chain_dicts(fallback_chain)
    return json.dumps(payload, ensure_ascii=False)


# ── Doctor 报告格式化（v5.1）──────────────────────────────────────
def format_doctor_report(results: List[EngineCheckResult]) -> str:
    """格式化 doctor 检查结果为人类可读报告。

    按 tier 分组展示：
      Tier 0: no local config
      Tier 1: API key/token
      Tier 2: local service/CLI

    包含修复建议（仅失败/警告引擎）。
    """
    if not results:
        return "No engines checked."

    # 按 tier 分组
    by_tier = {}
    for r in results:
        tier = r.tier
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(r)

    # 状态符号映射
    status_symbol = {
        "ok": "OK",
        "warn": "WARN",
        "fail": "FAIL",
        "skip": "SKIP",
    }

    # Tier 标签
    tier_labels = {
        0: "Tier 0: No local configuration required",
        1: "Tier 1: API key/token required",
        2: "Tier 2: Local service/CLI required",
    }

    lines = []
    lines.append("=" * 70)
    lines.append("WRR Doctor Report")
    lines.append("=" * 70)

    for tier in sorted(by_tier.keys()):
        tier_results = by_tier[tier]
        lines.append("")
        lines.append(tier_labels.get(tier, f"Tier {tier}"))
        lines.append("-" * 70)

        for r in tier_results:
            symbol = status_symbol.get(r.status, r.status.upper())
            backend = f" ({r.active_backend})" if r.active_backend else ""
            lines.append(f"  [{symbol:4}] {r.engine:15} {r.summary}{backend}")

    # 修复建议部分（仅 fail/warn）
    failed_or_warned = [r for r in results if r.status in ("fail", "warn")]
    if failed_or_warned:
        lines.append("")
        lines.append("=" * 70)
        lines.append("Repair Instructions")
        lines.append("=" * 70)

        for r in failed_or_warned:
            lines.append("")
            lines.append(f"[{r.status.upper()}] {r.engine}")
            if r.details:
                lines.append(f"  Details: {r.details}")
            if r.repair:
                lines.append("  How to fix:")
                for step in r.repair:
                    lines.append(f"    {step}")

    lines.append("")
    lines.append("=" * 70)

    # 汇总统计
    counts = {"ok": 0, "warn": 0, "fail": 0, "skip": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    summary_parts = []
    if counts["ok"]:
        summary_parts.append(f"{counts['ok']} OK")
    if counts["warn"]:
        summary_parts.append(f"{counts['warn']} WARN")
    if counts["fail"]:
        summary_parts.append(f"{counts['fail']} FAIL")
    if counts["skip"]:
        summary_parts.append(f"{counts['skip']} SKIP")

    lines.append("Summary: " + ", ".join(summary_parts))
    lines.append("=" * 70)

    return "\n".join(lines)
