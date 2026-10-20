#!/usr/bin/env python3
"""Douyin single-video metadata adapter with a controlled yt-dlp provider."""

from __future__ import annotations

import hashlib
import re
from typing import Callable, Mapping

from evidence_contract import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceBundle,
    EvidenceError,
    Provenance,
    SourceIdentity,
    TranscriptEvidence,
    validate_bundle,
)
from platform_router import CollectOptions, SourceInput, detect_platforms
from providers.ytdlp import YtDlpMetadataProvider

# Backward-compatible name for the D1 public surface; implementation is shared.
YtDlpDouyinProvider = YtDlpMetadataProvider


Clock = Callable[[], str]
Provider = Callable[[str, float], Mapping[str, object]]
_URL_RE = re.compile(
    r"https?://(?:v\.douyin\.com/[0-9A-Za-z_-]+/?|(?:www\.)?douyin\.com/video/\d+/?|[^\s/]*iesdouyin\.com/[^\s]+)",
    re.I,
)


def extract_douyin_url(raw: str) -> str:
    """Extract exactly one Douyin URL; reject missing or ambiguous inputs."""
    urls = list(dict.fromkeys(match.rstrip("。；;,，") for match in _URL_RE.findall(raw)))
    if len(urls) != 1:
        raise ValueError(f"需要且只能包含一个抖音单视频链接，实际 {len(urls)} 个")
    return urls[0]


class DouyinAdapter:
    """Normalize one Douyin video into the shared EvidenceBundle contract."""

    platform = "douyin"
    adapter_version = "1.0.0"

    def __init__(self, provider: Provider, clock: Clock):
        self._provider = provider
        self._clock = clock

    def can_handle(self, source: SourceInput) -> bool:
        return detect_platforms(source) == (self.platform,)

    def collect(self, source: SourceInput, options: CollectOptions) -> EvidenceBundle:
        try:
            url = extract_douyin_url(source.raw)
        except ValueError:
            return self._degraded(source.raw, "platform_changed", "resolve", False, "抖音链接不可识别")

        try:
            payload = self._provider(url, options.timeout_s)
        except PermissionError:
            return self._degraded(url, "auth_required", "metadata", True, "抖音视频需要授权访问")
        except LookupError:
            return self._degraded(url, "platform_changed", "resolve", False, "抖音链接已失效或平台结构变化")
        except TimeoutError:
            return self._degraded(url, "resolve_failed", "resolve", True, "抖音元数据获取超时")
        except Exception:
            return self._degraded(url, "metadata_failed", "metadata", True, "抖音元数据获取失败")

        if not isinstance(payload, Mapping):
            return self._degraded(url, "metadata_failed", "metadata", True, "抖音元数据格式无效")
        video_id = str(payload.get("id") or "")
        if not video_id:
            return self._degraded(url, "platform_changed", "metadata", False, "抖音视频缺少稳定标识")

        identity = SourceIdentity(
            platform=self.platform,
            canonical_id=video_id,
            canonical_url=f"https://www.douyin.com/video/{video_id}",
        )
        metadata = self._metadata(payload)
        if not metadata:
            return self._degraded(url, "metadata_failed", "metadata", True, "抖音元数据为空", identity)

        transcript = self._transcript(payload) if options.want_transcript else None
        if transcript is not None:
            bundle = EvidenceBundle(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                status="ready",
                identity=identity,
                metadata=metadata,
                transcript=transcript,
                audience_signals=(),
                provenance=self._provenance(identity, transcript.content_hash),
            )
        else:
            bundle = EvidenceBundle(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                status="metadata_only",
                identity=identity,
                metadata=metadata,
                transcript=None,
                audience_signals=(),
                provenance=self._provenance(identity),
                errors=(
                    EvidenceError(
                        code="transcript_unavailable",
                        stage="asr",
                        retryable=True,
                        safe_message="尚未获取抖音媒体转录",
                    ),
                ),
            )
        validate_bundle(bundle)
        return bundle

    @staticmethod
    def _metadata(payload: Mapping[str, object]) -> dict:
        def integer(name: str) -> int:
            try:
                return max(int(float(str(payload.get(name) or 0))), 0)
            except (TypeError, ValueError):
                return 0

        metadata = {
            "title": str(payload.get("title") or ""),
            "author": str(payload.get("uploader") or payload.get("creator") or ""),
            "description": str(payload.get("description") or ""),
            "duration_s": integer("duration"),
            "published_at": integer("timestamp"),
            "view_count": integer("view_count"),
            "like_count": integer("like_count"),
            "comment_count": integer("comment_count"),
        }
        return metadata if any(metadata.values()) else {}

    @staticmethod
    def _transcript(payload: Mapping[str, object]) -> TranscriptEvidence | None:
        text = str(payload.get("transcript_text") or "").strip()
        if not text:
            return None
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        return TranscriptEvidence(
            text=text,
            language=str(payload.get("transcript_language") or "zh"),
            source=str(payload.get("transcript_source") or "unknown"),
            content_hash=digest,
        )

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
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
            identity = SourceIdentity(self.platform, f"unresolved-{digest}", raw)
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


__all__ = ["DouyinAdapter", "YtDlpDouyinProvider", "extract_douyin_url"]
