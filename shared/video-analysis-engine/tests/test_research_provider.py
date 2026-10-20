#!/usr/bin/env python3
"""S3 planner/provider seam contracts."""
from dataclasses import replace

import pytest

import research_contract as rc
import research_pipeline as rp


def _claims(risk="P2", text="稳定机制"):
    return {
        "schema_version": "claim-bundle/1.0",
        "claim_bundle_semantic_hash": "sha256:claims",
        "claims": [{"claim_uid": "claim-1", "risk": risk, "text": text,
                    "evidence_locations": ["3:E1"], "support_scope": "video_evidence"}],
        "insights": [], "audit_log": [],
    }


def _plan(policy="auto", mode="sparse", claims=None):
    return rp.build_research_plan(
        evidence_bundle_hash="sha256:evidence", claim_bundle=claims or _claims(),
        canonical_id="BV1", platform="bilibili", report_mode=mode,
        research_policy=policy,
        capability_snapshot={"available": True, "route": "hermes_wrr", "checked_at": "now"},
        created_at="2026-07-14T00:00:00Z", plan_id="rp-fixed",
        topic_hints=("检索增强生成",),
    )


def test_planner_is_deterministic_and_auto_has_lightweight_grounding():
    first, second = _plan(), _plan()
    assert first == second
    assert first.plan_semantic_hash == second.plan_semantic_hash
    assert first.queries
    assert first.queries[0]["mode"] == "grounding"
    assert first.verification_enabled and first.knowledge_expansion_enabled


def test_risky_claim_adds_deterministic_verification_query_without_copying_prose():
    plan = _plan(claims=_claims("P1", "2026年当前排名第一"))
    requests = [item for item in plan.claims if item["claim_uid"] == "claim-1"]
    assert requests and "text" not in requests[0]
    assert any(q["lane"] == "verification" and q["claim_uids"] == ("claim-1",) for q in plan.queries)
    assert all(q["mode"] in {"grounding", "research", "discovery"} for q in plan.queries)


def test_claim_requests_are_order_normalized_and_duplicate_uids_fail_closed():
    first_claim = _claims("P1", "2026年当前排名第一")["claims"][0]
    second_claim = {**first_claim, "claim_uid": "claim-2", "risk": "P2", "text": "稳定背景"}
    left = _claims()
    left["claims"] = [first_claim, second_claim]
    right = _claims()
    right["claims"] = [second_claim, first_claim]
    assert _plan(claims=left) == _plan(claims=right)

    duplicate = _claims()
    duplicate["claims"] = [first_claim, dict(first_claim)]
    with pytest.raises(rc.ResearchContractViolation, match="duplicate claim_uid"):
        _plan(claims=duplicate)


@pytest.mark.parametrize("mode,queries,fetches,sources,seconds", [
    ("sparse", 4, 6, 6, 60), ("condensed", 8, 12, 10, 120), ("full", 16, 24, 20, 240),
])
def test_mode_budgets_match_spec(mode, queries, fetches, sources, seconds):
    budget = _plan(mode=mode).budget
    assert (budget.max_queries, budget.max_fetches, budget.max_sources, budget.max_elapsed_seconds) == (queries, fetches, sources, seconds)


def test_planner_preserves_temporal_class_and_freshness_window():
    claim_bundle = _claims("P0", "当前版本行为")
    claim_bundle["claims"][0].update({
        "claim_uid": "claim-current", "temporal_class": "current",
        "freshness_window_days": 14,
    })
    plan = _plan(claims=claim_bundle)
    claim = next(item for item in plan.claims if item["claim_uid"] == "claim-current")
    query = next(item for item in plan.queries if "claim-current" in item["claim_uids"])
    assert claim["temporal_class"] == "current" and claim["freshness_window_days"] == 14
    assert query["temporal_class"] == "current" and query["freshness_window_days"] == 14


def test_off_force_and_deep_semantics():
    off = _plan(policy="off")
    assert off.queries == () and not off.verification_enabled and not off.knowledge_expansion_enabled
    assert off.stop_conditions["research_disabled"] is True
    force = _plan(policy="force")
    assert force.stop_conditions["fail_on_coverage_miss"] is True
    deep = _plan(policy="deep")
    assert deep.budget.max_fetches == 36 and deep.budget.max_sources == 30
    assert deep.budget.max_elapsed_seconds == 360


def test_execute_calls_provider_exactly_once_and_never_retries():
    class Provider:
        def __init__(self): self.calls = 0
        def execute(self, plan):
            self.calls += 1
            raise RuntimeError("provider failed")
    provider = Provider()
    with pytest.raises(RuntimeError, match="provider failed"):
        rp.execute_research_once(_plan(), provider)
    assert provider.calls == 1


def test_fixture_and_archive_are_plan_bound_defensive_and_immutable():
    plan = _plan()
    fixture = {"candidates": [{"candidate_uid": "c1", "url": "https://example.com"}]}
    provider = rp.FixtureResearchProvider(fixture, plan_semantic_hash=plan.plan_semantic_hash)
    fixture["candidates"][0]["url"] = "https://mutated-before-execute.invalid"
    raw = rp.execute_research_once(plan, provider)
    fixture["candidates"][0]["url"] = "https://mutated.invalid"
    assert raw.raw_research["candidates"][0]["url"] == "https://example.com"
    with pytest.raises(TypeError): raw.raw_research["x"] = 1
    replay = rp.ArchivedResearchProvider(raw).execute(plan)
    assert replay == raw
    wrong_plan_run = rc.finalize_raw_research_run(
        replace(raw, plan_semantic_hash="sha256:wrong", raw_hash="")
    )
    with pytest.raises(rc.ResearchContractViolation, match="plan_semantic_hash"):
        rp.ArchivedResearchProvider(wrong_plan_run).execute(plan)

    other_plan = replace(plan, plan_semantic_hash="sha256:other")
    with pytest.raises(rc.ResearchContractViolation, match="plan_semantic_hash"):
        provider.execute(other_plan)


def test_no_provider_is_explicitly_unavailable_without_execution():
    raw = rp.execute_research_once(_plan(), None)
    assert raw.status == "unavailable"
    assert not raw.attempted and not raw.executed
    assert raw.capability_available is False and raw.validated_evidence_count == 0


def test_raw_run_rejects_secrets():
    plan = _plan()
    with pytest.raises(rc.ResearchContractViolation, match="敏感"):
        rp.FixtureResearchProvider(
            {"headers": {"Authorization": "secret"}},
            plan_semantic_hash=plan.plan_semantic_hash,
        )
