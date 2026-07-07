# -*- coding: utf-8 -*-
"""回归：fetch_all --report 不得在无 transcript 时生成正式报告。

verify_report.py 只能验证结构深度，不能证明来源充分。fetch_all.generate_report()
必须在写 /tmp/{BV}_report.md 前检查 report.frontmatter.has_transcript。

任务包 1 新增测试：
- 验证 fetch_all.generate_report() 传入 provider、depth_profile、claim_qa_gate
- 验证 writer 不可用时不生成报告
"""

import os
from unittest.mock import patch

import fetch_all


def test_generate_report_skips_formal_report_without_transcript(monkeypatch):
    bvid = "BV_NO_TRANSCRIPT_GATE"
    report_path = f"/tmp/{bvid}_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    def fake_report_markdown(results, run_fact_check=True, provider=None, depth_profile="standard", claim_qa_gate=False):
        return (
            "# thin but structured markdown should not matter\n",
            {"frontmatter": {"has_transcript": False, "comment_count": 3, "danmaku_count": 0}},
        )

    import generate_report
    monkeypatch.setattr(generate_report, "report_markdown", fake_report_markdown)

    # 模拟 writer 可用（否则会提前失败）
    monkeypatch.setenv('BILI_WRITER_CLI', '/usr/bin/omp')

    assert fetch_all.generate_report({"bvid": bvid, "subtitle": {"status": "failed"}}, bvid) is None
    assert not os.path.exists(report_path)


def test_generate_report_writes_when_transcript_exists(monkeypatch):
    bvid = "BV_WITH_TRANSCRIPT_GATE"
    report_path = f"/tmp/{bvid}_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    def fake_report_markdown(results, run_fact_check=True, provider=None, depth_profile="standard", claim_qa_gate=False):
        return (
            "# formal report with transcript\n",
            {"frontmatter": {"has_transcript": True, "comment_count": 0, "danmaku_count": 0}},
        )

    import generate_report
    monkeypatch.setattr(generate_report, "report_markdown", fake_report_markdown)

    # 模拟 writer 可用（设置环境变量）
    monkeypatch.setenv('BILI_WRITER_CLI', '/usr/bin/omp')

    assert fetch_all.generate_report({"bvid": bvid}, bvid) == report_path
    assert os.path.exists(report_path)
    assert open(report_path, encoding="utf-8").read().startswith("# formal report")
    os.remove(report_path)


def test_fetch_all_report_uses_default_writer_and_claim_first_depth(monkeypatch):
    """任务包1：验证 fetch_all.generate_report() 传入正确的 provider、depth_profile、claim_qa_gate 参数。"""
    from generate_report import cli_writer_provider

    bvid = "BV_PARAM_CHECK"
    report_path = f"/tmp/{bvid}_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    # 模拟 writer 可用
    monkeypatch.setenv('BILI_WRITER_CLI', '/usr/bin/omp')

    # monkeypatch report_markdown，记录传入的参数
    def fake_report_markdown(results, run_fact_check=True, provider=None, depth_profile="standard", claim_qa_gate=False):
        # 验证参数传递
        assert provider is cli_writer_provider, "应传入 cli_writer_provider 而非 None"
        assert depth_profile == "claim-first-full", "应传入 depth_profile='claim-first-full'"
        assert claim_qa_gate is True, "应传入 claim_qa_gate=True"

        return (
            "# Test Report\n",
            {
                'frontmatter': {'has_transcript': True, 'video_id': bvid},
                'evidence_gate': {'can_generate_formal_report': True},
            }
        )

    import generate_report
    monkeypatch.setattr(generate_report, "report_markdown", fake_report_markdown)

    result = fetch_all.generate_report({"bvid": bvid}, bvid)
    assert result == report_path, "应成功生成报告"
    if os.path.exists(report_path):
        os.remove(report_path)


def test_fetch_all_report_does_not_write_when_writer_unavailable(monkeypatch, tmp_path):
    """任务包1：当 writer 不可用时（BILI_WRITER_CLI 未设置且 omp 不存在），不应生成报告文件。"""
    bvid = "BV_NO_WRITER"
    report_path = f"/tmp/{bvid}_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    # 清空环境变量，模拟 writer 不可用
    monkeypatch.delenv('BILI_WRITER_CLI', raising=False)

    # 模拟 /opt/homebrew/bin/omp 不存在 — 使用 monkeypatch 替换 fetch_all 模块内的 os.path.exists
    import fetch_all as fa_module
    original_exists = os.path.exists

    def fake_exists(path):
        if path == '/opt/homebrew/bin/omp':
            return False
        # 其他路径调用真实的 exists
        return original_exists(path)

    # 注意：需要在 fetch_all 模块的命名空间中替换，因为 generate_report 函数内 import os
    monkeypatch.setattr('fetch_all.os.path.exists', fake_exists)

    result = fa_module.generate_report({"bvid": bvid}, bvid)

    # 应返回 None（writer 不可用时提前失败）
    assert result is None, "writer 不可用时应返回 None，不生成报告"

    # 验证没有写入报告文件（使用原始 exists 检查）
    assert not original_exists(report_path), f"不应生成报告文件: {report_path}"
