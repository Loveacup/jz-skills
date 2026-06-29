"""Skill 发现引擎 v5 包级评分层单测（STDD §5.2 双层模型上层 + 合成 + 缓存）。

修复 OMP 审计 concern（标准 4）：补齐包级评分层，单 skill 层不变。
"""
import asyncio
from datetime import datetime, timedelta, timezone

from wrr.engines import skill_discovery as sd
from wrr.schemas import SearchOptions
from wrr import config


def run(coro):
    return asyncio.run(coro)


NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)


def _iso(days_ago):
    return (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 纯函数：包级各维 ─────────────────────────────────────────────────
def test_bundle_weights():
    assert config.SKILL_BUNDLE_WEIGHTS == (0.30, 0.25, 0.25, 0.20)


def test_bundle_stars_monotonic_bounded():
    assert sd._bundle_stars(0) == 0.0
    assert 0.0 < sd._bundle_stars(100) < sd._bundle_stars(100000) <= 1.0


def test_bundle_recency_halflife():
    assert sd._bundle_recency(_iso(0), NOW) == 1.0
    hl = config.SKILL_BUNDLE_RECENCY_HALFLIFE_DAYS
    assert abs(sd._bundle_recency(_iso(hl), NOW) - 0.5) < 1e-9     # 半衰期 → 0.5
    assert sd._bundle_recency(None, NOW) == 0.0
    assert sd._bundle_recency(_iso(10), NOW) > sd._bundle_recency(_iso(400), NOW)


def test_bundle_community_activity():
    assert sd._bundle_community_activity(0, 0) == 0.0
    assert 0.0 < sd._bundle_community_activity(50, 50) <= 1.0


def test_bundle_license_tiers():
    assert sd._bundle_license({"spdx_id": "MIT"}) == 1.0          # 宽松
    assert sd._bundle_license({"spdx_id": "GPL-3.0"}) == 0.6      # 有但非宽松
    assert sd._bundle_license({"spdx_id": "NOASSERTION"}) == 0.0
    assert sd._bundle_license(None) == 0.0


def test_bundle_score_high_vs_low():
    high = {"stargazers_count": 50000, "pushed_at": _iso(5),
            "forks_count": 2000, "subscribers_count": 500, "license": {"spdx_id": "Apache-2.0"}}
    low = {"stargazers_count": 2, "pushed_at": _iso(800),
           "forks_count": 0, "subscribers_count": 0, "license": None}
    assert sd.bundle_score(high, NOW) > sd.bundle_score(low, NOW)
    assert sd.bundle_score(high, NOW) <= 1.0


def test_bundle_score_neutral_when_missing():
    assert sd.bundle_score(None, NOW) == config.SKILL_BUNDLE_NEUTRAL
    assert sd.bundle_score({}, NOW) == config.SKILL_BUNDLE_NEUTRAL


# ── 合成 ─────────────────────────────────────────────────────────────
def test_combine_scores_prior():
    assert sd.combine_scores(1.0, 1.0) == 1.0                     # 满包级 → 不缩
    assert sd.combine_scores(1.0, 0.0) == 0.5                     # 零包级 → 0.5x
    assert abs(sd.combine_scores(1.0, 0.5) - 0.75) < 1e-9         # 中性 → 0.75x
    # 包级越高，最终分越高（per_skill 相同）
    assert sd.combine_scores(0.8, 0.9) > sd.combine_scores(0.8, 0.2)


# ── search：包级先验影响排序 + 缓存只抓一次 ─────────────────────────
_SKILL_MD = ("---\nname: Same Skill\ndescription: identical per-skill signals\n"
             "version: 1.0.0\ntype: skill\n---\nbody")


class _BundleFakeClient:
    """两个 repo，单 skill 信号相同；repo 质量不同 → 包级应拉开排序。"""
    def __init__(self):
        self.get_repo_calls = {}

    async def code_search(self, query, per_page=30):
        return {"items": [
            {"repository": {"full_name": "org/good"}, "path": "skills/x/SKILL.md"},
            {"repository": {"full_name": "org/junk"}, "path": "skills/y/SKILL.md"},
        ], "total_count": 2, "incomplete_results": False}

    async def get_contents(self, repo, path):
        import base64
        if path.endswith("SKILL.md"):
            return {"content": base64.b64encode(_SKILL_MD.encode()).decode(),
                    "encoding": "base64"}
        return []                                       # 子目录列表（工程化信号，两边相同）

    async def subdir_commit_count(self, repo, path, since):
        return 20                                       # 两边相同活跃度

    async def get_repo(self, repo):
        self.get_repo_calls[repo] = self.get_repo_calls.get(repo, 0) + 1
        if repo == "org/good":
            return {"stargazers_count": 80000, "pushed_at": _iso(3),
                    "forks_count": 3000, "subscribers_count": 400,
                    "license": {"spdx_id": "MIT"}}
        return {"stargazers_count": 1, "pushed_at": _iso(900),
                "forks_count": 0, "subscribers_count": 0, "license": None}

    def _iso_helper(self):
        pass


def test_search_bundle_prior_ranks_quality_repo_first():
    fake = _BundleFakeClient()
    out = run(sd.SkillDiscoveryEngine(client=fake).search(
        SearchOptions("foo", count=10)))
    assert len(out) == 2
    # 单 skill 信号相同，包级先验把高质量仓的 skill 顶到前面
    assert out[0].url == "https://github.com/org/good/tree/HEAD/skills/x"
    assert "bundle=" in out[0].snippet
    # 每个唯一 repo 仅抓一次（缓存语义由引擎侧 unique set 保证）
    assert fake.get_repo_calls == {"org/good": 1, "org/junk": 1}


def test_search_graceful_when_no_get_repo():
    """client 无 get_repo（旧 fake）→ 中性先验，不丢结果（向后兼容）。"""
    class NoRepoClient(_BundleFakeClient):
        get_repo = None
    fake = NoRepoClient()
    out = run(sd.SkillDiscoveryEngine(client=fake).search(SearchOptions("foo", count=10)))
    assert len(out) == 2                                # 仍返回，包级中性
    assert "bundle=0.50" in out[0].snippet
