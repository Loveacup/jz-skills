# -*- coding: utf-8 -*-
"""回归：fetch_all --report 不得在无 transcript 时生成正式报告。

verify_report.py 只能验证结构深度，不能证明来源充分。fetch_all.generate_report()
必须在写 /tmp/{BV}_report.md 前检查 report.frontmatter.has_transcript。
"""

import os

import fetch_all


def test_generate_report_skips_formal_report_without_transcript(monkeypatch):
    bvid = "BV_NO_TRANSCRIPT_GATE"
    report_path = f"/tmp/{bvid}_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    def fake_report_markdown(results, run_fact_check=True):
        return (
            "# thin but structured markdown should not matter\n",
            {"frontmatter": {"has_transcript": False, "comment_count": 3, "danmaku_count": 0}},
        )

    import generate_report
    monkeypatch.setattr(generate_report, "report_markdown", fake_report_markdown)

    assert fetch_all.generate_report({"bvid": bvid, "subtitle": {"status": "failed"}}, bvid) is None
    assert not os.path.exists(report_path)


def test_generate_report_writes_when_transcript_exists(monkeypatch):
    bvid = "BV_WITH_TRANSCRIPT_GATE"
    report_path = f"/tmp/{bvid}_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    def fake_report_markdown(results, run_fact_check=True):
        return (
            "# formal report with transcript\n",
            {"frontmatter": {"has_transcript": True, "comment_count": 0, "danmaku_count": 0}},
        )

    import generate_report
    monkeypatch.setattr(generate_report, "report_markdown", fake_report_markdown)

    assert fetch_all.generate_report({"bvid": bvid}, bvid) == report_path
    assert os.path.exists(report_path)
    assert open(report_path, encoding="utf-8").read().startswith("# formal report")
    os.remove(report_path)
