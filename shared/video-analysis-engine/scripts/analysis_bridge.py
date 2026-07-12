#!/usr/bin/env python3
"""Bridge the v4 EvidenceBundle contract into the proven legacy analysis core."""

from __future__ import annotations

from dataclasses import asdict

from evidence_contract import EvidenceBundle, is_publishable, validate_bundle
from video_analysis_engine import AnalysisInput, Comment, Danmaku, Transcript, TranscriptSegment


class BundleNotPublishable(ValueError):
    """Raised when degraded evidence is routed toward the formal analysis core."""


def evidence_bundle_to_analysis_input(bundle: EvidenceBundle) -> AnalysisInput:
    """Validate and map one publishable bundle; never bypass degraded-state policy."""
    validate_bundle(bundle)
    if not is_publishable(bundle):
        raise BundleNotPublishable(
            f"EvidenceBundle status={bundle.status!r} cannot enter the formal Writer"
        )

    transcript_evidence = bundle.transcript
    if transcript_evidence is None:
        raise BundleNotPublishable("ready EvidenceBundle is missing transcript")
    legacy_segments = [
        TranscriptSegment(start=segment.start, end=segment.end, text=segment.text)
        for segment in transcript_evidence.segments
    ]
    if not legacy_segments:
        legacy_segments = [TranscriptSegment(start=0.0, text=transcript_evidence.text)]
    transcript = Transcript(
        segments=legacy_segments,
        language=transcript_evidence.language,
        source=transcript_evidence.source,
    )
    comments = [
        Comment(
            text=signal.label,
            likes=max(int(round(signal.weight)), 0),
            platform=bundle.identity.platform,
        )
        for signal in bundle.audience_signals
        if signal.kind == "comment"
    ]
    danmaku = [
        Danmaku(text=signal.label, time=0.0)
        for signal in bundle.audience_signals
        if signal.kind == "danmaku"
    ]
    metadata = bundle.metadata
    try:
        duration = max(int(float(str(metadata.get("duration_s") or 0))), 0)
    except (TypeError, ValueError):
        duration = 0

    fact_checks = (
        {"items": [asdict(item) for item in bundle.fact_checks]}
        if bundle.fact_checks
        else None
    )
    cross_platform = (
        {"evidence": [asdict(item) for item in bundle.cross_platform]}
        if bundle.cross_platform
        else None
    )
    return AnalysisInput(
        video_id=bundle.identity.canonical_id,
        title=str(metadata.get("title") or ""),
        author=str(metadata.get("author") or ""),
        duration=duration,
        platform=bundle.identity.platform,
        description=str(metadata.get("description") or ""),
        transcript=transcript,
        comments=comments,
        danmaku=danmaku,
        fact_checks=fact_checks,
        cross_platform=cross_platform,
    )


__all__ = ["BundleNotPublishable", "evidence_bundle_to_analysis_input"]
