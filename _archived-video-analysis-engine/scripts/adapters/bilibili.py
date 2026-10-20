#!/usr/bin/env python3
"""Bilibili legacy fetch_all payload → v4 EvidenceBundle adapter."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable, Mapping, Optional

from evidence_contract import (
    AudienceSignal,
    EvidenceBundle,
    EvidenceError,
    Provenance,
    SourceIdentity,
    TranscriptEvidence,
    EVIDENCE_SCHEMA_VERSION,
    validate_bundle,
)
from platform_router import CollectOptions, SourceInput, detect_platforms


Collector = Callable[[SourceInput, CollectOptions], Mapping[str, object]]
Clock = Callable[[], str]


class BilibiliAdapter:
    """Normalize an injected Bilibili collector; owns no Writer/report logic."""

    platform = "bilibili"
    adapter_version = "1.0.0"

    def __init__(self, collector: Collector, clock: Clock):
        self._collector = collector
        self._clock = clock

    def can_handle(self, source: SourceInput) -> bool:
        return detect_platforms(source) == (self.platform,)

    def collect(self, source: SourceInput, options: CollectOptions) -> EvidenceBundle:
        try:
            payload = self._collector(source, options)
            if not isinstance(payload, Mapping):
                payload = {}
        except Exception:
            return self._unavailable(source, {}, "Bilibili 采集失败")

        identity = self._identity(source, payload)
        metadata = self._metadata(payload)
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
        elif metadata:
            bundle = EvidenceBundle(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                status="metadata_only",
                identity=identity,
                metadata=metadata,
                transcript=None,
                audience_signals=audience,
                provenance=self._provenance(identity),
                errors=(
                    EvidenceError(
                        code="transcript_unavailable",
                        stage="asr",
                        retryable=True,
                        safe_message="Bilibili 转录不可用",
                    ),
                ),
            )
        else:
            return self._unavailable(source, payload, "Bilibili 证据不可用")

        validate_bundle(bundle)
        return bundle

    def _identity(self, source: SourceInput, payload: Mapping[str, object]) -> SourceIdentity:
        bvid = str(payload.get("bvid") or "")
        if not bvid:
            match = re.search(r"\bBV[0-9A-Za-z]{10}\b", source.raw)
            bvid = match.group(0) if match else self._unresolved_id(source.raw)
        canonical_url = f"https://www.bilibili.com/video/{bvid}"
        return SourceIdentity(self.platform, bvid, canonical_url)

    @staticmethod
    def _unresolved_id(raw: str) -> str:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return f"unresolved-{digest}"

    @staticmethod
    def _metadata(payload: Mapping[str, object]) -> dict:
        subtitle_value = payload.get("subtitle")
        subtitle: Mapping[str, object] = subtitle_value if isinstance(subtitle_value, Mapping) else {}
        title = str(payload.get("title") or subtitle.get("title") or "")
        author = str(payload.get("author") or "")
        description = str(payload.get("description") or "")
        duration_value = payload.get("duration_s") or subtitle.get("duration") or 0
        try:
            duration = int(float(str(duration_value or 0)))
        except (TypeError, ValueError):
            duration = 0
        metadata = {
            "title": title,
            "author": author,
            "description": description,
            "duration_s": max(duration, 0),
        }
        return metadata if any((title, author, description, duration)) else {}

    @staticmethod
    def _transcript(payload: Mapping[str, object]) -> Optional[TranscriptEvidence]:
        subtitle = payload.get("subtitle")
        if not isinstance(subtitle, Mapping):
            return None
        text = str(subtitle.get("text") or "").strip()
        if not text:
            segments = subtitle.get("segments")
            if isinstance(segments, list):
                text = "\n".join(
                    str(segment.get("text") or "").strip()
                    for segment in segments
                    if isinstance(segment, Mapping) and str(segment.get("text") or "").strip()
                )
        if not text and subtitle.get("txt_path"):
            try:
                text = Path(str(subtitle["txt_path"])).expanduser().read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                text = ""
        if not text:
            return None
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        return TranscriptEvidence(
            text=text,
            language=str(subtitle.get("language") or "zh"),
            source=str(subtitle.get("method") or "unknown"),
            content_hash=digest,
        )

    @staticmethod
    def _audience(payload: Mapping[str, object]) -> tuple[AudienceSignal, ...]:
        signals = []
        comments = payload.get("comments")
        if isinstance(comments, Mapping):
            raw_comments = comments.get("merged_comments") or comments.get("hot_comments") or []
            if isinstance(raw_comments, list):
                for item in raw_comments:
                    if not isinstance(item, Mapping):
                        continue
                    label = str(item.get("content") or item.get("text") or "").strip()
                    if not label:
                        continue
                    try:
                        weight = float(item.get("like") or item.get("like_count") or 0)
                    except (TypeError, ValueError):
                        weight = 0.0
                    signals.append(AudienceSignal("comment", label, max(weight, 0.0)))
        danmaku = payload.get("danmaku")
        if isinstance(danmaku, Mapping):
            raw_danmaku = danmaku.get("data") or danmaku.get("danmaku") or []
            if isinstance(raw_danmaku, list):
                for item in raw_danmaku:
                    if not isinstance(item, Mapping):
                        continue
                    label = str(item.get("text") or "").strip()
                    if label:
                        signals.append(AudienceSignal("danmaku", label, 1.0))
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

    def _unavailable(
        self,
        source: SourceInput,
        payload: Mapping[str, object],
        message: str,
    ) -> EvidenceBundle:
        identity = self._identity(source, payload)
        bundle = EvidenceBundle(
            schema_version=EVIDENCE_SCHEMA_VERSION,
            status="unavailable",
            identity=identity,
            metadata={},
            transcript=None,
            audience_signals=(),
            provenance=self._provenance(identity),
            errors=(EvidenceError("media_unavailable", "media", True, message),),
        )
        validate_bundle(bundle)
        return bundle


__all__ = ["BilibiliAdapter"]
