# -*- coding: utf-8 -*-
"""DraftReport deterministic §6 knowledge graph slice."""

import verify_publishable_report
from test_verify_publishable_report import _good_report
from video_analysis_engine import assemble_draft_report_slice, write_knowledge_graph_section


def _kg_candidate(text, reason="knowledge_candidate", source_type="transcript", timestamp="0:10"):
    return {
        "section_id": "6",
        "source_type": source_type,
        "reason": reason,
        "timestamp": timestamp,
        "url": "https://www.bilibili.com/video/BVkg?t=10",
        "text": text,
    }


def _report_with_section6(candidates):
    return {
        "frontmatter": {"title": "KG test", "video_id": "BVkg"},
        "report_plan": {
            "can_generate_formal_report": True,
            "sections": [
                {"id": "6", "title": "知识图谱 (Knowledge Graph)", "purpose": "抽取概念、关系和应用", "quality_gate": ""},
            ],
        },
        "evidence_map": {"by_section": {"6": candidates}, "warnings": []},
        "evidence_gate": {"sources": {"transcript": {"available": True, "source": "h200-asr", "language": "zh", "segments": len(candidates), "chars": 200}}},
    }


def test_knowledge_graph_writer_outputs_concepts_relations_and_applications():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("虚拟偶像依赖人格资产，粉丝信任来自连续互动和稳定人设。"),
            _kg_candidate("人格资产影响商业化边界，过度商业化会削弱粉丝信任。"),
            _kg_candidate("可以把虚拟偶像治理转化为 Obsidian 知识卡片和行动清单。", reason="application_candidate"),
        ]
    })

    assert "### 核心概念" in body
    assert "### 关系链" in body
    assert "### 可落库/可行动项" in body
    assert "[[虚拟偶像]]" in body
    assert "[[人格资产]]" in body
    assert "[[粉丝信任]]" in body
    assert "[[虚拟偶像]] → [[人格资产]]" in body
    assert "Obsidian 知识卡片" in body
    assert "_骨架占位" not in body


def test_knowledge_graph_writer_filters_noise_and_deduplicates_concepts():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("虚拟偶像和虚拟偶像重复出现，但应该只输出一次概念。"),
            _kg_candidate("这个评论不错", source_type="comments"),
            _kg_candidate("高光不是知识图谱输入", reason="quote_candidate"),
            _kg_candidate("", reason="knowledge_candidate"),
        ]
    })

    assert body.count("[[虚拟偶像]]") <= 3  # concept list + relation at most
    assert "这个评论不错" not in body
    assert "高光不是知识图谱输入" not in body


def test_knowledge_graph_empty_evidence_is_non_publishable_placeholder():
    body = write_knowledge_graph_section({"evidence": []})

    assert "_骨架占位" in body
    md = _good_report().replace("- [[虚拟偶像]] → [[人格资产]] → [[信任机制]]", body)
    results, passed = verify_publishable_report.evaluate(md)
    assert passed is False
    assert results["P0_NO_SKELETON"]["pass"] is False


def test_assemble_draft_report_slice_writes_section6_only_when_requested():
    report = _report_with_section6([
        _kg_candidate("虚拟偶像依赖人格资产，粉丝信任来自连续互动。"),
        _kg_candidate("人格资产影响商业化边界，过度商业化会削弱粉丝信任。"),
    ])

    draft = assemble_draft_report_slice(report, section_ids=("6",))

    assert draft.publishable is False
    assert set(draft.draft_sections) == {"6"}
    assert "### 核心概念" in draft.draft_sections["6"]
    assert "[[虚拟偶像]]" in draft.draft_sections["6"]
