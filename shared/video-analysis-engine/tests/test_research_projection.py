#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED-first contracts for S6a ResearchProjectionPlan builder + materializer.

Pure builder: one finalized + validated ResearchBundle -> distinct
sparse/condensed/full ResearchProjectionPlan artifacts, without mutating the
bundle. A separate materializer resolves projection entries against the bundle
into structured per-section records with deterministic [R#]/[S#] labels.

Run:
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3.12 -m pytest -q \
      -p no:cacheprovider tests/test_research_projection.py
"""

from dataclasses import replace

import pytest

import research_contract as rc
import research_projection as rp


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _validated_research(n_rc=3, n_ent=3, n_kx=2, n_src=2, n_quote=2):
    sources = [
        {"source_uid": f"src-{i}", "content_hash": f"sha256:src{i}", "title": f"来源{i}"}
        for i in range(1, n_src + 1)
    ]
    quotes = [
        {
            "quote_uid": f"quote-{i}",
            "source_uid": f"src-{((i - 1) % n_src) + 1}",
            "verbatim_quote": f"原文引述{i}",
        }
        for i in range(1, n_quote + 1)
    ]
    research_claims = [
        {
            "research_claim_uid": f"rc-{i}",
            "priority": 100 - i,
            "statement": f"研究结论文本{i}",
            "supporting_quote_uids": [f"quote-{((i - 1) % n_quote) + 1}"],
            "source_uids": [f"src-{((i - 1) % n_src) + 1}"],
        }
        for i in range(1, n_rc + 1)
    ]
    entity_results = [
        {
            "entity_uid": f"ent-{i}",
            "priority": 100 - i,
            "label": f"实体标签{i}",
            "source_uid": f"src-{((i - 1) % n_src) + 1}",
        }
        for i in range(1, n_ent + 1)
    ]
    knowledge_expansions = [
        {
            "expansion_uid": f"kx-{i}",
            "priority": 100 - i,
            "relation": "supports",
            "research_claim_uids": [f"rc-{((i - 1) % n_rc) + 1}"],
        }
        for i in range(1, n_kx + 1)
    ]
    return {
        "sources": sources,
        "quotes": quotes,
        "research_claims": research_claims,
        "entity_results": entity_results,
        "knowledge_expansions": knowledge_expansions,
    }


def _bundle(validated_research=None):
    vr = validated_research if validated_research is not None else _validated_research()
    return rc.finalize_research_bundle(
        rc.ResearchBundle(
            schema_version=rc.RESEARCH_BUNDLE_SCHEMA_VERSION,
            bundle_id="rb-proj",
            plan_id="rp-proj",
            plan_semantic_hash="sha256:plan",
            evidence_bundle_hash="sha256:evidence",
            claim_bundle_hash="sha256:claims",
            attempted=True,
            executed=True,
            status="completed",
            publication_disposition="pass",
            started_at="2026-07-14T00:00:00Z",
            completed_at="2026-07-14T00:00:10Z",
            wrr_version="wrr/1",
            execution={"elapsed_ms": 1000, "query_count": 1},
            raw_research={"sources": [{"url": "https://example.com", "snippet": "c"}]},
            validated_research=vr,
            coverage={"verification": {"p0": 1.0}},
            conflicts=(),
            unresolved=(),
            errors=(),
            rule_versions={"validator": "1", "adjudicator": "1"},
        )
    )


def _build(mode, bundle=None, projection_id="proj-1", created_at="2026-07-14T00:00:00Z"):
    b = bundle if bundle is not None else _bundle()
    return rp.build_research_projection(
        b,
        report_plan_hash="sha256:reportplan",
        report_mode=mode,
        projection_id=projection_id,
        created_at=created_at,
    )


# ─── 1. Binding + validity ───────────────────────────────────────────────────

def test_projection_binds_bundle_inputs_and_validates():
    b = _bundle()
    proj = _build("sparse", bundle=b)

    assert proj.research_bundle_hash == b.validated_semantic_hash
    assert proj.evidence_bundle_hash == b.evidence_bundle_hash
    assert proj.claim_bundle_hash == b.claim_bundle_hash
    assert proj.report_plan_hash == "sha256:reportplan"
    assert proj.report_mode == "sparse"
    # Must be a finalized, self-consistent projection.
    rc.validate_research_projection(proj)


# ─── 2. Same bundle hash unchanged across modes; projections still distinct ───

def test_same_bundle_hash_across_modes_but_distinct_projections():
    b = _bundle()
    sparse = _build("sparse", bundle=b)
    condensed = _build("condensed", bundle=b)
    full = _build("full", bundle=b)

    # Acceptance 1: identical research_bundle_hash across all three modes.
    assert sparse.research_bundle_hash == condensed.research_bundle_hash == full.research_bundle_hash

    # Distinct projections: different budgets => different semantic hashes.
    hashes = {sparse.projection_semantic_hash,
              condensed.projection_semantic_hash,
              full.projection_semantic_hash}
    assert len(hashes) == 3


# ─── 3. Sparse budgets exactly spec §11.2 ────────────────────────────────────

def test_sparse_budgets_match_spec_11_2():
    proj = _build("sparse")
    sb = proj.section_budgets

    assert sb["3"]["max_research_items"] == 1 and sb["3"]["max_chars"] == 220
    assert sb["4"]["max_research_items"] == 1 and sb["4"]["max_chars"] == 320
    assert sb["6"]["max_entities"] == 3 and sb["6"]["max_edges"] == 2 and sb["6"]["max_chars"] == 260
    assert sb["7"]["max_research_items"] == 1 and sb["7"]["max_chars"] == 180
    assert sb["report_caps"]["max_rc"] == 4 and sb["report_caps"]["max_kx"] == 2


# ─── 4. Sparse caps enforced; overflow recorded as omissions, never dropped ──

def test_sparse_caps_and_omissions_never_silently_drop():
    b = _bundle(_validated_research(n_rc=5, n_ent=4, n_kx=3))
    proj = _build("sparse", bundle=b)

    def kinds(kind, coll):
        return [x for x in coll if x.get("object_type") == kind]

    rc_entries = kinds("research_claim", proj.entries)
    ent_entries = kinds("entity_result", proj.entries)
    edge_entries = kinds("knowledge_expansion", proj.entries)

    # report-wide RC cap = 4, but sparse §3/§4/§7 hold 1 each => 3 placeable.
    assert len(rc_entries) == 3
    assert len(ent_entries) == 3          # sparse §6 max_entities
    assert len(edge_entries) == 2         # sparse §6 max_edges / report kx cap

    # Every eligible object is either an entry or an omission — nothing dropped.
    rc_om = kinds("research_claim", proj.omissions)
    ent_om = kinds("entity_result", proj.omissions)
    edge_om = kinds("knowledge_expansion", proj.omissions)
    assert len(rc_entries) + len(rc_om) == 5
    assert len(ent_entries) + len(ent_om) == 4
    assert len(edge_entries) + len(edge_om) == 3
    for om in proj.omissions:
        assert om.get("object_uid") and om.get("reason")


# ─── 5. Stable hash + order despite run IDs, timestamps, and input order ─────

def test_stable_hash_despite_ids_timestamps_and_input_order():
    vr_a = _validated_research()
    vr_b = _validated_research()
    # Shuffle every collection order for the second bundle.
    vr_b = {k: list(reversed(v)) for k, v in vr_b.items()}

    a = _build("sparse", bundle=_bundle(vr_a), projection_id="run-A", created_at="2026-01-01T00:00:00Z")
    z = _build("sparse", bundle=_bundle(vr_b), projection_id="run-Z", created_at="2099-12-31T23:59:59Z")

    # projection_id / created_at are excluded from the semantic hash.
    assert a.projection_semantic_hash == z.projection_semantic_hash
    payload_a = rc.research_projection_semantic_payload(a)
    payload_z = rc.research_projection_semantic_payload(z)
    assert rc.canonical_json_bytes(payload_a) == rc.canonical_json_bytes(payload_z)


# ─── 6. Builder does not mutate the input bundle ─────────────────────────────

def test_builder_does_not_mutate_bundle():
    b = _bundle()
    before = b.validated_semantic_hash
    _build("full", bundle=b)
    rc.validate_research_bundle(b)
    assert b.validated_semantic_hash == before


# ─── 7. Plan entries carry only UIDs/purpose/policy/template/budgets ─────────

def test_plan_entries_contain_no_free_form_prose():
    proj = _build("full")
    allowed = {
        "entry_uid", "target_section", "object_type", "object_uid",
        "purpose", "priority", "required_video_evidence_uids",
        "allowed_research_claim_uids", "allowed_quote_uids",
        "deterministic_template_id", "max_chars", "citation_policy", "optional",
    }
    prose_markers = ("研究结论文本", "实体标签", "原文引述", "来源")
    for entry in proj.entries:
        assert set(entry.keys()) <= allowed, f"unexpected keys: {set(entry.keys()) - allowed}"
        flat = repr(entry)
        for marker in prose_markers:
            assert marker not in flat, f"free-form prose leaked into plan: {marker}"


# ─── 8. Materializer resolves deterministic [R#]/[S#] labels + display text ──

def test_materialize_returns_structured_records_with_stable_labels():
    b = _bundle()
    proj = _build("sparse", bundle=b)

    records = rp.materialize_research_projection(proj, b)
    # Structured per-section mapping.
    assert set(records.keys()) <= {"3", "4", "6", "7"}

    rc_records = [r for sec in records.values() for r in sec if r["object_type"] == "research_claim"]
    assert rc_records, "expected research_claim records"
    for r in rc_records:
        assert r["object_label"].startswith("RC")
        assert all(label.startswith("[R") for label in r["citation_labels"])
        assert r["display_text"].startswith("研究结论文本")  # read from bundle

    # Labels are deterministic across two independent materializations.
    again = rp.materialize_research_projection(proj, b)
    assert records == again

    # Every projected RC object is unique, so prose is not duplicated across sections.
    object_uids = [r["object_uid"] for sec in records.values() for r in sec
                   if r["object_type"] == "research_claim"]
    assert len(object_uids) == len(set(object_uids))


def test_materialize_labels_social_sources_as_s_and_research_sources_as_r():
    vr = _validated_research(n_rc=2, n_src=2, n_quote=2)
    vr["sources"][0]["source_kind"] = "official"
    vr["sources"][1]["source_kind"] = "social"
    b = _bundle(vr)
    records = rp.materialize_research_projection(_build("sparse", bundle=b), b)
    labels = {
        label
        for section in records.values()
        for record in section
        for label in record["citation_labels"]
    }
    assert any(label.startswith("[R") for label in labels)
    assert any(label.startswith("[S") for label in labels)


# ─── 9. Broken UID references fail closed ────────────────────────────────────

def _corrupt_first_rc_uid(proj, bogus="rc-does-not-exist"):
    entries = list(proj.entries)
    for i, e in enumerate(entries):
        if e.get("object_type") == "research_claim":
            entries[i] = {**e, "object_uid": bogus, "allowed_research_claim_uids": (bogus,)}
            break
    tampered = replace(proj, entries=tuple(entries))
    return rc.finalize_research_projection(tampered)


def test_broken_rc_ref_fails_closed_on_materialize():
    b = _bundle()
    proj = _build("sparse", bundle=b)
    tampered = _corrupt_first_rc_uid(proj)

    with pytest.raises(rp.ResearchProjectionError):
        rp.materialize_research_projection(tampered, b)


def test_broken_quote_ref_fails_closed_on_materialize():
    b = _bundle()
    proj = _build("sparse", bundle=b)

    entries = list(proj.entries)
    patched = False
    for i, e in enumerate(entries):
        if e.get("object_type") == "research_claim":
            entries[i] = {**e, "allowed_quote_uids": ("quote-nope",)}
            patched = True
            break
    assert patched
    tampered = rc.finalize_research_projection(replace(proj, entries=tuple(entries)))

    with pytest.raises(rp.ResearchProjectionError):
        rp.materialize_research_projection(tampered, b)


def test_materialize_rejects_mismatched_bundle():
    proj = _build("sparse", bundle=_bundle())
    other = _bundle(_validated_research(n_rc=4))  # different validated_semantic_hash

    with pytest.raises(rp.ResearchProjectionError):
        rp.materialize_research_projection(proj, other)
