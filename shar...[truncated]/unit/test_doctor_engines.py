"""测试 7 个引擎的 health_check 实现。"""
import asyncio
import os
from unittest.mock import patch, MagicMock

import pytest
import httpx

from wrr.engines.exa import ExaEngine
from wrr.engines.brave import BraveEngine
from wrr.engines.github import GitHubEngine
from wrr.engines.skill_discovery import SkillDiscoveryEngine
from wrr.engines.academic import AcademicEngine
from wrr.engines.searxng import SearxngEngine
from wrr.engines.community import CommunityEngine
from wrr.schemas import EngineCheckResult


def run(coro):
    """同步运行协程。"""
    return asyncio.run(coro)


# ── Exa 引擎测试 ───────────────────────────────────────────────────
def test_exa_missing_key():
    """Exa: 缺少 API key → fail。"""
    with patch.dict(os.environ, {}, clear=True):
        result = run(ExaEngine().health_check())
    assert result.status == "fail"
    assert result.engine == "exa"
    assert result.tier == 1
    assert "EXA_API_KEY" in result.summary
    assert "env:EXA_API_KEY" in result.requirements
    assert len(result.repair) > 0
    assert result.evidence.get("env.EXA_API_KEY") == "missing"


def test_exa_key_present():
    """Exa: API key 存在 → ok。"""
    with patch.dict(os.environ, {"EXA_API_KEY": "fake_key"}):
        result = run(ExaEngine().health_check())
    assert result.status == "ok"
    assert result.engine == "exa"
    assert result.tier == 1
    assert result.active_backend == "exa-api"
    assert result.evidence.get("env.EXA_API_KEY") == "present"


# ── Brave 引擎测试 ─────────────────────────────────────────────────
def test_brave_missing_key():
    """Brave: 两个别名都缺失 → fail。"""
    with patch.dict(os.environ, {}, clear=True):
        result = run(BraveEngine().health_check())
    assert result.status == "fail"
    assert result.engine == "brave"
    assert "BRAVE_API_KEY" in result.summary
    assert "env:BRAVE_API_KEY" in result.requirements
    assert result.evidence.get("env.BRAVE_API_KEY") == "missing"
    assert result.evidence.get("env.BRAVE_SEARCH_API_KEY") == "missing"


def test_brave_primary_key():
    """Brave: 主 key 存在 → ok。"""
    with patch.dict(os.environ, {"BRAVE_API_KEY": "primary"}):
        result = run(BraveEngine().health_check())
    assert result.status == "ok"
    assert "BRAVE_API_KEY" in result.summary
    assert result.evidence.get("env.BRAVE_API_KEY") == "present"


def test_brave_fallback_key():
    """Brave: 备用 key 存在 → ok。"""
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "fallback"}, clear=True):
        result = run(BraveEngine().health_check())
    assert result.status == "ok"
    # 备用 key 逻辑在 health_check 中会检测出 BRAVE_API_KEY 缺失，因此走 fallback 分支
    assert "configured" in result.summary.lower()
    assert result.active_backend == "brave-api"


# ── GitHub 引擎测试 ────────────────────────────────────────────────
def test_github_missing_token():
    """GitHub: 缺少 token → fail。"""
    with patch.dict(os.environ, {}, clear=True):
        result = run(GitHubEngine().health_check())
    assert result.status == "fail"
    assert result.engine == "github"
    assert "GITHUB_TOKEN" in result.summary
    assert result.evidence.get("env.GITHUB_TOKEN") == "missing"


def test_github_token_present():
    """GitHub: token 存在 → ok。"""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
        result = run(GitHubEngine().health_check())
    assert result.status == "ok"
    assert result.active_backend == "github-api"
    assert result.evidence.get("env.GITHUB_TOKEN") == "present"


# ── Skill Discovery 引擎测试 ───────────────────────────────────────
def test_skill_missing_token():
    """Skill Discovery: 缺少 GITHUB_TOKEN → fail。"""
    with patch.dict(os.environ, {}, clear=True):
        result = run(SkillDiscoveryEngine().health_check())
    assert result.status == "fail"
    assert result.engine == "skill"
    assert "GITHUB_TOKEN" in result.summary
    assert "code search" in result.details.lower()
    assert result.evidence.get("env.GITHUB_TOKEN") == "missing"


def test_skill_token_present():
    """Skill Discovery: token + code search OK → ok；模拟 API 返回。"""
    async def mock_get(url, **kwargs):
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {"total_count": 42}
        return m

    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(SkillDiscoveryEngine().health_check())
    assert result.status == "ok"
    assert "code search" in result.summary.lower()
    assert result.evidence.get("env.GITHUB_TOKEN") == "present"
    assert "42" in result.evidence.get("code_search", "")


# ── Academic 引擎测试 ──────────────────────────────────────────────
def test_academic_always_ok():
    """Academic: 公开 API 可达 → ok；模拟 3 源全通。"""
    async def mock_get(url, **kwargs):
        m = MagicMock()
        m.status_code = 200
        return m

    with patch.dict(os.environ, {}, clear=True):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(AcademicEngine().health_check())
    assert result.status == "ok"
    assert result.engine == "academic"
    assert result.tier == 0
    assert "3/3" in result.summary
    assert "openalex" in result.active_backend


# ── SearXNG 引擎测试 ───────────────────────────────────────────────
def test_searxng_missing_url():
    """SearXNG: 缺少 SEARXNG_URL → fail。"""
    with patch.dict(os.environ, {}, clear=True):
        result = run(SearxngEngine().health_check())
    assert result.status == "fail"
    assert result.engine == "searxng"
    assert "SEARXNG_URL" in result.summary
    assert result.evidence.get("env.SEARXNG_URL") == "missing"


def test_searxng_endpoint_timeout():
    """SearXNG: endpoint 超时 → fail。"""
    async def mock_get(endpoint, **kwargs):
        raise httpx.TimeoutException("timeout")

    with patch.dict(os.environ, {"SEARXNG_URL": "http://127.0.0.1:32080"}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(SearxngEngine().health_check())
    assert result.status == "fail"
    assert "timeout" in result.summary.lower()
    assert result.evidence.get("error") == "timeout"


def test_searxng_endpoint_unreachable():
    """SearXNG: endpoint 连接失败 → fail。"""
    async def mock_get(endpoint, **kwargs):
        raise httpx.ConnectError("connection refused")

    with patch.dict(os.environ, {"SEARXNG_URL": "http://127.0.0.1:32080"}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(SearxngEngine().health_check())
    assert result.status == "fail"
    assert "unreachable" in result.summary.lower()
    assert result.evidence.get("error") == "ConnectError"


def test_searxng_endpoint_reachable():
    """SearXNG: endpoint 可达（2xx）→ ok。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    async def mock_get(endpoint, **kwargs):
        return mock_resp

    with patch.dict(os.environ, {"SEARXNG_URL": "http://127.0.0.1:32080"}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(SearxngEngine().health_check())
    assert result.status == "ok"
    assert "reachable" in result.summary.lower()
    assert result.evidence.get("status_code") == 200


def test_searxng_endpoint_server_error():
    """SearXNG: endpoint 返回 5xx → fail。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 503

    async def mock_get(endpoint, **kwargs):
        return mock_resp

    with patch.dict(os.environ, {"SEARXNG_URL": "http://127.0.0.1:32080"}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(SearxngEngine().health_check())
    assert result.status == "fail"
    assert "503" in result.summary
    assert result.evidence.get("status_code") == 503


def test_searxng_endpoint_client_error():
    """SearXNG: endpoint 返回 4xx → warn。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    async def mock_get(endpoint, **kwargs):
        return mock_resp

    with patch.dict(os.environ, {"SEARXNG_URL": "http://127.0.0.1:32080"}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = run(SearxngEngine().health_check())
    assert result.status == "warn"
    assert "404" in result.summary
    assert result.evidence.get("status_code") == 404


# ── Community 引擎测试 ─────────────────────────────────────────────
def test_community_opencli_missing():
    """Community: opencli 命令不存在 → fail。"""
    with patch("shutil.which", return_value=None):
        result = run(CommunityEngine().health_check())
    assert result.status == "fail"
    assert result.engine == "community"
    assert "opencli" in result.summary.lower()
    assert result.evidence.get("command.opencli") == "missing"


def test_community_opencli_present():
    """Community: opencli 可用 → ok。"""
    with patch("shutil.which", return_value="/usr/local/bin/opencli"):
        with patch.dict(os.environ, {"COMMUNITY_INCLUDE_LAST30DAYS": "False"}):
            result = run(CommunityEngine().health_check())
    assert result.status == "ok"
    assert "opencli available" in result.summary
    assert result.active_backend == "opencli"
    assert "/opencli" in result.evidence.get("command.opencli", "")


def test_community_last30days_missing_warn():
    """Community: opencli OK，但 last30days 脚本缺失（启用时）→ warn。"""
    with patch("shutil.which", return_value="/usr/local/bin/opencli"):
        with patch("os.path.exists", return_value=False):
            with patch.dict(os.environ, {"COMMUNITY_INCLUDE_LAST30DAYS": "True"}):
                # 需要导入 config 后设置
                from wrr import config
                original = config.COMMUNITY_INCLUDE_LAST30DAYS
                try:
                    config.COMMUNITY_INCLUDE_LAST30DAYS = True
                    result = run(CommunityEngine().health_check())
                finally:
                    config.COMMUNITY_INCLUDE_LAST30DAYS = original

    assert result.status == "warn"
    assert "last30days" in result.summary.lower()
    assert "not found" in result.details.lower()


def test_community_deep_probe_ok():
    """Community deep=True: opencli --version 成功 → ok。"""
    from wrr.engines._probe import CommandProbeResult

    async def mock_probe_command(cmd, args, timeout):
        return CommandProbeResult(
            command=cmd,
            status="ok",
            path="/usr/local/bin/opencli",
            exit_code=0,
            stdout="opencli version 1.0.0\n",
        )

    with patch("shutil.which", return_value="/usr/local/bin/opencli"):
        with patch("wrr.engines._probe.probe_command", side_effect=mock_probe_command):
            result = run(CommunityEngine().health_check(deep=True))

    assert result.status == "ok"
    assert "opencli available" in result.summary


def test_community_deep_probe_timeout():
    """Community deep=True: opencli --version 超时 → fail。"""
    from wrr.engines._probe import CommandProbeResult

    async def mock_probe_command(cmd, args, timeout):
        return CommandProbeResult(
            command=cmd,
            status="timeout",
            path="/usr/local/bin/opencli",
            error="Command timed out after 3.0s",
        )

    with patch("shutil.which", return_value="/usr/local/bin/opencli"):
        with patch("wrr.engines._probe.probe_command", side_effect=mock_probe_command):
            result = run(CommunityEngine().health_check(deep=True))

    assert result.status == "fail"
    assert "timeout" in result.summary.lower()
    assert result.evidence.get("probe") == "timeout"


def test_community_deep_probe_broken():
    """Community deep=True: opencli --version 非零退出 → fail。"""
    from wrr.engines._probe import CommandProbeResult

    async def mock_probe_command(cmd, args, timeout):
        return CommandProbeResult(
            command=cmd,
            status="broken",
            path="/usr/local/bin/opencli",
            exit_code=127,
            error="Command exited with code 127",
        )

    with patch("shutil.which", return_value="/usr/local/bin/opencli"):
        with patch("wrr.engines._probe.probe_command", side_effect=mock_probe_command):
            result = run(CommunityEngine().health_check(deep=True))

    assert result.status == "fail"
    assert "broken" in result.summary.lower()
    assert result.evidence.get("exit_code") == 127
