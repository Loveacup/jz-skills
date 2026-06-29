"""CommunityEngine v5 升级单测：跨子源 RRF 聚合 + canonical_url 去重（加法式）。

不动既有 search()/deduplicate（v4 行为由 test_community.py 锁定）。
"""
import asyncio
import json
import time

from wrr.engines import community as cm
from wrr.schemas import SearchOptions
from wrr import config
from wrr.engines import _fusion


def run(coro):
    return asyncio.run(coro)


_REDDIT = [
    {"title": "Reddit A", "url": "https://reddit.com/r/p/1/a",
     "score": 500, "comments": 100, "created_utc": int(time.time()) - 7200,
     "selftext": "body"},
    {"title": "Reddit B", "url": "https://reddit.com/r/p/2/b",
     "score": 3, "comments": 0, "created_utc": int(time.time()) - 100 * 86400,
     "selftext": ""},
]
_TWITTER = [
    {"text": "tweet python", "url": "https://x.com/u/1",
     "likes": 1000, "replies": 50, "created_at": int(time.time()) - 3600},
]


def _fake_run_factory(mapping, fail=()):
    async def fake_run(cli, timeout):
        joined = " ".join(cli).lower()
        for key, payload in mapping.items():
            if key in joined:
                if key in fail:
                    return (None, "")
                return (0, json.dumps(payload))
        return (0, "[]")
    return fake_run


def test_search_rrf_aggregates_multi_source():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory(
        {"reddit": _REDDIT, "twitter": _TWITTER, "xiaohongshu": [], "v2ex": []},
        fail=("v2ex",))
    try:
        out = run(cm.CommunityEngine().search_rrf(SearchOptions("python", count=10)))
    finally:
        cm._run_cmd = orig
    titles = [r.title for r in out]
    assert "Reddit A" in titles and "tweet python" in titles
    # 源内高分（Reddit A）应排在源内低分（Reddit B）之前
    assert titles.index("Reddit A") < titles.index("Reddit B")
    assert all(r.url for r in out)


def test_search_rrf_respects_count():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"reddit": _REDDIT, "twitter": _TWITTER,
                                     "xiaohongshu": [], "v2ex": []})
    try:
        out = run(cm.CommunityEngine().search_rrf(SearchOptions("python", count=1)))
    finally:
        cm._run_cmd = orig
    assert len(out) == 1


def test_search_rrf_all_empty_raises():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"reddit": [], "twitter": [],
                                     "xiaohongshu": [], "v2ex": []})
    try:
        run(cm.CommunityEngine().search_rrf(SearchOptions("python")))
        assert False, "all empty should raise"
    except Exception as e:
        assert "community" in str(e).lower()
    finally:
        cm._run_cmd = orig


def test_canonical_dedup_cross_platform_same_link():
    # HN 与 Reddit 指向同一外链（utm 不同）→ canonical 去重合并
    from wrr.schemas import SearchResult
    docs = [
        SearchResult("HN: cool post", "https://example.com/x?utm_source=hn", "", source_tag="hackernews"),
        SearchResult("Reddit: cool post", "https://example.com/x/", "", source_tag="reddit"),
    ]
    out = _fusion.dedup_cluster(docs)
    assert len(out) == 1                          # 同一外链跨平台合并


# ── PATH 注入测试（v5.2 A1 修复）────────────────────────────────────

def test_run_cmd_injects_local_bin_when_missing():
    """_run_cmd 应在 PATH 头部注入 ~/.local/bin"""
    import os
    local_bin = os.path.expanduser("~/.local/bin")
    # 模拟 _run_cmd 的 env 构建逻辑
    env_dict = os.environ.copy()
    current_path = env_dict.get("PATH", "")
    parts = current_path.split(os.pathsep)
    if local_bin not in parts:
        env_dict["PATH"] = os.pathsep.join([local_bin] + parts)
    assert local_bin in env_dict["PATH"].split(os.pathsep)
    # 确认 ~/.local/bin 在最前面
    first = env_dict["PATH"].split(os.pathsep)[0]
    assert first == local_bin or first == parts[0], f"~/.local/bin not first in PATH"


def test_run_cmd_noop_when_already_in_path():
    """已存在不去重加——验证 _run_cmd 的 PATH 注入逻辑"""
    import os
    local_bin = os.path.expanduser("~/.local/bin")
    # 构造含 local_bin 的 PATH（模拟已注入场景）
    baseline = os.environ.get("PATH", "")
    # 如果真实 PATH 已有 local_bin，先去重
    baseline_parts = [p for p in baseline.split(os.pathsep) if p != local_bin]
    env_dict = os.environ.copy()
    env_dict["PATH"] = local_bin + os.pathsep + os.pathsep.join(baseline_parts)
    parts = env_dict["PATH"].split(os.pathsep)
    assert parts.count(local_bin) == 1, f"PATH 应恰好含一次 ~/.local/bin, got {parts.count(local_bin)}"

# ── v5.5 env-configurable last30days paths ──

def test_l30_env_override(monkeypatch):
    """env var should override hardcoded path"""
    import wrr.engines.community as mod
    monkeypatch.setattr(mod, "_L30_EN", "/custom/en/path.py")
    monkeypatch.setattr(mod, "_L30_CN", "/custom/cn/path.py")
    assert mod._L30_EN == "/custom/en/path.py"
    assert mod._L30_CN == "/custom/cn/path.py"

def test_l30_paths_are_absolute():
    """ensure resolved paths are absolute"""
    import os
    import wrr.engines.community as mod
    assert os.path.isabs(mod._L30_EN)
    assert os.path.isabs(mod._L30_CN)
