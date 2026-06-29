"""_fusion.py 单测（RED-first）：RRF / canonical_url / 连续衰减 / Wilson / 分位数 / 去重聚类。

纯函数，零网络。手算 fixture 锁定 RRF 数学与 URL 归一行为。
"""
import math

from wrr.engines import _fusion as fz
from wrr.schemas import SearchResult


# ── RRF ──────────────────────────────────────────────────────────────
def test_rrf_matches_hand_calc():
    # 两源，k=60。doc A 在 s1 排1、s2 排1；doc B 仅 s1 排2。
    per_source = {
        "s1": [SearchResult(title="A", url="https://a"), SearchResult(title="B", url="https://b")],
        "s2": [SearchResult(title="A", url="https://a")],
    }
    fused = fz.rrf_fuse(per_source, k=60, weights={"s1": 1.0, "s2": 1.0})
    # A: 1/(60+1) + 1/(60+1) = 0.032786...; B: 1/(60+2) = 0.016129...
    by_url = {f["doc"].url: f for f in fused}
    assert abs(by_url["https://a"]["rrf"] - (1/61 + 1/61)) < 1e-9
    assert abs(by_url["https://b"]["rrf"] - (1/62)) < 1e-9


def test_rrf_multi_source_outranks_single():
    per_source = {
        "s1": [SearchResult(title="solo", url="https://solo"),
               SearchResult(title="both", url="https://both")],
        "s2": [SearchResult(title="both", url="https://both")],
    }
    fused = fz.rrf_fuse(per_source, k=60, weights={"s1": 1.0, "s2": 1.0})
    # 多源命中 both 应排在仅单源的 solo 之前，尽管 solo 在 s1 排名更高
    assert fused[0]["doc"].url == "https://both"
    assert len(fused[0]["sources"]) == 2


def test_rrf_weights_applied():
    per_source = {
        "hi": [SearchResult(title="x", url="https://x")],
        "lo": [SearchResult(title="y", url="https://y")],
    }
    fused = fz.rrf_fuse(per_source, k=60, weights={"hi": 2.0, "lo": 0.5})
    by_url = {f["doc"].url: f["rrf"] for f in fused}
    assert by_url["https://x"] > by_url["https://y"]   # 权重高的胜出


# ── canonical_url ────────────────────────────────────────────────────
def test_canonical_url_strips_tracking():
    base = fz.canonical_url("https://example.com/post")
    assert fz.canonical_url("https://example.com/post?utm_source=x&utm_medium=y") == base
    assert fz.canonical_url("https://example.com/post?fbclid=abc") == base
    assert fz.canonical_url("https://example.com/post/") == base
    assert fz.canonical_url("HTTPS://Example.com/post") == base


def test_canonical_url_keeps_meaningful_query():
    # 非追踪参数应保留（避免过度合并）
    a = fz.canonical_url("https://x.com/a?id=1")
    b = fz.canonical_url("https://x.com/a?id=2")
    assert a != b


# ── 连续时间衰减 ─────────────────────────────────────────────────────
def test_recency_decay_monotonic_continuous():
    tau = 12.0
    prev = fz.recency_decay(0, tau)
    assert prev == 1.0                         # age 0 → 1.0
    for age in range(1, 200):
        cur = fz.recency_decay(age, tau)
        assert cur > 0.0                       # 恒正
        assert cur < prev                      # 严格单调递减
        assert prev - cur < 0.2                # 相邻差分有界（无断崖）
        prev = cur


# ── Wilson 置信下界 ──────────────────────────────────────────────────
def test_wilson_lower_bound():
    assert fz.wilson_lower_bound(0, 0) == 0.0
    # 全样本：10/10 的下界 < 1（保守），但 > 1/1 的下界（样本量更大更自信）
    lb_10 = fz.wilson_lower_bound(10, 10)
    lb_1 = fz.wilson_lower_bound(1, 1)
    assert 0 < lb_1 < lb_10 < 1.0
    # 40 赞 20 踩(p=0.667) 下界 应 > 10 赞 5 踩? 样本更大 → 更自信
    assert fz.wilson_lower_bound(40, 60) > fz.wilson_lower_bound(4, 6)


# ── 分位数秩 ─────────────────────────────────────────────────────────
def test_percentile_rank():
    dist = [10, 20, 30, 40]
    assert fz.percentile_rank(10, dist) == 0.0        # 最小
    assert fz.percentile_rank(40, dist) == 1.0        # 最大
    assert 0.0 < fz.percentile_rank(25, dist) < 1.0
    assert fz.percentile_rank(5, []) == 0.0           # 空分布安全


# ── 去重聚类 ─────────────────────────────────────────────────────────
def test_dedup_cluster_url_canonical():
    docs = [
        SearchResult(title="HN post", url="https://example.com/x?utm_source=hn"),
        SearchResult(title="Reddit post", url="https://example.com/x/"),
        SearchResult(title="other", url="https://other.com/y"),
    ]
    clusters = fz.dedup_cluster(docs)
    # 前两条 canonical 同 URL → 合并为一簇
    assert len(clusters) == 2
    merged = [c for c in clusters if "example.com/x" in fz.canonical_url(c.url)][0]
    assert merged is not None


def test_dedup_cluster_title_jaccard():
    docs = [
        SearchResult(title="GPT 5 released today", url="https://a.com/1"),
        SearchResult(title="GPT 5 released today", url="https://b.com/2"),
    ]
    clusters = fz.dedup_cluster(docs, jaccard_threshold=0.8)
    assert len(clusters) == 1                          # 标题高度相似 → 合并
