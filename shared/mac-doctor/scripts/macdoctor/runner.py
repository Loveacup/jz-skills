"""Bounded command execution and isolated, ordered check registry."""
from __future__ import annotations

import concurrent.futures
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable

from .result import CheckResult

Command = Callable[[list[str], float], tuple[int, str, str]]


class CommandTimeout(Exception):
    """Structured failure when a command exceeds its per-command deadline."""

    def __init__(self, message: str, *, cmd: list[str] | None = None, timeout: float | None = None):
        super().__init__(message)
        self.cmd = tuple(cmd) if cmd is not None else None
        self.timeout = timeout

    def to_dict(self) -> dict[str, object]:
        return {"error": "timeout", "command": self.cmd, "timeout": self.timeout, "message": str(self)}

class CommandError(Exception):
    """A command could not be launched."""


def run(cmd: list[str], timeout: float = 10) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise CommandTimeout(f"command timed out after {timeout:g}s: {cmd[0]}", cmd=cmd, timeout=timeout) from exc
    except OSError as exc:
        raise CommandError(f"cannot run {cmd[0]}: {exc}") from exc
    return completed.returncode, completed.stdout, completed.stderr


@dataclass(frozen=True)
class CheckSpec:
    id: str
    category: str
    title: str
    function: Callable[[Command, float], CheckResult]

_REGISTRY: list[CheckSpec] = []


def check(id: str, category: str, title: str):
    def decorate(function: Callable[[Command, float], CheckResult]):
        _REGISTRY.append(CheckSpec(id, category, title, function))
        return function
    return decorate


def registry() -> tuple[CheckSpec, ...]:
    return tuple(_REGISTRY)


def redact(text: str) -> str:
    """Remove common credential-like command-line values before evidence output."""
    patterns = (
        (r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]"),
        (r"(?i)(-e\s+)([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)=\S+", r"\1\2=[REDACTED]"),
        (r"(?i)(\b(?:token|api[_-]?key|secret|password|passwd)\b\s*[=:]\s*)([^\s,;]+)", r"\1[REDACTED]"),
        (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "[REDACTED]"),
        (r"\bsk-[A-Za-z0-9_-]{16,}\b", "[REDACTED]"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def _load_checks() -> None:
    # Importing modules registers them; failures surface as internal errors.
    from .checks import devenv, hardware, network, performance, security, storage  # noqa: F401


def execute(*, categories: set[str] | None = None, ids: set[str] | None = None,
            timeout: float = 10, command: Command = run, parallel: bool = False) -> list[CheckResult]:
    _load_checks()
    specs = [spec for spec in registry()
             if (categories is None or spec.category in categories)
             and (ids is None or spec.id in ids)]

    def invoke(spec: CheckSpec) -> CheckResult:
        started = time.monotonic()
        if sys.platform != "darwin":
            return CheckResult(spec.id, spec.category, "skip", spec.title,
                               evidence="macOS only", source="platform gate",
                               duration_ms=0, recommendation=None)
        try:
            result = spec.function(command, timeout)
            return result
        except CommandTimeout as exc:
            return CheckResult(spec.id, spec.category, "unknown", spec.title,
                               evidence=redact(str(exc))[:1000], source="command timeout",
                               duration_ms=int((time.monotonic() - started) * 1000))
        except Exception as exc:
            return CheckResult(spec.id, spec.category, "error", spec.title,
                               evidence=redact(f"{type(exc).__name__}: {exc}")[:1000], source="check execution",
                               duration_ms=int((time.monotonic() - started) * 1000))

    if parallel and len(specs) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(specs))) as pool:
            return list(pool.map(invoke, specs))
    return [invoke(spec) for spec in specs]
