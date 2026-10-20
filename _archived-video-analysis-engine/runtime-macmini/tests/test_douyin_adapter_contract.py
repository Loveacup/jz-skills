import json
import subprocess
from pathlib import Path

import pytest

import evidence_contract as ec
import platform_router as pr
from adapters.douyin import DouyinAdapter, YtDlpDouyinProvider, extract_douyin_url


FIXTURE = Path(__file__).parent / "fixtures" / "douyin_ytdlp_metadata.json"
SHARE_URL = "https://v.douyin.com/AbCd1234/"
SHARE_TEXT = f"7.99 复制打开抖音，看看【作者的作品】 {SHARE_URL}"
NOW = lambda: "2026-07-11T00:00:00Z"


def _metadata():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_extracts_single_douyin_url_from_share_text():
    assert extract_douyin_url(SHARE_TEXT) == SHARE_URL
    with pytest.raises(ValueError):
        extract_douyin_url("没有视频链接")
    with pytest.raises(ValueError):
        extract_douyin_url(f"{SHARE_URL} https://www.douyin.com/video/7591234567890123456")


def test_ytdlp_provider_uses_argv_without_shell_and_parses_json(monkeypatch):
    observed = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(_metadata()), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = YtDlpDouyinProvider(binary="yt-dlp").fetch(SHARE_URL, timeout_s=17)
    assert result["id"] == "7591234567890123456"
    assert observed["kwargs"]["shell"] is False
    assert observed["kwargs"]["timeout"] == 17
    assert "--skip-download" in observed["argv"]
    assert SHARE_URL == observed["argv"][-1]


def test_metadata_provider_normalizes_without_leaking_private_ytdlp_fields():
    adapter = DouyinAdapter(provider=lambda url, timeout: _metadata(), clock=NOW)
    bundle = adapter.collect(pr.SourceInput(SHARE_TEXT), pr.CollectOptions())
    assert bundle.status == "metadata_only"
    assert bundle.identity.platform == "douyin"
    assert bundle.identity.canonical_id == "7591234567890123456"
    assert bundle.identity.canonical_url == "https://www.douyin.com/video/7591234567890123456"
    assert bundle.metadata == {
        "title": "短视频证据契约示例",
        "author": "fixture-author",
        "description": "用于验证 Douyin Adapter 的 yt-dlp metadata 归一化。",
        "duration_s": 42,
        "published_at": 1783776000,
        "view_count": 1234,
        "like_count": 88,
        "comment_count": 7,
    }
    serialized = json.dumps(bundle.metadata, ensure_ascii=False).lower()
    assert "private-media" not in serialized
    assert "cookie" not in serialized
    assert "token" not in serialized
    assert ec.is_publishable(bundle) is False
    ec.validate_bundle(bundle)


def test_provider_auth_failure_maps_to_auth_required_without_leaking_stderr():
    def auth_fail(url, timeout):
        raise PermissionError("cookie=secret; login required")

    bundle = DouyinAdapter(provider=auth_fail, clock=NOW).collect(
        pr.SourceInput(SHARE_URL), pr.CollectOptions()
    )
    assert bundle.status == "auth_required"
    assert bundle.metadata == {}
    assert bundle.errors[0].code == "auth_required"
    assert "secret" not in bundle.errors[0].safe_message
    ec.validate_bundle(bundle)


def test_expired_or_platform_changed_link_is_unavailable():
    def unavailable(url, timeout):
        raise LookupError("redirected to homepage")

    bundle = DouyinAdapter(provider=unavailable, clock=NOW).collect(
        pr.SourceInput(SHARE_URL), pr.CollectOptions()
    )
    assert bundle.status == "unavailable"
    assert bundle.metadata == {}
    assert bundle.errors[0].code == "platform_changed"
    assert ec.is_publishable(bundle) is False
    ec.validate_bundle(bundle)


def test_provider_timeout_is_safe_retryable_unavailable():
    def timeout(url, timeout_s):
        raise TimeoutError("signed-url?access_token=secret")

    bundle = DouyinAdapter(provider=timeout, clock=NOW).collect(
        pr.SourceInput(SHARE_URL), pr.CollectOptions(timeout_s=3)
    )
    assert bundle.status == "unavailable"
    assert bundle.errors[0].retryable is True
    assert "secret" not in bundle.errors[0].safe_message
    ec.validate_bundle(bundle)


def test_adapter_handles_only_unambiguous_douyin_source():
    adapter = DouyinAdapter(provider=lambda url, timeout: _metadata(), clock=NOW)
    assert adapter.can_handle(pr.SourceInput(SHARE_TEXT)) is True
    assert adapter.can_handle(pr.SourceInput("https://youtu.be/dQw4w9WgXcQ")) is False
    ambiguous = f"{SHARE_URL} https://youtu.be/dQw4w9WgXcQ"
    assert adapter.can_handle(pr.SourceInput(ambiguous)) is False
