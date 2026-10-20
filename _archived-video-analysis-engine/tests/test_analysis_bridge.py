import pytest

import evidence_contract as ec
from analysis_bridge import BundleNotPublishable, evidence_bundle_to_analysis_input


def _ready_bundle():
    return ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="ready",
        identity=ec.SourceIdentity(
            platform="youtube",
            canonical_id="6xXjHM3V1zM",
            canonical_url="https://www.youtube.com/watch?v=6xXjHM3V1zM",
        ),
        metadata={
            "title": "Pi coding agent",
            "author": "author",
            "description": "description",
            "duration_s": 120,
        },
        transcript=ec.TranscriptEvidence(
            text="First claim. Second boundary.",
            language="en",
            source="youtube-transcript-api",
            content_hash="sha256:abc",
            segments=(
                ec.TranscriptSegmentEvidence(0.0, 4.0, "First claim."),
                ec.TranscriptSegmentEvidence(18.5, 22.0, "Second boundary."),
            ),
        ),
        audience_signals=(
            ec.AudienceSignal("comment", "Useful boundary", 12),
            ec.AudienceSignal("danmaku", "interesting", 1),
        ),
        provenance=ec.Provenance(
            adapter="youtube",
            adapter_version="1.0.0",
            collected_at="2026-07-11T00:00:00Z",
            source_refs=("https://www.youtube.com/watch?v=6xXjHM3V1zM",),
            hashes={"transcript": "sha256:abc"},
        ),
    )


def test_ready_bundle_maps_to_legacy_analysis_input():
    analysis = evidence_bundle_to_analysis_input(_ready_bundle())
    assert analysis.video_id == "6xXjHM3V1zM"
    assert analysis.platform == "youtube"
    assert analysis.title == "Pi coding agent"
    assert analysis.author == "author"
    assert analysis.description == "description"
    assert analysis.duration == 120
    assert analysis.transcript.full_text() == "First claim.\nSecond boundary."
    assert analysis.transcript.language == "en"
    assert analysis.transcript.source == "youtube-transcript-api"
    assert [(s.start, s.end, s.text) for s in analysis.transcript.segments] == [
        (0.0, 4.0, "First claim."),
        (18.5, 22.0, "Second boundary."),
    ]
    assert [(c.text, c.likes, c.platform) for c in analysis.comments] == [
        ("Useful boundary", 12, "youtube")
    ]
    assert [(d.text, d.time) for d in analysis.danmaku] == [("interesting", 0.0)]


def test_non_ready_bundle_is_rejected_before_writer():
    ready = _ready_bundle()
    degraded = ec.EvidenceBundle(
        schema_version=ready.schema_version,
        status="metadata_only",
        identity=ready.identity,
        metadata=ready.metadata,
        transcript=None,
        audience_signals=(),
        provenance=ready.provenance,
        errors=(ec.EvidenceError("transcript_unavailable", "asr", True, "missing"),),
    )
    with pytest.raises(BundleNotPublishable, match="metadata_only"):
        evidence_bundle_to_analysis_input(degraded)


def test_invalid_bundle_is_rejected_before_mapping():
    bundle = _ready_bundle()
    object.__setattr__(bundle, "status", "metadata_only")
    with pytest.raises(ec.ContractViolation):
        evidence_bundle_to_analysis_input(bundle)
