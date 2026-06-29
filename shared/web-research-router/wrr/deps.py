"""外部依赖控制面（v5.5）。

设计约束：
- calling_pattern 枚举区分 subprocess / http / mcp 三种调用模式（OMP 修正 1）
- failure_observability 子结构捕获 {exit_code, stderr, duration_ms}（OMP 修正 2）
- 从 ENGINE_REQUIREMENTS.external_repos 派生，不新建配置源（OMP 修正 3）
- 引擎透过能力适配器调用，不直接接触路径/URL（Codex 建议）
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════
# 核心类型
# ══════════════════════════════════════════════════════════════════════

class CallingPattern(str, Enum):
    SUBPROCESS = "subprocess"
    HTTP = "http"
    MCP = "mcp"


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    MISSING = "missing"


@dataclass
class FailureObservability:
    """故障可观测性（OMP 修正 2）。"""
    exit_code: Optional[int] = None
    stderr: str = ""
    duration_ms: float = 0.0
    provenance: str = ""   # 最后一次尝试的路径/URL/命令


@dataclass
class HealthResult:
    status: HealthStatus
    version: str = ""
    detail: str = ""
    failure: Optional[FailureObservability] = None


@dataclass
class CallResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


# ══════════════════════════════════════════════════════════════════════
# 基类
# ══════════════════════════════════════════════════════════════════════

class ExternalDep:
    """外部依赖基类。每个具体实现覆盖 discover / health / call。"""

    id: str
    capability: str           # 能力名（如 recent_web_search），非仓库名
    calling_pattern: CallingPattern
    source_url: str
    description: str = ""

    def __init__(self) -> None:
        self._cached_path: Optional[str] = None

    # ── 发现 ──
    async def discover(self) -> Optional[str]:
        """返回安装路径或 URL，未安装返回 None。"""
        raise NotImplementedError

    # ── 健康 ──
    async def health(self, deep: bool = False) -> HealthResult:
        """检查依赖自身是否健康。"""
        raise NotImplementedError

    # ── 版本 ──
    async def version(self) -> str:
        """返回当前版本 / commit hash。"""
        return "unknown"

    # ── 调用 ──
    async def call(self, query: str, **kwargs) -> CallResult:
        """统一调用入口。"""
        raise NotImplementedError

    # ── 引导 ──
    @property
    def bootstrap_steps(self) -> List[str]:
        """安装此依赖需要的命令列表。"""
        return []


# ══════════════════════════════════════════════════════════════════════
# Subprocess 工具函数
# ══════════════════════════════════════════════════════════════════════

async def _run_subprocess(
    cli: List[str], timeout: float = 30.0, inject_local_bin: bool = True
) -> Tuple[int, str, str, float]:
    """执行子进程，返回 (exit_code, stdout, stderr, duration_ms)。

    对齐 _local_utils.run_command 标准：同时捕获 stdout + stderr。
    可选注入 ~/.local/bin 到 PATH（Agent-Reach / OpenCLI 需要）。
    """
    env = os.environ.copy()
    if inject_local_bin:
        local_bin = os.path.expanduser("~/.local/bin")
        parts = env.get("PATH", "").split(os.pathsep)
        if local_bin not in parts:
            env["PATH"] = os.pathsep.join([local_bin] + parts)

    t0 = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cli,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except (FileNotFoundError, OSError) as e:
        return (-1, "", str(e), (time.monotonic() - t0) * 1000)

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
        return (-1, "", "timeout", (time.monotonic() - t0) * 1000)

    duration = (time.monotonic() - t0) * 1000
    return (
        proc.returncode or 0,
        (stdout or b"").decode("utf-8", "replace"),
        (stderr or b"").decode("utf-8", "replace"),
        duration,
    )


# ══════════════════════════════════════════════════════════════════════
# 具体实现
# ══════════════════════════════════════════════════════════════════════

class Last30DaysDep(ExternalDep):
    """last30days CLI 脚本依赖（subprocess）。"""

    calling_pattern = CallingPattern.SUBPROCESS

    def __init__(self, id: str, env_var: str, fallback_path: str, locale: str) -> None:
        super().__init__()
        self.id = id
        self.capability = "recent_web_search"
        self.source_url = {
            "last30days_en": "https://github.com/mvanhorn/last30days-skill",
            "last30days_cn": "https://github.com/Jesseovo/last30days-skill-cn",
        }.get(id, "")
        self.description = f"last30days {locale} 脚本"
        self._env_var = env_var
        self._fallback = os.path.expanduser(fallback_path)
        self._locale = locale

    async def discover(self) -> Optional[str]:
        path = os.environ.get(self._env_var) or self._fallback
        if os.path.exists(path):
            self._cached_path = path
            return path
        return None

    async def health(self, deep: bool = False) -> HealthResult:
        path = await self.discover()
        if not path:
            return HealthResult(
                status=HealthStatus.MISSING,
                detail=f"{self.id}: script not found at {self._fallback}",
                failure=FailureObservability(
                    exit_code=-1,
                    stderr="path not found",
                    provenance=self._fallback,
                ),
            )
        if deep:
            rc, stdout, stderr, dur = await _run_subprocess(
                ["python3", path, "--help"], timeout=5.0
            )
            if rc != 0:
                return HealthResult(
                    status=HealthStatus.DEGRADED,
                    detail=f"{self.id}: --help returned {rc}",
                    failure=FailureObservability(
                        exit_code=rc, stderr=stderr, duration_ms=dur, provenance=path
                    ),
                )
        return HealthResult(
            status=HealthStatus.OK,
            version=await self.version(),
            detail=f"{self.id}: OK ({path})",
        )

    async def version(self) -> str:
        path = await self.discover()
        if not path:
            return "unknown"
        # 尝试从脚本文件 mtime 推断版本
        try:
            mtime = os.path.getmtime(path)
            import datetime
            return datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except OSError:
            return "unknown"

    async def call(self, query: str, **kwargs) -> CallResult:
        path = await self.discover()
        if not path:
            return CallResult(
                stdout="", stderr=f"{self.id}: not found", exit_code=-1, duration_ms=0
            )
        quick = kwargs.get("quick", True)
        cli = ["python3", path]
        if quick:
            cli.append("--quick")
        cli.append(query)
        rc, stdout, stderr, dur = await _run_subprocess(
            cli, timeout=kwargs.get("timeout", 30.0), inject_local_bin=False
        )
        return CallResult(stdout=stdout, stderr=stderr, exit_code=rc, duration_ms=dur)

    @property
    def bootstrap_steps(self) -> List[str]:
        repo = self.source_url
        return [
            f"git clone {repo}",
            f"# 然后设置 export {self._env_var}=<path_to_script>",
        ]


class AgentReachDep(ExternalDep):
    """Agent-Reach / OpenCLI 依赖（subprocess）。"""

    id = "agent_reach"
    capability = "internet_access"
    calling_pattern = CallingPattern.SUBPROCESS
    source_url = "https://github.com/Panniantong/Agent-Reach"
    description = "Agent-Reach OpenCLI（社区搜索底层渠道）"

    async def discover(self) -> Optional[str]:
        candidates = [
            os.path.expanduser("~/.local/bin/opencli"),
            "/usr/local/bin/opencli",
        ]
        env_path = os.environ.get("OPENCLI_PATH")
        if env_path:
            candidates.insert(0, env_path)
        for p in candidates:
            if os.path.exists(p):
                self._cached_path = p
                return p
        # PATH 搜索
        import shutil
        found = shutil.which("opencli")
        if found:
            self._cached_path = found
            return found
        return None

    async def health(self, deep: bool = False) -> HealthResult:
        path = await self.discover()
        if not path:
            return HealthResult(
                status=HealthStatus.MISSING,
                detail="opencli not found in PATH or ~/.local/bin",
                failure=FailureObservability(
                    exit_code=-1,
                    stderr="opencli not found",
                    provenance="PATH search",
                ),
            )
        if deep:
            rc, stdout, stderr, dur = await _run_subprocess(
                [path, "--version"], timeout=5.0
            )
            if rc != 0:
                return HealthResult(
                    status=HealthStatus.DEGRADED,
                    detail=f"opencli --version returned {rc}",
                    failure=FailureObservability(
                        exit_code=rc, stderr=stderr, duration_ms=dur, provenance=path
                    ),
                )
        return HealthResult(
            status=HealthStatus.OK,
            version=await self.version(),
            detail=f"opencli OK ({path})",
        )

    async def version(self) -> str:
        path = await self.discover()
        if not path:
            return "unknown"
        rc, stdout, stderr, dur = await _run_subprocess(
            [path, "--version"], timeout=5.0
        )
        return stdout.strip() if rc == 0 else "unknown"

    async def call(self, query: str, **kwargs) -> CallResult:
        """注意：opencli 不走常规 query 调用，社区引擎直接调。这里只做 health/version。"""
        path = await self.discover()
        if not path:
            return CallResult(
                stdout="", stderr="opencli: not found", exit_code=-1, duration_ms=0
            )
        rc, stdout, stderr, dur = await _run_subprocess(
            [path, "search", query], timeout=kwargs.get("timeout", 30.0)
        )
        return CallResult(stdout=stdout, stderr=stderr, exit_code=rc, duration_ms=dur)

    @property
    def bootstrap_steps(self) -> List[str]:
        return [
            "git clone https://github.com/Panniantong/Agent-Reach",
            "cd Agent-Reach && pip install -e .",
            "# 确保 ~/.local/bin 在 PATH 中",
        ]


class PaperSearchMcpDep(ExternalDep):
    """Paper Search MCP 依赖（HTTP）。"""

    id = "paper_search_mcp"
    capability = "academic_search"
    calling_pattern = CallingPattern.HTTP
    source_url = "https://github.com/openags/paper-search-mcp"
    description = "paper-search-mcp 学术搜索 MCP 服务"

    def __init__(self) -> None:
        super().__init__()
        import urllib.parse
        self._base_url = os.environ.get(
            "PAPER_SEARCH_MCP_URL",
            "http://localhost:8080"
        ).rstrip("/")
        # 确保 URL 有效
        if self._base_url and not self._base_url.startswith("http"):
            self._base_url = "http://" + self._base_url

    async def discover(self) -> Optional[str]:
        return self._base_url

    async def health(self, deep: bool = False) -> HealthResult:
        url = f"{self._base_url}/health"
        import urllib.request
        import urllib.error
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=5.0)
            dur = (time.monotonic() - t0) * 1000
            return HealthResult(
                status=HealthStatus.OK,
                version=await self.version(),
                detail=f"paper-search-mcp OK ({url})",
            )
        except (urllib.error.URLError, OSError) as e:
            dur = (time.monotonic() - t0) * 1000
            return HealthResult(
                status=HealthStatus.MISSING,
                detail=f"paper-search-mcp unreachable: {e}",
                failure=FailureObservability(
                    exit_code=-1,
                    stderr=str(e),
                    duration_ms=dur,
                    provenance=url,
                ),
            )

    async def version(self) -> str:
        url = f"{self._base_url}/version"
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.read().decode("utf-8", "replace").strip()
        except Exception:
            return "unknown"

    async def call(self, query: str, **kwargs) -> CallResult:
        """通过 MCP HTTP 端点调用搜索。"""
        import json
        import urllib.request
        import urllib.error
        url = f"{self._base_url}/search"
        data = json.dumps({"query": query, "limit": kwargs.get("limit", 5)}).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 15.0)) as resp:
                body = resp.read().decode("utf-8", "replace")
                dur = (time.monotonic() - t0) * 1000
                return CallResult(stdout=body, stderr="", exit_code=0, duration_ms=dur)
        except Exception as e:
            dur = (time.monotonic() - t0) * 1000
            return CallResult(
                stdout="", stderr=str(e), exit_code=-1, duration_ms=dur
            )

    @property
    def bootstrap_steps(self) -> List[str]:
        return [
            "git clone https://github.com/openags/paper-search-mcp",
            "cd paper-search-mcp && pip install -e .",
            "# 启动服务: python -m paper_search_mcp",
            "# 或设置 PAPER_SEARCH_MCP_URL=http://localhost:8080",
        ]


# ══════════════════════════════════════════════════════════════════════
# 注册表（单一事实源）
# ══════════════════════════════════════════════════════════════════════

class DepRegistry:
    """从 ENGINE_REQUIREMENTS.external_repos 派生的依赖注册表。"""

    _instance: Optional[DepRegistry] = None

    def __init__(self) -> None:
        self._deps: Dict[str, ExternalDep] = {}

    @classmethod
    def get(cls) -> DepRegistry:
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """延迟导入避免循环依赖。"""
        from wrr.requirements import ENGINE_REQUIREMENTS

        # last30days_en
        self._deps["last30days_en"] = Last30DaysDep(
            id="last30days_en",
            env_var="WRR_LAST30DAYS_EN",
            fallback_path="~/code/last30days-skill/skills/last30days/scripts/last30days.py",
            locale="en",
        )

        # last30days_cn
        self._deps["last30days_cn"] = Last30DaysDep(
            id="last30days_cn",
            env_var="WRR_LAST30DAYS_CN",
            fallback_path="~/code/last30days-skill-cn/skills/last30days/scripts/last30days.py",
            locale="cn",
        )

        # agent_reach
        self._deps["agent_reach"] = AgentReachDep()

        # paper_search_mcp
        self._deps["paper_search_mcp"] = PaperSearchMcpDep()

    @property
    def all(self) -> Dict[str, ExternalDep]:
        return self._deps

    def get_dep(self, dep_id: str) -> Optional[ExternalDep]:
        return self._deps.get(dep_id)

    def by_capability(self, capability: str) -> List[ExternalDep]:
        return [d for d in self._deps.values() if d.capability == capability]
