"""跨源融合共享层（v5.0）。community + academic + router 共用，避免各引擎自造评分语义。

提供：
  - rrf_fuse        跨源 Reciprocal Rank Fusion（k=60，Cormack 2009），天然奖励多源一致性。
  - recency_decay   连续时间衰减 1/(1+age/τ)^p，替代 24h/7d/30d 阶梯断崖。
  - canonical_url   URL 规范化（剥 utm_*/fbclid、统一 host、去尾斜杠）——去重第一闸。
  - wilson_lower_bound  赞踩比置信下界（Reddit confidence sort），小样本质量信号更稳。
  - percentile_rank 分位数秩（替 z-score 做源内归一，有界抗长尾）。
  - dedup_cluster   去重聚类：URL canonical → 标题 Jaccard，产出代表条目。

研究依据见 /tmp/wrr-research-report.md §2 与 STDD §6。纯函数，零网络，单测可直接调用。
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from ..schemas import SearchResult

RRF_K_DEFAULT = 60

# 追踪类 query 参数（去重时剥离）。前缀匹配 utm_*，精确匹配其余。
_TRACKING_EXACT = {"fbclid", "gclid", "ref", "ref_src", "ref_url", "spm",
                   "from", "source", "mc_cid", "mc_eid", "igshid", "_hsenc"}
_TRACKING_PREFIX = ("utm_",)


# ── URL 规范化 ───────────────────────────────────────────────────────
def canonical_url(url: str) -> str:
    """规范化 URL：小写 scheme/host、剥追踪参数、去末尾斜杠、去 fragment。

    保留有意义的 query（如 ?id=1），仅剥已知追踪参数，避免过度合并。
    """
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    scheme = (parts.scheme or "https").lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parts.port:
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not _is_tracking(k)]
    kept.sort()
    query = urlencode(kept)
    return urlunsplit((scheme, host, path, query, ""))


def _is_tracking(key: str) -> bool:
    k = key.lower()
    return k in _TRACKING_EXACT or any(k.startswith(p) for p in _TRACKING_PREFIX)


# ── 连续时间衰减 ─────────────────────────────────────────────────────
def recency_decay(age_hours: float, tau: float, p: float = 1.5) -> float:
    """连续衰减 1/(1+age/τ)^p。age 0 → 1.0；单调递减、恒正、无断崖。

    τ = 半衰期尺度（小时），按平台调（twitter/reddit 12、v2ex/hn 48、知乎 720）。
    """
    if age_hours is None or age_hours < 0:
        return 0.5                              # 未知时间 → 中性
    if tau <= 0:
        tau = 1.0
    return 1.0 / (1.0 + age_hours / tau) ** p


# ── Wilson 置信下界 ──────────────────────────────────────────────────
def wilson_lower_bound(pos: int, n: int, z: float = 1.96) -> float:
    """赞踩比 Wilson 95% 置信下界（Reddit confidence sort）。兼顾比例与样本量。"""
    if n <= 0:
        return 0.0
    phat = pos / n
    z2 = z * z
    return ((phat + z2 / (2 * n) - z * math.sqrt((phat * (1 - phat) + z2 / (4 * n)) / n))
            / (1 + z2 / n))


# ── 分位数秩 ─────────────────────────────────────────────────────────
def percentile_rank(value: float, dist: Sequence[float]) -> float:
    """value 在 dist 中的分位（0~1）。有界、抗长尾离群；空分布返回 0.0。"""
    if not dist:
        return 0.0
    n = len(dist)
    if n == 1:
        return 1.0 if value >= dist[0] else 0.0
    below = sum(1 for x in dist if x < value)
    # 严格小于计数归一到 [0,1]：最小值→0.0，最大值→1.0
    return min(1.0, max(0.0, below / (n - 1)))


# ── RRF 跨源融合 ─────────────────────────────────────────────────────
def rrf_fuse(per_source: Dict[str, List[SearchResult]],
             k: int = RRF_K_DEFAULT,
             weights: Optional[Dict[str, float]] = None,
             recency_mult: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """跨源 Reciprocal Rank Fusion。

    RRF(d) = Σ_s  w_s · recency_mult_s(d) / (k + rank_s(d))

    - per_source: {source_name: [SearchResult 已按源内秩降序]}
    - weights:    {source_name: 融合权重}，缺省 1.0
    - recency_mult: 可选 {url: 乘子}，补回 RRF 丢失的绝对新鲜度
    返回 [{"doc": SearchResult, "rrf": float, "sources": set}]，按 rrf 降序。
    去重键 = canonical_url，跨源同 URL 合并秩贡献。
    """
    weights = weights or {}
    recency_mult = recency_mult or {}
    bucket: Dict[str, Dict[str, Any]] = {}
    for source, items in per_source.items():
        w = weights.get(source, 1.0)

        # v5.3: 本地引擎结果乘新鲜度衰减因子
        is_local = source.startswith("local_")
        local_mult = 1.0
        for doc in items:
            if is_local and doc.freshness_score < 1.0:
                local_mult = doc.freshness_score
                break

        for rank, doc in enumerate(items, start=1):
            key = canonical_url(doc.url) or f"{source}:{doc.title}"
            slot = bucket.setdefault(key, {"doc": doc, "rrf": 0.0, "sources": set()})
            mult = recency_mult.get(doc.url, 1.0)
            slot["rrf"] += w * mult * local_mult / (k + rank)
            slot["sources"].add(source)
            # 代表条目：取已有快照或更靠前者（首见即代表，已是源内最高秩）
    return sorted(bucket.values(), key=lambda s: s["rrf"], reverse=True)


# ── 去重聚类 ─────────────────────────────────────────────────────────
def _title_tokens(title: str) -> set:
    return set(re.findall(r"\w+", (title or "").lower()))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup_cluster(docs: List[SearchResult],
                  jaccard_threshold: float = 0.80) -> List[SearchResult]:
    """去重聚类：① canonical_url 相等 ② 标题 Jaccard > 阈值。保留先到者为代表。

    输入应已按分数降序，先到者即簇代表。返回去重后的 SearchResult 列表。
    """
    out: List[SearchResult] = []
    seen_urls: set = set()
    seen_tokens: List[set] = []
    for d in docs:
        cu = canonical_url(d.url)
        if cu and cu in seen_urls:
            continue
        toks = _title_tokens(d.title)
        if any(_jaccard(toks, t) > jaccard_threshold for t in seen_tokens):
            continue
        if cu:
            seen_urls.add(cu)
        seen_tokens.append(toks)
        out.append(d)
    return out
