#!/usr/bin/env python3
"""YouTube single-video adapter for the shared EvidenceBundle contract."""

from __future__ import annotations

import hashlib
import re
from typing import Callable, Mapping, Optional

from evidence_contract import (
    AudienceSignal,
    EVIDENCE_SCHEMA_VERSION,
    EvidenceBundle,
    EvidenceError,
    Provenance,
    SourceIdentity,
    TranscriptEvidence,
    TranscriptSegmentEvidence,
    validate_bundle,
)
from platform_router import CollectOptions, SourceInput, detect_platforms
from providers.youtube_ytdlp import YtDlpYouTubeProvider


Clock = Callable[[], str]
Provider = Callable[[str, float], Mapping[str, object]]
_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/(?:watch\?[^\s]*\bv=[0-9A-Za-z_-]{11}|shorts/[0-9A-Za-z_-]{11})|youtu\.be/[0-9A-Za-z_-]{11})",
    re.I,
)
_ID_PATTERNS = (
    re.compile(r"[?&]v=([0-9A-Za-z_-]{11})"),
    re.compile(r"youtu\.be/([0-9A-Za-z_-]{11})"),
    re.compile(r"youtube\.com/shorts/([0-9A-Za-z_-]{11})"),
)


def extract_youtube_url(raw: str) -> str:
    urls = list(dict.fromkeys(match.rstrip("。；;,，") for match in _URL_RE.findall(raw)))
    if len(urls) != 1:
        raise ValueError(f"需要且只能包含一个 YouTube 单视频链接，实际 {len(urls)} 个")
    return urls[0]


class YouTubeAdapter:
    platform = "youtube"
    adapter_version = "1.0.0"

    def __init__(self, provider: Provider, clock: Clock):
        self._provider = provider
        self._clock = clock

    def can_handle(self, source: SourceInput) -> bool:
        return detect_platforms(source) == (self.platform,)

    def collect(self, source: SourceInput, options: CollectOptions) -> EvidenceBundle:
        try:
            url = extract_youtube_url(source.raw)
        except ValueError:
            return self._degraded(source.raw, "platform_changed", "resolve", False, "YouTube 链接不可识别")
        try:
            payload = self._provider(url, options.timeout_s)
        except PermissionError:
            return self._degraded(url, "auth_required", "metadata", True, "YouTube 视频需要授权访问")
        except LookupError:
            return self._degraded(url, "platform_changed", "resolve", False, "YouTube 链接失效或平台结构变化")
        except TimeoutError:
            return self._degraded(url, "resolve_failed", "resolve", True, "YouTube 元数据获取超时")
        except Exception:
            return self._degraded(url, "metadata_failed", "metadata", True, "YouTube 元数据获取失败")

        if not isinstance(payload, Mapping):
            return self._degraded(url, "metadata_failed", "metadata", True, "YouTube 元数据格式无效")
        video_id = str(payload.get("id") or self._video_id(url) or "")
        if not video_id:
            return self._degraded(url, "platform_changed", "metadata", False, "YouTube 视频缺少稳定标识")
        identity = SourceIdentity(
            platform=self.platform,
            canonical_id=video_id,
            canonical_url=f"https://www.youtube.com/watch?v={video_id}",
        )
        metadata = self._metadata(payload)
        if not metadata:
            return self._degraded(url, "metadata_failed", "metadata", True, "YouTube 元数据为空", identity)
        transcript = self._transcript(payload) if options.want_transcript else None
        audience = self._audience(payload) if options.want_audience else ()
        if transcript is not None:
            bundle = EvidenceBundle(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                status="ready",
                identity=identity,
                metadata=metadata,
                transcript=transcript,
                audience_signals=audience,
                provenance=self._provenance(identity, transcript.content_hash),
            )
        else:
            bundle = EvidenceBundle(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                status="metadata_only",
                identity=identity,
                metadata=metadata,
                transcript=None,
                audience_signals=audience,
                provenance=self._provenance(identity),
                errors=(EvidenceError("transcript_unavailable", "asr", True, "尚未获取 YouTube 转录"),),
            )
        validate_bundle(bundle)
        return bundle

    @staticmethod
    def _video_id(url: str) -> str:
        for pattern in _ID_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _metadata(payload: Mapping[str, object]) -> dict:
        def integer(name: str) -> int:
            try:
                return max(int(float(str(payload.get(name) or 0))), 0)
            except (TypeError, ValueError):
                return 0

        metadata = {
            "title": str(payload.get("title") or ""),
            "author": str(payload.get("uploader") or payload.get("channel") or ""),
            "description": str(payload.get("description") or ""),
            "duration_s": integer("duration"),
            "published_at": integer("timestamp"),
            "view_count": integer("view_count"),
            "like_count": integer("like_count"),
            "comment_count": integer("comment_count"),
        }
        return metadata if any(metadata.values()) else {}

    @staticmethod
    def _transcript(payload: Mapping[str, object]) -> Optional[TranscriptEvidence]:
        text = str(payload.get("transcript_text") or "").strip()
        if not text:
            return None
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        segments = []
        raw_segments = payload.get("transcript_segments")
        if isinstance(raw_segments, list):
            for item in raw_segments:
                if not isinstance(item, Mapping):
                    continue
                try:
                    start = float(str(item.get("start")))
                    raw_end = item.get("end")
                    end = None if raw_end is None else float(str(raw_end))
                except (TypeError, ValueError):
                    continue
                cue_text = str(item.get("text") or "").strip()
                if cue_text:
                    segments.append(TranscriptSegmentEvidence(start, end, cue_text))
        return TranscriptEvidence(
            text=text,
            language=str(payload.get("transcript_language") or "auto"),
            source=str(payload.get("transcript_source") or "unknown"),
            content_hash=digest,
            segments=tuple(segments),
        )

    @staticmethod
    def _audience(payload: Mapping[str, object]) -> tuple[AudienceSignal, ...]:
        comments = payload.get("comments")
        if not isinstance(comments, list):
            return ()
        signals = []
        for item in comments:
            if not isinstance(item, Mapping):
                continue
            label = str(item.get("text") or item.get("content") or "").strip()
            if not label:
                continue
            try:
                weight = max(float(str(item.get("like_count") or item.get("like") or 0)), 0.0)
            except (TypeError, ValueError):
                weight = 0.0
            signals.append(AudienceSignal("comment", label, weight))
        return tuple(signals)

    def _provenance(self, identity: SourceIdentity, transcript_hash: str = "") -> Provenance:
        hashes = {"transcript": transcript_hash} if transcript_hash else {}
        return Provenance(
            adapter=self.platform,
            adapter_version=self.adapter_version,
            collected_at=self._clock(),
            source_refs=(identity.canonical_url,),
            hashes=hashes,
        )

    def _degraded(
        self,
        raw: str,
        code: str,
        stage: str,
        retryable: bool,
        message: str,
        identity: SourceIdentity | None = None,
    ) -> EvidenceBundle:
        if identity is None:
            video_id = self._video_id(raw)
            if not video_id:
                video_id = "unresolved-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
            identity = SourceIdentity(self.platform, video_id, raw)
        status = "auth_required" if code == "auth_required" else "unavailable"
        bundle = EvidenceBundle(
            schema_version=EVIDENCE_SCHEMA_VERSION,
            status=status,
            identity=identity,
            metadata={},
            transcript=None,
            audience_signals=(),
            provenance=self._provenance(identity),
            errors=(EvidenceError(code, stage, retryable, message),),
        )
        validate_bundle(bundle)
        return bundle


__all__ = ["YouTubeAdapter", "YtDlpYouTubeProvider", "extract_youtube_url"]
