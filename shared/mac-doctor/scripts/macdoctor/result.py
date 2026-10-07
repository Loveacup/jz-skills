"""Structured check findings and conservative subsystem scoring."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

STATUSES = ("pass", "warn", "crit", "unknown", "error", "skip")
CATEGORIES = ("performance", "storage", "security", "hardware", "network", "devenv")
_WORST = {"pass": 0, "skip": 1, "unknown": 2, "warn": 3, "error": 4, "crit": 5}


@dataclass(frozen=True)
class CheckResult:
    id: str
    category: str
    status: str
    title: str
    value: Any = None
    unit: str | None = None
    evidence: str = ""
    source: str = ""
    duration_ms: int = 0
    recommendation: str | None = None
    collected_at: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"invalid check status: {self.status}")
        if self.category not in CATEGORIES:
            raise ValueError(f"invalid check category: {self.category}")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if not result["collected_at"]:
            result["collected_at"] = datetime.now(timezone.utc).isoformat()
        return result


def worst_status(results: list[CheckResult]) -> str:
    return max((r.status for r in results), key=lambda status: _WORST[status], default="pass")


def score_results(results: list[CheckResult]) -> dict[str, float | None]:
    """Return three scoped scores and coverage; unavailable checks earn no points."""
    groups = {"security": {"security"}, "performance": {"performance", "hardware", "network", "devenv"}, "storage": {"storage"}}
    # Penalties mirror Mac Audit's severity weighting, with group-specific stakes.
    deductions = {
        "security": {"crit": 15, "warn": 4},
        "performance": {"crit": 10, "warn": 3},
        "storage": {"crit": 10, "warn": 3},
    }
    scores: dict[str, float] = {}
    for group, categories in groups.items():
        selected = [r for r in results if r.category in categories]
        if not selected:
            scores[group] = None  # not checked in this run; never report as 0
            continue
        earned = 0.0
        for result in selected:
            if result.status == "pass":
                earned += 100.0
            elif result.status in ("warn", "crit"):
                earned += max(0.0, 100.0 - deductions[group][result.status])
            # unknown/error/skip receive zero rather than being treated as pass.
        scores[group] = round(earned / len(selected), 1)
    known = sum(r.status in ("pass", "warn", "crit") for r in results)
    scores["coverage"] = round(100.0 * known / len(results), 1) if results else 0.0
    return scores
