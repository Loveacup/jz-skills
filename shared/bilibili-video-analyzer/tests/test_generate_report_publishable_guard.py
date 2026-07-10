from pathlib import Path

import generate_report


def test_formal_output_path_detection_for_bilibili_note_name(tmp_path):
    formal = tmp_path / "B站笔记_坏稿_20260703.md"
    casual = tmp_path / "debug_report.md"

    assert generate_report.is_formal_report_output(formal) is True
    assert generate_report.is_formal_report_output(casual) is False


def test_formal_output_guard_blocks_unpublishable_markdown(tmp_path):
    formal = tmp_path / "B站笔记_坏稿_20260703.md"
    bad_markdown = "# B站笔记_坏稿\n\n## 0. 元信息\n\n_骨架占位：暂无证据候选。_\n"

    ok, summary = generate_report.check_formal_output_publishable(formal, bad_markdown)

    assert ok is False
    assert summary["passed"] is False
    assert "P0_NO_SKELETON" in summary["failed_codes"]


def test_formal_output_guard_skips_nonformal_debug_paths(tmp_path):
    casual = tmp_path / "debug_report.md"
    bad_markdown = "# debug\n\n_骨架占位：暂无证据候选。_\n"

    ok, summary = generate_report.check_formal_output_publishable(casual, bad_markdown)

    assert ok is True
    assert summary["skipped"] is True


def test_formal_output_guard_combines_versioned_claim_evidence_gate(tmp_path, monkeypatch):
    formal = tmp_path / "B站笔记_证据缺失_20260710.md"
    good_markdown = "## 0. 元信息\n\n## 1. 逻辑链\n\n| a | b |\n| --- | --- |\n\n## 2. 弹幕\n\n正文\n\n## 2.5 评论\n\n正文\n\n## 3. 洞察\n\n正文\n\n## 4. 深拆\n\n正文\n\n## 5. 高光\n\n> 短引文\n\n## 6. 图谱\n\n正文\n\n## 7. 行动\n\n正文\n\n## 8. 附录\n\n正文\n"
    report = {
        "claim_bundle": {
            "evidence_contract_version": 1,
            "claims": [{"id": "C1", "source_type": "transcript", "evidence_locations": []}],
        },
        "evidence_map": {"by_section": {"3": []}},
    }

    monkeypatch.setattr(
        generate_report.verify_publishable_report,
        "evaluate",
        lambda _markdown: ({"P0_MARKDOWN": {"pass": True, "measured": "ok", "reason": "ok"}}, True),
    )
    ok, summary = generate_report.check_formal_output_publishable(formal, good_markdown, report)

    assert ok is False
    assert "P0_CLAIM_EVIDENCE_SCORE" in summary["failed_codes"]
    assert summary["gates"]["P0_CLAIM_EVIDENCE_SCORE"]["measured"]["unsupported_claim_ids"] == ["C1"]


def test_formal_output_guard_blocks_unresolved_final_markdown_citation(tmp_path, monkeypatch):
    formal = tmp_path / "B站笔记_正文错误引用_20260710.md"
    markdown = "## 3. 核心洞察\n正文 [E99]\n\n## 4. 深拆\n正文 [E1]"
    report = {
        "claim_bundle": {
            "evidence_contract_version": 1,
            "claims": [
                {"id": "C1", "source_type": "transcript", "evidence_locations": ["3:E1"]},
            ],
        },
        "evidence_map": {
            "by_section": {
                "3": [{"source_type": "transcript", "text": "§3 evidence", "start": 10}],
                "4": [{"source_type": "transcript", "text": "§4 evidence", "start": 20}],
            }
        },
    }

    monkeypatch.setattr(
        generate_report.verify_publishable_report,
        "evaluate",
        lambda _markdown: ({"P0_MARKDOWN": {"pass": True, "measured": "ok", "reason": "ok"}}, True),
    )
    ok, summary = generate_report.check_formal_output_publishable(formal, markdown, report)

    assert ok is False
    assert "P0_VIDEO_EVIDENCE_USAGE" in summary["failed_codes"]
    assert summary["gates"]["P0_VIDEO_EVIDENCE_USAGE"]["measured"]["sections"]["3"]["unresolved_refs"] == ["E99"]
