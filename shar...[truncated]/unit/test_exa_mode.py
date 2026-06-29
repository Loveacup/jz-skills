"""Exa mode 自动路由单测：classify_query / get_search_mode / get_timeout_for_mode。

验证文档记录的「Exa 四模式自动路由」特性确实按设计工作。
"""
from wrr.engines import exa as exa_mod
from wrr.schemas import SearchOptions
from wrr import config


def test_classify_academic():
    assert exa_mod.classify_query("transformer architecture 综述") == "academic"


def test_classify_research():
    assert exa_mod.classify_query("详细比较 A 和 B 的优劣") == "research"


def test_classify_factual():
    assert exa_mod.classify_query("Claude 4.8 release 日期是哪天") == "factual"


def test_classify_standard_default():
    assert exa_mod.classify_query("buy a cheap laptop") == "standard"


def test_get_search_mode_auto_routing():
    assert exa_mod.get_search_mode(SearchOptions("survey of X")) == config.EXA_MODE_ROUTING["academic"]
    assert exa_mod.get_search_mode(SearchOptions("买电脑")) == "auto"   # standard → auto


def test_get_search_mode_explicit_override():
    # 显式 mode 优先于自动路由
    assert exa_mod.get_search_mode(SearchOptions("survey", mode="fast")) == "fast"


def test_get_timeout_for_mode():
    assert exa_mod.get_timeout_for_mode("deep") == config.EXA_MODE_TIMEOUT["deep"]
    assert exa_mod.get_timeout_for_mode("unknown-mode") == 5.0   # 兜底默认
