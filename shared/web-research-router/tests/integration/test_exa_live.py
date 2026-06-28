"""Exa 集成测试 — 需要 EXA_API_KEY。"""
import os
import pytest
from wrr.engines.exa import ExaEngine
from wrr.schemas import SearchOptions

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("EXA_API_KEY"), reason="EXA_API_KEY not set")
async def test_exa_search_live():
    engine = ExaEngine()
    results = await engine.search(SearchOptions(query="OpenAI API official docs", count=3))
    assert len(results) > 0
    assert results[0].url.startswith("http")
    print(f"Got {len(results)} results from Exa")

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("EXA_API_KEY"), reason="EXA_API_KEY not set")
async def test_exa_mode_routing():
    """测试自动路由是否正确选择模式。"""
    from wrr.engines.exa import classify_query, get_search_mode
    
    # 学术查询应选 deep
    opt1 = SearchOptions(query="LLM survey paper", count=3)
    mode1 = get_search_mode(opt1)
    assert mode1 == "deep", f"Expected deep, got {mode1}"
    
    # 事实查询应选 fast
    opt2 = SearchOptions(query="Python 3.12 release date", count=3)
    mode2 = get_search_mode(opt2)
    assert mode2 == "fast", f"Expected fast, got {mode2}"
    
    # 显式覆盖
    opt3 = SearchOptions(query="test", count=3, mode="auto")
    mode3 = get_search_mode(opt3)
    assert mode3 == "auto", f"Expected auto, got {mode3}"
