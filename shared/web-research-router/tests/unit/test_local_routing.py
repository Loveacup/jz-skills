"""本地搜索层路由单测：classify_intent local / dispatch / weights / RRF / web 补位。"""
import asyncio

from conftest import FakeEngine, mk_results
from wrr.registry import EngineRegistry
from wrr.router import route_search_v5, resolve_mode
from wrr.schemas import SearchOptions, SearchResult
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _reg(*engines):
    r = EngineRegistry()
    for e in engines:
        r.register(e)
    return r


def _local_results(name, n=2):
    return [SearchResult(title=f"{name}-{i}", url=f"{name}://{i}",
                         snippet=f"s{i}", source_tag=f"local:{name}") for i in range(n)]


# ── classify_intent → local ─────────────────────────────────────────
def test_classify_local_memory():
    for q in ["我之前让你查的论文", "记忆里的偏好", "supermemory 里有什么"]:
        assert config.classify_intent(q) == "local"


def test_classify_local_notes():
    for q in ["查笔记里的 WRR 路由", "obsidian 里的方法论", "我的知识库有没有这个"]:
        assert config.classify_intent(q) == "local"


def test_classify_local_session():
    for q in ["刚才我们聊的 hermes", "历史对话里提到的方案", "聊天记录里的决定"]:
        assert config.classify_intent(q) == "local"


def test_classify_scope_combo_triggers_local():
    assert config.classify_intent("本地笔记里的结论") == "local"
    assert config.classify_intent("我们讨论过的之前的结论") == "local"


def test_classify_scope_only_not_local():
    """弱 scope 词单独出现不进 local（避免误伤部署类查询）。"""
    assert config.classify_intent("本地部署 redis 怎么做") == "grounding"
    assert config.classify_intent("localhost 端口冲突") == "grounding"


def test_classify_non_local_unaffected():
    assert config.classify_intent("what is python") == "grounding"
    assert config.classify_intent("survey of llm") == "academic"
    assert config.classify_intent("gpt site:reddit.com") == "platform"


# ── MODE_DISPATCH / MODE_WEIGHTS ─────────────────────────────────────
def test_local_dispatch_registered():
    from wrr.registry import default_registry
    reg = default_registry()
    for name in config.MODE_DISPATCH["local"]:
        assert reg.get(name) is not None, f"{name} not registered"


def test_local_dispatch_order_local_first():
    disp = config.MODE_DISPATCH["local"]
    assert disp[0] == "local_supermemory"
    assert disp.index("local_qmd") < disp.index("exa")     # 本地在 web 之前


def test_local_weights_local_dominates_web():
    w = config.MODE_WEIGHTS["local"]
    assert w["local_supermemory"] == 1.0
    assert w["local_qmd"] == 0.9
    assert w["exa"] == 0.3 and w["brave"] == 0.3           # web 仅低权补位
    assert w["local_obsidian"] > w["exa"]


def test_resolve_mode_explicit_local():
    assert resolve_mode(SearchOptions("anything", mode="local")) == "local"


def test_mode_engines_local():
    eng = config.mode_engines("local", "我的笔记")
    assert eng[:4] == ["local_supermemory", "local_session", "local_qmd", "local_obsidian"]


# ── route_search_v5：local mode ──────────────────────────────────────
def test_v5_local_mode_fuses_local_engines():
    reg = _reg(
        FakeEngine("local_supermemory", search_results=_local_results("supermemory")),
        FakeEngine("local_session", search_results=_local_results("session")),
        FakeEngine("local_qmd", search_results=_local_results("qmd")),
        FakeEngine("local_obsidian", search_results=_local_results("obsidian")),
        FakeEngine("exa", search_results=mk_results(2)),
        FakeEngine("brave", search_results=mk_results(2)),
    )
    rr = run(route_search_v5(SearchOptions("我之前的偏好", count=10), reg))
    assert rr.mode == "local"
    assert rr.fusion_method == "rrf"
    assert rr.weights.get("local_supermemory") == 1.0
    assert len(rr.payload) >= 1


def test_v5_local_engines_fail_web_fallback_in_dispatch():
    """Tier1 本地引擎在 CLI 环境失败，dispatch 内 exa/brave 兜底仍返回结果。"""
    reg = _reg(
        FakeEngine("local_supermemory", error="no hermes tool"),
        FakeEngine("local_session", error="no hermes tool"),
        FakeEngine("local_qmd", error="no qmd"),
        FakeEngine("local_obsidian", error="no vault"),
        FakeEngine("exa", search_results=mk_results(3)),
        FakeEngine("brave", search_results=mk_results(2)),
    )
    rr = run(route_search_v5(SearchOptions("查笔记里的东西", count=10), reg))
    assert rr.mode == "local"
    assert len(rr.payload) >= 1                            # web 补位成功
    failed = [s.provider for s in rr.fallback_chain if not s.ok]
    assert "local_qmd" in failed                           # 本地失败被记录、隔离
