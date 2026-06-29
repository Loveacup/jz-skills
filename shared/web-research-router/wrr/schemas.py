"""WRR 统一 dataclass：Search / Extract / Similar 的 options/result + 路由结构。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time as _time

from . import config


# ── Search ───────────────────────────────────────────────────────────
@dataclass
class SearchOptions:
    query: str
    count: int = config.DEFAULT_SEARCH_COUNT
    provider: Optional[str] = None   # 显式 provider → 禁用 fallback
    mode: Optional[str] = None       # 显式 mode → 禁用自动路由（exa: fast/auto/deep-lite/deep）


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    highlights: List[str] = field(default_factory=list)   # citation 源片段（Exa）
    source_tag: str = ""                                  # 来源标签（如 community: reddit/twitter）
    # ── v5.3 时效感知 ──
    source_ts: float = 0.0                                # 数据源时间戳（unix timestamp，0=未知）
    freshness_score: float = 0.5                           # 时效分 (0.0-1.0)，0.5=未知

    @property
    def age_days(self) -> Optional[float]:
        """距今天数（None=未知）。"""
        if self.source_ts <= 0:
            return None
        return (_time.time() - self.source_ts) / 86400.0

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "highlights": self.highlights,
            "source_tag": self.source_tag,
        }
        if self.source_ts > 0:
            d["source_ts"] = self.source_ts
            d["freshness_score"] = round(self.freshness_score, 3)
        return d


# ── Extract（web_fetch）──────────────────────────────────────────────
@dataclass
class ExtractOptions:
    url: str
    max_characters: int = config.DEFAULT_MAX_CHARACTERS
    provider: Optional[str] = None


@dataclass
class ExtractResult:
    url: str
    text: str
    highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"url": self.url, "text": self.text, "highlights": self.highlights}


# ── Similar（findSimilar）────────────────────────────────────────────
@dataclass
class SimilarOptions:
    url: str
    count: int = config.DEFAULT_SEARCH_COUNT
    provider: Optional[str] = None


# ── 路由公共结构 ─────────────────────────────────────────────────────
@dataclass
class FallbackStep:
    provider: str
    ok: bool
    count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"provider": self.provider, "ok": self.ok,
                "count": self.count, "error": self.error}


@dataclass
class RouterResult:
    """路由结果。payload 为引擎返回（List[SearchResult] 或 ExtractResult）。"""
    actual_provider: str
    payload: Any
    fallback_chain: List[FallbackStep] = field(default_factory=list)
    # v5.0：mode 路由 + RRF 融合诊断（加法式，v4 路径留空）
    mode: Optional[str] = None
    fusion_method: Optional[str] = None
    weights: Optional[Dict[str, Any]] = None

    @property
    def degraded_from(self) -> Optional[str]:
        """若发生降级，返回原计划的首选 provider（fallback_chain 第一个失败项）。"""
        for step in self.fallback_chain:
            if not step.ok:
                return step.provider
        return None


# ── Doctor ───────────────────────────────────────────────────────────
@dataclass
class EngineCheckResult:
    """单个引擎的健康检查结果。"""
    engine: str
    status: str  # ok | warn | fail | skip
    tier: int
    summary: str
    details: Optional[str] = None
    active_backend: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    repair: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """是否通过检查（ok/skip 视为通过）。"""
        return self.status in ("ok", "skip")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "status": self.status,
            "tier": self.tier,
            "summary": self.summary,
            "details": self.details,
            "active_backend": self.active_backend,
            "requirements": self.requirements,
            "repair": self.repair,
            "evidence": self.evidence,
        }
