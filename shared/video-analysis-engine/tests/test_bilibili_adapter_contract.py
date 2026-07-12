import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

import evidence_contract as ec
import platform_router as pr
from adapters.bilibili import BilibiliAdapter


FIXTURE = Path(__file__).parent / "fixtures" / "bilibili_bundle_v4.json"
SOURCE = pr.SourceInput(raw="https://www.bilibili.com/video/BV14fTc6TEi5")
NOW = lambda: "2026-07-11T00:00:00Z"


def _payload(transcript=True):
    subtitle = {
        "method": "fixture-official",
        "language": "zh-Hans",
        "duration": 62,
    }
    if transcript:
        subtitle["text"] = "第一段提出 Pi 的核心能力。第二段说明使用边界。"
    return {
        "bvid": "BV14fTc6TEi5",
        "title": "Pi 编程智能体",
        "author": "fixture-author",
        "description": "用于验证 Bilibili Adapter。",
        "subtitle": subtitle,
        "comments": {
            "hot_comments": [
                {"content": "希望补充边界条件", "like": 12},
            ]
        },
        "danmaku": {"data": [{"text": "这个观点有意思", "time_sec": 5}]},
    }


def _adapter(payload):
    return BilibiliAdapter(collector=lambda source, options: payload, clock=NOW)


def test_adapter_satisfies_platform_contract_and_handles_only_bilibili():
    adapter = _adapter(_payload())
    assert isinstance(adapter, pr.PlatformAdapter)
    assert adapter.can_handle(SOURCE) is True
    assert adapter.can_handle(pr.SourceInput("https://youtu.be/dQw4w9WgXcQ")) is False


def test_ready_payload_normalizes_to_golden_bundle():
    bundle = _adapter(_payload()).collect(SOURCE, pr.CollectOptions())
    ec.validate_bundle(bundle)
    actual = json.loads(json.dumps(asdict(bundle), ensure_ascii=False))
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    digest = "sha256:" + hashlib.sha256(bundle.transcript.text.encode("utf-8")).hexdigest()
    expected["transcript"]["content_hash"] = digest
    expected["provenance"]["hashes"]["transcript"] = digest
    assert actual == expected
    assert ec.is_publishable(bundle) is True


def test_missing_transcript_degrades_to_metadata_only():
    bundle = _adapter(_payload(transcript=False)).collect(SOURCE, pr.CollectOptions())
    assert bundle.status == "metadata_only"
    assert bundle.transcript is None
    assert any(error.code == "transcript_unavailable" for error in bundle.errors)
    ec.validate_bundle(bundle)
    assert ec.is_publishable(bundle) is False


def test_collector_failure_returns_safe_unavailable_without_exception_text():
    def fail(source, options):
        raise RuntimeError("cookie=SESSDATA=secret")

    bundle = BilibiliAdapter(collector=fail, clock=NOW).collect(SOURCE, pr.CollectOptions())
    assert bundle.status == "unavailable"
    assert bundle.metadata == {}
    assert bundle.transcript is None
    assert "secret" not in bundle.errors[0].safe_message
    assert "cookie" not in bundle.errors[0].safe_message.lower()
    ec.validate_bundle(bundle)


def test_private_raw_payload_is_not_copied_into_metadata():
    payload = _payload()
    payload["raw_response"] = {"cookie": "secret"}
    payload["subtitle"]["raw_payload"] = {"token": "secret"}
    bundle = _adapter(payload).collect(SOURCE, pr.CollectOptions())
    assert set(bundle.metadata) == {"title", "author", "description", "duration_s"}
    ec.validate_bundle(bundle)


def test_txt_path_is_supported_as_legacy_transcript_source(tmp_path):
    transcript_path = tmp_path / "subtitle.txt"
    transcript_path.write_text("从旧 txt_path 读取的字幕。", encoding="utf-8")
    payload = _payload(transcript=False)
    payload["subtitle"]["txt_path"] = str(transcript_path)
    bundle = _adapter(payload).collect(SOURCE, pr.CollectOptions())
    assert bundle.status == "ready"
    assert bundle.transcript.text == "从旧 txt_path 读取的字幕。"
    assert bundle.transcript.source == "fixture-official"
    ec.validate_bundle(bundle)


def test_empty_payload_is_unavailable_with_stable_identity():
    bundle = _adapter({}).collect(SOURCE, pr.CollectOptions())
    assert bundle.status == "unavailable"
    assert bundle.identity.platform == "bilibili"
    assert bundle.identity.canonical_id == "BV14fTc6TEi5"
    assert bundle.metadata == {}
    ec.validate_bundle(bundle)
