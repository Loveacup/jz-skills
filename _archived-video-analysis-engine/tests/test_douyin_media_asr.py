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


# --- Fallback seam tests (RED → GREEN) ---


@pytest.mark.parametrize("trigger", ["nonzero", "timeout", "no_output"])
def test_fallback_runs_once_after_ytdlp_failure(tmp_path, trigger):
    """Fallback runs exactly once after yt-dlp nonzero/timeout/no-output."""
    fallback_calls = []
    post = _Post()

    def failing_runner(argv, **kwargs):
        if trigger == "nonzero":
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
        elif trigger == "timeout":
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 30))
        else:  # no_output: exit 0 but write nothing
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    def my_fallback(url, tmpdir, timeout_s):
        fallback_calls.append((url, str(tmpdir), timeout_s))
        audio = Path(tmpdir) / "fallback_audio.wav"
        audio.write_bytes(b"RIFF-fallback")
        return audio

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=failing_runner,
        post=post,
        temp_root=tmp_path,
        media_fallback=my_fallback,
    )
    payload = provider(URL, 30)

    assert len(fallback_calls) == 1, "fallback must be called exactly once"
    assert fallback_calls[0][0] == URL
    assert Path(fallback_calls[0][1]).parent == tmp_path
    assert fallback_calls[0][2] == 30
    assert len(post.calls) == 1, "H200 must receive the fallback audio"
    assert post.calls[0][0] == "http://h200.test/ASR/transcribe"
    uploaded = post.calls[0][1]["files"]["file"]
    assert uploaded[0] == "fallback_audio.wav"
    assert uploaded[2] == "audio/wav"
    assert list(tmp_path.iterdir()) == [], "temp_root must be empty after call"
    assert payload["transcript_source"] == "h200-asr"


def test_fallback_not_called_when_ytdlp_succeeds(tmp_path):
    """Fallback is NOT called when yt-dlp succeeds."""
    fallback_calls = []

    def my_fallback(url, tmpdir, timeout_s):
        fallback_calls.append(url)
        return Path(tmpdir) / "should_not_be_called.wav"

    def runner(argv, **kwargs):
        template = Path(argv[argv.index("-o") + 1])
        template.with_name("audio.wav").write_bytes(b"RIFF-primary")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=runner,
        post=_Post(),
        temp_root=tmp_path,
        media_fallback=my_fallback,
    )
    provider(URL, 30)
    assert fallback_calls == [], "fallback must not be called when yt-dlp succeeds"


def test_outside_path_rejected_before_h200(tmp_path):
    """Fallback returning a path outside tmpdir raises exact error; H200 not called; external file untouched."""
    external_file = tmp_path / "external_secret.wav"
    external_file.write_bytes(b"DO-NOT-TOUCH")
    post = _Post()

    provider_root = tmp_path / "provider"
    provider_root.mkdir()

    def my_fallback(url, tmpdir, timeout_s):
        return external_file

    def failing_runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=failing_runner,
        post=post,
        temp_root=provider_root,
        media_fallback=my_fallback,
    )
    with pytest.raises(RuntimeError, match=r"^Douyin browser media resolver returned unsafe path$"):
        provider(URL, 30)

    assert post.calls == [], "H200 must not be called"
    assert external_file.read_bytes() == b"DO-NOT-TOUCH", "external file must be untouched"


def test_symlink_inside_tmpdir_targeting_outside_rejected(tmp_path):
    """Symlink inside tmpdir pointing to external file raises exact error; H200 not called; target untouched."""
    external_file = tmp_path / "real_audio.wav"
    external_file.write_bytes(b"DO-NOT-TOUCH-SYMLINK-TARGET")
    post = _Post()

    provider_root = tmp_path / "provider"
    provider_root.mkdir()

    def my_fallback(url, tmpdir, timeout_s):
        link = Path(tmpdir) / "link.wav"
        link.symlink_to(external_file)
        return link

    def failing_runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=failing_runner,
        post=post,
        temp_root=provider_root,
        media_fallback=my_fallback,
    )
    with pytest.raises(RuntimeError, match=r"^Douyin browser media resolver returned unsafe path$"):
        provider(URL, 30)

    assert post.calls == [], "H200 must not be called"
    assert external_file.read_bytes() == b"DO-NOT-TOUCH-SYMLINK-TARGET"


def test_resolver_exception_sanitized_through_adapter(tmp_path):
    """Resolver exception containing fake token is sanitized; no secret in safe_message or provenance."""
    import evidence_contract as ec
    import platform_router as pr

    secret = "cookie=abc123&signed_url=https://secret.cdn/token=XYZ"

    def my_fallback(url, tmpdir, timeout_s):
        raise RuntimeError(f"Failed to resolve: {secret}")

    def failing_runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    provider = DouyinMediaAsrProvider(
        metadata_provider=_metadata_provider,
        endpoint="http://h200.test/ASR/transcribe",
        runner=failing_runner,
        post=_Post(),
        temp_root=tmp_path,
        media_fallback=my_fallback,
    )

    bundle = DouyinAdapter(provider=provider, clock=NOW).collect(
        pr.SourceInput(URL), pr.CollectOptions()
    )

    assert bundle.status == "unavailable"
    safe_msg = bundle.errors[0].safe_message
    for fragment in ("cookie", "abc123", "signed_url", "token", "XYZ"):
        assert fragment not in safe_msg, f"secret fragment '{fragment}' must not appear in safe_message"

    provenance_str = str(bundle.provenance)
    for fragment in ("cookie", "abc123", "XYZ"):
        assert fragment not in provenance_str, f"secret fragment '{fragment}' must not appear in provenance"

    ec.validate_bundle(bundle)
