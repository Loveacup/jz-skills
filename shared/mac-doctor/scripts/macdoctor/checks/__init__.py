"""Read-only macOS check modules."""
from __future__ import annotations

import re
import time
from typing import Any

from ..result import CheckResult
from ..runner import Command, redact


def command_text(command: Command, argv: list[str], timeout: float) -> tuple[int, str]:
    rc, stdout, stderr = command(argv, timeout)
    return rc, redact("\n".join(part for part in (stdout, stderr) if part))


def result(check_id: str, category: str, status: str, title: str, *, value: Any = None,
           unit: str | None = None, evidence: str = "", source: str = "", started: float | None = None,
           recommendation: str | None = None) -> CheckResult:
    elapsed = int((time.monotonic() - started) * 1000) if started is not None else 0
    return CheckResult(check_id, category, status, title, value, unit, redact(evidence)[:1000], source,
                       elapsed, recommendation)


def status_from_command(rc: int, text: str) -> str:
    return "pass" if rc == 0 and text.strip() else "unknown"


def number(text: str, pattern: str, cast=float) -> Any:
    match = re.search(pattern, text, re.I | re.M)
    return cast(match.group(1)) if match else None
