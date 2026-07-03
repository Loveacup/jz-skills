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
    assert calls[0]["provider"] is fake_provider
    assert calls[0]["draft"].artifact_kind == "draft_report"
    assert calls[0]["draft"].publishable is False
