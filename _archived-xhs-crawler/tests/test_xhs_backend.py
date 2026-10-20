"""XHS-Downloader 后端胶水层：subprocess 边界的分类与编排。

子进程边界（stdin=url，stdout=JSON）既是 Python 版本隔离层，也是 mock 缝：
单元测试通过注入 runner_fn 完全避开真实子进程与网络。

覆盖：成功 / 后端失败 / 坏 JSON / 非零退出 / 超时 / IP 风控(300012) 六分支，
以及「永远传 cookie=''」「跑前规范化 URL」「非法 URL 短路不起子进程」。
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import xhs_backend  # noqa: E402
from xhs_backend import build_command, classify, fetch_note  # noqa: E402

SAMPLE = {
    "评论数量": "15",
    "作品标签": "Obsidian AI工具",
    "作品ID": "6a116dd8000000003502a688",
    "作品标题": "",
    "作品描述": "标题在这里\n正文...",
    "作品类型": "图文",
    "作者昵称": "艾康的AI自留地",
    "作者ID": "65e17d09000000000500d97b",
    "发布时间": "2026-05-23_20:01:14",
    "点赞数量": "959",
    "收藏数量": "1641",
    "分享数量": "190",
    "下载地址": ["u1", "u2", "u3"],
}


def _ok_stdout(data=SAMPLE):
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _fake_runner(returncode, stdout, stderr="", record=None):
    """造一个可注入的 runner_fn，签名 (cmd, timeout) -> (rc, out, err)。"""

    def runner(cmd, timeout):
        if record is not None:
            record["cmd"] = cmd
            record["timeout"] = timeout
        return returncode, stdout, stderr

    return runner


# ---- build_command：cookie 契约 -------------------------------------------


def test_build_command_defaults_cookie_empty():
    cmd = build_command("https://www.xiaohongshu.com/explore/abc?xsec_token=t")
    # 永远传 cookie="" 这个空字符串元素（免登录关键）
    assert cmd[-1] == ""
    assert "https://www.xiaohongshu.com/explore/abc?xsec_token=t" in cmd


def test_build_command_passes_explicit_cookie():
    cmd = build_command("https://xhslink.com/o/x", cookie="web_session=y")
    assert cmd[-1] == "web_session=y"


# ---- classify：纯分类 -----------------------------------------------------


def test_classify_ok():
    r = classify(0, _ok_stdout(), "")
    assert r["status"] == "ok"
    assert r["data"]["作品ID"] == "6a116dd8000000003502a688"
    assert r["stop_loss"] is False


def test_classify_backend_failed():
    r = classify(0, json.dumps({"ok": False, "data": None}), "")
    assert r["status"] == "failed"


def test_classify_malformed_json():
    r = classify(0, "这不是 JSON", "")
    assert r["status"] == "error"


def test_classify_ok_with_leading_progress_chatter():
    # 真实库会把进度行打到 stdout，排在 JSON 之前；classify 必须只认最后那行 JSON
    chatter = (
        "共 1 个小红书作品待处理...\n"
        "开始处理作品：6a116dd8000000003502a688\n"
        "作品处理完成：6a116dd8000000003502a688\n"
    ) + _ok_stdout()
    r = classify(0, chatter, "")
    assert r["status"] == "ok"
    assert r["data"]["作品ID"] == "6a116dd8000000003502a688"


def test_classify_nonzero_returncode():
    r = classify(1, "", "Traceback (most recent call last): ...")
    assert r["status"] == "error"
    assert r["stop_loss"] is False


def test_classify_ip_risk_in_stderr():
    r = classify(1, "", "request failed: error_code 300012 IP at risk")
    assert r["status"] == "ip_risk"
    assert r["stop_loss"] is True


def test_classify_ip_risk_in_stdout():
    r = classify(0, "...风控 300012...", "")
    assert r["status"] == "ip_risk"
    assert r["stop_loss"] is True


# ---- fetch_note：端到端编排（注入 runner_fn）-------------------------------


def test_fetch_note_success_returns_report_input():
    out = fetch_note(
        "https://www.xiaohongshu.com/explore/6a116dd8000000003502a688?xsec_token=t",
        runner_fn=_fake_runner(0, _ok_stdout()),
    )
    assert out["status"] == "ok"
    # 走了适配器：作者 + 评论标注
    assert out["report_input"]["author"] == "艾康的AI自留地"
    assert out["report_input"]["comments"].startswith("[评论数据不足")


def test_fetch_note_backend_failure_no_report_input():
    out = fetch_note(
        "https://xhslink.com/o/x",
        runner_fn=_fake_runner(0, json.dumps({"ok": False, "data": None})),
    )
    assert out["status"] == "failed"
    assert out["report_input"] is None


def test_fetch_note_timeout():
    def boom(cmd, timeout):
        raise TimeoutError("runner timed out")

    out = fetch_note("https://xhslink.com/o/x", runner_fn=boom)
    assert out["status"] == "timeout"


def test_fetch_note_ip_risk_sets_stop_loss():
    out = fetch_note(
        "https://xhslink.com/o/x",
        runner_fn=_fake_runner(1, "", "error_code 300012 IP at risk"),
    )
    assert out["status"] == "ip_risk"
    assert out["stop_loss"] is True


def test_fetch_note_invalid_url_short_circuits():
    def must_not_run(cmd, timeout):
        raise AssertionError("非法 URL 不应该起子进程")

    out = fetch_note("just garbage text", runner_fn=must_not_run)
    assert out["status"] == "invalid_url"


def test_fetch_note_normalizes_url_before_run():
    record = {}
    raw = (
        "看看 https://www.xiaohongshu.com/explore/"
        "6a116dd8000000003502a688?xsec_token=ABC 真不错"
    )
    fetch_note(raw, runner_fn=_fake_runner(0, _ok_stdout(), record=record))
    # 子进程收到的是去掉「看看 / 真不错」、且 token 完好的干净链接
    cleaned = (
        "https://www.xiaohongshu.com/explore/"
        "6a116dd8000000003502a688?xsec_token=ABC"
    )
    assert cleaned in record["cmd"]


def test_fetch_note_always_passes_empty_cookie_by_default():
    record = {}
    fetch_note(
        "https://xhslink.com/o/x",
        runner_fn=_fake_runner(0, _ok_stdout(), record=record),
    )
    assert record["cmd"][-1] == ""


def test_fetch_note_preserves_original_url_in_result():
    url = "https://www.xiaohongshu.com/explore/6a116dd8000000003502a688?xsec_token=t"
    out = fetch_note(url, runner_fn=_fake_runner(0, _ok_stdout()))
    # report_input 里的 url 应是规范化后的原链接（带 token）
    assert out["report_input"]["url"] == url
