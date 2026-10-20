import json
from pathlib import Path

import evidence_contract as ec
import platform_router as pr
from adapters.youtube import YouTubeAdapter, YtDlpYouTubeProvider, extract_youtube_url
from providers.youtube_ytdlp import YtDlpYouTubeProvider as ProviderImplementation


FIXTURE = Path(__file__).parent / "fixtures" / "youtube_provider_payload.json"
URL = "https://www.youtube.com/watch?v=6xXjHM3V1zM"
NOW = lambda: "2026-07-11T00:00:00Z"


def _payload(with_transcript=True):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not with_transcript:
        for key in ("transcript_text", "transcript_language", "transcript_source"):
            payload.pop(key, None)
    return payload


def test_youtube_adapter_exports_platform_specific_provider():
    assert YtDlpYouTubeProvider is ProviderImplementation


def test_extracts_exactly_one_youtube_url():
    assert extract_youtube_url(f"Original source: {URL}") == URL
    assert extract_youtube_url("https://youtu.be/6xXjHM3V1zM") == "https://youtu.be/6xXjHM3V1zM"


def test_ready_payload_normalizes_transcript_comments_and_metadata():
    adapter = YouTubeAdapter(provider=lambda url, timeout: _payload(), clock=NOW)
    bundle = adapter.collect(pr.SourceInput(URL), pr.CollectOptions())
    assert bundle.status == "ready"
    assert bundle.identity.platform == "youtube"
    assert bundle.identity.canonical_id == "6xXjHM3V1zM"
    assert bundle.identity.canonical_url == URL
    assert bundle.transcript.source == "youtube-transcript-api"
    assert bundle.transcript.language == "en"
    assert bundle.provenance.hashes["transcript"].startswith("sha256:")
    assert [(s.kind, s.label, s.weight) for s in bundle.audience_signals] == [
        ("comment", "The boundary discussion was useful.", 19.0)
    ]
    assert bundle.metadata["duration_s"] == 1286
    serialized = json.dumps(bundle.metadata, ensure_ascii=False).lower()
    assert "private-media" not in serialized
    assert "authorization" not in serialized
    assert "token" not in serialized
    ec.validate_bundle(bundle)
    assert ec.is_publishable(bundle) is True


def test_adapter_preserves_typed_transcript_segments():
    payload = _payload()
    payload["transcript_segments"] = [
        {"start": 1.5, "end": 3.0, "text": "First cue"},
        {"start": 8.0, "end": 10.0, "text": "Second cue"},
    ]
    bundle = YouTubeAdapter(provider=lambda url, timeout: payload, clock=NOW).collect(
        pr.SourceInput(URL), pr.CollectOptions()
    )
    assert [(s.start, s.end, s.text) for s in bundle.transcript.segments] == [
        (1.5, 3.0, "First cue"),
        (8.0, 10.0, "Second cue"),
    ]


def test_ytdlp_metadata_without_transcript_is_metadata_only():
    adapter = YouTubeAdapter(provider=lambda url, timeout: _payload(False), clock=NOW)
    bundle = adapter.collect(pr.SourceInput(URL), pr.CollectOptions())
    assert bundle.status == "metadata_only"
    assert bundle.transcript is None
    assert any(error.code == "transcript_unavailable" for error in bundle.errors)
    ec.validate_bundle(bundle)
    assert ec.is_publishable(bundle) is False


def test_provider_failure_is_safe_unavailable():
    def fail(url, timeout):
        raise RuntimeError("Authorization: Bearer secret")

    adapter = YouTubeAdapter(provider=fail, clock=NOW)
    bundle = adapter.collect(pr.SourceInput(URL), pr.CollectOptions())
    assert bundle.status == "unavailable"
    assert bundle.metadata == {}
    assert "secret" not in bundle.errors[0].safe_message
    ec.validate_bundle(bundle)


def test_adapter_handles_only_unambiguous_youtube_source():
    adapter = YouTubeAdapter(provider=lambda url, timeout: _payload(), clock=NOW)
    assert adapter.can_handle(pr.SourceInput(URL)) is True
    assert adapter.can_handle(pr.SourceInput("https://v.douyin.com/AbCd1234/")) is False
    assert adapter.can_handle(pr.SourceInput(f"{URL} https://v.douyin.com/AbCd1234/")) is False
