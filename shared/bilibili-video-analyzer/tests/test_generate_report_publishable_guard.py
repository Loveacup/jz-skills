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
