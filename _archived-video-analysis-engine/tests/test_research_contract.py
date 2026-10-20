#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED-first contracts for research artifacts and canonical hashing."""

from dataclasses import replace

import pytest

import evidence_contract as ec
import research_contract as rc


def _identity():
    return ec.SourceIdentity(
        platform="bilibili",
        canonical_id="BVresearch",
        canonical_url="https://www.bilibili.com/video/BVresearch",
    )


def _evidence_bundle(metadata=None, errors=(), audience=()):
    return ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="ready",
        identity=_identity(),
        metadata=metadata or {"title": "研究样例", "duration_s": 62},
        transcript=ec.TranscriptEvidence(
            text="事实声明",
            language="zh",
            source="official_subtitle",
            content_hash="sha256:transcript",
            segments=(ec.TranscriptSegmentEvidence(0.0, 5.0, "事实声明"),),
        ),
        audience_signals=audience,
        provenance=ec.Provenance(
            adapter="test",
            adapter_version="1",
            collected_at="2026-07-13T00:00:00Z",
            source_refs=("https://example.com/b", "https://example.com/a"),
            hashes={"transcript": "sha256:transcript", "metadata": "sha256:metadata"},
        ),
        errors=errors,
    )


def _budget(max_queries=4):
    return rc.ResearchBudget(
        max_queries=max_queries,
        max_fetches=6,
        max_sources=6,
        max_elapsed_seconds=60,
        cross_check_depth=2,
        max_topics=2,
        max_knowledge_expansions=2,
        max_research_claims=4,
        p0_coverage=1.0,
        adopted_p1_coverage=1.0,
        p2_coverage=0.5,
        freshness_policy_id="default-v1",
    )


def _plan(**overrides):
    values = dict(
        schema_version=rc.RESEARCH_PLAN_SCHEMA_VERSION,
        plan_id="rp-one",
        created_at="2026-07-13T00:00:00Z",
        planner_version="research-planner/1",
        evidence_bundle_hash="sha256:evidence",
        claim_bundle_hash="sha256:claims",
        canonical_id="BVresearch",
        platform="bilibili",
        report_mode="sparse",
        research_policy="auto",
        capability_snapshot={"available": True, "route": "hermes_wrr", "checked_at": "t1"},
        verification_enabled=True,
        knowledge_expansion_enabled=True,
        budget=_budget(),
        entities=({"entity_uid": "ent-1", "priority": 90},),
        topics=({"topic_uid": "topic-1", "label": "概念"},),
        claims=({"claim_uid": "claim-1", "risk": "P1"},),
        queries=({"query_uid": "query-1", "priority": 90, "query": "概念 官方"},),
        expansion_candidates=(),
        stop_conditions={"require_all_p0_resolved": True},
    )
    values.update(overrides)
    return rc.finalize_research_plan(rc.ResearchPlan(**values))


def _bundle(**overrides):
    values = dict(
        schema_version=rc.RESEARCH_BUNDLE_SCHEMA_VERSION,
        bundle_id="rb-one",
        plan_id="rp-one",
        plan_semantic_hash="sha256:plan",
        evidence_bundle_hash="sha256:evidence",
        claim_bundle_hash="sha256:claims",
        attempted=True,
        executed=True,
        status="completed",
        publication_disposition="pass",
        started_at="2026-07-13T00:00:00Z",
        completed_at="2026-07-13T00:00:10Z",
        wrr_version="wrr/1",
        execution={"elapsed_ms": 1000, "query_count": 1},
        raw_research={"sources": [{"url": "https://example.com", "snippet": "candidate"}]},
        validated_research={
            "sources": [{"source_uid": "src-1", "content_hash": "sha256:source"}],
            "quotes": [{"quote_uid": "quote-1", "verbatim_quote": "原文"}],
            "claim_results": [{"claim_uid": "claim-1", "verdict": "supported"}],
            "knowledge_expansions": [{"expansion_uid": "kx-1", "research_claim_uids": ["rc-1"]}],
        },
        coverage={"verification": {"p0": 1.0}, "expansion": {"grounded": 1}},
        conflicts=(),
        unresolved=(),
        errors=(),
        rule_versions={"validator": "1", "adjudicator": "1"},
    )
    values.update(overrides)
    return rc.finalize_research_bundle(rc.ResearchBundle(**values))


def test_evidence_bundle_semantic_hash_is_order_stable_for_unordered_fields():
    err_a = ec.EvidenceError("audience_unavailable", "audience", True, "a")
    err_b = ec.EvidenceError("asr_failed", "asr", False, "b")
    sig_a = ec.AudienceSignal("comment", "A", 1.0)
    sig_b = ec.AudienceSignal("danmaku", "B", 2.0)
    left = _evidence_bundle(
        metadata={"title": "研究样例", "duration_s": 62},
        errors=(err_a, err_b),
        audience=(sig_a, sig_b),
    )
    right = _evidence_bundle(
        metadata={"duration_s": 62, "title": "研究样例"},
        errors=(err_b, err_a),
        audience=(sig_b, sig_a),
    )

    assert ec.evidence_bundle_semantic_hash(left) == ec.evidence_bundle_semantic_hash(right)
    assert ec.evidence_bundle_semantic_hash(left).startswith("sha256:")


def test_plan_semantic_hash_excludes_identity_and_check_time_but_tracks_behavior():
    first = _plan()
    same_semantics = _plan(
        plan_id="rp-two",
        created_at="2026-07-14T00:00:00Z",
        capability_snapshot={"available": True, "route": "hermes_wrr", "checked_at": "t2"},
    )
    changed_budget = _plan(budget=_budget(max_queries=5))

    assert first.plan_semantic_hash == same_semantics.plan_semantic_hash
    assert first.plan_semantic_hash != changed_budget.plan_semantic_hash
    rc.validate_research_plan(first)


def test_research_bundle_separates_validated_semantic_and_audit_hashes():
    first = _bundle()
    changed_execution = _bundle(
        bundle_id="rb-two",
        started_at="2026-07-14T00:00:00Z",
        execution={"elapsed_ms": 9000, "query_count": 1},
    )

    assert first.validated_semantic_hash == changed_execution.validated_semantic_hash
    assert first.audit_artifact_hash != changed_execution.audit_artifact_hash
    assert first.raw_hash == changed_execution.raw_hash
    rc.validate_research_bundle(first)


def test_projection_hash_uses_validated_bundle_hash_and_excludes_run_identity():
    first = rc.finalize_research_projection(rc.ResearchProjectionPlan(
        schema_version=rc.RESEARCH_PROJECTION_SCHEMA_VERSION,
        projection_id="projection-one",
        created_at="2026-07-13T00:00:00Z",
        projector_version="research-projector/1",
        evidence_bundle_hash="sha256:evidence",
        claim_bundle_hash="sha256:claims",
        research_bundle_hash="sha256:validated",
        report_plan_hash="sha256:report-plan",
        report_mode="sparse",
        section_budgets={"3": {"max_research_items": 1}},
        entries=({"entry_uid": "entry-1", "target_section": "3", "object_uid": "kx-1"},),
        omissions=(),
    ))
    same_semantics = rc.finalize_research_projection(replace(
        first,
        projection_id="projection-two",
        created_at="2026-07-14T00:00:00Z",
        projection_semantic_hash="",
    ))

    assert first.projection_semantic_hash == same_semantics.projection_semantic_hash
    assert first.research_bundle_hash == "sha256:validated"
    rc.validate_research_projection(first)


def test_hash_validation_rejects_tampered_artifact():
    plan = _plan()
    with pytest.raises(rc.ResearchContractViolation, match="plan_semantic_hash"):
        rc.validate_research_plan(replace(plan, queries=({"query_uid": "tampered"},)))

    bundle = _bundle()
    with pytest.raises(rc.ResearchContractViolation, match="validated_semantic_hash"):
        rc.validate_research_bundle(replace(bundle, coverage={"verification": {"p0": 0.0}}))


def test_research_contract_recursively_rejects_sensitive_payloads():
    with pytest.raises(rc.ResearchContractViolation, match="敏感"):
        rc.finalize_research_bundle(_bundle(
            raw_research={"provider": {"headers": {"Authorization": "Bearer secret"}}},
        ))


def test_research_status_and_policy_sets_are_closed():
    assert set(rc.RESEARCH_STATUSES) == {
        "not_requested", "unavailable", "completed", "partial", "failed", "blocked", "invalid",
    }
    assert set(rc.RESEARCH_POLICIES) == {"auto", "force", "deep", "off"}
    with pytest.raises(rc.ResearchContractViolation, match="status"):
        rc.validate_research_bundle(replace(_bundle(), status="mystery"))


def test_raw_hash_includes_route_trace_and_safe_provider_errors_but_not_latency():
    base = _bundle(execution={
        "elapsed_ms": 1000,
        "query_count": 1,
        "route_trace": ["grounding:exa", "grounding:brave"],
    })
    latency_only = _bundle(execution={
        "elapsed_ms": 9000,
        "query_count": 1,
        "route_trace": ["grounding:exa", "grounding:brave"],
    })
    changed_route = _bundle(execution={
        "elapsed_ms": 1000,
        "query_count": 1,
        "route_trace": ["grounding:brave", "grounding:exa"],
    })
    changed_error = _bundle(
        execution={
            "elapsed_ms": 1000,
            "query_count": 1,
            "route_trace": ["grounding:exa", "grounding:brave"],
        },
        errors=({"stage": "fetch", "code": "timeout", "safe_message": "timed out"},),
    )

    assert base.raw_hash == latency_only.raw_hash
    assert base.raw_hash != changed_route.raw_hash
    assert base.raw_hash != changed_error.raw_hash


def test_validated_semantic_hash_normalizes_uid_collections_and_nested_refs():
    left = _bundle(validated_research={
        "sources": [
            {"source_uid": "src-2", "content_hash": "sha256:2"},
            {"source_uid": "src-1", "content_hash": "sha256:1"},
        ],
        "quotes": [
            {"quote_uid": "quote-2", "source_uid": "src-2"},
            {"quote_uid": "quote-1", "source_uid": "src-1"},
        ],
        "claim_results": [
            {"claim_uid": "claim-2", "supporting_quote_uids": ["quote-2", "quote-1"]},
            {"claim_uid": "claim-1", "supporting_quote_uids": ["quote-1"]},
        ],
        "knowledge_expansions": [
            {"expansion_uid": "kx-2", "research_claim_uids": ["rc-2", "rc-1"]},
            {"expansion_uid": "kx-1", "research_claim_uids": ["rc-1"]},
        ],
    })
    right = _bundle(validated_research={
        "knowledge_expansions": [
            {"expansion_uid": "kx-1", "research_claim_uids": ["rc-1"]},
            {"expansion_uid": "kx-2", "research_claim_uids": ["rc-1", "rc-2"]},
        ],
        "claim_results": [
            {"claim_uid": "claim-1", "supporting_quote_uids": ["quote-1"]},
            {"claim_uid": "claim-2", "supporting_quote_uids": ["quote-1", "quote-2"]},
        ],
        "quotes": [
            {"quote_uid": "quote-1", "source_uid": "src-1"},
            {"quote_uid": "quote-2", "source_uid": "src-2"},
        ],
        "sources": [
            {"source_uid": "src-1", "content_hash": "sha256:1"},
            {"source_uid": "src-2", "content_hash": "sha256:2"},
        ],
    })

    assert left.validated_semantic_hash == right.validated_semantic_hash


@pytest.mark.parametrize(
    "validated",
    [
        {"sources": [{"content_hash": "sha256:missing-uid"}]},
        {"quotes": [{"quote_uid": "dup"}, {"quote_uid": "dup"}]},
    ],
)
def test_validated_uid_collections_reject_missing_or_duplicate_uids(validated):
    with pytest.raises(rc.ResearchContractViolation, match="UID"):
        _bundle(validated_research=validated)


def test_research_artifacts_are_deeply_immutable_copies():
    raw = {"sources": [{"candidate_uid": "candidate-1", "url": "https://example.com"}]}
    bundle = _bundle(raw_research=raw)
    raw["sources"][0]["url"] = "https://mutated.invalid"

    assert bundle.raw_research["sources"][0]["url"] == "https://example.com"
    with pytest.raises(TypeError):
        bundle.raw_research["new"] = "forbidden"
    with pytest.raises(TypeError):
        bundle.raw_research["sources"][0]["url"] = "forbidden"

    capability = {"available": True, "nested": {"route": "wrr"}}
    plan = _plan(capability_snapshot=capability)
    capability["nested"]["route"] = "mutated"
    assert plan.capability_snapshot["nested"]["route"] == "wrr"
    with pytest.raises(TypeError):
        plan.capability_snapshot["nested"]["route"] = "forbidden"

    projection = rc.finalize_research_projection(rc.ResearchProjectionPlan(
        schema_version=rc.RESEARCH_PROJECTION_SCHEMA_VERSION,
        projection_id="projection-immutable",
        created_at="2026-07-13T00:00:00Z",
        projector_version="research-projector/1",
        evidence_bundle_hash="sha256:evidence",
        claim_bundle_hash="sha256:claims",
        research_bundle_hash="sha256:validated",
        report_plan_hash="sha256:report-plan",
        report_mode="sparse",
        section_budgets={"3": {"max_chars": 220}},
    ))
    with pytest.raises(TypeError):
        projection.section_budgets["3"]["max_chars"] = 999


# ---------------------------------------------------------------------------
# S5A-1: validate_and_adjudicate_research 基础验证
# ---------------------------------------------------------------------------


def _ch(text):
    return rc.research_content_hash(text)


def _quote(
    text,
    snapshot_text=None,
    *,
    priority="P2",
    mode="full",
    mutable=False,
    conflicting=False,
    quote_hash=None,
    snapshot_hash=None,
    drop_snapshot=False,
    snippet_only=False,
):
    snapshot_text = text if snapshot_text is None else snapshot_text
    record = {
        "quote": text,
        "quote_hash": _ch(text) if quote_hash is None else quote_hash,
        "priority": priority,
        "mutable": mutable,
        "conflicting": conflicting,
    }
    if snippet_only:
        record["snippet"] = snapshot_text[:12]
        return record
    if drop_snapshot:
        return record
    record["snapshot"] = {
        "mode": mode,
        "text": snapshot_text,
        "snapshot_hash": _ch(snapshot_text) if snapshot_hash is None else snapshot_hash,
    }
    return record


def _candidate(candidate_uid, url, content, quotes):
    return {
        "candidate_uid": candidate_uid,
        "url": url,
        "content_hash": _ch(content),
        "quotes": list(quotes),
    }


def _execution(*, fetch_count, source_count, **overrides):
    execution = {
        "started_at": "2026-07-13T00:00:00Z",
        "completed_at": "2026-07-13T00:00:05Z",
        "query_count": 1,
        "fetch_count": fetch_count,
        "source_count": source_count,
        "elapsed_seconds": 5,
        "topic_count": 1,
        "knowledge_expansion_count": 1,
        "research_claim_count": 1,
    }
    execution.update(overrides)
    return execution


def _run(plan, candidates, *, source_count, execution=None, **run_overrides):
    raw_research = {
        "input_hashes": {
            "plan_semantic_hash": plan.plan_semantic_hash,
            "evidence_bundle_hash": plan.evidence_bundle_hash,
            "claim_bundle_hash": plan.claim_bundle_hash,
        },
        "candidates": list(candidates),
    }
    if "raw_research" in run_overrides:
        raw_research = run_overrides.pop("raw_research")
    execution = execution or _execution(
        fetch_count=len(candidates), source_count=source_count
    )
    values = dict(
        schema_version=rc.RAW_RESEARCH_RUN_SCHEMA_VERSION,
        run_id="raw-run-1",
        plan_semantic_hash=plan.plan_semantic_hash,
        capability_available=True,
        attempted=True,
        executed=True,
        status="completed",
        validated_evidence_count=0,
        route_trace=("grounding:exa", "grounding:brave"),
        execution=execution,
        raw_research=raw_research,
    )
    values.update(run_overrides)
    return rc.finalize_raw_research_run(rc.RawResearchRun(**values))


def _happy_candidates():
    body = "官方文档指出该机制在 2026 年保持稳定运行。"
    return [_candidate("cand-1", "https://example.com/doc", "page-body", [
        _quote("该机制在 2026 年保持稳定运行", body, priority="P1"),
    ])]


def test_validate_and_adjudicate_produces_finalized_immutable_bundle():
    plan = _plan()
    run = _run(plan, _happy_candidates(), source_count=1)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    assert isinstance(bundle, rc.ResearchBundle)
    rc.validate_research_bundle(bundle)  # finalized hashes close
    assert bundle.plan_semantic_hash == plan.plan_semantic_hash
    assert bundle.evidence_bundle_hash == plan.evidence_bundle_hash
    assert bundle.claim_bundle_hash == plan.claim_bundle_hash
    # A2b opens adjudication: the lone claim has no quote-backed assessment, so it
    # resolves to unresolved -> drop -> the bundle degrades (no required block).
    assert bundle.publication_disposition == "degraded"
    assert bundle.rule_versions["validator"] == rc.RESEARCH_VALIDATOR_RULE_VERSION
    assert bundle.started_at == "2026-07-13T00:00:00Z"  # time only from run.execution
    # An unbound quote (no claim_uid) cannot cross into validated research;
    # reverse claim references must close.
    sources = bundle.validated_research["sources"]
    assert len(sources) == 1 and sources[0]["source_uid"].startswith("src_")
    assert bundle.validated_research["quotes"] in ((), [])
    with pytest.raises(TypeError):
        bundle.validated_research["sources"] = "forbidden"


def test_run_plan_hash_binding_and_input_hash_closure_fail_closed():
    plan = _plan()
    # run.plan_semantic_hash must equal plan.plan_semantic_hash
    with pytest.raises(rc.ResearchContractViolation, match="plan_semantic_hash"):
        rc.validate_and_adjudicate_research(
            plan,
            _run(
                plan,
                _happy_candidates(),
                source_count=1,
                plan_semantic_hash="sha256:wrong",
                raw_hash="",
            ),
        )
    # raw_research.input_hashes must fully close with the plan
    for key, bad in (
        ("plan_semantic_hash", "sha256:x"),
        ("evidence_bundle_hash", "sha256:x"),
        ("claim_bundle_hash", "sha256:x"),
    ):
        raw = {
            "input_hashes": {
                "plan_semantic_hash": plan.plan_semantic_hash,
                "evidence_bundle_hash": plan.evidence_bundle_hash,
                "claim_bundle_hash": plan.claim_bundle_hash,
            },
            "candidates": _happy_candidates(),
        }
        raw["input_hashes"][key] = bad
        run = _run(plan, _happy_candidates(), source_count=1, raw_research=raw)
        with pytest.raises(rc.ResearchContractViolation, match="input_hashes"):
            rc.validate_and_adjudicate_research(plan, run)
    # missing input_hashes entirely also fails closed
    run = _run(
        plan,
        _happy_candidates(),
        source_count=1,
        raw_research={"candidates": _happy_candidates()},
    )
    with pytest.raises(rc.ResearchContractViolation, match="input_hashes"):
        rc.validate_and_adjudicate_research(plan, run)


@pytest.mark.parametrize(
    "over",
    [
        {"query_count": 99},
        {"fetch_count": 99},
        {"source_count": 99},
        {"elapsed_seconds": 9999},
        {"topic_count": 99},
        {"knowledge_expansion_count": 99},
        {"research_claim_count": 99},
    ],
)
def test_hard_budget_overflow_raises_and_never_truncates(over):
    plan = _plan()
    candidates = _happy_candidates()
    # fetch_count must still equal candidate count except where we overflow it
    execution_values = {"fetch_count": len(candidates), "source_count": 1}
    execution_values.update(over)
    execution = _execution(**execution_values)
    run = _run(plan, candidates, source_count=1, execution=execution)
    with pytest.raises(rc.ResearchContractViolation, match="预算|budget"):
        rc.validate_and_adjudicate_research(plan, run)


def test_execution_summary_must_close_with_stable_uid_counts():
    plan = _plan()
    candidates = _happy_candidates()
    # declared source_count disagrees with the actual accepted stable UID set
    execution = _execution(fetch_count=len(candidates), source_count=3)
    run = _run(plan, candidates, source_count=3, execution=execution)
    with pytest.raises(rc.ResearchContractViolation, match="闭合|source_count"):
        rc.validate_and_adjudicate_research(plan, run)
    # declared fetch_count disagrees with the actual candidate material
    execution = _execution(fetch_count=5, source_count=1)
    run = _run(plan, candidates, source_count=1, execution=execution)
    with pytest.raises(rc.ResearchContractViolation, match="闭合|fetch_count"):
        rc.validate_and_adjudicate_research(plan, run)


def test_canonical_url_dedup_keeps_minimal_stable_representative():
    body = "官方来源确认该结论成立于 2026 年。"
    quote = "该结论成立于 2026 年"
    # Same canonical target reached three ways: case, default port, tracking, sort, fragment.
    variants = [
        _candidate("cand-3", "HTTPS://Example.com:443/Doc?b=2&a=1", "same-body", [
            _quote(quote, body, priority="P1")]),
        _candidate("cand-1", "https://example.com/Doc?a=1&b=2#frag", "same-body", [
            _quote(quote, body, priority="P1")]),
        _candidate("cand-2", "https://example.com/Doc?utm_source=x&a=1&b=2", "same-body", [
            _quote(quote, body, priority="P1")]),
    ]
    plan = _plan()
    run = _run(plan, variants, source_count=1)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    sources = bundle.validated_research["sources"]
    assert len(sources) == 1
    assert sources[0]["canonical_url"] == "https://example.com/Doc?a=1&b=2"
    assert sources[0]["representative_candidate_uid"] == "cand-1"  # minimal stable UID


def test_canonical_url_rejects_credentials_and_signed_tokens_as_candidate_rejections():
    body = "内容正文含被引用片段。"
    quote = "被引用片段"
    plan = _plan()
    bad = [
        _candidate("cand-cred", "https://user:pass@example.com/a", "b1", [
            _quote(quote, body, priority="P1")]),
        _candidate("cand-sig", "https://example.com/a?sig=deadbeef", "b2", [
            _quote(quote, body, priority="P1")]),
    ]
    run = _run(plan, bad, source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    assert bundle.validated_research.get("sources", ()) == () or len(
        bundle.validated_research["sources"]
    ) == 0
    reasons = {
        r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]
    }
    assert "url_credentials" in reasons and "url_signed_token" in reasons
    # signed/credential material never leaks into the bundle
    rc.validate_research_bundle(bundle)


@pytest.mark.parametrize(
    "quote_kwargs,reason",
    [
        (dict(snippet_only=True), "snippet_only"),
        (dict(drop_snapshot=True), "missing_snapshot"),
        (dict(quote_hash=""), "missing_hash"),
        (dict(snapshot_hash="sha256:bogus"), "snapshot_hash_mismatch"),
        (dict(quote_hash="sha256:bogus"), "quote_hash_mismatch"),
    ],
)
def test_quote_snapshot_defects_become_candidate_rejections(quote_kwargs, reason):
    body = "正文完整包含引用句子内容。"
    quote = "引用句子内容"
    plan = _plan()
    candidate = _candidate("cand-x", "https://example.com/x", "body", [
        _quote(quote, body, priority="P1", **quote_kwargs)])
    run = _run(plan, [candidate], source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    assert bundle.validated_research.get("quotes", ()) in ((), [])
    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert reason in reasons


def test_quote_not_in_snapshot_body_is_rejected():
    plan = _plan()
    candidate = _candidate("cand-q", "https://example.com/q", "body", [
        _quote("不在正文中的句子", "完全不同的正文内容。", priority="P1")])
    run = _run(plan, [candidate], source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)
    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "quote_not_in_snapshot" in reasons


def test_p0_and_mutable_p1_require_full_snapshot():
    body = "正文里明确写着这句被引用的话。"
    quote = "这句被引用的话"
    plan = _plan()
    # P0 snippet-mode snapshot -> must be full
    p0 = _candidate("cand-p0", "https://example.com/p0", "b", [
        _quote(quote, body, priority="P0", mode="snippet")])
    # P1 conflicting snippet-mode snapshot -> must be full
    p1 = _candidate("cand-p1", "https://example.com/p1", "b", [
        _quote(quote, body, priority="P1", mode="snippet", conflicting=True)])
    for candidate in (p0, p1):
        run = _run(plan, [candidate], source_count=0)
        bundle = rc.validate_and_adjudicate_research(plan, run)
        reasons = {
            r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]
        }
        assert "snapshot_not_full" in reasons
        assert bundle.validated_research.get("quotes", ()) in ((), [])
    # A non-conflicting P2 snippet snapshot is acceptable
    p2_quote = _quote(quote, body, priority="P2", mode="snippet")
    p2_quote["claim_uid"] = "claim-1"
    p2 = _candidate("cand-p2", "https://example.com/p2", "b", [p2_quote])
    run = rc.validate_and_adjudicate_research(plan, _run(plan, [p2], source_count=1))
    assert len(run.validated_research["quotes"]) == 1


def test_rejections_never_enter_validated_research_and_order_is_stable():
    body = "正文包含唯一有效的引用片段内容。"
    good = _quote("唯一有效的引用片段内容", body, priority="P1")
    accepted = _candidate("cand-ok", "https://example.com/ok", "b-ok", [good])
    rejected = _candidate("cand-bad", "https://example.com/bad", "b-bad", [
        _quote("坏引用", "坏引用", priority="P1", snapshot_hash="sha256:bogus")])
    plan = _plan()
    forward = _run(plan, [accepted, rejected], source_count=1)
    reverse = _run(plan, [rejected, accepted], source_count=1)

    bundle_a = rc.validate_and_adjudicate_research(plan, forward)
    bundle_b = rc.validate_and_adjudicate_research(plan, reverse)

    # identical inputs in any order -> identical validated + audit hashes
    assert bundle_a.validated_semantic_hash == bundle_b.validated_semantic_hash
    assert bundle_a.raw_hash == bundle_b.raw_hash
    # accepted source present, rejected candidate absent from validated_research
    src_uids = {s["representative_candidate_uid"] for s in bundle_a.validated_research["sources"]}
    assert src_uids == {"cand-ok"}
    audit_cands = {r["candidate_uid"] for r in bundle_a.raw_research["validation_audit"]["rejections"]}
    assert "cand-bad" in audit_cands


def test_canonical_and_content_hash_helpers_are_pure_public_api():
    assert rc.canonical_research_url("HTTPS://Example.com:443/A?b=2&utm_x=1&a=1#f") == (
        "https://example.com/A?a=1&b=2"
    )
    with pytest.raises(rc.ResearchContractViolation, match="credential|凭据|signed"):
        rc.canonical_research_url("https://u:p@example.com/a")
    assert rc.research_content_hash("abc").startswith("sha256:")


def test_sensitive_payload_rejection_covers_plan_bundle_projection_and_signed_url():
    with pytest.raises(rc.ResearchContractViolation, match="敏感"):
        _plan(capability_snapshot={"available": True, "headers": {"X": "secret"}})
    with pytest.raises(rc.ResearchContractViolation, match="敏感"):
        _bundle(validated_research={"sources": [{"source_uid": "src", "token": "secret"}]})
    with pytest.raises(rc.ResearchContractViolation, match="敏感"):
        _bundle(raw_research={"url": "https://example.com/a?X-Amz-Signature=secret"})

    projection = rc.ResearchProjectionPlan(
        schema_version=rc.RESEARCH_PROJECTION_SCHEMA_VERSION,
        projection_id="projection-secret",
        created_at="2026-07-13T00:00:00Z",
        projector_version="research-projector/1",
        evidence_bundle_hash="sha256:evidence",
        claim_bundle_hash="sha256:claims",
        research_bundle_hash="sha256:validated",
        report_plan_hash="sha256:report-plan",
        report_mode="sparse",
        section_budgets={},
        entries=({"entry_uid": "entry", "headers": {"Authorization": "secret"}},),
    )
    with pytest.raises(rc.ResearchContractViolation, match="敏感"):
        rc.finalize_research_projection(projection)


# ---------------------------------------------------------------------------
# S5A-1 hardening: Hermes-adapter schema (url/content/query_uid/quote_candidates)
# shares the fixture snapshot/quote/full-snapshot rules and the conservative
# counter/dedup/audit invariants.
# ---------------------------------------------------------------------------


def _h_quote(
    quote_text,
    *,
    claim_uid="claim-1",
    priority="P2",
    mutable=False,
    conflicting=False,
    quote_hash=None,
):
    return {
        "claim_uid": claim_uid,
        "quote_text": quote_text,
        "quote_hash": _ch(quote_text) if quote_hash is None else quote_hash,
        "priority": priority,
        "mutable": mutable,
        "conflicting": conflicting,
    }


def _h_candidate(
    candidate_uid,
    url,
    content,
    quotes,
    *,
    query_uid="query-1",
    content_hash=None,
    snapshot_mode="full",
    snippet_only=False,
):
    candidate = {
        "candidate_uid": candidate_uid,
        "query_uid": query_uid,
        "url": url,
        "content": content,
        "content_hash": _ch(content) if content_hash is None else content_hash,
        "snapshot_mode": snapshot_mode,
        "quote_candidates": list(quotes),
    }
    if snippet_only:
        candidate["snippet_only"] = True
    return candidate


def _h_happy():
    body = "官方文档指出该机制在 2026 年保持稳定运行。"
    return [
        _h_candidate(
            "hc-1", "https://example.com/doc", body,
            [_h_quote("该机制在 2026 年保持稳定运行", priority="P1")],
        )
    ]


def test_hermes_schema_produces_conservative_blocked_bundle():
    plan = _plan()
    run = _run(plan, _h_happy(), source_count=1)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    assert isinstance(bundle, rc.ResearchBundle)
    rc.validate_research_bundle(bundle)  # finalized hashes close
    assert bundle.publication_disposition == "degraded"  # single P1 support < 2 publishers
    sources = bundle.validated_research["sources"]
    assert len(sources) == 1 and sources[0]["source_uid"].startswith("src_")
    assert sources[0]["representative_candidate_uid"] == "hc-1"
    assert bundle.validated_research["quotes"][0]["quote_uid"].startswith("quote_")
    # detailed rejection ledger lives only in raw_research.validation_audit
    assert "validation_audit" in bundle.raw_research
    with pytest.raises(TypeError):
        bundle.validated_research["sources"] = "forbidden"


@pytest.mark.parametrize("mutate", ["missing", "nan", "inf", "negative"])
def test_hermes_hard_counters_fail_closed(mutate):
    plan = _plan()
    candidates = _h_happy()
    execution = _execution(fetch_count=len(candidates), source_count=1)
    if mutate == "missing":
        execution.pop("topic_count")
    elif mutate == "nan":
        execution["topic_count"] = float("nan")
    elif mutate == "inf":
        execution["elapsed_seconds"] = float("inf")
    elif mutate == "negative":
        execution["research_claim_count"] = -1
    with pytest.raises(
        rc.ResearchContractViolation, match="counter|有限|非有限|非法|负数|数值|预算|budget|canonicalize"
    ):
        # NaN/Inf 可以在 canonical RawResearchRun 构造阶段被拒绝；其余非法计数
        # 在 adjudication 的 hard-budget gate 被拒绝。两条入口都必须 fail closed。
        run = _run(plan, candidates, source_count=1, execution=execution)
        rc.validate_and_adjudicate_research(plan, run)


def test_hermes_source_count_closure_fails_closed():
    plan = _plan()
    candidates = _h_happy()
    execution = _execution(fetch_count=len(candidates), source_count=3)
    run = _run(plan, candidates, source_count=3, execution=execution)
    with pytest.raises(rc.ResearchContractViolation, match="闭合|source_count"):
        rc.validate_and_adjudicate_research(plan, run)


def test_hermes_canonical_url_dedup_keeps_min_representative():
    body = "同一来源正文包含被引用的稳定结论内容。"
    quote = "被引用的稳定结论内容"
    variants = [
        _h_candidate("hc-3", "HTTPS://Example.com:443/Doc?b=2&a=1", body, [
            _h_quote(quote, priority="P1")]),
        _h_candidate("hc-1", "https://example.com/Doc?a=1&b=2#frag", body, [
            _h_quote(quote, priority="P1")]),
        _h_candidate("hc-2", "https://example.com/Doc?utm_source=x&a=1&b=2", body, [
            _h_quote(quote, priority="P1")]),
    ]
    plan = _plan()
    run = _run(plan, variants, source_count=1)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    sources = bundle.validated_research["sources"]
    assert len(sources) == 1
    assert sources[0]["canonical_url"] == "https://example.com/Doc?a=1&b=2"
    assert sources[0]["representative_candidate_uid"] == "hc-1"  # minimal stable UID


def test_hermes_conflicting_content_hash_keeps_min_and_audits_conflict():
    quote = "两个抓取共享的稳定结论"
    body_a = "抓取A的正文包含两个抓取共享的稳定结论片段。"
    body_b = "抓取B的正文同样包含两个抓取共享的稳定结论但正文不同。"
    plan = _plan()
    candidates = [
        _h_candidate("hc-b", "https://example.com/same", body_b, [
            _h_quote(quote, priority="P1")]),
        _h_candidate("hc-a", "https://example.com/same", body_a, [
            _h_quote(quote, priority="P1")]),
    ]
    run = _run(plan, candidates, source_count=1)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    sources = bundle.validated_research["sources"]
    assert len(sources) == 1
    # canonical URL is identity; minimal candidate_uid wins even across hash conflict
    assert sources[0]["representative_candidate_uid"] == "hc-a"
    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "content_hash_conflict" in reasons
    # conflicting body content never leaks into the sealed bundle
    rc.validate_research_bundle(bundle)
    assert "抓取B" not in repr(bundle.validated_research)


def test_hermes_snippet_only_candidate_rejected():
    plan = _plan()
    body = "正文包含被引用的稳定片段内容。"
    cand = _h_candidate(
        "hc-s", "https://example.com/s", body,
        [_h_quote("被引用的稳定片段内容", priority="P1")], snippet_only=True,
    )
    run = _run(plan, [cand], source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "snippet_only" in reasons
    assert bundle.validated_research.get("quotes", ()) in ((), [])


@pytest.mark.parametrize(
    "cand_kwargs,quote_kwargs,reason",
    [
        (dict(), dict(quote_hash="sha256:bogus"), "quote_hash_mismatch"),
        (dict(content_hash="sha256:bogus"), dict(), "missing_content_hash"),
        (dict(snapshot_mode="snippet"), dict(priority="P0"), "snapshot_not_full"),
    ],
)
def test_hermes_quote_defects_become_rejections(cand_kwargs, quote_kwargs, reason):
    plan = _plan()
    body = "正文完整包含被引用句子内容片段。"
    quote = "被引用句子内容片段"
    cand = _h_candidate(
        "hc-d", "https://example.com/d", body,
        [_h_quote(quote, **quote_kwargs)], **cand_kwargs,
    )
    run = _run(plan, [cand], source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert reason in reasons
    assert bundle.validated_research.get("quotes", ()) in ((), [])


def test_hermes_quote_not_in_content_rejected():
    plan = _plan()
    cand = _h_candidate(
        "hc-n", "https://example.com/n", "完全不同的正文内容。",
        [_h_quote("不在正文中的句子", priority="P1")],
    )
    run = _run(plan, [cand], source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "quote_not_in_snapshot" in reasons


def test_hermes_order_independent_bundle_id_and_hashes():
    plan = _plan()
    body1 = "第一份来源正文包含第一处稳定引用内容。"
    body2 = "第二份来源正文包含第二处稳定引用内容。"
    c1 = _h_candidate("hc-1", "https://example.com/one", body1, [
        _h_quote("第一处稳定引用内容", priority="P1")])
    c2 = _h_candidate("hc-2", "https://example.com/two", body2, [
        _h_quote("第二处稳定引用内容", priority="P1")])
    forward = _run(plan, [c1, c2], source_count=2)
    reverse = _run(plan, [c2, c1], source_count=2)

    a = rc.validate_and_adjudicate_research(plan, forward)
    b = rc.validate_and_adjudicate_research(plan, reverse)

    # bundle_id must not depend on input-order-sensitive run.raw_hash
    assert a.bundle_id == b.bundle_id
    assert a.raw_hash == b.raw_hash
    assert a.validated_semantic_hash == b.validated_semantic_hash
    assert a.audit_artifact_hash == b.audit_artifact_hash


def test_hermes_rejections_only_in_audit_with_stable_fields():
    plan = _plan()
    good_body = "有效来源正文包含唯一有效引用片段内容。"
    good = _h_candidate("hc-ok", "https://example.com/ok", good_body, [
        _h_quote("唯一有效引用片段内容", priority="P1")])
    bad = _h_candidate("hc-bad", "https://example.com/bad", "坏来源正文。", [
        _h_quote("缺席引用", priority="P1")])
    forward = _run(plan, [good, bad], source_count=1)
    reverse = _run(plan, [bad, good], source_count=1)

    a = rc.validate_and_adjudicate_research(plan, forward)
    b = rc.validate_and_adjudicate_research(plan, reverse)

    assert a.validated_semantic_hash == b.validated_semantic_hash
    reps = {s["representative_candidate_uid"] for s in a.validated_research["sources"]}
    assert reps == {"hc-ok"}
    audit = a.raw_research["validation_audit"]["rejections"]
    assert {"hc-bad"} <= {r["candidate_uid"] for r in audit}
    for record in audit:
        assert set(record) >= {"candidate_uid", "stage", "quote_index", "reason"}
    assert "坏来源正文" not in repr(a.validated_research)


def test_fixture_conflicting_content_hash_keeps_min_and_audits():
    quote = "两抓取共享的确认结论"
    body_a = "抓取A正文包含两抓取共享的确认结论。"
    body_b = "抓取B正文也包含两抓取共享的确认结论但不同。"
    plan = _plan()
    candidates = [
        _candidate("cf-b", "https://example.com/same", "content-b", [
            _quote(quote, body_b, priority="P1")]),
        _candidate("cf-a", "https://example.com/same", "content-a", [
            _quote(quote, body_a, priority="P1")]),
    ]
    run = _run(plan, candidates, source_count=1)
    bundle = rc.validate_and_adjudicate_research(plan, run)

    sources = bundle.validated_research["sources"]
    assert len(sources) == 1
    assert sources[0]["representative_candidate_uid"] == "cf-a"
    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "content_hash_conflict" in reasons


def test_conservative_duplicate_candidate_uid_fails_closed():
    plan = _plan()
    body = "正文包含被引用稳定片段内容。"
    quote = "被引用稳定片段内容"
    dup = [
        _candidate("dup", "https://example.com/a", "c-a", [_quote(quote, body, priority="P1")]),
        _candidate("dup", "https://example.com/b", "c-b", [_quote(quote, body, priority="P1")]),
    ]
    run = _run(plan, dup, source_count=2)
    with pytest.raises(rc.ResearchContractViolation, match="candidate_uid|重复"):
        rc.validate_and_adjudicate_research(plan, run)


def test_conservative_missing_candidate_uid_fails_closed():
    plan = _plan()
    body = "正文包含被引用稳定片段内容。"
    quote = "被引用稳定片段内容"
    cand = _candidate("", "https://example.com/a", "c-a", [_quote(quote, body, priority="P1")])
    run = _run(plan, [cand], source_count=1)
    with pytest.raises(rc.ResearchContractViolation, match="candidate_uid|缺少"):
        rc.validate_and_adjudicate_research(plan, run)


@pytest.mark.parametrize("counter", rc._HARD_COUNTERS)
def test_hermes_every_hard_counter_is_required(counter):
    plan = _plan()
    candidates = _h_happy()
    execution = _execution(fetch_count=1, source_count=1)
    execution.pop(counter)
    run = _run(plan, candidates, source_count=1, execution=execution)
    with pytest.raises(rc.ResearchContractViolation, match="counter|缺少"):
        rc.validate_and_adjudicate_research(plan, run)


@pytest.mark.parametrize("counter", ["fetch_count", "source_count"])
def test_materialized_counter_fraction_never_closes(counter):
    plan = _plan()
    candidates = _h_happy()
    execution = _execution(fetch_count=1, source_count=1)
    execution[counter] = 1.5
    run = _run(plan, candidates, source_count=1, execution=execution)
    with pytest.raises(rc.ResearchContractViolation, match="闭合|整数|counter"):
        rc.validate_and_adjudicate_research(plan, run)


def test_non_mapping_candidate_fails_closed_before_filtering():
    plan = _plan()
    candidates = [*_h_happy(), "not-a-candidate"]
    run = _run(plan, candidates, source_count=1)
    with pytest.raises(rc.ResearchContractViolation, match="candidate.*mapping|候选.*mapping"):
        rc.validate_and_adjudicate_research(plan, run)


@pytest.mark.parametrize("candidate_uid", ["", "duplicate"])
def test_hermes_missing_or_duplicate_candidate_uid_fails_closed(candidate_uid):
    plan = _plan()
    body = "Hermes 正文包含稳定引用片段。"
    quote = _h_quote("稳定引用片段", priority="P1")
    first = _h_candidate(candidate_uid, "https://example.com/a", body, [quote])
    candidates = [first]
    source_count = 1
    if candidate_uid == "duplicate":
        candidates.append(_h_candidate(candidate_uid, "https://example.com/b", body, [quote]))
        source_count = 2
    run = _run(plan, candidates, source_count=source_count)
    with pytest.raises(rc.ResearchContractViolation, match="candidate_uid|缺少|重复"):
        rc.validate_and_adjudicate_research(plan, run)


@pytest.mark.parametrize("flag", ["mutable", "conflicting"])
def test_hermes_p1_mutable_or_conflicting_requires_full_snapshot(flag):
    plan = _plan()
    body = "Hermes 正文包含需要验证的稳定引用片段。"
    quote_kwargs = {flag: True, "priority": "P1"}
    candidate = _h_candidate(
        "hc-p1", "https://example.com/p1", body,
        [_h_quote("需要验证的稳定引用片段", **quote_kwargs)],
        snapshot_mode="snippet",
    )
    run = _run(plan, [candidate], source_count=0)
    bundle = rc.validate_and_adjudicate_research(plan, run)
    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "snapshot_not_full" in reasons
    assert bundle.validated_research.get("quotes", ()) in ((), [])


# ---------------------------------------------------------------------------
# S5A-2a: Validator semantic layer — freshness / source suitability /
# independence / social restriction. The conservative shared path emits
# deterministic, quote-backed claim_source_assessments; publication stays
# unconditionally blocked (final five-state verdict opens in A2b).
# ---------------------------------------------------------------------------


def _sem_claim(
    claim_uid,
    *,
    temporal_class="stable",
    window_days=None,
    claim_class="factual",
    risk="P1",
):
    claim = {
        "claim_uid": claim_uid,
        "risk": risk,
        "temporal_class": temporal_class,
        "claim_class": claim_class,
    }
    if window_days is not None:
        claim["freshness_window_days"] = window_days
    return claim


def _sem_quote(text, snapshot_text=None, *, claim_uid="claim-1", priority="P1", **kw):
    quote = _quote(text, snapshot_text, priority=priority, **kw)
    quote["claim_uid"] = claim_uid
    return quote


def _sem_candidate(candidate_uid, url, content, quotes, **meta):
    candidate = _candidate(candidate_uid, url, content, quotes)
    candidate.update(meta)
    return candidate


def _assessments(bundle):
    return tuple(bundle.validated_research.get("claim_source_assessments", ()))


def _assessment_rejections(bundle):
    audit = bundle.raw_research.get("validation_audit", {})
    return tuple(audit.get("assessment_rejections", ()))


def _for_claim(bundle, claim_uid):
    return [a for a in _assessments(bundle) if a["claim_uid"] == claim_uid]


_STRONG_META = dict(
    source_kind="official_doc",
    authority_relation="primary",
    quality="high",
    access="public",
    publisher="OfficialCorp",
)


def _sem_run(plan, candidates, *, source_count, **overrides):
    return _run(plan, candidates, source_count=source_count, **overrides)


@pytest.mark.parametrize(
    "temporal_class,window,published_at,expected",
    [
        ("stable", None, "", "timeless"),
        ("timeless", None, "", "timeless"),
        ("current", 30, "2026-07-01T00:00:00Z", "fresh"),
        ("current", 30, "2026-05-01T00:00:00Z", "stale"),
        ("breaking", 7, "", "unverifiable"),
        ("versioned", 30, "", "unverifiable"),
    ],
)
def test_freshness_is_pure_and_reference_time_from_run(
    temporal_class, window, published_at, expected
):
    # Reference time is run.execution.completed_at (2026-07-13T00:00:05Z); no
    # wall clock is ever consulted.
    plan = _plan(
        claims=(_sem_claim("claim-1", temporal_class=temporal_class, window_days=window),)
    )
    body = "官方来源正文包含被引用的稳定结论内容片段。"
    cand = _sem_candidate(
        "s1", "https://example.com/doc", body,
        [_sem_quote("被引用的稳定结论内容片段", body)],
        published_at=published_at, **_STRONG_META,
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    a = _for_claim(bundle, "claim-1")[0]
    assert a["freshness_status"] == expected
    assert a["suitability_factors"]["freshness"] == expected


@pytest.mark.parametrize(
    "temporal_class,published_at",
    [
        ("unknown-temporal-class", "2026-07-01T00:00:00Z"),
        ("current", "2026-08-01T00:00:00Z"),
    ],
)
def test_freshness_unknown_class_or_future_date_is_unverifiable(
    temporal_class, published_at
):
    plan = _plan(claims=(
        _sem_claim("claim-1", temporal_class=temporal_class, window_days=30),
    ))
    body = "官方来源正文包含被引用的稳定结论内容片段。"
    cand = _sem_candidate(
        "s1", "https://example.com/doc", body,
        [_sem_quote("被引用的稳定结论内容片段", body)],
        published_at=published_at, **_STRONG_META,
    )
    bundle = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [cand], source_count=1)
    )
    assert _for_claim(bundle, "claim-1")[0]["freshness_status"] == "unverifiable"


def test_source_suitability_keeps_orthogonal_fields_and_derives_grade():
    plan = _plan(claims=(_sem_claim("claim-1"),))
    body = "官方来源正文包含被引用的稳定结论内容片段。"
    strong = _sem_candidate(
        "s-strong", "https://example.com/strong", body,
        [_sem_quote("被引用的稳定结论内容片段", body)], **_STRONG_META,
    )
    weak = _sem_candidate(
        "s-weak", "https://blog.example.com/weak", body,
        [_sem_quote("被引用的稳定结论内容片段", body)],
        source_kind="blog", authority_relation="self", quality="low",
        access="public", publisher="RandomBlog",
    )
    bundle = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [strong, weak], source_count=2)
    )
    by_src = {a["source_uid"]: a for a in _for_claim(bundle, "claim-1")}
    grades = {a["suitability"] for a in by_src.values()}
    assert grades == {"strong", "weak"}
    for a in by_src.values():
        factors = a["suitability_factors"]
        # orthogonal fields survive; the derived grade never replaces them
        assert set(factors) >= {
            "source_kind", "authority_relation", "quality", "access", "freshness",
        }
        assert a["suitability"] not in factors.values() or a["suitability"] == "strong"
    strong_a = next(a for a in by_src.values() if a["suitability"] == "strong")
    assert strong_a["suitability_factors"]["source_kind"] == "official_doc"
    assert strong_a["suitability_factors"]["authority_relation"] == "primary"


def test_restricted_access_is_invalid_and_only_in_raw_audit():
    plan = _plan(claims=(_sem_claim("claim-1"),))
    body = "受限来源正文包含被引用的稳定结论内容片段。"
    cand = _sem_candidate(
        "s-restricted", "https://paywall.example.com/x", body,
        [_sem_quote("被引用的稳定结论内容片段", body)],
        source_kind="news", authority_relation="secondary", quality="medium",
        access="restricted", publisher="Paywalled",
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    # invalid suitability -> assessment never enters the validated collection
    assert _for_claim(bundle, "claim-1") == []
    rejected = _assessment_rejections(bundle)
    assert any(r["suitability"] == "invalid" for r in rejected)
    rc.validate_research_bundle(bundle)


def test_normal_factual_source_supports_and_is_quote_backed():
    plan = _plan(claims=(_sem_claim("claim-1"),))
    body = "官方来源正文包含被引用的稳定结论内容片段。"
    cand = _sem_candidate(
        "s1", "https://example.com/doc", body,
        [_sem_quote("被引用的稳定结论内容片段", body)], **_STRONG_META,
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    a = _for_claim(bundle, "claim-1")[0]
    assert a["role"] == "support"
    assert a["proposed_relation"] == "supports"
    assert a["validated_relation"] == "supports"
    assert a["assessment_uid"].startswith("assessment_")
    assert a["quote_uids"] and all(q.startswith("quote_") for q in a["quote_uids"])
    # A2b adjudicates: one P1 support is below the 2-publisher threshold -> unresolved.
    assert bundle.publication_disposition == "degraded"
    results = bundle.validated_research["claim_results"]
    assert len(results) == 1 and results[0]["verdict"] == "unresolved"


def _indep_pair(meta_a, meta_b, *, body_a, body_b):
    plan = _plan(claims=(_sem_claim("claim-1"),))
    ca = _sem_candidate(
        "s-a", "https://a.example.com/x", body_a,
        [_sem_quote("被引用的稳定结论内容片段", body_a)], **meta_a,
    )
    cb = _sem_candidate(
        "s-b", "https://b.example.com/y", body_b,
        [_sem_quote("被引用的稳定结论内容片段", body_b)], **meta_b,
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [ca, cb], source_count=2))
    return {a["source_uid"]: a["independence_group"] for a in _for_claim(bundle, "claim-1")}


def test_independence_same_publisher_merges_into_one_group():
    body_a = "甲来源正文包含被引用的稳定结论内容片段其一。"
    body_b = "乙来源正文包含被引用的稳定结论内容片段其二。"
    groups = _indep_pair(
        dict(publisher="ACME", source_kind="news"),
        dict(publisher="ACME", source_kind="news"),
        body_a=body_a, body_b=body_b,
    )
    assert len(groups) == 2 and len(set(groups.values())) == 1


def test_independence_same_content_hash_merges_even_across_publishers():
    body = "共享正文包含被引用的稳定结论内容片段完全相同。"
    groups = _indep_pair(
        dict(publisher="ACME", source_kind="news"),
        dict(publisher="BETA", source_kind="news"),
        body_a=body, body_b=body,
    )
    assert len(groups) == 2 and len(set(groups.values())) == 1


def test_independence_syndication_and_translation_merge():
    body_a = "原始来源正文包含被引用的稳定结论内容片段甲。"
    body_b = "转载来源正文包含被引用的稳定结论内容片段乙。"
    syndicated = _indep_pair(
        dict(publisher="ACME", source_kind="news"),
        dict(publisher="BETA", source_kind="news",
             syndicated_from="https://a.example.com/x"),
        body_a=body_a, body_b=body_b,
    )
    assert len(set(syndicated.values())) == 1
    translated = _indep_pair(
        dict(publisher="ACME", source_kind="news"),
        dict(publisher="BETA", source_kind="news",
             translation_of="https://a.example.com/x"),
        body_a=body_a, body_b=body_b,
    )
    assert len(set(translated.values())) == 1


def test_independence_distinct_publishers_stay_independent():
    body_a = "甲来源正文包含被引用的稳定结论内容片段其一。"
    body_b = "乙来源正文包含被引用的稳定结论内容片段其二。"
    groups = _indep_pair(
        dict(publisher="ACME", source_kind="news"),
        dict(publisher="BETA", source_kind="news"),
        body_a=body_a, body_b=body_b,
    )
    assert len(set(groups.values())) == 2  # URL count != independent source count


def test_social_only_factual_cannot_grant_support():
    plan = _plan(claims=(_sem_claim("claim-1", claim_class="factual"),))
    body = "社媒帖子正文包含被引用的稳定结论内容片段。"
    cand = _sem_candidate(
        "s-social", "https://social.example.com/p", body,
        [_sem_quote("被引用的稳定结论内容片段", body)],
        source_kind="social_post", authority_relation="unknown",
        quality="medium", access="public", publisher="SomeUser",
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    a = _for_claim(bundle, "claim-1")[0]
    assert a["role"] in {"social", "contextual"}
    assert a["role"] != "support"
    assert a["validated_relation"] == "contextual"
    # a purely social assessment never yields factual support
    assert all(x["validated_relation"] != "supports" for x in _for_claim(bundle, "claim-1"))


def test_social_opinion_claim_is_acceptable_as_contextual():
    plan = _plan(claims=(_sem_claim("claim-1", claim_class="opinion"),))
    body = "评论来源正文包含被引用的稳定观点内容片段。"
    cand = _sem_candidate(
        "s-op", "https://forum.example.com/t", body,
        [_sem_quote("被引用的稳定观点内容片段", body)],
        source_kind="forum", authority_relation="independent",
        quality="medium", access="public", publisher="ForumUser",
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    a = _for_claim(bundle, "claim-1")[0]
    assert a["role"] == "contextual"
    assert a["validated_relation"] == "contextual"


def test_assessments_are_input_order_stable():
    plan = _plan(claims=(_sem_claim("claim-1"),))
    body_a = "甲来源正文包含被引用的稳定结论内容片段其一。"
    body_b = "乙来源正文包含被引用的稳定结论内容片段其二。"
    ca = _sem_candidate(
        "s-a", "https://a.example.com/x", body_a,
        [_sem_quote("被引用的稳定结论内容片段", body_a)],
        publisher="ACME", source_kind="news",
    )
    cb = _sem_candidate(
        "s-b", "https://b.example.com/y", body_b,
        [_sem_quote("被引用的稳定结论内容片段", body_b)],
        publisher="ACME", source_kind="news",
    )
    forward = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [ca, cb], source_count=2))
    reverse = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cb, ca], source_count=2))
    assert forward.validated_semantic_hash == reverse.validated_semantic_hash
    assert forward.audit_artifact_hash == reverse.audit_artifact_hash
    fwd = {a["assessment_uid"]: a["independence_group"] for a in _assessments(forward)}
    rev = {a["assessment_uid"]: a["independence_group"] for a in _assessments(reverse)}
    assert fwd == rev


def test_semantic_rule_versions_are_pinned_and_immutable():
    plan = _plan(claims=(_sem_claim("claim-1"),))
    body = "官方来源正文包含被引用的稳定结论内容片段。"
    cand = _sem_candidate(
        "s1", "https://example.com/doc", body,
        [_sem_quote("被引用的稳定结论内容片段", body)], **_STRONG_META,
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    assert bundle.rule_versions["freshness"] == rc.RESEARCH_FRESHNESS_RULE_VERSION
    assert bundle.rule_versions["suitability"] == rc.RESEARCH_SUITABILITY_RULE_VERSION
    assert bundle.rule_versions["independence"] == rc.RESEARCH_INDEPENDENCE_RULE_VERSION
    with pytest.raises(TypeError):
        bundle.validated_research["claim_source_assessments"] = "forbidden"


# ---------------------------------------------------------------------------
# S5A-2b: deterministic five-state claim adjudication + publication action.
# Consumes A2a quote-backed assessments (suitability in {strong,acceptable},
# validated_relation in {supports,contradicts,contextual}), counts by
# independence_group (never URL), and emits keep/qualify/drop/block actions
# plus a split verification/expansion coverage ledger.
# ---------------------------------------------------------------------------


def _adj_claim(
    claim_uid,
    *,
    risk="P2",
    temporal_class="stable",
    window_days=None,
    claim_class="factual",
    required=False,
    min_publishers=None,
):
    claim = _sem_claim(
        claim_uid, temporal_class=temporal_class, window_days=window_days,
        claim_class=claim_class, risk=risk,
    )
    if required:
        claim["required_for_publication"] = True
    if min_publishers is not None:
        claim["min_independent_publishers"] = min_publishers
    return claim


def _adj_body(quote, tag=""):
    return f"{tag}权威来源正文完整表述了{quote}这一结论内容片段。"


def _support(
    candidate_uid,
    url,
    quote_text,
    *,
    claim_uid="claim-1",
    tag="",
    stance="supports",
    published_at="",
    publisher="Pub",
    source_kind="official_doc",
    authority_relation="primary",
    quality="high",
    access="public",
    **extra,
):
    body = _adj_body(quote_text, tag or candidate_uid)
    meta = dict(
        source_kind=source_kind, authority_relation=authority_relation,
        quality=quality, access=access, publisher=publisher, stance=stance,
        published_at=published_at,
    )
    meta.update(extra)
    return _sem_candidate(
        candidate_uid, url, body,
        [_sem_quote(quote_text, body, claim_uid=claim_uid)], **meta,
    )


def _result(bundle, claim_uid):
    for record in bundle.validated_research["claim_results"]:
        if record["claim_uid"] == claim_uid:
            return record
    return None


def test_adj_supported_single_p2_keeps_and_bundle_passes():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2"),))
    cand = _support("s1", "https://a.example.com/x", "结论稳定成立")
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [cand], source_count=1))
    r = _result(bundle, "claim-1")
    assert r["verdict"] == "supported"
    assert r["publication_action"] == "keep"
    assert r["qualifier"] == ""
    assert r["independent_publisher_count"] == 1
    assert r["required_publisher_count"] == 1
    assert r["freshness_satisfied"] is True
    assert 0.0 <= r["confidence"] <= 1.0
    assert r["supporting_quote_uids"] and all(
        q.startswith("quote_") for q in r["supporting_quote_uids"]
    )
    assert r["checked_at"] == "2026-07-13T00:00:05Z"  # run.execution.completed_at only
    assert r["adjudication"]["rule_version"] == rc.RESEARCH_ADJUDICATOR_RULE_VERSION
    assert r["adjudication"]["coverage_passed"] is True
    assert bundle.publication_disposition == "pass"
    assert bundle.rule_versions["adjudicator"] == rc.RESEARCH_ADJUDICATOR_RULE_VERSION


def test_adj_p1_requires_two_independent_publishers():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P1"),))
    one = _support("s1", "https://a.example.com/x", "结论稳定成立", publisher="ACME")
    b1 = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [one], source_count=1))
    r1 = _result(b1, "claim-1")
    assert r1["verdict"] == "unresolved"
    assert r1["required_publisher_count"] == 2
    assert r1["independent_publisher_count"] == 1
    assert r1["publication_action"] == "drop"
    assert b1.publication_disposition == "degraded"

    two_a = _support("s1", "https://a.example.com/x", "结论稳定成立", publisher="ACME")
    two_b = _support("s2", "https://b.example.com/y", "结论稳定成立", publisher="BETA")
    b2 = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [two_a, two_b], source_count=2))
    r2 = _result(b2, "claim-1")
    assert r2["verdict"] == "supported"
    assert r2["independent_publisher_count"] == 2
    assert r2["publication_action"] == "keep"
    assert b2.publication_disposition == "pass"


def test_adj_same_publisher_multi_url_does_not_add_independence():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P1"),))
    a = _support("s1", "https://a.example.com/x", "结论稳定成立", publisher="ACME")
    b = _support("s2", "https://a.example.com/y", "结论稳定成立", publisher="ACME")
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [a, b], source_count=2))
    r = _result(bundle, "claim-1")
    # two URLs, one publisher -> one independent group -> below the 2-publisher gate
    assert r["independent_publisher_count"] == 1
    assert r["verdict"] == "unresolved"


def test_adj_contradicted_drops_and_required_escalates_to_block():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2", required=True),))
    c = _support("s1", "https://a.example.com/x", "结论并不成立", stance="contradicts")
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [c], source_count=1))
    r = _result(bundle, "claim-1")
    assert r["verdict"] == "contradicted"
    assert r["contradicting_quote_uids"] and not r["supporting_quote_uids"]
    assert r["publication_action"] == "block"  # required_for_publication + not supported
    assert r["qualifier"].startswith("required_claim_")
    assert bundle.publication_disposition == "block"


def test_adj_mixed_qualifies_and_does_not_swallow_conflict():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2"),))
    s1 = _support("s1", "https://a.example.com/x", "结论成立", publisher="ACME")
    s2 = _support("s2", "https://b.example.com/y", "结论成立", publisher="BETA")
    c1 = _support("s3", "https://c.example.com/z", "结论成立", publisher="GAMMA", stance="contradicts")
    bundle = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [s1, s2, c1], source_count=3)
    )
    r = _result(bundle, "claim-1")
    # majority (2 supports vs 1 contradict) must NOT swallow the conflict
    assert r["verdict"] == "mixed"
    assert r["publication_action"] == "qualify"
    assert r["adjudication"]["conflict_present"] is True
    assert r["supporting_quote_uids"] and r["contradicting_quote_uids"]
    assert bundle.publication_disposition == "degraded"
    # conflict recorded once with closed assessment references
    conflict = next(cf for cf in bundle.conflicts if cf["subject_uid"] == "claim-1")
    all_assess = {a["assessment_uid"] for a in bundle.validated_research["claim_source_assessments"]}
    assert set(conflict["assessment_uids"]) <= all_assess
    assert list(conflict["assessment_uids"]) == sorted(conflict["assessment_uids"])


def test_adj_stale_when_all_support_is_stale():
    plan = _plan(claims=(
        _adj_claim("claim-1", risk="P2", temporal_class="current", window_days=30),
    ))
    c = _support(
        "s1", "https://a.example.com/x", "结论成立",
        published_at="2026-05-01T00:00:00Z",  # >30d before completed_at -> stale
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [c], source_count=1))
    r = _result(bundle, "claim-1")
    assert r["verdict"] == "stale"
    assert r["freshness_satisfied"] is False
    assert r["publication_action"] == "drop"
    assert bundle.publication_disposition == "degraded"


def test_adj_weak_and_social_evidence_never_grant_support():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2"),))
    weak = _support(
        "s1", "https://blog.example.com/x", "结论成立",
        source_kind="blog", authority_relation="self", quality="low", publisher="Blog",
    )
    bw = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [weak], source_count=1))
    rw = _result(bw, "claim-1")
    assert rw["verdict"] == "unresolved"
    assert not rw["supporting_quote_uids"]
    # weak-suitability assessment is excluded from adjudication (rejected, not consumed)
    assert rw["adjudication"]["rejected_assessment_uids"]
    assert not rw["adjudication"]["accepted_assessment_uids"]

    plan2 = _plan(claims=(_adj_claim("claim-1", risk="P2", claim_class="factual"),))
    soc = _support(
        "s1", "https://social.example.com/x", "结论成立",
        source_kind="social_post", authority_relation="unknown", quality="medium",
        publisher="SomeUser",
    )
    bs = rc.validate_and_adjudicate_research(plan2, _sem_run(plan2, [soc], source_count=1))
    rs = _result(bs, "claim-1")
    assert rs["verdict"] == "unresolved"
    assert not rs["supporting_quote_uids"]


def test_adj_quote_uid_classification_is_closed_across_relations():
    plan = _plan(claims=(
        _adj_claim("claim-1", risk="P2"),
        _adj_claim("claim-2", risk="P2", claim_class="opinion"),
    ))
    sup = _support("s1", "https://a.example.com/x", "甲结论成立", claim_uid="claim-1")
    ctx = _support(
        "s2", "https://news.example.com/y", "乙观点成立", claim_uid="claim-2",
        source_kind="news", authority_relation="secondary", quality="medium", publisher="News",
    )
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [sup, ctx], source_count=2))
    quote_uids = {q["quote_uid"] for q in bundle.validated_research["quotes"]}
    for r in bundle.validated_research["claim_results"]:
        for key in ("supporting_quote_uids", "contradicting_quote_uids", "contextual_quote_uids"):
            for uid in r[key]:
                assert uid in quote_uids  # every classified quote resolves in the bundle
    r1 = _result(bundle, "claim-1")
    assert r1["verdict"] == "supported" and r1["supporting_quote_uids"]
    r2 = _result(bundle, "claim-2")
    # an acceptable-suitability contextual source informs but never supports the claim
    assert r2["verdict"] == "unresolved"
    assert r2["contextual_quote_uids"] and not r2["supporting_quote_uids"]


def test_adj_is_input_order_stable_and_checked_at_is_pure():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P1"),))
    a = _support("s1", "https://a.example.com/x", "结论成立", publisher="ACME")
    b = _support("s2", "https://b.example.com/y", "结论成立", publisher="BETA")
    fwd = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [a, b], source_count=2))
    rev = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [b, a], source_count=2))
    assert fwd.validated_semantic_hash == rev.validated_semantic_hash
    assert fwd.audit_artifact_hash == rev.audit_artifact_hash
    assert _result(fwd, "claim-1")["checked_at"] == "2026-07-13T00:00:05Z"
    assert _result(fwd, "claim-1") == _result(rev, "claim-1")


def test_adj_coverage_splits_verification_and_expansion_without_merging():
    plan = _plan(claims=(
        _adj_claim("c0", risk="P0"),
        _adj_claim("c1", risk="P1"),
        _adj_claim("c2", risk="P2"),
    ))
    cands = [
        _support("c0a", "https://a0.example.com/x", "零结论成立", claim_uid="c0", publisher="A0"),
        _support("c0b", "https://b0.example.com/x", "零结论成立", claim_uid="c0", publisher="B0"),
        _support("c1a", "https://a1.example.com/x", "一结论成立", claim_uid="c1", publisher="A1"),
        _support("c1b", "https://b1.example.com/x", "一结论成立", claim_uid="c1", publisher="B1"),
        _support("c2a", "https://a2.example.com/x", "二结论成立", claim_uid="c2", publisher="A2"),
    ]
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, cands, source_count=5))
    cov = bundle.coverage
    assert "verification" in cov and "expansion" in cov
    ver = cov["verification"]
    assert set(ver) >= {
        "p0_total", "p0_resolved", "adopted_p1_total", "adopted_p1_resolved",
        "p2_total", "p2_resolved", "p2_ratio", "gate_passed",
    }
    assert (ver["p0_total"], ver["p0_resolved"]) == (1, 1)
    assert (ver["adopted_p1_total"], ver["adopted_p1_resolved"]) == (1, 1)
    assert (ver["p2_total"], ver["p2_resolved"]) == (1, 1)
    assert ver["p2_ratio"] == 1.0
    assert ver["gate_passed"] is True
    # coverage is never collapsed into a single scalar score
    assert not isinstance(cov, (int, float))
    assert bundle.publication_disposition == "pass"


def test_adj_no_claim_results_blocks_the_bundle():
    plan = _plan(claims=())
    bundle = rc.validate_and_adjudicate_research(plan, _sem_run(plan, [], source_count=0))
    assert bundle.validated_research["claim_results"] in ((), [])
    assert bundle.publication_disposition == "block"


def test_adj_confidence_is_bounded_and_orders_supported_above_unresolved():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2"),))
    supported = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [_support("s1", "https://a.example.com/x", "结论成立")], source_count=1)
    )
    unresolved = rc.validate_and_adjudicate_research(
        plan,
        _sem_run(plan, [_support(
            "s1", "https://blog.example.com/x", "结论成立",
            source_kind="blog", authority_relation="self", quality="low",
        )], source_count=1),
    )
    cs = _result(supported, "claim-1")["confidence"]
    cu = _result(unresolved, "claim-1")["confidence"]
    assert 0.0 <= cu <= cs <= 1.0
    assert cs > cu


def test_adjudication_ignores_external_completed_at_override():
    plan = _plan(claims=(
        _adj_claim("claim-1", risk="P2", temporal_class="current", window_days=30),
    ))
    candidate = _support(
        "s1", "https://a.example.com/x", "结论成立",
        published_at="2026-07-01T00:00:00Z",
    )
    run = _sem_run(plan, [candidate], source_count=1)
    bundle = rc.validate_and_adjudicate_research(
        plan, run, completed_at="2030-01-01T00:00:00Z"
    )
    result = _result(bundle, "claim-1")
    assert result is not None
    assert result["verdict"] == "supported"
    assert result["checked_at"] == run.execution["completed_at"]


def test_same_quote_hash_can_support_multiple_claims_without_overwrite():
    plan = _plan(claims=(
        _adj_claim("claim-1", risk="P2"),
        _adj_claim("claim-2", risk="P2"),
    ))
    body = _adj_body("共享结论成立", "shared")
    quotes = [
        _sem_quote("共享结论成立", body, claim_uid="claim-1"),
        _sem_quote("共享结论成立", body, claim_uid="claim-2"),
    ]
    candidate = _sem_candidate(
        "s1", "https://a.example.com/x", body, quotes, **_STRONG_META
    )
    forward = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [candidate], source_count=1)
    )
    candidate_reversed = _sem_candidate(
        "s1", "https://a.example.com/x", body, list(reversed(quotes)), **_STRONG_META
    )
    reverse = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [candidate_reversed], source_count=1)
    )
    first = _result(forward, "claim-1")
    second = _result(forward, "claim-2")
    assert first is not None and second is not None
    assert first["verdict"] == "supported"
    assert second["verdict"] == "supported"
    assert forward.validated_semantic_hash == reverse.validated_semantic_hash
    assert len(forward.validated_research["quotes"]) == 2


def test_semantically_empty_content_hash_is_rejected():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2"),))
    body = _adj_body("结论成立", "empty-hash")
    candidate = _sem_candidate(
        "s1", "https://a.example.com/x", body,
        [_sem_quote("结论成立", body)],
        content_hash="sha256:", **_STRONG_META,
    )
    bundle = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [candidate], source_count=0)
    )
    reasons = {r["reason"] for r in bundle.raw_research["validation_audit"]["rejections"]}
    assert "missing_content_hash" in reasons
    assert bundle.validated_research["sources"] in ((), [])


def test_unknown_claim_quote_is_audit_only_not_validated():
    plan = _plan(claims=(_adj_claim("claim-1", risk="P2"),))
    body = _adj_body("未知声明文本", "unknown")
    candidate = _sem_candidate(
        "s1", "https://a.example.com/x", body,
        [_sem_quote("未知声明文本", body, claim_uid="claim-missing")],
        **_STRONG_META,
    )
    bundle = rc.validate_and_adjudicate_research(
        plan, _sem_run(plan, [candidate], source_count=1)
    )
    assert bundle.validated_research["quotes"] in ((), [])
    rejected = bundle.raw_research["validation_audit"]["assessment_rejections"]
    assert any(r["claim_uid"] == "claim-missing" for r in rejected)
