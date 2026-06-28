"""SkillDiscoveryEngine 单测：纯函数（frontmatter/真伪/评分/兼容）+ search 聚合。

零网络：search 用一个普通 fake client 注入（带 async code_search/get_contents/
subdir_commit_count），canned 返回值；get_contents 返回含 base64 content 的 dict。
"""
import asyncio
import base64

from wrr.engines import skill_discovery as sd
from wrr.schemas import SearchOptions
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _b64(text: str) -> dict:
    return {"content": base64.b64encode(text.encode()).decode(), "encoding": "base64"}


# ── 纯函数：parse_frontmatter ────────────────────────────────────────
def test_parse_frontmatter_normal():
    md = "---\nname: Foo\ndescription: does foo\nversion: 1.0\n---\n# body\ntext"
    fm = sd.parse_frontmatter(md)
    assert fm is not None
    assert fm["name"] == "Foo"
    assert fm["description"] == "does foo"


def test_parse_frontmatter_malformed():
    assert sd.parse_frontmatter("no frontmatter at all") is None
    assert sd.parse_frontmatter("") is None
    assert sd.parse_frontmatter("---\nname: x\nno closing fence") is None   # 无闭合
    assert sd.parse_frontmatter("---\nname: [unclosed\n---\nbody") is None  # 坏 yaml
    assert sd.parse_frontmatter("---\n- just\n- a\n- list\n---\n") is None  # 非 dict


# ── 纯函数：is_true_skill ────────────────────────────────────────────
def test_is_true_skill():
    assert sd.is_true_skill({"name": "a", "description": "b"}) is True
    assert sd.is_true_skill({"description": "b"}) is False          # 缺 name
    assert sd.is_true_skill({"name": "a"}) is False                 # 缺 description
    assert sd.is_true_skill({"name": "", "description": "b"}) is False
    assert sd.is_true_skill({"name": "a", "description": ""}) is False
    assert sd.is_true_skill(None) is False
    assert sd.is_true_skill({}) is False


# ── 纯函数：skill_score 单调 ─────────────────────────────────────────
def test_skill_score_weights():
    assert config.SKILL_SCORE_WEIGHTS == (0.40, 0.35, 0.25)


def test_skill_score_activity_monotonic():
    fm = {"name": "a", "description": "b"}
    files = []
    s_low = sd.skill_score(1, fm, files)
    s_mid = sd.skill_score(20, fm, files)
    s_high = sd.skill_score(200, fm, files)
    assert s_low < s_mid < s_high
    assert sd.skill_score(0, fm, files) <= s_low


def test_skill_score_frontmatter_and_engineering_lift():
    minimal = {"name": "a", "description": "b"}
    rich = {"name": "a", "description": "b", "version": "1", "license": "MIT",
            "triggers": ["x"]}
    # frontmatter 越完整分越高（其余相同）
    assert sd.skill_score(10, rich, []) > sd.skill_score(10, minimal, [])
    # 工程化文件存在 → 分更高
    assert sd.skill_score(10, minimal, ["scripts", "references", "test_foo.py"]) \
        > sd.skill_score(10, minimal, [])


# ── 纯函数：hermes_compat ────────────────────────────────────────────
def test_hermes_compat():
    full = {"name": "a", "description": "b", "type": "skill", "version": "1.0"}
    assert sd.hermes_compat(full) == "✓"
    # name+desc 齐但缺 type/version → 需补默认
    assert sd.hermes_compat({"name": "a", "description": "b"}) == "⚠needs-default"
    assert sd.hermes_compat({"name": "a", "description": "b", "type": "skill"}) \
        == "⚠needs-default"
    assert sd.hermes_compat(None) == "⚠needs-default"


# ── search 聚合（fake client，零网络）────────────────────────────────
_FOO_MD = ("---\nname: Foo Skill\ndescription: does foo well\n"
           "version: 1.0\ntype: skill\nlicense: MIT\n---\n# Foo\nbody")
_BAR_MD = "---\ndescription: missing name here\n---\nbody"   # 缺 name → 丢弃


class FakeClient:
    """普通对象（非 httpx），记录调用参数以便断言。"""

    def __init__(self):
        self.subdir_calls = []
        self.code_search_q = None
        self.incomplete = False

    async def code_search(self, query, per_page=30):
        self.code_search_q = query
        return {
            "items": [
                {"repository": {"full_name": "org/good"}, "path": "skills/foo/SKILL.md"},
                {"repository": {"full_name": "org/bad"}, "path": "skills/bar/SKILL.md"},
                {"repository": {"full_name": "org/tmpl"}, "path": "template/SKILL.md"},
            ],
            "total_count": 3,
            "incomplete_results": self.incomplete,
        }

    async def get_contents(self, repo, path):
        if path.endswith("SKILL.md"):
            return _b64(_FOO_MD if "foo" in path else _BAR_MD)
        # 目录 listing → 工程化信号
        return [{"name": "SKILL.md", "type": "file"},
                {"name": "scripts", "type": "dir"},
                {"name": "references", "type": "dir"}]

    async def subdir_commit_count(self, repo, path, since):
        self.subdir_calls.append({"repo": repo, "path": path, "since": since})
        return 12


def test_search_drops_skillless_and_emits_subdir_url():
    fake = FakeClient()
    out = run(sd.SkillDiscoveryEngine(client=fake).search(
        SearchOptions("data viz", count=10)))
    # 缺 name 的 bar 被丢弃；template/ 被排除 → 只剩 foo
    assert len(out) == 1
    r = out[0]
    assert r.title == "Foo Skill"
    assert r.url == "https://github.com/org/good/tree/HEAD/skills/foo"   # 直指子目录
    assert r.source_tag == "skill"
    assert "hermes=✓" in r.snippet
    # code search 拼上了 path 限定
    assert config.SKILL_CODE_SEARCH_PATH in fake.code_search_q
    # subdir_commit_count 以 path=子目录 调用（非仓库根）
    paths = [c["path"] for c in fake.subdir_calls]
    assert "skills/foo" in paths
    assert "template/" not in paths and "" not in paths


def test_search_tolerates_incomplete_results():
    fake = FakeClient()
    fake.incomplete = True
    out = run(sd.SkillDiscoveryEngine(client=fake).search(
        SearchOptions("data viz", count=10)))
    assert len(out) == 1 and out[0].title == "Foo Skill"


def test_skill_triggered_config():
    assert config.skill_triggered("有没有 data viz 的 skill")
    assert config.skill_triggered("skill 推荐")
    assert not config.skill_triggered("plain query")
