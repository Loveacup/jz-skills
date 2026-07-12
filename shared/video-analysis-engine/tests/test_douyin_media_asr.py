import json
import subprocess
from pathlib import Path

import pytest

import evidence_contract as ec
import platform_router as pr
from adapters.douyin import DouyinAdapter
from providers.douyin_media_asr import DouyinMediaAsrProvider
from providers.ytdlp import YtDlpMetadataProvider


FIXTURE = Path(__file__).parent / "fixtures" / "douyin_ytdlp_metadata.json"
URL = "https://www.douyin.com/video/7591234567890123456"
NOW = lambda: "2026-07-11T00:00:00Z"


class _Response:
    status_code = 200

    def json(self):
        return {"text": "这段视频提出了一个明确观点，并说明了适用边界。"}


class _Post:
    def __init__(self):
        self.calls = []

    def __call__(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        return _Response()


def _metadata_provider(url, timeout):
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_media_asr_provider_downloads_one_audio_and_posts_h200(tmp_path):
    observed = {}
    post = _Post()

    def runner(argv, **kwargs):
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        template = Path(argv[argv.index("-o") + 1])
        template.with_name("audio.wav").write_bytes(b"RIFF-fixture")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=runner,
        post=post,
        temp_root=tmp_path,
    )
    payload = provider(URL, 30)
    assert payload["transcript_text"].startswith("这段视频")
    assert payload["transcript_source"] == "h200-asr"
    assert payload["transcript_language"] == "zh"
    assert observed["kwargs"]["shell"] is False
    assert "--no-playlist" in observed["argv"]
    assert "--playlist-items" not in observed["argv"]
    assert post.calls[0][0] == "http://h200.test/ASR/transcribe"
    assert post.calls[0][1]["data"] == {"language": "Chinese"}
    assert list(tmp_path.iterdir()) == []


def test_enriched_payload_makes_douyin_bundle_ready(tmp_path):
    def provider(url, timeout):
        payload = _metadata_provider(url, timeout)
        payload["transcript_text"] = "视频观点与边界。"
        payload["transcript_source"] = "h200-asr"
        payload["transcript_language"] = "zh"
        return payload

    bundle = DouyinAdapter(provider=provider, clock=NOW).collect(
        pr.SourceInput(URL), pr.CollectOptions()
    )
    assert bundle.status == "ready"
    assert bundle.transcript.source == "h200-asr"
    assert bundle.provenance.hashes["transcript"].startswith("sha256:")
    ec.validate_bundle(bundle)
    assert ec.is_publishable(bundle) is True


def test_download_failure_does_not_leak_cli_stderr(tmp_path):
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="cookie=secret")

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=runner,
        post=_Post(),
        temp_root=tmp_path,
    )
    bundle = DouyinAdapter(provider=provider, clock=NOW).collect(
        pr.SourceInput(URL), pr.CollectOptions()
    )
    assert bundle.status == "unavailable"
    assert "secret" not in bundle.errors[0].safe_message
    ec.validate_bundle(bundle)


def test_from_env_prefers_video_analysis_names():
    provider = DouyinMediaAsrProvider.from_env(
        metadata_provider=YtDlpMetadataProvider(),
        env={
            "VIDEO_ANALYSIS_ASR_ENDPOINT": "http://canonical.test/asr",
            "VIDEO_ANALYSIS_ASR_LANGUAGE": "en",
            "BILI_ASR_ENDPOINT": "http://legacy.test/asr",
        },
    )
    assert provider._endpoint == "http://canonical.test/asr"
    assert provider._language == "en"


def test_from_env_reads_runtime_endpoint_file(tmp_path):
    endpoint_file = tmp_path / "asr_endpoint"
    endpoint_file.write_text("http://asr.example.test/transcribe\n")
    provider = DouyinMediaAsrProvider.from_env(
        metadata_provider=YtDlpMetadataProvider(),
        env={"VIDEO_ANALYSIS_ASR_ENDPOINT_FILE": str(endpoint_file)},
    )
    assert provider._endpoint == "http://asr.example.test/transcribe"


def test_from_env_accepts_legacy_alias_with_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="BILI_ASR_ENDPOINT"):
        provider = DouyinMediaAsrProvider.from_env(
            metadata_provider=YtDlpMetadataProvider(),
            env={"BILI_ASR_ENDPOINT": "http://legacy.test/asr"},
        )
    assert provider._endpoint == "http://legacy.test/asr"
