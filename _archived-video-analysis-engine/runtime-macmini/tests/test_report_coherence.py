# -*- coding: utf-8 -*-
"""P2-D5: Cross-section coherence checker tests."""

from video_analysis_engine import check_report_coherence


def _minimal_full_report(section3=None, section4=None, section7=None):
    section3 = section3 or "- 第一条关键洞察包含足够正文，并引用证据 [E1] 来保证可追溯。"
    section4 = section4 or "- 第一项深度拆解包含足够正文，并引用证据 [E2] 来保证可追溯。"
    section7 = section7 or "- 第一条价值评估包含足够正文，并引用证据 [E3] 来保证可追溯。"
    return f"""## 0. 元信息
这是元信息摘要。

## 1. 基础信息
这是基础信息正文。

## 2. 互动信号
这是互动信号正文。

## 3. 关键洞察
{section3}

## 4. 深度拆解
{section4}

## 5. 高光时刻
> "这是一句高光原文" — [E1]

## 6. 延伸问题
这是延伸问题正文。

## 7. 价值评估
{section7}

## 8. 数据源附录
| source_type | available |
| --- | --- |
| transcript | true |
"""


def _codes(result):
    return {issue.code for issue in result.issues}


def test_coherence_pass_minimal_full_report():
    result = check_report_coherence(_minimal_full_report())
    assert result.passed is True
    assert result.issues == []


def test_coherence_detects_section_order_blocker():
    markdown = """## 0. 元信息
正常正文。

## 4. 深度拆解
这一节有足够的正文避免空节误报，并引用 [E1]。

## 3. 关键洞察
这一节也有足够的正文避免空节误报，并引用 [E2]。

## 8. 数据源附录
正常正文。
"""
    result = check_report_coherence(markdown)
    assert result.passed is False
    assert 'section_order' in _codes(result)
    assert any(i.severity == 'blocker' for i in result.issues if i.code == 'section_order')


def test_coherence_detects_skeleton_residue():
    result = check_report_coherence(
        _minimal_full_report(section3="- _骨架占位：核心洞察待 LLM 基于上方证据填充。_")
    )
    assert 'skeleton_residue' in _codes(result)
    assert any(i.severity == 'concern' for i in result.issues if i.code == 'skeleton_residue')


def test_coherence_detects_duplicate_paragraph():
    duplicate = "这是一段长度超过三十个字符的重复正文，用来触发重复段落检查逻辑。"
    markdown = _minimal_full_report() + f"\n{duplicate}\n\n{duplicate}\n"
    result = check_report_coherence(markdown)
    assert 'duplicate_paragraph' in _codes(result)
    assert any(i.severity == 'concern' for i in result.issues if i.code == 'duplicate_paragraph')


def test_coherence_detects_bad_evidence_citation():
    result = check_report_coherence(
        _minimal_full_report(section3="- 这一条引用格式错误 [E]，但正文长度足够用于单独测试引用格式。")
    )
    assert 'bad_evidence_citation' in _codes(result)
    assert any(i.severity == 'concern' for i in result.issues if i.code == 'bad_evidence_citation')



def test_coherence_allows_skeleton_residue_in_non_llm_sections():
    markdown = _minimal_full_report().replace(
        "## 7. 价值评估",
        "## 6. 知识图谱\n_骨架占位：暂无证据候选。_\n\n## 7. 价值评估",
    )
    result = check_report_coherence(markdown)
    assert 'skeleton_residue' not in _codes(result)


def test_coherence_detects_empty_llm_section():
    result = check_report_coherence(_minimal_full_report(section3="短"))
    assert result.passed is False
    assert 'empty_llm_section' in _codes(result)
    assert any(
        i.severity == 'blocker' and i.section_id == '3'
        for i in result.issues
        if i.code == 'empty_llm_section'
    )
