from providers.youtube_ytdlp import YtDlpYouTubeProvider


VTT = """WEBVTT

00:00:00.000 --> 00:00:01.000
<c>Hello world</c>

00:00:00.500 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:03.000
Second line
"""


class MetadataProvider:
    def __init__(self, payload):
        self.payload = payload

    def fetch(self, url, timeout_s):
        return dict(self.payload)


def test_prefers_manual_vtt_and_normalizes_transcript():
    payload = {
        "id": "MhjNYYAxGVI",
        "title": "Demo",
        "subtitles": {"en": [{"ext": "vtt", "url": "https://subs/manual.vtt"}]},
        "automatic_captions": {"en": [{"ext": "vtt", "url": "https://subs/auto.vtt"}]},
    }
    seen = []
    provider = YtDlpYouTubeProvider(
        metadata_provider=MetadataProvider(payload),
        fetch_text=lambda url, timeout: seen.append(url) or VTT,
    )
    result = provider.fetch("https://www.youtube.com/watch?v=MhjNYYAxGVI", 30)
    assert seen == ["https://subs/manual.vtt"]
    assert result["transcript_text"] == "Hello world Second line"
    assert result["transcript_language"] == "en"
    assert result["transcript_source"] == "youtube-manual-subtitles"
    assert result["transcript_segments"] == [
        {"start": 0.0, "end": 3.0, "text": "Hello world Second line"},
    ]


def test_falls_back_to_automatic_caption_language():
    payload = {
        "id": "MhjNYYAxGVI",
        "automatic_captions": {"en-US": [{"ext": "vtt", "url": "https://subs/auto.vtt"}]},
    }
    provider = YtDlpYouTubeProvider(
        metadata_provider=MetadataProvider(payload),
        fetch_text=lambda url, timeout: VTT,
    )
    result = provider.fetch("https://www.youtube.com/watch?v=MhjNYYAxGVI", 30)
    assert result["transcript_language"] == "en-US"
    assert result["transcript_source"] == "youtube-auto-subtitles"


def test_caption_failure_preserves_metadata_only_payload():
    payload = {
        "id": "MhjNYYAxGVI",
        "title": "Demo",
        "automatic_captions": {"en": [{"ext": "vtt", "url": "https://subs/auto.vtt"}]},
    }

    def fail(url, timeout):
        raise TimeoutError("caption timed out")

    result = YtDlpYouTubeProvider(
        metadata_provider=MetadataProvider(payload), fetch_text=fail
    ).fetch("https://www.youtube.com/watch?v=MhjNYYAxGVI", 30)
    assert result["id"] == "MhjNYYAxGVI"
    assert "transcript_text" not in result
