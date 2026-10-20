# -*- coding: utf-8 -*-
"""S9-0 offline research transport contract.

Pins the *shape* of an injected research query executor without ever opening a
socket: a Protocol the WRR adapter types against, an error that leaks only a
stable ``code``, and deterministic scripted doubles. Nothing here selects an
engine, performs HTTP, or registers a real provider — that is the whole point of
S9-0, and the quality-gate assertions below prove no real transport is wired.
"""
import research_pipeline as rp
from research_transport import (
    ResearchExecutorError,
    ResearchQueryExecutor,
    ScriptedFailure,
    ScriptedResearchExecutor,
    ScriptedSuccess,
)


SECRET = "token=SUPER-SECRET-ac9931/private?key=leakme"


def _one_query_plan():
    """A plan with exactly one (grounding) query: no claims, no topic hints."""
    return rp.build_research_plan(
        evidence_bundle_hash="sha256:evidence",
        claim_bundle={"claim_bundle_semantic_hash": "sha256:" + "0" * 64, "claims": []},
        canonical_id="BV1", platform="bilibili", report_mode="full",
        research_policy="auto", capability_snapshot={"available": True},
        created_at="2026-07-14T00:00:00Z", plan_id="rp-one-query",
    )


# ---------------------------------------------------------------------------
# Executor-level transport contract
# ---------------------------------------------------------------------------
def test_scripted_success_returns_result_and_records_exactly_one_call():
    executor = ScriptedResearchExecutor([
        ScriptedSuccess({"candidates": [{"url": "https://a.example", "content": "甲"}]}),
    ])

    result = executor({"query_uid": "q-1", "mode": "grounding"})

    assert result["candidates"][0]["url"] == "https://a.example"
    assert len(executor.calls) == 1
    assert executor.calls[0]["query_uid"] == "q-1"


def test_scripted_failure_raises_code_only_and_records_exactly_one_call():
    executor = ScriptedResearchExecutor([
        ScriptedFailure(code="query_failed", private_error=SECRET),
    ])

    try:
        executor({"query_uid": "q-1"})
    except ResearchExecutorError as exc:
        raised = exc
    else:  # pragma: no cover - contract requires a raise
        raise AssertionError("ScriptedFailure did not raise ResearchExecutorError")

    # Exactly one call, and the error surfaces only the public code.
    assert len(executor.calls) == 1
    assert raised.code == "query_failed"


def test_executor_never_leaks_private_error_in_str_repr_or_chain():
    failure = ScriptedFailure(code="query_failed", private_error=SECRET)
    # The scripted double itself must not expose the private cause.
    assert SECRET not in repr(failure)
    assert SECRET not in str(failure)

    executor = ScriptedResearchExecutor([failure])
    try:
        executor({"query_uid": "q-1"})
    except ResearchExecutorError as exc:
        raised = exc
    else:  # pragma: no cover
        raise AssertionError("expected ResearchExecutorError")

    assert SECRET not in str(raised)
    assert SECRET not in repr(raised)
    # `raise ... from None` severs the chain so no traceback can leak the cause.
    assert raised.__cause__ is None
    assert raised.__suppress_context__ is True
    assert not hasattr(raised, "private_error")


def test_extra_call_beyond_script_fails_deterministically():
    executor = ScriptedResearchExecutor([
        ScriptedSuccess({"candidates": []}),
    ])
    executor({"query_uid": "q-1"})  # consumes the only scripted step

    first_code = second_code = None
    try:
        executor({"query_uid": "q-2"})
    except ResearchExecutorError as exc:
        first_code = exc.code
    try:
        executor({"query_uid": "q-3"})
    except ResearchExecutorError as exc:
        second_code = exc.code

    # Deterministic: every over-run raises the same stable code, no IndexError,
    # and each attempt is still recorded.
    assert first_code is not None
    assert first_code == second_code
    assert len(executor.calls) == 3


def test_scripted_executor_satisfies_protocol():
    executor = ScriptedResearchExecutor([])
    assert isinstance(executor, ResearchQueryExecutor)


# ---------------------------------------------------------------------------
# Adapter integration: one query -> exactly one executor call, no retry
# ---------------------------------------------------------------------------
def test_adapter_single_query_success_makes_exactly_one_call():
    from research_wrr_adapter import HermesWRRAdapter

    plan = _one_query_plan()
    assert len(plan.queries) == 1  # guard the fixture's one-query invariant

    executor = ScriptedResearchExecutor([
        ScriptedSuccess({"candidates": [
            {"url": "https://primary.example/a", "content": "甲", "authority_relation": "primary"},
        ]}),
    ])

    raw = HermesWRRAdapter(executor).execute(plan)

    assert len(executor.calls) == 1  # one query -> one call, no retry
    assert raw.status == "completed"
    assert raw.execution["successful_query_count"] == 1


def test_adapter_single_query_failure_makes_exactly_one_call_and_hides_secret():
    from research_wrr_adapter import HermesWRRAdapter

    plan = _one_query_plan()
    assert len(plan.queries) == 1

    executor = ScriptedResearchExecutor([
        ScriptedFailure(code="query_failed", private_error=SECRET),
    ])

    raw = HermesWRRAdapter(executor).execute(plan)

    # WRR owns retries; the adapter records the single failure exactly once.
    assert len(executor.calls) == 1
    assert raw.status == "failed"
    assert raw.execution["successful_query_count"] == 0

    # The private cause never reaches the raw run's recorded errors.
    blob = repr(raw.errors) + repr(raw.raw_research)
    assert SECRET not in blob
    assert raw.errors and raw.errors[0]["code"] == "query_failed"
