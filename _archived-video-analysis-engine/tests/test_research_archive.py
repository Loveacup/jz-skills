import hashlib
import os
import stat
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
import research_contract as rc
import research_pipeline as rp

from research_archive import (
    ArchiveCollisionError,
    ArchiveViolation,
    ResearchArchive,
    sanitize_canonical_url,
)


def _archive(tmp_path: Path, **kwargs) -> ResearchArchive:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir(parents=True, exist_ok=True)
    vault.mkdir(parents=True, exist_ok=True)
    return ResearchArchive(
        tmp_path / "private" / "research",
        forbidden_roots=(repo, vault),
        **kwargs,
    )


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def test_archive_root_must_be_outside_each_forbidden_root(tmp_path: Path):
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    vault.mkdir()

    for forbidden in (repo, vault):
        with pytest.raises(ArchiveViolation, match="forbidden"):
            ResearchArchive(forbidden / "private-archive", forbidden_roots=(repo, vault))

    with pytest.raises(ArchiveViolation, match="forbidden_roots"):
        ResearchArchive(tmp_path / "archive", forbidden_roots=())
    with pytest.raises(ArchiveViolation, match="forbidden"):
        ResearchArchive(tmp_path, forbidden_roots=(repo, vault))


def test_rejects_absolute_children_and_parent_traversal(tmp_path: Path):
    archive = _archive(tmp_path)

    with pytest.raises(ArchiveViolation, match="absolute"):
        archive.resolve_child("/tmp/escape")
    with pytest.raises(ArchiveViolation, match="traversal"):
        archive.resolve_child("bundles", "..", "escape.json")


def test_symlinked_archive_component_cannot_escape(tmp_path: Path):
    archive = _archive(tmp_path)
    archive.root.mkdir(parents=True, mode=0o700)
    outside = tmp_path / "outside"
    outside.mkdir()
    (archive.root / "bundles").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ArchiveViolation, match="symlink"):
        archive.write_bundle({"bundle_id": "b-1"})
    assert list(outside.iterdir()) == []


def test_configured_archive_root_itself_cannot_be_a_symlink(tmp_path: Path):
    repo = tmp_path / "repo"; repo.mkdir()
    vault = tmp_path / "vault"; vault.mkdir()
    outside = tmp_path / "outside"; outside.mkdir()
    alias = tmp_path / "archive-link"
    alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ArchiveViolation, match="symlink"):
        ResearchArchive(alias, forbidden_roots=(repo, vault))


def test_archive_rejects_existing_symlink_in_configured_root_ancestors(tmp_path: Path):
    repo = tmp_path / "repo"; repo.mkdir()
    vault = tmp_path / "vault"; vault.mkdir()
    outside = tmp_path / "outside"; outside.mkdir()
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ArchiveViolation, match="symlink"):
        ResearchArchive(alias_parent / "research", forbidden_roots=(repo, vault))


def test_bundle_is_canonical_content_addressed_private_and_idempotent(tmp_path: Path):
    archive = _archive(tmp_path)
    payload = {"z": [2, 1], "title": "研究", "a": {"ok": True}}
    expected = '{"a":{"ok":true},"title":"研究","z":[2,1]}'.encode("utf-8")

    digest = archive.write_bundle(payload)
    assert digest == _sha256(expected)
    assert archive.write_bundle({"a": {"ok": True}, "title": "研究", "z": [2, 1]}) == digest
    target = archive.path_for("bundles", digest)
    assert target.read_bytes() == expected
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(archive.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert archive.read_bundle(digest) == payload


def test_source_snapshot_is_utf8_content_addressed_and_private(tmp_path: Path):
    archive = _archive(tmp_path)
    text = "公开来源\n第二行：证据"
    raw = text.encode("utf-8")

    digest = archive.write_source(text)
    target = archive.path_for("sources", digest)
    assert digest == _sha256(raw)
    assert target.read_bytes() == raw
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert archive.read_source(digest) == text
    assert archive.write_source(text) == digest


def test_collision_at_existing_hash_is_a_hard_error(tmp_path: Path):
    archive = _archive(tmp_path)
    payload = {"bundle_id": "b-1"}
    canonical = b'{"bundle_id":"b-1"}'
    digest = _sha256(canonical)
    target = archive.path_for("bundles", digest)
    target.parent.mkdir(parents=True, mode=0o700)
    target.write_bytes(b"different")
    os.chmod(target, 0o600)

    with pytest.raises(ArchiveCollisionError, match="different bytes"):
        archive.write_bundle(payload)
    assert target.read_bytes() == b"different"


def test_idempotent_write_rejects_insecure_existing_permissions(tmp_path: Path):
    archive = _archive(tmp_path)
    payload = {"bundle_id": "b-1"}
    digest = archive.write_bundle(payload)
    os.chmod(archive.path_for("bundles", digest), 0o644)

    with pytest.raises(ArchiveViolation, match="permission"):
        archive.write_bundle(payload)


def test_read_rechecks_hash_and_rejects_one_bit_tamper(tmp_path: Path):
    archive = _archive(tmp_path)
    digest = archive.write_source("abcdef")
    target = archive.path_for("sources", digest)
    tampered = bytearray(target.read_bytes())
    tampered[0] ^= 1
    target.write_bytes(tampered)

    with pytest.raises(ArchiveViolation, match="hash"):
        archive.read_source(digest)


def test_read_rejects_symlink_substitution(tmp_path: Path):
    archive = _archive(tmp_path)
    digest = archive.write_bundle({"bundle_id": "b-1"})
    target = archive.path_for("bundles", digest)
    saved = tmp_path / "saved.json"
    target.replace(saved)
    target.symlink_to(saved)

    with pytest.raises(ArchiveViolation, match="symlink"):
        archive.read_bundle(digest)


def test_bundle_and_source_byte_caps_apply_on_write_and_read(tmp_path: Path):
    archive = _archive(tmp_path, max_bundle_bytes=20, max_source_bytes=5)
    with pytest.raises(ArchiveViolation, match="bundle.*cap"):
        archive.write_bundle({"payload": "x" * 30})
    with pytest.raises(ArchiveViolation, match="source.*cap"):
        archive.write_source("123456")

    roomy = _archive(tmp_path / "other", max_bundle_bytes=100, max_source_bytes=100)
    digest = roomy.write_source("123456")
    roomy.max_source_bytes = 5
    with pytest.raises(ArchiveViolation, match="source.*cap"):
        roomy.read_source(digest)


@pytest.mark.parametrize(
    "payload",
    [
        {"headers": {"Authorization": "Bearer secret"}},
        {"nested": [{"cookies": "session=x"}]},
        {"authorization": "Bearer secret"},
        {"x-api-key": "secret"},
        {"provider_payload": {"safe": "apparently"}},
        {"url": "https://example.com/a?X-Amz-Signature=secret"},
        {"url": "https://example.com/a?access_token=secret"},
        {"url": "https://example.com/a?token=secret"},
        {"path": "/Users/alex/private/file.txt"},
        {"path": "/etc/private-service/config.json"},
        {"path": "C:\\Users\\alex\\private.txt"},
        {"clientSecret": "secret"},
        {"sessionCookie": "secret"},
        {"path": "/srv/company/private.txt"},
        {"path": "C:/Users/alex/private.txt"},
        {"path": "\\\\server\\share\\private.txt"},
        {"note": "path:/srv/company/private.txt"},
        {"note": "session=abc123"},
        {"note": "Set-Cookie: sid=abc123"},
    ],
)
def test_payload_scanner_recursively_rejects_private_material(tmp_path: Path, payload):
    archive = _archive(tmp_path)
    with pytest.raises(ArchiveViolation, match="sensitive|private"):
        archive.write_bundle(payload)


def test_source_scanner_rejects_bearers_signed_urls_and_private_paths(tmp_path: Path):
    archive = _archive(tmp_path)
    for text in (
        "Authorization: Bearer abcdef",
        "https://example.com/x?sig=replayable",
        "local file /private/var/secret.txt",
    ):
        with pytest.raises(ArchiveViolation, match="sensitive|private"):
            archive.write_source(text)


def test_payload_scanner_checks_dataclass_fields(tmp_path: Path):
    @dataclass(frozen=True)
    class Artifact:
        headers: object

    with pytest.raises(ArchiveViolation, match="sensitive"):
        _archive(tmp_path).write_bundle(Artifact(headers={"safe-looking": "value"}))


def test_canonical_url_sanitizes_tracking_and_signed_parameters():
    sanitized = sanitize_canonical_url(
        "HTTPS://Example.COM:443/a?utm_source=x&b=2&X-Amz-Signature=secret&token=abc#frag"
    )
    assert sanitized == "https://example.com/a?b=2"

    with pytest.raises(ArchiveViolation, match="credentials"):
        sanitize_canonical_url("https://user:password@example.com/private")
    with pytest.raises(ArchiveViolation, match="http"):
        sanitize_canonical_url("file:///Users/alex/private")


def test_bundle_canonical_url_is_sanitized_before_hash_and_persistence(tmp_path: Path):
    archive = _archive(tmp_path)
    digest = archive.write_bundle({
        "source": {
            "canonical_url": "HTTPS://Example.COM:443/a?utm_source=x&b=2&X-Amz-Signature=secret#frag"
        }
    })
    assert archive.read_bundle(digest)["source"]["canonical_url"] == "https://example.com/a?b=2"


def test_governed_delete_removes_content_and_writes_content_free_tombstone(tmp_path: Path):
    archive = _archive(tmp_path)
    digest = archive.write_bundle({"bundle_id": "bundle-7", "content": "private"})

    tombstone_hash = archive.delete(
        "bundles",
        digest,
        selector={"video_canonical_id": "BV1abc"},
        reason="user privacy request",
        deleted_at="2026-07-14T12:00:00Z",
    )

    assert not archive.path_for("bundles", digest).exists()
    tombstone = archive.read_tombstone(tombstone_hash)
    assert tombstone == {
        "deleted_at": "2026-07-14T12:00:00Z",
        "hash": digest,
        "reason": "user privacy request",
        "selector": {"video_canonical_id": "BV1abc"},
        "status": "completed",
    }
    raw = archive.path_for("tombstones", tombstone_hash).read_text("utf-8")
    assert "private" not in raw
    assert archive.delete(
        "bundles",
        digest,
        selector={"video_canonical_id": "BV1abc"},
        reason="user privacy request",
        deleted_at="2026-07-14T12:00:00Z",
    ) == tombstone_hash


def test_delete_persists_pending_tombstone_before_unlink(monkeypatch, tmp_path: Path):
    archive = _archive(tmp_path)
    digest = archive.write_bundle({"bundle_id": "bundle-8", "content": "private"})
    original_publish = archive._publish
    tombstone_calls = 0

    def fail_completed(kind, content_hash, data, limit):
        nonlocal tombstone_calls
        if kind == "tombstones":
            tombstone_calls += 1
            if tombstone_calls == 2:
                raise OSError("completed tombstone write failed")
        return original_publish(kind, content_hash, data, limit)

    monkeypatch.setattr(archive, "_publish", fail_completed)
    with pytest.raises(OSError, match="completed"):
        archive.delete(
            "bundles", digest, selector={"video_canonical_id": "BV1abc"},
            reason="privacy", deleted_at="2026-07-14T12:00:00Z",
        )
    assert not archive.path_for("bundles", digest).exists()
    pending_files = list((archive.root / "tombstones").glob("*.json"))
    assert len(pending_files) == 1
    assert '"status":"pending"' in pending_files[0].read_text("utf-8")


def test_invalid_hash_and_kind_are_rejected_before_path_use(tmp_path: Path):
    archive = _archive(tmp_path)
    with pytest.raises(ArchiveViolation, match="hash"):
        archive.read_bundle("sha256:../../escape")
    with pytest.raises(ArchiveViolation, match="kind"):
        archive.path_for("other", "sha256:" + "0" * 64)


def _validation_plan():
    return rp.build_research_plan(
        evidence_bundle_hash="sha256:" + "1" * 64,
        claim_bundle={
            "claim_bundle_semantic_hash": "sha256:" + "2" * 64,
            "claims": ({"claim_uid": "claim-1", "text": "事实主张", "risk": "P0"},),
        },
        canonical_id="BV1test", platform="bilibili", report_mode="full",
        research_policy="force", capability_snapshot={"available": True},
        created_at="2026-07-14T12:00:00Z", plan_id="plan-s5",
    )


def _raw_run(plan, candidates):
    return rc.finalize_raw_research_run(rc.RawResearchRun(
        schema_version=rc.RAW_RESEARCH_RUN_SCHEMA_VERSION,
        run_id="run-s5", plan_semantic_hash=plan.plan_semantic_hash,
        capability_available=True, attempted=True, executed=True, status="completed",
        validated_evidence_count=0, route_trace=(), execution={},
        raw_research={
            "input_hashes": {
                "plan_semantic_hash": plan.plan_semantic_hash,
                "evidence_bundle_hash": plan.evidence_bundle_hash,
                "claim_bundle_hash": plan.claim_bundle_hash,
            },
            "candidates": tuple(candidates),
        }, errors=(),
    ))


def _candidate(plan, publisher, *, social=False, snippet_only=False, bad_quote=False,
               stance="supports", published_at="2026-07-01T00:00:00Z"):
    query = next(item for item in plan.queries if "claim-1" in item.get("claim_uids", ()))
    content = f"{publisher} 的完整正文明确说明事实主张成立。"
    quote = "事实主张成立"
    start = content.index(quote)
    quote_hash = _sha256((quote + "x" if bad_quote else quote).encode("utf-8"))
    return {
        "candidate_uid": f"cand-{publisher}", "query_uid": query["query_uid"],
        "canonical_url": f"https://{publisher}.example/source", "title": "来源",
        "publisher": publisher, "publisher_group": publisher,
        "source_kind": "social" if social else "official",
        "published_at": published_at, "fetched_at": "2026-07-14T12:01:00Z",
        "content": content, "content_hash": _sha256(content.encode("utf-8")),
        "snippet": content[:8], "snippet_only": snippet_only,
        "stance": stance,
        "quote_candidates": ({
            "claim_uid": "claim-1", "quote_text": quote,
            "start": start, "end": start + len(quote), "quote_hash": quote_hash,
            "stance": "supports",
        },),
    }


def test_validator_rejects_plan_hash_mismatch():
    plan = _validation_plan()
    raw = _raw_run(plan, ())
    wrong = rc.finalize_research_plan(replace(plan, canonical_id="other", plan_semantic_hash=""))
    with pytest.raises(rc.ResearchContractViolation, match="plan.*hash|绑定"):
        rc.validate_and_adjudicate_research(wrong, raw, bundle_id="bundle-s5")


def test_validator_rejects_snippet_only_and_bad_quote_hash():
    plan = _validation_plan()
    raw = _raw_run(plan, (
        _candidate(plan, "one", snippet_only=True),
        _candidate(plan, "two", bad_quote=True),
    ))
    bundle = rc.validate_and_adjudicate_research(plan, raw, bundle_id="bundle-s5")
    assessments = bundle.validated_research["claim_source_assessments"]
    assert all(item["verdict"] == "rejected" for item in assessments)
    assert bundle.validated_research["quotes"] == ()
    assert bundle.publication_disposition == "block"


def test_validator_accepts_exact_quotes_but_requires_independent_publishers():
    plan = _validation_plan()
    one = rc.validate_and_adjudicate_research(
        plan, _raw_run(plan, (_candidate(plan, "one"),)), bundle_id="bundle-one"
    )
    assert one.validated_research["claim_results"][0]["verdict"] == "unresolved"
    assert one.publication_disposition == "block"

    two = rc.validate_and_adjudicate_research(
        plan, _raw_run(plan, (_candidate(plan, "one"), _candidate(plan, "two"))),
        bundle_id="bundle-two",
    )
    result = two.validated_research["claim_results"][0]
    assert result["verdict"] == "corroborated"
    assert len(result["accepted_assessment_uids"]) == 2
    assert len(two.validated_research["quotes"]) == 2
    rc.validate_research_bundle(two)


def test_validator_rejects_social_only_support_for_p0():
    plan = _validation_plan()
    raw = _raw_run(plan, (_candidate(plan, "one", social=True), _candidate(plan, "two", social=True)))
    bundle = rc.validate_and_adjudicate_research(plan, raw, bundle_id="bundle-social")
    assert bundle.validated_research["claim_results"][0]["verdict"] == "unresolved"
    assert bundle.publication_disposition == "block"


def test_validator_enforces_freshness_for_current_claims():
    plan = _validation_plan()
    current_claim = {**dict(plan.claims[0]), "temporal_class": "current", "freshness_window_days": 30}
    plan = rc.finalize_research_plan(replace(plan, claims=(current_claim,), plan_semantic_hash=""))
    raw = _raw_run(plan, (_candidate(plan, "one", published_at="2020-01-01T00:00:00Z"),))
    bundle = rc.validate_and_adjudicate_research(
        plan, raw, bundle_id="bundle-stale", completed_at="2026-07-14T12:00:00Z"
    )
    assert "stale_source" in bundle.validated_research["claim_source_assessments"][0]["reasons"]
    assert bundle.publication_disposition == "block"


def test_validator_preserves_source_conflict_and_fails_closed():
    plan = _validation_plan()
    raw = _raw_run(plan, (
        _candidate(plan, "one", stance="supports"),
        _candidate(plan, "two", stance="contradicts"),
    ))
    bundle = rc.validate_and_adjudicate_research(plan, raw, bundle_id="bundle-conflict")
    assert bundle.validated_research["claim_results"][0]["verdict"] == "unresolved"
    assert len(bundle.conflicts) == 1
    assert bundle.publication_disposition == "block"
