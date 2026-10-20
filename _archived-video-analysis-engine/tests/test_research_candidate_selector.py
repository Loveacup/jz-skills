"""S9-4 tests for the standalone plan-global research candidate selector.

The selector is a pure function ``select_plan_candidates(input_mapping)``. It must
never touch transport/adapter/WRR/Hermes surfaces; it only reasons over the plan
snapshot it is handed. These tests drive the implementation red -> green and pin
the provenance / feasibility / determinism contract described in the S9-4 task.
"""

import copy
import importlib.util
import pathlib
import sys

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import research_candidate_selector as sel  # noqa: E402


# --------------------------------------------------------------------------- #
# builders
# --------------------------------------------------------------------------- #
def _cand(uid, rank, url, **extra):
    c = {"candidate_uid": uid, "discovery_rank": rank, "url": url}
    c.update(extra)
    return c


def _query(query_uid, priority, plan_index, claim_uids, candidates):
    return {
        "query_uid": query_uid,
        "priority": priority,
        "plan_index": plan_index,
        "claim_uids": list(claim_uids),
        "candidates": list(candidates),
    }


def _plan(queries, max_sources, max_fetches):
    return {
        "queries": list(queries),
        "max_sources": max_sources,
        "max_fetches": max_fetches,
    }


def _urls(result):
    return [u["canonical_url"] for u in result["selected_urls"]]


# --------------------------------------------------------------------------- #
# 1. priority + plan ordering
# --------------------------------------------------------------------------- #
def test_priority_dominates_plan_index_in_selection_order():
    plan = _plan(
        [
            # higher plan_index but P0 -> must come first
            _query("qA", "P0", 5, ["c1"], [_cand("a", 0, "http://a.example/")]),
            # lower plan_index but only P1 -> second
            _query("qB", "P1", 0, ["c2"], [_cand("b", 0, "http://b.example/")]),
        ],
        max_sources=5,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    assert _urls(result) == ["http://a.example/", "http://b.example/"]
    assert result["feasible"] is True
    diag = result["diagnostics"]
    assert diag["required_p01_binding_count"] == 2
    assert diag["covered_p01_binding_count"] == 2
    assert diag["required_p01_unique_url_count"] == 2


def test_first_candidate_per_binding_is_lowest_discovery_rank():
    plan = _plan(
        [
            _query(
                "qA",
                "P0",
                0,
                ["c1"],
                [
                    _cand("late", 9, "http://late.example/"),
                    _cand("early", 1, "http://early.example/"),
                ],
            )
        ],
        max_sources=1,
        max_fetches=1,
    )
    result = sel.select_plan_candidates(plan)
    # only the first (lowest rank) candidate covers the binding
    assert _urls(result) == ["http://early.example/"]
    assert result["feasible"] is True


# --------------------------------------------------------------------------- #
# 2. cross-query / cross-claim dedupe + provenance
# --------------------------------------------------------------------------- #
def test_same_url_across_queries_and_claims_dedupes_but_keeps_provenance():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://shared.example/")]),
            _query("qB", "P1", 1, ["c2"], [_cand("b", 0, "http://shared.example/")]),
        ],
        max_sources=5,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    assert len(result["selected_urls"]) == 1
    url = result["selected_urls"][0]
    assert url["canonical_url"] == "http://shared.example/"
    assert url["representative_candidate_uid"] == "a"
    assert url["contributor_candidate_uids"] == ["a", "b"]
    assert url["binding_ids"] == ["qA:c1", "qB:c2"]
    assert url["query_uids"] == ["qA", "qB"]
    assert url["claim_uids"] == ["c1", "c2"]
    diag = result["diagnostics"]
    assert diag["required_p01_binding_count"] == 2
    assert diag["covered_p01_binding_count"] == 2
    assert diag["required_p01_unique_url_count"] == 1
    # representative appears exactly once in raw candidates
    raw = result["selected_raw_candidates"]
    assert len(raw) == 1
    assert raw[0]["candidate_uid"] == "a"
    assert raw[0]["matched_binding_ids"] == ["qA:c1", "qB:c2"]


def test_query_without_claim_uses_none_binding():
    plan = _plan(
        [_query("qA", "P0", 0, [], [_cand("a", 0, "http://a.example/")])],
        max_sources=2,
        max_fetches=2,
    )
    result = sel.select_plan_candidates(plan)
    assert result["diagnostics"]["required_p01_binding_count"] == 1
    assert result["selected_urls"][0]["binding_ids"] == ["qA:<none>"]
    assert result["selected_urls"][0]["claim_uids"] == []


# --------------------------------------------------------------------------- #
# 3. three infeasibility causes, each isolated
# --------------------------------------------------------------------------- #
def test_missing_required_candidate_is_infeasible():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "")]),  # empty url -> unselectable
            _query("qB", "P1", 1, ["c2"], [_cand("b", 0, "http://b.example/")]),
        ],
        max_sources=5,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    assert result["feasible"] is False
    diag = result["diagnostics"]
    assert "MISSING_REQUIRED_CANDIDATE" in diag["reasons"]
    assert "MAX_SOURCES_INSUFFICIENT" not in diag["reasons"]
    assert "MAX_FETCHES_INSUFFICIENT" not in diag["reasons"]
    assert diag["uncovered_binding_ids"] == ["qA:c1"]
    assert diag["covered_p01_binding_count"] == 1


def test_max_sources_insufficient_is_isolated():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            _query("qB", "P0", 1, ["c2"], [_cand("b", 0, "http://b.example/")]),
        ],
        max_sources=1,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    assert result["feasible"] is False
    diag = result["diagnostics"]
    assert "MAX_SOURCES_INSUFFICIENT" in diag["reasons"]
    assert "MAX_FETCHES_INSUFFICIENT" not in diag["reasons"]
    assert "MISSING_REQUIRED_CANDIDATE" not in diag["reasons"]
    # required P0/P1 URLs are never silently dropped for budget
    assert diag["required_p01_unique_url_count"] == 2
    assert diag["selected_unique_url_count"] == 2
    assert len(result["selected_urls"]) == 2


def test_max_fetches_insufficient_is_isolated():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            _query("qB", "P0", 1, ["c2"], [_cand("b", 0, "http://b.example/")]),
        ],
        max_sources=5,
        max_fetches=1,
    )
    result = sel.select_plan_candidates(plan)
    assert result["feasible"] is False
    diag = result["diagnostics"]
    assert "MAX_FETCHES_INSUFFICIENT" in diag["reasons"]
    assert "MAX_SOURCES_INSUFFICIENT" not in diag["reasons"]
    assert "MISSING_REQUIRED_CANDIDATE" not in diag["reasons"]
    assert diag["required_p01_unique_url_count"] == 2
    assert diag["selected_unique_url_count"] == 2  # no silent drop


# --------------------------------------------------------------------------- #
# 4. budget exactly equal -> feasible
# --------------------------------------------------------------------------- #
def test_budget_exactly_equal_is_feasible():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            _query("qB", "P1", 1, ["c2"], [_cand("b", 0, "http://b.example/")]),
        ],
        max_sources=2,
        max_fetches=2,
    )
    result = sel.select_plan_candidates(plan)
    assert result["feasible"] is True
    assert result["diagnostics"]["reasons"] == []
    assert result["diagnostics"]["selected_unique_url_count"] == 2


# --------------------------------------------------------------------------- #
# 5. second-pass fill: stable order, no duplication
# --------------------------------------------------------------------------- #
def test_second_pass_fills_stably_without_duplicates():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            # non-required P2 pool provides optional fill URLs, one duplicated
            _query(
                "qP2",
                "P2",
                1,
                [],
                [
                    _cand("b", 0, "http://b.example/"),
                    _cand("c", 1, "http://c.example/"),
                    _cand("bdup", 2, "http://b.example/"),  # dup of b -> single slot
                ],
            ),
        ],
        max_sources=3,
        max_fetches=3,
    )
    result = sel.select_plan_candidates(plan)
    urls = _urls(result)
    # required first, then stable fill b before c; duplicate b collapses
    assert urls == ["http://a.example/", "http://b.example/", "http://c.example/"]
    assert len(urls) == len(set(urls))
    assert result["feasible"] is True
    # fill URLs carry no required binding provenance
    b_slot = next(u for u in result["selected_urls"] if u["canonical_url"] == "http://b.example/")
    assert b_slot["binding_ids"] == []
    assert b_slot["contributor_candidate_uids"] == ["b", "bdup"]


def test_second_pass_respects_source_cap():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            _query(
                "qP2",
                "P2",
                1,
                [],
                [_cand("b", 0, "http://b.example/"), _cand("c", 1, "http://c.example/")],
            ),
        ],
        max_sources=2,
        max_fetches=9,
    )
    result = sel.select_plan_candidates(plan)
    # 1 required + fill up to max_sources=2 -> exactly 2 unique urls
    assert _urls(result) == ["http://a.example/", "http://b.example/"]
    assert result["diagnostics"]["selected_unique_url_count"] == 2


# --------------------------------------------------------------------------- #
# 6. representative / contributor stability under canonical collision
# --------------------------------------------------------------------------- #
def test_representative_is_highest_priority_earliest_contributor():
    # same canonical URL discovered by P2 (first in input) and P0 (later in input)
    plan = _plan(
        [
            _query("qP2", "P2", 0, [], [_cand("z", 0, "http://collide.example/")]),
            _query("qP0", "P0", 9, ["c1"], [_cand("y", 0, "http://collide.example/")]),
        ],
        max_sources=5,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    assert len(result["selected_urls"]) == 1
    slot = result["selected_urls"][0]
    # P0 contributor outranks P2 despite later input order
    assert slot["representative_candidate_uid"] == "y"
    assert slot["contributor_candidate_uids"] == ["y", "z"]
    assert slot["binding_ids"] == ["qP0:c1"]


def test_canonicalization_collapses_trailing_and_tracking_noise():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://x.example")]),
            _query(
                "qB",
                "P1",
                1,
                ["c2"],
                [_cand("b", 0, "http://x.example/?utm_source=news")],
            ),
        ],
        max_sources=5,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    # trailing slash + utm stripping collapse both to one canonical URL
    assert len(result["selected_urls"]) == 1
    assert result["selected_urls"][0]["contributor_candidate_uids"] == ["a", "b"]


def test_canonical_url_field_preferred_over_url():
    plan = _plan(
        [
            _query(
                "qA",
                "P0",
                0,
                ["c1"],
                [_cand("a", 0, "http://redirect.example/", canonical_url="http://real.example/")],
            )
        ],
        max_sources=2,
        max_fetches=2,
    )
    result = sel.select_plan_candidates(plan)
    assert _urls(result) == ["http://real.example/"]


# --------------------------------------------------------------------------- #
# 7. determinism + input immutability
# --------------------------------------------------------------------------- #
def test_repeated_calls_are_deep_equal_and_input_unmutated():
    plan = _plan(
        [
            _query("qA", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            _query(
                "qP2",
                "P2",
                1,
                [],
                [_cand("b", 0, "http://b.example/"), _cand("c", 1, "http://c.example/")],
            ),
        ],
        max_sources=3,
        max_fetches=3,
    )
    snapshot = copy.deepcopy(plan)
    first = sel.select_plan_candidates(plan)
    second = sel.select_plan_candidates(plan)
    assert first == second
    # input never mutated
    assert plan == snapshot
    # raw candidate copies must not carry back into the input
    assert "matched_binding_ids" not in plan["queries"][0]["candidates"][0]


# --------------------------------------------------------------------------- #
# 8. P2 alone does not create required coverage
# --------------------------------------------------------------------------- #
def test_p2_only_plan_has_no_required_bindings():
    plan = _plan(
        [_query("qP2", "P2", 0, ["c1"], [_cand("a", 0, "http://a.example/")])],
        max_sources=2,
        max_fetches=2,
    )
    result = sel.select_plan_candidates(plan)
    diag = result["diagnostics"]
    assert diag["required_p01_binding_count"] == 0
    assert diag["covered_p01_binding_count"] == 0
    assert diag["uncovered_binding_ids"] == []
    assert result["feasible"] is True
    # P2 url is still eligible for optional fill
    assert _urls(result) == ["http://a.example/"]
    assert result["selected_urls"][0]["binding_ids"] == []


def test_p2_missing_candidate_never_makes_plan_infeasible():
    plan = _plan(
        [
            _query("qP0", "P0", 0, ["c1"], [_cand("a", 0, "http://a.example/")]),
            _query("qP2", "P2", 1, ["c9"], [_cand("z", 0, "")]),  # unselectable P2
        ],
        max_sources=5,
        max_fetches=5,
    )
    result = sel.select_plan_candidates(plan)
    assert result["feasible"] is True
    assert result["diagnostics"]["uncovered_binding_ids"] == []


# --------------------------------------------------------------------------- #
# 9. static guard: no transport / network side-effect imports
# --------------------------------------------------------------------------- #
def test_module_has_no_transport_or_network_imports():
    source = pathlib.Path(sel.__file__).read_text(encoding="utf-8")
    forbidden = (
        "research_transport",
        "research_wrr_adapter",
        "research_wrr_tool_bridge",
        "hermes",
        "requests",
        "httpx",
        "urllib.request",
        "socket",
        "import aiohttp",
    )
    for token in forbidden:
        assert token not in source, f"selector must not reference {token!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
