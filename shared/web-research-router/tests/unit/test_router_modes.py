"""v5 mode 路由单测：classify_intent / MODE_DISPATCH / 触发提升 / gather 隔离 / RRF details。"""
import asyncio

from conftest import FakeEngine, mk_results
from wrr.registry import EngineRegistry
from wrr.router import route_search_v5, resolve_mode
from wrr.schemas import SearchOptions
from wrr.errors import AllEnginesFailedError
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _reg(*engines):
    r = EngineRegistry()
    for e in engines:
        r.register(e)
    return r


def _full_reg():
    return _reg(*[FakeEngine(n, search_results=mk_results(2))
                  for n in ("exa", "brave", "searxng", "github",
                            "community", "academic", "skill")])


# ── classify_intent（每 mode ≥3 例）──────────────────────────────────
def test_classify_intent_grounding():
    for q in ["what is python", "tesla 股价多少", "react 版本"]:
        assert config.classify_intent(q) == "grounding"


def test_classify_intent_academic():
    for q in ["survey of llm", "transformer 论文", "graph algorithm methodology"]:
        assert config.classify_intent(q) == "academic"


def test_classify_intent_research():
    for q in ["深度分析 ai", "全面比较 react vue", "comparison of databases"]:
        assert config.classify_intent(q) == "research"


def test_classify_intent_discovery():
    for q in ["有哪些 rust 库", "2026 ai 趋势", "best python tools"]:
        assert config.classify_intent(q) == "discovery"


def test_classify_intent_platform():
    for q in ["gpt site:reddit.com", "ai site:zhihu.com", "x site:news.ycombinator.com"]:
        assert config.classify_intent(q) == "platform"


def test_classify_intent_broad():
    """开放式兴趣查询 → broad mode (v5.2)"""
    for q in ["今天有啥好玩的", "今日热点", "今天可能感兴趣的事",
              "what's new in AI", "最近有啥新鲜事"]:
        assert config.classify_intent(q) == "broad"


def test_classify_intent_recovery():
    """丢失/删除查询 → recovery mode (v5.2)"""
    for q in ["找不到刚才的文件", "恢复被删的记录", "missing deleted config"]:
        assert config.classify_intent(q) == "recovery"


def test_resolve_mode_explicit_and_recovery():
    assert resolve_mode(SearchOptions("anything", mode="recovery")) == "recovery"
    assert resolve_mode(SearchOptions("anything", mode="academic")) == "academic"
    # 非法 mode 回退自动分类
    assert resolve_mode(SearchOptions("survey of x", mode="bogus")) == "academic"


# ── MODE_DISPATCH 完整性 ─────────────────────────────────────────────
def test_mode_dispatch_non_empty_and_registered():
    reg = _full_reg()
    for mode in ("discovery", "grounding", "research", "academic", "platform", "recovery", "local", "broad"):
        engines = config.MODE_DISPATCH[mode]
        assert engines, f"{mode} empty"
        for name in engines:
            if name.startswith("local_"):  # 本地引擎在 CLI 环境不可用
                continue
            assert reg.get(name) is not None, f"{mode}:{name} not in registry"


# ── 触发提升不重复 ───────────────────────────────────────────────────
def test_trigger_promotion_no_dup():
    # academic mode 基础已含 academic，触发词再命中不应重复
    engines = config.mode_engines("academic", "survey of transformers")
    assert engines.count("academic") == 1
    # grounding + github 触发
    eg = config.mode_engines("grounding", "asyncio site:github.com")
    assert "github" in eg and eg.count("github") == 1
    # skill 触发
    es = config.mode_engines("grounding", "有没有 X 的 skill")
    assert "skill" in es


# ── route_search_v5：并行 + RRF + details ────────────────────────────
def test_v5_search_returns_rrf_details():
    reg = _full_reg()
    rr = run(route_search_v5(SearchOptions("深度分析 ai", count=10), reg))
    assert rr.mode == "research"
    assert rr.fusion_method == "rrf"
    assert rr.weights is not None
    assert len(rr.payload) >= 1
    # research mode 含 community/academic 权重
    assert rr.weights.get("community") == 0.35   # v5.4: research community 0.30→0.35
    assert rr.weights.get("academic") == 0.30


def test_v5_academic_mode_weights():
    reg = _full_reg()
    rr = run(route_search_v5(SearchOptions("survey of llm", count=5), reg))
    assert rr.mode == "academic"
    assert rr.weights.get("academic") == 1.0          # 学术绝对主力


def test_v5_one_engine_exception_isolated():
    # exa 抛异常，brave 正常 → 整体仍返回（gather 隔离）
    reg = _reg(FakeEngine("exa", error="exa down"),
               FakeEngine("brave", search_results=mk_results(3)))
    rr = run(route_search_v5(SearchOptions("what is x", count=10), reg))   # grounding
    assert rr.mode == "grounding"
    assert len(rr.payload) >= 1
    failed = [s.provider for s in rr.fallback_chain if not s.ok]
    assert "exa" in failed                            # 失败被记录但不致命


def test_v5_all_fail_falls_to_recovery_then_raises():
    # grounding 的 exa/brave 全挂，recovery 的 brave/exa/searxng 也全挂 → 抛
    reg = _reg(FakeEngine("exa", error="down"),
               FakeEngine("brave", error="down"),
               FakeEngine("searxng", error="down"))
    try:
        run(route_search_v5(SearchOptions("what is x"), reg))
        assert False, "should raise"
    except AllEnginesFailedError:
        pass


def test_v5_recovery_fallback_recovers():
    # grounding(exa/brave) 空，但 searxng 有结果 → recovery 兜底成功
    reg = _reg(FakeEngine("exa", search_results=[]),
               FakeEngine("brave", search_results=[]),
               FakeEngine("searxng", search_results=mk_results(2)))
    rr = run(route_search_v5(SearchOptions("what is x", count=5), reg))
    assert rr.mode == "recovery"
    assert len(rr.payload) >= 1


def test_v5_explicit_provider_single_engine():
    reg = _reg(FakeEngine("brave", search_results=mk_results(2)),
               FakeEngine("exa", error="should not be used"))
    rr = run(route_search_v5(SearchOptions("q", provider="brave"), reg))
    assert rr.actual_provider == "brave"              # 显式 → 单引擎，禁 mode 路由


# ── v5.4 实践意图社区触发 ──

def test_practical_triggers_community():
    """工具使用/操作指南类查询应触发社区引擎"""
    from wrr.config import community_triggered
    assert community_triggered("Windows Terminal 操作指南和快捷键怎么用")
    assert community_triggered("best practices for Claude Code")
    assert community_triggered("Neovim 插件怎么选，有什么推荐")
    assert community_triggered("Kubernetes 实战经验和踩坑")
    assert community_triggered("how to configure tmux with gotchas")


def test_practical_no_false_positive():
    """纯事实查询不应被实践关键词误触发"""
    from wrr.config import community_triggered
    assert not community_triggered("python 3.14 release date")
    assert not community_triggered("Windows Terminal latest stable version")
    assert not community_triggered("postgres 16 changelog")


def test_community_weights_raised():
    """discovery/broad/grounding 社区权重提升"""
    assert config.MODE_WEIGHTS["discovery"]["community"] >= 0.50
    assert config.MODE_WEIGHTS["broad"]["community"] >= 0.50
    assert config.MODE_WEIGHTS["grounding"]["community"] >= 0.40
    # academic 不变
    assert config.MODE_WEIGHTS["academic"]["community"] <= 0.30
