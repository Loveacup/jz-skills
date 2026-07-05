# -*- coding: utf-8 -*-
"""P2-D6: generate_report writer provider wiring."""

import argparse

import generate_report


def _minimal_results(tmp_path):
    jp = tmp_path / "BVwriter_subtitle.json"
    jp.write_text(
        '{"body":[{"from":0,"to":2,"content":"开场介绍核心观点"},'
        '{"from":2,"to":5,"content":"进一步解释方法和价值"},'
        '{"from":5,"to":8,"content":"总结对观众的启发"}]}',
        encoding="utf-8",
    )
    return {
        "bvid": "BVwriter",
        "title": "writer provider test",
        "subtitle": {"method": "official", "json_path": str(jp), "language": "zh"},
        "comments": {"hot_comments": [{"content": "这个观点很有启发", "like": 10, "user": {"name": "u"}}]},
        "danmaku": {"data": [{"text": "学到了", "time_sec": 3}]},
    }


def test_resolve_writer_provider_none():
    args = argparse.Namespace(writer_provider="none")
    assert generate_report.resolve_writer_provider(args) is None


def test_resolve_writer_provider_cli():
    args = argparse.Namespace(writer_provider="cli")
    assert generate_report.resolve_writer_provider(args) is generate_report.cli_writer_provider


def test_resolve_writer_provider_deepseek():
    args = argparse.Namespace(writer_provider="deepseek")
    assert generate_report.resolve_writer_provider(args) is generate_report.deepseek_writer_provider


def test_report_markdown_passes_provider_to_debug_renderer(monkeypatch, tmp_path):
    calls = []

    def fake_render(draft, provider=None):
        calls.append({"draft": draft, "provider": provider})
        return "# rendered"

    def fake_provider(system, user):
        return "unused"

    monkeypatch.setattr(generate_report, "render_debug_markdown", fake_render)

    markdown, report = generate_report.report_markdown(
        _minimal_results(tmp_path),
        run_fact_check=False,
        provider=fake_provider,
    )

    assert markdown == "# rendered"
    assert report["frontmatter"]["video_id"] == "BVwriter"
    assert calls[0]["provider"] is not None
    assert calls[0]["draft"].artifact_kind == "draft_report"
    assert calls[0]["draft"].publishable is False


def test_report_markdown_populates_section_qa_without_changing_rendered_markdown(tmp_path):
    """Phase 3: report_markdown() 填充 section_qa 元数据但不改变 Markdown 语义。"""
    markdown, report = generate_report.report_markdown(
        _minimal_results(tmp_path),
        run_fact_check=False,
        provider=None,
    )

    # Markdown 不包含 QA JSON
    assert isinstance(markdown, str)
    assert len(markdown) > 0
    assert "section_qa" not in markdown
    assert "overall_passed" not in markdown

    # report["section_qa"] 存在且 JSON 可序列化
    import json
    section_qa = report.get("section_qa")
    assert section_qa is not None
    assert isinstance(section_qa, dict)
    json.dumps(section_qa)  # 验证可序列化

    # 至少包含 §1 和 §5 的 QA 结果
    assert "1" in section_qa
    assert "5" in section_qa

    # 每个 section QA 结果包含必需字段
    for sid in ("1", "5"):
        qa = section_qa[sid]
        assert "overall_passed" in qa
        assert "blockers" in qa
        assert "critical_issues" in qa
        assert "improvements" in qa
        assert "word_count" in qa
        assert "evidence_refs_count" in qa
        assert "time_anchor_count" in qa
        assert isinstance(qa["overall_passed"], bool)
        assert isinstance(qa["blockers"], list)
        assert isinstance(qa["critical_issues"], list)
        assert isinstance(qa["improvements"], list)
        assert isinstance(qa["word_count"], int)
        assert isinstance(qa["evidence_refs_count"], int)
        assert isinstance(qa["time_anchor_count"], int)


def test_report_markdown_reuses_provider_responses_for_qa_and_debug_render(tmp_path):
    """Phase 3: QA assembly + debug render must not double-call real writer prompts."""
    import run_quality_gate

    calls = []

    def counting_fixture_provider(system, user):
        calls.append((system, user))
        return run_quality_gate.fixture_writer_provider(system, user)

    markdown, report = generate_report.report_markdown(
        _minimal_results(tmp_path),
        run_fact_check=False,
        provider=counting_fixture_provider,
    )

    assert "section_qa" not in markdown
    assert set((report.get("section_qa") or {}).keys()) >= {"1", "3", "4", "5", "6", "7"}
    assert len(calls) == len(set(calls))
    assert len(calls) == 3  # §3/§4/§7 prompts; render_debug_markdown hits cache
