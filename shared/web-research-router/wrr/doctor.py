"""WRR doctor 运行器 + 诊断汇总。"""
import asyncio
from typing import Dict, List, Optional

from .registry import EngineRegistry
from .schemas import EngineCheckResult


async def run_doctor(
    registry: EngineRegistry,
    *,
    engine: Optional[str] = None,
    tier: Optional[int] = None,
    deep: bool = False,
) -> List[EngineCheckResult]:
    """
    运行 doctor 检查。

    Args:
        registry: 引擎注册表
        engine: 指定单个引擎名称，None 表示检查所有
        tier: 过滤特定 tier，None 表示不过滤
        deep: 是否执行深度检查（P0 未实现）

    Returns:
        检查结果列表

    Raises:
        ValueError: 指定的 engine 不存在时抛出
    """
    targets = registry.doctor_targets()

    # 过滤指定 engine
    if engine:
        target_engine = registry.get(engine)
        if not target_engine:
            raise ValueError(f"Unknown engine: {engine}")
        targets = [target_engine]

    # 过滤 tier
    if tier is not None:
        targets = [e for e in targets if e.tier == tier]

    # 并发执行检查，隔离异常
    async def _check_safe(eng):
        try:
            return await eng.health_check(deep=deep)
        except Exception as exc:
            return EngineCheckResult(
                engine=eng.name,
                status="fail",
                tier=getattr(eng, "tier", 1),
                summary="Doctor check crashed",
                evidence={"exception": type(exc).__name__, "message": str(exc)},
            )

    results = await asyncio.gather(*[_check_safe(e) for e in targets])
    return list(results)


def summarize_checks(results: List[EngineCheckResult]) -> Dict:
    """
    汇总检查结果。

    Returns:
        {
            "ok": int,
            "warn": int,
            "fail": int,
            "skip": int,
            "status": "ok" | "warn" | "fail"
        }
    """
    counts = {"ok": 0, "warn": 0, "fail": 0, "skip": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    # 聚合状态：有 fail 则 fail，有 warn 则 warn，否则 ok
    if counts["fail"] > 0:
        agg_status = "fail"
    elif counts["warn"] > 0:
        agg_status = "warn"
    else:
        agg_status = "ok"

    return {**counts, "status": agg_status}


def doctor_exit_code(results: List[EngineCheckResult], *, strict: bool = False) -> int:
    """
    计算 doctor 退出码。

    Args:
        results: 检查结果列表
        strict: True 时 warn 也视为失败

    Returns:
        0: 通过（无 fail，或 strict=False 且仅有 warn）
        1: 失败（有 fail，或 strict=True 且有 warn）
    """
    has_fail = any(r.status == "fail" for r in results)
    has_warn = any(r.status == "warn" for r in results)

    if has_fail:
        return 1
    if strict and has_warn:
        return 1
    return 0
