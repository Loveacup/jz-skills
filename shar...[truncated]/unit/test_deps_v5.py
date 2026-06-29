"""wrr/deps.py 单元测试（v5.5 外部依赖控制面）。"""
import pytest

from wrr.deps import (
    DepRegistry,
    HealthStatus,
    CallingPattern,
    CallingPattern as CP,
    HealthResult,
    FailureObservability,
    CallResult,
    Last30DaysDep,
    AgentReachDep,
    PaperSearchMcpDep,
    _run_subprocess,
)


# ══════════════════════════════════════════════════════════════════════
# 注册表
# ══════════════════════════════════════════════════════════════════════

class TestRegistry:
    def test_singleton(self):
        r1 = DepRegistry.get()
        r2 = DepRegistry.get()
        assert r1 is r2

    def test_all_deps_registered(self):
        reg = DepRegistry.get()
        deps = reg.all
        assert "last30days_en" in deps
        assert "last30days_cn" in deps
        assert "agent_reach" in deps
        assert "paper_search_mcp" in deps

    def test_get_dep(self):
        reg = DepRegistry.get()
        dep = reg.get_dep("agent_reach")
        assert dep is not None
        assert dep.id == "agent_reach"
        assert dep.capability == "internet_access"

    def test_by_capability(self):
        reg = DepRegistry.get()
        recent = reg.by_capability("recent_web_search")
        assert len(recent) == 2
        ids = {d.id for d in recent}
        assert ids == {"last30days_en", "last30days_cn"}


# ══════════════════════════════════════════════════════════════════════
# 调用模式
# ══════════════════════════════════════════════════════════════════════

class TestCallingPatterns:
    def test_last30days_is_subprocess(self):
        reg = DepRegistry.get()
        for dep_id in ("last30days_en", "last30days_cn"):
            dep = reg.get_dep(dep_id)
            assert dep.calling_pattern == CP.SUBPROCESS

    def test_agent_reach_is_subprocess(self):
        dep = DepRegistry.get().get_dep("agent_reach")
        assert dep.calling_pattern == CP.SUBPROCESS

    def test_paper_search_mcp_is_http(self):
        dep = DepRegistry.get().get_dep("paper_search_mcp")
        assert dep.calling_pattern == CP.HTTP


# ══════════════════════════════════════════════════════════════════════
# Health / 可观测性
# ══════════════════════════════════════════════════════════════════════

class TestHealth:
    @pytest.mark.asyncio
    async def test_last30days_missing_returns_missing(self, monkeypatch):
        """当脚本不存在时，health 返回 MISSING。"""
        dep = Last30DaysDep(
            id="test_l30", env_var="TEST_L30_PATH",
            fallback_path="/nonexistent/path/test.py", locale="test",
        )
        monkeypatch.setattr(dep, "_fallback", "/nonexistent/path/test.py")
        result = await dep.health()
        assert result.status == HealthStatus.MISSING
        assert result.failure is not None
        assert result.failure.exit_code == -1

    def test_failure_observability_fields(self):
        """验证 OMP 修正 2：failure_observability 字段。"""
        fo = FailureObservability(
            exit_code=1, stderr="timeout", duration_ms=5000.0,
            provenance="/usr/bin/opencli",
        )
        assert fo.exit_code == 1
        assert fo.stderr == "timeout"
        assert fo.duration_ms == 5000.0
        assert fo.provenance == "/usr/bin/opencli"

    def test_health_result_defaults(self):
        hr = HealthResult(status=HealthStatus.OK)
        assert hr.version == ""
        assert hr.failure is None


# ══════════════════════════════════════════════════════════════════════
# Discover
# ══════════════════════════════════════════════════════════════════════

class TestDiscover:
    @pytest.mark.asyncio
    async def test_last30days_discovers_env_var(self, monkeypatch, tmp_path):
        """env var 覆盖默认路径。"""
        script = tmp_path / "last30days.py"
        script.write_text("#!/usr/bin/env python3\n")
        monkeypatch.setenv("TEST_L30_DISCOVER", str(script))

        dep = Last30DaysDep(
            id="test_l30", env_var="TEST_L30_DISCOVER",
            fallback_path="/fallback/path.py", locale="test",
        )
        path = await dep.discover()
        assert path == str(script)

    @pytest.mark.asyncio
    async def test_agent_reach_discovers_path(self, monkeypatch, tmp_path):
        """shutil.which 找到 opencli。"""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        opencli = bin_dir / "opencli"
        opencli.write_text("#!/bin/sh\necho 1.0\n")
        opencli.chmod(0o755)

        monkeypatch.setenv("PATH", str(bin_dir))
        dep = AgentReachDep()
        path = await dep.discover()
        assert path is not None
        assert "opencli" in path


# ══════════════════════════════════════════════════════════════════════
# CallResult
# ══════════════════════════════════════════════════════════════════════

class TestCallResult:
    def test_call_result_defaults(self):
        cr = CallResult(stdout="hello", stderr="", exit_code=0, duration_ms=100.0)
        assert cr.stdout == "hello"
        assert cr.exit_code == 0
        assert cr.duration_ms == 100.0

    def test_call_result_error(self):
        cr = CallResult(stdout="", stderr="not found", exit_code=-1, duration_ms=0)
        assert cr.exit_code == -1
        assert "not found" in cr.stderr
