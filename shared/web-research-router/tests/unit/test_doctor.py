"""测试 doctor 基础设施：schemas, runner, summarize, exit_code。"""
import asyncio
import pytest

from wrr.schemas import EngineCheckResult
from wrr.doctor import run_doctor, summarize_checks, doctor_exit_code
from wrr.registry import EngineRegistry
from wrr.engines.base import SearchEngine


def run(coro):
    """同步运行协程（遵循现有测试模式）。"""
    return asyncio.run(coro)


class FakeEngine(SearchEngine):
    """测试用假引擎。"""
    def __init__(self, name: str, tier: int = 1, check_status: str = "ok"):
        self.name = name
        self.tier = tier
        self._check_status = check_status

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        return EngineCheckResult(
            engine=self.name,
            status=self._check_status,
            tier=self.tier,
            summary=f"{self.name} check {self._check_status}",
        )


class CrashEngine(SearchEngine):
    """故意崩溃的引擎。"""
    name = "crash"
    tier = 1

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        raise RuntimeError("Intentional crash")


# ── EngineCheckResult schema 测试 ──────────────────────────────────
def test_engine_check_result_to_dict():
    """to_dict 返回完整字段。"""
    result = EngineCheckResult(
        engine="test",
        status="ok",
        tier=1,
        summary="Test summary",
        details="Test details",
        active_backend="test-api",
        requirements=["env:TEST_KEY"],
        repair=["export TEST_KEY=xxx"],
        evidence={"env.TEST_KEY": "present"},
    )
    d = result.to_dict()
    assert d["engine"] == "test"
    assert d["status"] == "ok"
    assert d["tier"] == 1
    assert d["summary"] == "Test summary"
    assert d["details"] == "Test details"
    assert d["active_backend"] == "test-api"
    assert d["requirements"] == ["env:TEST_KEY"]
    assert d["repair"] == ["export TEST_KEY=xxx"]
    assert d["evidence"] == {"env.TEST_KEY": "present"}


def test_engine_check_result_ok_property():
    """ok 属性：ok/skip 为 True，warn/fail 为 False。"""
    assert EngineCheckResult("e", "ok", 1, "s").ok is True
    assert EngineCheckResult("e", "skip", 1, "s").ok is True
    assert EngineCheckResult("e", "warn", 1, "s").ok is False
    assert EngineCheckResult("e", "fail", 1, "s").ok is False


def test_engine_check_result_evidence_redaction():
    """evidence 不应包含敏感值，只存在性标识。"""
    # 这是规范测试，验证使用者遵守约定
    result = EngineCheckResult(
        engine="test",
        status="ok",
        tier=1,
        summary="Key present",
        evidence={"env.API_KEY": "present"},  # 正确：只标识存在性
    )
    assert "present" in str(result.evidence.get("env.API_KEY", ""))
    # 不应出现实际密钥值


# ── run_doctor 测试 ────────────────────────────────────────────────
def test_run_doctor_all_engines():
    """无过滤时运行所有引擎检查。"""
    reg = EngineRegistry()
    reg.register(FakeEngine("e1", tier=1, check_status="ok"))
    reg.register(FakeEngine("e2", tier=2, check_status="warn"))

    results = run(run_doctor(reg))
    assert len(results) == 2
    assert {r.engine for r in results} == {"e1", "e2"}


def test_run_doctor_filter_by_engine():
    """--engine 过滤指定引擎。"""
    reg = EngineRegistry()
    reg.register(FakeEngine("e1"))
    reg.register(FakeEngine("e2"))

    results = run(run_doctor(reg, engine="e1"))
    assert len(results) == 1
    assert results[0].engine == "e1"


def test_run_doctor_unknown_engine_raises():
    """指定不存在的引擎抛出 ValueError。"""
    reg = EngineRegistry()
    reg.register(FakeEngine("e1"))

    with pytest.raises(ValueError, match="Unknown engine: nonexist"):
        run(run_doctor(reg, engine="nonexist"))


def test_run_doctor_filter_by_tier():
    """--tier 过滤指定层级。"""
    reg = EngineRegistry()
    reg.register(FakeEngine("e1", tier=1))
    reg.register(FakeEngine("e2", tier=2))
    reg.register(FakeEngine("e3", tier=1))

    results = run(run_doctor(reg, tier=1))
    assert len(results) == 2
    assert {r.engine for r in results} == {"e1", "e3"}


def test_run_doctor_crash_isolation():
    """某引擎崩溃不影响其他引擎检查。"""
    reg = EngineRegistry()
    reg.register(FakeEngine("e1", check_status="ok"))
    reg.register(CrashEngine())
    reg.register(FakeEngine("e2", check_status="warn"))

    results = run(run_doctor(reg))
    assert len(results) == 3

    # e1/e2 正常
    e1_result = next(r for r in results if r.engine == "e1")
    assert e1_result.status == "ok"
    e2_result = next(r for r in results if r.engine == "e2")
    assert e2_result.status == "warn"

    # crash 引擎返回 fail 包含异常信息
    crash_result = next(r for r in results if r.engine == "crash")
    assert crash_result.status == "fail"
    assert crash_result.summary == "Doctor check crashed"
    assert crash_result.evidence["exception"] == "RuntimeError"


# ── summarize_checks 测试 ──────────────────────────────────────────
def test_summarize_checks_all_ok():
    """全部 ok 时聚合状态为 ok。"""
    results = [
        EngineCheckResult("e1", "ok", 1, "s1"),
        EngineCheckResult("e2", "skip", 1, "s2"),
    ]
    summary = summarize_checks(results)
    assert summary["ok"] == 1
    assert summary["skip"] == 1
    assert summary["warn"] == 0
    assert summary["fail"] == 0
    assert summary["status"] == "ok"


def test_summarize_checks_with_warn():
    """有 warn 但无 fail 时聚合状态为 warn。"""
    results = [
        EngineCheckResult("e1", "ok", 1, "s1"),
        EngineCheckResult("e2", "warn", 1, "s2"),
    ]
    summary = summarize_checks(results)
    assert summary["warn"] == 1
    assert summary["status"] == "warn"


def test_summarize_checks_with_fail():
    """有 fail 时聚合状态为 fail。"""
    results = [
        EngineCheckResult("e1", "ok", 1, "s1"),
        EngineCheckResult("e2", "warn", 1, "s2"),
        EngineCheckResult("e3", "fail", 1, "s3"),
    ]
    summary = summarize_checks(results)
    assert summary["fail"] == 1
    assert summary["status"] == "fail"


# ── doctor_exit_code 测试 ──────────────────────────────────────────
def test_doctor_exit_code_default_ignores_warn():
    """默认模式：warn 不影响退出码（返回 0）。"""
    results = [
        EngineCheckResult("e1", "ok", 1, "s1"),
        EngineCheckResult("e2", "warn", 1, "s2"),
    ]
    assert doctor_exit_code(results) == 0


def test_doctor_exit_code_strict_treats_warn_as_failure():
    """严格模式：warn 导致退出码 1。"""
    results = [
        EngineCheckResult("e1", "ok", 1, "s1"),
        EngineCheckResult("e2", "warn", 1, "s2"),
    ]
    assert doctor_exit_code(results, strict=True) == 1


def test_doctor_exit_code_fail_always_nonzero():
    """有 fail 时无论 strict 均返回 1。"""
    results = [
        EngineCheckResult("e1", "fail", 1, "s1"),
    ]
    assert doctor_exit_code(results) == 1
    assert doctor_exit_code(results, strict=True) == 1


def test_doctor_exit_code_all_ok_returns_zero():
    """全部通过返回 0。"""
    results = [
        EngineCheckResult("e1", "ok", 1, "s1"),
        EngineCheckResult("e2", "skip", 1, "s2"),
    ]
    assert doctor_exit_code(results) == 0
    assert doctor_exit_code(results, strict=True) == 0
