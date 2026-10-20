# -*- coding: utf-8 -*-
"""S8-A public boundary: offline research fixture quality lane."""
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import run_quality_gate
from research_pipeline import build_research_plan
from research_contract import finalize_research_plan, validate_and_adjudicate_research


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "tests/fixtures/p2e_fetch_all.json"
FIXTURE = ROOT / "tests/fixtures/research/release_fixture.json"


def _context(path: Path) -> Path:
    path.write_text(json.dumps({
        "canonical_id": "fixture-release", "platform": "bilibili",
        "evidence_bundle_hash": "sha256:fixture", "created_at": "2026-07-15T00:00:00Z",
        "plan_id": "fixture-release-plan",
    }), encoding="utf-8")
    return path


def test_research_is_off_by_default_and_preserves_existing_quality_gate(tmp_path):
    passed, summary = run_quality_gate.run_quality_gate(
        str(INPUT), str(tmp_path / "report.md"), writer_provider="fixture", mode="full",
    )
    assert passed is True
    assert summary["research"]["executed"] is False
    assert summary["research"]["status"] == "unavailable"


@pytest.mark.parametrize("missing", ("context", "fixture", "archive"))
def test_fixture_research_requires_all_private_inputs(tmp_path, missing):
    kwargs = {
        "research_provider": "fixture",
        "research_context": str(_context(tmp_path / "context.json")),
        "research_fixture": str(FIXTURE),
        "research_archive_dir": str(tmp_path / "private-archive"),
    }
    kwargs[f"research_{missing}" if missing != "archive" else "research_archive_dir"] = None
    with pytest.raises(ValueError):
        run_quality_gate.run_quality_gate(
            str(INPUT), str(tmp_path / "report.md"), writer_provider="fixture", mode="full", **kwargs,
        )


def test_real_research_requires_explicit_network_opt_in(tmp_path):
    with pytest.raises(ValueError, match="allow-network"):
        run_quality_gate.run_quality_gate(
            str(INPUT), str(tmp_path / "report.md"), writer_provider="fixture", mode="full",
            research_provider="real", research_context=str(_context(tmp_path / "context.json")),
            research_archive_dir=str(tmp_path / "private-archive"),
        )


def test_release_research_fixture_is_sanitized():
    text = FIXTURE.read_text(encoding="utf-8")
    assert "/Users/" not in text
    lowered = text.lower()
    assert not any(token in lowered for token in ("authorization", "api_key", "private_key", "token"))


def _fixture_kwargs(tmp_path):
    return {
        "research_provider": "fixture",
        "research_context": str(_context(tmp_path / "context.json")),
        "research_fixture": str(FIXTURE),
        "research_archive_dir": str(tmp_path / "private-archive"),
    }


def test_fixture_research_is_archived_projected_and_passes_all_public_p0_gates(tmp_path):
    output = tmp_path / "fixture-report.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(INPUT), str(output), writer_provider="fixture", mode="full", **_fixture_kwargs(tmp_path),
    )

    assert passed is True
    assert summary["research"]["executed"] is True
    assert summary["research"]["validated_evidence_count"] >= 1
    assert summary["research_artifact_hashes"]["archive_bundle_hash"].startswith("sha256:")
    assert summary["research_artifact_hashes"]["archive_source_hashes"]
    assert summary["research_gate_passed"] is True
    assert all(gate["pass"] for gate in summary["research_gates"].values())

    archive = Path(_fixture_kwargs(tmp_path)["research_archive_dir"])
    assert (archive / "bundles").is_dir()
    assert (archive / "sources").is_dir()
    public = output.read_text(encoding="utf-8") + json.dumps(summary, ensure_ascii=False)
    assert "PRIVATE-RAW-FIXTURE-MARKER" not in public
    assert str(tmp_path) not in public
    assert "api_key=" not in public.lower()


def _budget_pressure_plan():
    """A plan where P2 grounding alone would exhaust ``max_sources`` (=20).

    12 contextual P2 claims feed the single grounding query; capped at 10 they
    still emit 10*2 = 20 candidates, exactly the full-mode source budget. Without
    global P0/P1 scheduling the lone P1 verify query is starved to zero sources.
    """
    claims = [{"claim_uid": "claim_p1_budget", "risk": "P1", "text": "P1 claim under budget pressure"}]
    claims += [{"claim_uid": f"claim_p2_{i:02d}", "risk": "P2", "text": f"context claim {i}"} for i in range(12)]
    return build_research_plan(
        evidence_bundle_hash="sha256:evidence",
        claim_bundle={"claim_bundle_semantic_hash": "sha256:" + "0" * 64, "claims": claims},
        canonical_id="fixture-release", platform="bilibili", report_mode="full",
        research_policy="auto", capability_snapshot={"available": True},
        created_at="2026-07-15T00:00:00Z", plan_id="fixture-budget-plan",
    )


def test_p1_bundle_wins_shared_source_budget_under_pressure():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    provider = run_quality_gate._PlanBoundFixtureResearchProvider(fixture)
    plan = _budget_pressure_plan()

    run = provider.execute(plan)
    candidates = list(run.raw_research["candidates"])

    # Shared source budget is still respected globally.
    assert plan.budget.max_sources == 20
    assert len(candidates) <= plan.budget.max_sources

    def _p1(relation):
        return [
            c for c in candidates
            if str(c.get("authority_relation")) == relation
            and "claim_p1_budget" in str(c.get("canonical_url") or c.get("url") or "")
        ]

    # The P1 bundle keeps BOTH its primary and its independent source despite the
    # P2 grounding query competing for the same 20-slot budget.
    assert _p1("primary"), "P1 primary source was starved out of the budget"
    assert _p1("independent"), "P1 independent source was starved out of the budget"


def test_two_round_scheduler_never_starves_tail_p2_claims_and_holds_coverage():
    """RED: the shared source cap must ground every claim before doubling up.

    One grounding query fans out 12 P2 claims and a lone P1 verify query needs
    two publishers. Binding primary+independent per claim fills the 20-slot
    budget after 10 claims, leaving the last two P2 claims with *no* source, so
    ``P0_RESEARCH_COVERAGE`` only survives because the loose 0.5 P2 ratio masks
    the starvation. The two-round scheduler must first emit one primary per claim
    (P0-P3), then spend the remainder on P0/P1 independents: every P2 keeps a
    primary, the P1 keeps both publishers, and the coverage gate closes cleanly.
    """
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    provider = run_quality_gate._PlanBoundFixtureResearchProvider(fixture)
    plan = _budget_pressure_plan()

    run = provider.execute(plan)
    candidates = list(run.raw_research["candidates"])

    # The shared source budget is still respected globally.
    assert plan.budget.max_sources == 20
    assert len(candidates) <= plan.budget.max_sources

    def _has_relation(claim_uid, relation):
        return any(
            str(c.get("authority_relation")) == relation
            and claim_uid in str(c.get("canonical_url") or c.get("url") or "")
            for c in candidates
        )

    p2_uids = [f"claim_p2_{i:02d}" for i in range(12)]
    starved = [uid for uid in p2_uids if not _has_relation(uid, "primary")]
    assert not starved, f"tail P2 claims starved of a primary source: {starved}"

    # The P1 verify claim keeps BOTH publishers despite the P2 grounding query
    # competing for the same 20-slot budget.
    assert _has_relation("claim_p1_budget", "primary")
    assert _has_relation("claim_p1_budget", "independent")

    bundle = validate_and_adjudicate_research(
        plan, run, bundle_id="fixture-budget-bundle",
        started_at="2026-07-15T00:00:00Z", completed_at="2026-07-15T00:00:00Z",
    )
    verification = dict(bundle.coverage["verification"])
    assert verification["p2_resolved"] == verification["p2_total"] == 12
    assert verification["adopted_p1_resolved"] == verification["adopted_p1_total"] == 1
    # P0_RESEARCH_COVERAGE keys off this gate — no claim is starved, so it holds.
    assert verification["gate_passed"] is True


def _failclosed_budget_plan():
    """A plan whose ``max_sources`` cannot possibly ground the required claims.

    Two high-risk claims (one P0, one P1) each demand a first-party *and* an
    independent publisher to resolve (``min_independent_publishers == 2``), so the
    scheduler needs at least four sources. ``max_sources`` is pinned to 2 — below
    that floor — which forces the fail-closed path no matter how the shared budget
    is sliced. The budget is re-finalised so ``plan_semantic_hash`` stays bound.
    """
    claims = [
        {"claim_uid": "claim_p0_fc", "risk": "P0", "text": "P0 high-risk claim under starved budget"},
        {"claim_uid": "claim_p1_fc", "risk": "P1", "text": "P1 high-risk claim under starved budget"},
    ]
    plan = build_research_plan(
        evidence_bundle_hash="sha256:evidence",
        claim_bundle={"claim_bundle_semantic_hash": "sha256:" + "0" * 64, "claims": claims},
        canonical_id="fixture-release", platform="bilibili", report_mode="full",
        research_policy="auto", capability_snapshot={"available": True},
        created_at="2026-07-15T00:00:00Z", plan_id="fixture-failclosed-plan",
    )
    return finalize_research_plan(replace(plan, budget=replace(plan.budget, max_sources=2)))


def test_failclosed_when_source_budget_cannot_ground_required_claims():
    """Fail-closed: a sub-floor source budget must block, never silently pass.

    Two required claims need primary+independent each (>=4 sources) but the shared
    budget is capped at 2. Whatever two candidates survive the cap, at least one
    required claim is left without its independent publisher, so its P0/P1 coverage
    lane cannot resolve. The verification coverage gate must report False and the
    bundle must refuse publication (``block``) rather than degrade to a pass. The
    assertions read the *set* of emitted relations per claim, never a positional
    slice, so they hold regardless of candidate truncation order.
    """
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    provider = run_quality_gate._PlanBoundFixtureResearchProvider(fixture)
    plan = _failclosed_budget_plan()

    run = provider.execute(plan)
    candidates = list(run.raw_research["candidates"])

    # The shared source budget is genuinely below the resolution floor.
    assert plan.budget.max_sources == 2
    assert len(candidates) <= plan.budget.max_sources

    def _relations(claim_uid):
        return {
            str(c.get("authority_relation"))
            for c in candidates
            if claim_uid in str(c.get("canonical_url") or c.get("url") or "")
        }

    required_uids = ("claim_p0_fc", "claim_p1_fc")
    starved_independent = [uid for uid in required_uids if "independent" not in _relations(uid)]
    # At least one required claim is left with zero independent coverage; the budget
    # cannot fund the second publisher both claims require.
    assert starved_independent, "budget too small yet every claim still got an independent source"

    bundle = validate_and_adjudicate_research(
        plan, run, bundle_id="fixture-failclosed-bundle",
        started_at="2026-07-15T00:00:00Z", completed_at="2026-07-15T00:00:00Z",
    )
    verification = dict(bundle.coverage["verification"])

    # Coverage gate fails closed: the required P0/P1 lanes cannot resolve.
    assert verification["gate_passed"] is False
    assert verification["p0_resolved"] == 0
    assert verification["adopted_p1_resolved"] == 0

    # Overall publication is refused, not silently degraded to a pass.
    assert bundle.publication_disposition in {"block", "blocked"}
    actions = {
        str(r.get("claim_uid")): str(r.get("publication_action"))
        for r in bundle.validated_research["claim_results"]
    }
    assert all(actions[uid] == "block" for uid in required_uids)


def test_cli_accepts_explicit_offline_fixture_research(tmp_path):
    output = tmp_path / "cli-report.md"
    kwargs = _fixture_kwargs(tmp_path)
    completed = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/run_quality_gate.py"),
            "--input", str(INPUT), "--output", str(output), "--writer-provider", "fixture",
            "--research-provider", "fixture", "--research-context", kwargs["research_context"],
            "--research-fixture", kwargs["research_fixture"],
            "--research-archive-dir", kwargs["research_archive_dir"], "--json",
        ],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = completed.stdout.split("RESULT_JSON_START", 1)[1].split("RESULT_JSON_END", 1)[0]
    assert json.loads(payload)["research_gate_passed"] is True
