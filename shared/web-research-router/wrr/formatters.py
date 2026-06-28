"""Hermes JSON 输出格式化（success/content/details）。

保持 v3 兼容（含 banner、details 主键），新增 highlights 与 backup_hint。
fallback_chain 统一 snake_case（v3 web_fetch 曾用 camel 的 fallbackChain，此处归一）。
"""
import json
from typing import List, Optional

from . import config
from .schemas import FallbackStep, RouterResult


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
