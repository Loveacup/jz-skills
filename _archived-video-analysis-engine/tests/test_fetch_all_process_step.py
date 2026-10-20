"""fetch_all 子进程输出边界的回归测试。"""

import fetch_all


def test_process_step_decodes_bytes_stderr_on_failed_subprocess(monkeypatch):
    monkeypatch.setattr(
        fetch_all,
        "run_script",
        lambda *args: (1, "stdout diagnostic", b"youtube downloader failed"),
    )

    result = fetch_all.process_step("YouTube评论", "fetch_youtube_comments.py", "https://example.com")

    assert result["status"] == "failed"
    assert result["returncode"] == 1
    assert "youtube downloader failed" in result["error"]
