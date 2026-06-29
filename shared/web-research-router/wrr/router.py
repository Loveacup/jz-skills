"""Fallback 路由（search / extract / similar 共用）+ 总预算控制。

规则（对齐执行包关键约束）：
  - 显式 provider → 单元素链，禁用 fallback
  - 自动模式按 config fallback order；引擎异常 **或空结果** → 切下一个
  - 每引擎只试一次（不重试同一 provider）
  - per-engine timeout + 按操作的总预算 config.budget_for(op)（超预算的后续引擎标记跳过）
"""
import asyncio
import time
from typing import Any, Dict, List, Optional

from . import config
from .engines import _fusion
from .errors import EngineError, AllEnginesFailedError
from .registry import EngineRegistry
from .schemas import FallbackStep, RouterResult, SearchResult


def build_chain(operation: str, explicit_provider: Optional[str],
                query: Optional[str] = None) -> List[str]:
    if explicit_provider:
        return [explicit_provider]
    if operation == "search":
        chain = list(config.SEARCH_FALLBACK_ORDER)
        promote = []
        if query and config.github_triggered(query):
            promote.append("github")           # site:github.com
        if query and config.community_triggered(query):
            promote.append("community")        # site:reddit/hn/twitter/zhihu/weibo
        if promote:
            chain = promote + [p for p in chain if p not in promote]
        return chain
    if operation == "extract":
        return list(config.EXTRACT_FALLBACK_ORDER)
    if operation == "similar":
        return list(config.SIMILAR_PROVIDERS)
    raise ValueError(f"unknown operation: {operation}")


async def _invoke(engine, operation: str, options) -> Any:
    if operation == "search":
        return await engine.search(options)
    if operation == "extract":
        return await engine.extract(options)
    if operation == "similar":
        return await engine.similar(options)
    raise ValueError(f"unknown operation: {operation}")


def _is_empty(operation: str, result) -> bool:
    if operation in ("search", "similar"):
        return not result                       # 空 list
    return not getattr(result, "text", "")      # extract：空 text


def _count(operation: str, result) -> int:
    if operation in ("search", "similar"):
        return len(result)
    return len(getattr(result, "text", "") or "")


async def route(operation: str, options, registry: EngineRegistry,
                explicit_provider: Optional[str] = None) -> RouterResult:
    chain = build_chain(operation, explicit_provider, getattr(options, "query", None))
    budget = config.budget_for(operation)
    steps: List[FallbackStep] = []
    start = time.monotonic()
    actual: Optional[str] = None
    payload: Any = None

    for provider in chain:
        elapsed = time.monotonic() - start
        if elapsed > budget:
            steps.append(FallbackStep(provider, False, 0, "budget exceeded (skipped)"))
            continue
        engine = registry.get(provider)
        if engine is None:
            steps.append(FallbackStep(provider, False, 0, f"unknown provider: {provider}"))
            continue
        remaining = budget - elapsed
        per_engine = min(engine.timeout, max(0.1, remaining))
        try:
            result = await asyncio.wait_for(_invoke(engine, operation, options), timeout=per_engine)
            if _is_empty(operation, result):
                steps.append(FallbackStep(provider, False, 0, "empty result"))
                continue
            steps.append(FallbackStep(provider, True, _count(operation, result)))
            actual, payload = provider, result
            break
        except asyncio.TimeoutError:
            steps.append(FallbackStep(provider, False, 0, f"timeout >{per_engine:.1f}s"))
        except EngineError as e:
            steps.append(FallbackStep(provider, False, 0, str(e) or type(e).__name__))
        except Exception as e:  # 引擎内部未归一的异常也不该让整链崩
            steps.append(FallbackStep(provider, False, 0, str(e) or type(e).__name__))

    if actual is None:
        reasons = "\n".join(f"  - {s.provider}: {s.error}" for s in steps)
        raise AllEnginesFailedError(f"All engines failed for {operation}:\n{reasons}")

    return RouterResult(actual_provider=actual, payload=payload, fallback_chain=steps)


# ══════════════════════════════════════════════════════════════════════
# v5.0：mode 分发 + 多引擎并行 + 跨源 RRF 融合（加法式，与 route() 并存）
# 真相源：/tmp/wrr-v5.0-stdd-final.md。STDD §3。
# ══════════════════════════════════════════════════════════════════════

_V5_MODES = ("discovery", "grounding", "research", "academic", "platform",
             "recovery", "local", "broad")


def resolve_mode(options) -> str:
    """显式 options.mode（若是 v5 mode）优先，否则 classify_intent 自动分类。"""
    m = getattr(options, "mode", None)
    if m in _V5_MODES:
        return m
    return config.classify_intent(getattr(options, "query", "") or "")


async def _run_engine(registry, name, options, budget):
    """跑单引擎 search，超时/异常隔离，返回 (name, results_or_None, FallbackStep)。"""
    engine = registry.get(name)
    if engine is None:
        return name, None, FallbackStep(name, False, 0, f"unknown provider: {name}")
    try:
        per_engine = min(engine.timeout, max(0.1, budget))
        res = await asyncio.wait_for(engine.search(options), timeout=per_engine)
        if not res:
            return name, None, FallbackStep(name, False, 0, "empty result")
        return name, res, FallbackStep(name, True, len(res))
    except asyncio.TimeoutError:
        return name, None, FallbackStep(name, False, 0, "timeout")
    except Exception as e:                       # 单引擎异常不拖垮整组
        return name, None, FallbackStep(name, False, 0, str(e) or type(e).__name__)


async def _dispatch(registry, engine_names, options, weights, mode, budget):
    """并行发射一组引擎 → 跨源 RRF 融合 → canonical 去重。返回 (payload, steps)。"""
    results = await asyncio.gather(
        *[_run_engine(registry, n, options, budget) for n in engine_names])
    per_source: Dict[str, List[SearchResult]] = {}
    steps: List[FallbackStep] = []
    for name, res, step in results:
        steps.append(step)
        if res:
            per_source[name] = res
    if not per_source:
        return None, steps
    fused = _fusion.rrf_fuse(per_source, k=config.RRF_K, weights=weights)
    deduped = _fusion.dedup_cluster([f["doc"] for f in fused],
                                    config.COMMUNITY_DEDUP_THRESHOLD)
    return deduped[:options.count], steps


async def route_search_v5(options, registry: EngineRegistry) -> RouterResult:
    """v5 搜索路由：classify_intent → mode → 并行引擎 → RRF 融合 → 去重排序。

    显式 options.provider 仍走单引擎（兼容 v4 语义）。主 mode 空结果 → recovery 兜底。
    """
    # 显式 provider → 单引擎（复用 v4 route 语义，禁用 mode 路由）
    explicit = getattr(options, "provider", None)
    if explicit:
        return await route("search", options, registry, explicit_provider=explicit)

    mode = resolve_mode(options)
    budget = config.budget_for("search")
    weights = config.MODE_WEIGHTS.get(mode, config.MODE_WEIGHTS["grounding"])
    engine_names = config.mode_engines(mode, getattr(options, "query", "") or "")

    payload, steps = await _dispatch(registry, engine_names, options, weights, mode, budget)

    # v5.3 全量陈旧门控：local mode 下所有结果 freshness < 0.8 → 追加外网交叉
    if mode == "local" and payload is not None:
        if all(getattr(r, "freshness_score", 1.0) < 0.8 for r in payload):
            web_mode = config.classify_intent(getattr(options, "query", "") or "")
            if web_mode == "local":
                web_mode = "discovery"
            web_engines = config.mode_engines(web_mode, getattr(options, "query", "") or "")
            web_weights = config.MODE_WEIGHTS.get(web_mode, config.MODE_WEIGHTS["grounding"])
            wpayload, wsteps = await _dispatch(registry, web_engines, options, web_weights,
                                               web_mode, budget)
            steps.extend(wsteps)
            if wpayload is not None:
                # 合并：web 结果在前（更新），本地垫后
                payload = wpayload + payload

    # 主 mode 空 → recovery 兜底（Brave + Exa + SearXNG）
    if payload is None and mode != "recovery":
        rec_weights = config.MODE_WEIGHTS["recovery"]
        rec_names = config.mode_engines("recovery", getattr(options, "query", "") or "")
        rpayload, rsteps = await _dispatch(registry, rec_names, options, rec_weights,
                                           "recovery", budget)
        steps.extend(rsteps)
        if rpayload is not None:
            return RouterResult(actual_provider=f"rrf:recovery", payload=rpayload,
                                fallback_chain=steps, mode="recovery",
                                fusion_method="rrf", weights=dict(rec_weights))
        mode_for_err = mode

    if payload is None:
        reasons = "\n".join(f"  - {s.provider}: {s.error}" for s in steps if not s.ok)
        raise AllEnginesFailedError(f"All engines failed for search (mode={mode}):\n{reasons}")

    used = {n: weights.get(n, 1.0) for n in engine_names}
    return RouterResult(actual_provider=f"rrf:{mode}", payload=payload,
                        fallback_chain=steps, mode=mode,
                        fusion_method="rrf", weights=used)
