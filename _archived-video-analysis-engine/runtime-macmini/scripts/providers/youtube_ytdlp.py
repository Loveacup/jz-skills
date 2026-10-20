#!/usr/bin/env python3
"""YouTube yt-dlp provider with public caption extraction."""

from __future__ import annotations

import html
import re
import urllib.request
from typing import Callable, Mapping, Protocol

from providers.ytdlp import YtDlpMetadataProvider


FetchText = Callable[[str, float], str]


class MetadataProvider(Protocol):
    def fetch(self, url: str, timeout_s: float) -> Mapping[str, object]: ...


_TIMESTAMP_RE = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}\s+-->\s+(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}"
)
_TAG_RE = re.compile(r"<[^>]+>")
_PREFERRED_LANGUAGES = ("en", "en-US", "en-GB", "zh-Hans", "zh-Hant", "zh")


def _default_fetch_text(url: str, timeout_s: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return response.read().decode("utf-8", errors="replace")


def _seconds(raw: str) -> float:
    parts = raw.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = 0.0
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts[-3:]
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)


def _incremental_segments(segments: list[dict[str, object]]) -> list[dict[str, object]]:
    """Remove rolling-caption prefix/suffix repetition while retaining cue timing."""
    output: list[dict[str, object]] = []
    previous: list[str] = []
    for segment in segments:
        words = str(segment["text"]).split()
        if not words:
            continue
        overlap = 0
        max_overlap = min(len(previous), len(words))
        for size in range(max_overlap, 0, -1):
            if previous[-size:] == words[:size]:
                overlap = size
                break
        delta = words[overlap:]
        previous = words
        if not delta:
            continue
        output.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": " ".join(delta),
        })
    return output


def _chunk_segments(
    segments: list[dict[str, object]], max_span_s: float = 15.0, max_chars: int = 500
) -> list[dict[str, object]]:
    """Combine tiny incremental cues into analysis-sized timestamped chunks."""
    chunks: list[dict[str, object]] = []
    for segment in segments:
        if not chunks:
            chunks.append(dict(segment))
            continue
        current = chunks[-1]
        proposed = f'{current["text"]} {segment["text"]}'.strip()
        span = float(str(segment["end"] or segment["start"])) - float(str(current["start"]))
        if span <= max_span_s and len(proposed) <= max_chars:
            current["text"] = proposed
            current["end"] = segment["end"]
        else:
            chunks.append(dict(segment))
    return chunks


def parse_vtt(vtt: str) -> list[dict[str, object]]:
    """Parse public VTT cues into ordered, deduplicated typed segment dicts."""
    segments: list[dict[str, object]] = []
    seen: set[str] = set()
    start: float | None = None
    end: float | None = None
    cue_lines: list[str] = []

    def flush() -> None:
        nonlocal cue_lines
        text = " ".join(cue_lines).strip()
        cue_lines = []
        if start is None or not text or text in seen:
            return
        seen.add(text)
        segments.append({"start": start, "end": end, "text": text})

    in_note = False
    for raw_line in (vtt or "").splitlines():
        line = raw_line.strip()
        if line.startswith("NOTE"):
            flush()
            in_note = True
            continue
        if in_note:
            if not line:
                in_note = False
            continue
        if "-->" in line and _TIMESTAMP_RE.match(line):
            flush()
            left, right = line.split("-->", 1)
            start = _seconds(left.strip())
            end = _seconds(right.strip().split()[0])
            continue
        if (
            not line
            or line == "WEBVTT"
            or line.startswith(("Kind:", "Language:", "STYLE", "REGION"))
            or line.isdigit()
        ):
            if not line:
                flush()
            continue
        cleaned = html.unescape(_TAG_RE.sub("", line)).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned:
            cue_lines.append(cleaned)
    flush()
    return _chunk_segments(_incremental_segments(segments))


def normalize_vtt(vtt: str) -> str:
    """Strip VTT control data and duplicate cues while preserving order."""
    return "\n".join(str(segment["text"]) for segment in parse_vtt(vtt))


class YtDlpYouTubeProvider:
    """Enrich yt-dlp metadata with one public manual/automatic VTT track."""

    def __init__(
        self,
        binary: str = "yt-dlp",
        metadata_provider: MetadataProvider | None = None,
        fetch_text: FetchText = _default_fetch_text,
    ):
        self._metadata_provider = metadata_provider or YtDlpMetadataProvider(binary=binary)
        self._fetch_text = fetch_text

    def __call__(self, url: str, timeout_s: float) -> Mapping[str, object]:
        return self.fetch(url, timeout_s)

    def fetch(self, url: str, timeout_s: float) -> Mapping[str, object]:
        payload = dict(self._metadata_provider.fetch(url, timeout_s))
        selected = self._select_track(payload)
        if selected is None:
            return payload
        language, track_url, source = selected
        try:
            segments = parse_vtt(self._fetch_text(track_url, timeout_s))
        except Exception:
            return payload
        transcript = "\n".join(str(segment["text"]) for segment in segments)
        if not transcript:
            return payload
        payload["transcript_text"] = transcript
        payload["transcript_segments"] = segments
        payload["transcript_language"] = language
        payload["transcript_source"] = source
        return payload

    @staticmethod
    def _select_track(payload: Mapping[str, object]) -> tuple[str, str, str] | None:
        for field, source in (
            ("subtitles", "youtube-manual-subtitles"),
            ("automatic_captions", "youtube-auto-subtitles"),
        ):
            tracks = payload.get(field)
            if not isinstance(tracks, Mapping):
                continue
            languages = list(tracks.keys())
            ordered = []
            for preferred in _PREFERRED_LANGUAGES:
                ordered.extend(
                    language for language in languages
                    if language == preferred and language not in ordered
                )
            ordered.extend(
                language for language in languages
                if any(str(language).startswith(prefix + "-") for prefix in ("en", "zh"))
                and language not in ordered
            )
            ordered.extend(language for language in languages if language not in ordered)
            for language in ordered:
                entries = tracks.get(language)
                if not isinstance(entries, list):
                    continue
                vtt_entries = [
                    entry for entry in entries
                    if isinstance(entry, Mapping)
                    and str(entry.get("ext") or "").lower() == "vtt"
                    and str(entry.get("url") or "").startswith(("http://", "https://"))
                ]
                if vtt_entries:
                    return str(language), str(vtt_entries[0]["url"]), source
        return None


__all__ = ["YtDlpYouTubeProvider", "normalize_vtt"]
