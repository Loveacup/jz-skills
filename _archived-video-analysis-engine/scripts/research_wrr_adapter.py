#!/usr/bin/env python3
"""Hermes WRR adapter: injected execution only, raw/untrusted output only."""
from __future__ import annotations

import hashlib
import time
from typing import Mapping

from research_transport import ResearchQueryExecutor

from research_contract import (
    RAW_RESEARCH_RUN_SCHEMA_VERSION,
    RawResearchRun,
    ResearchPlan,
    finalize_raw_research_run,
    validate_research_plan,
    _canonical_public_url,
)


class HermesWRRAdapter:
    """Execute plan queries through an injected WRR-owned callable.

    This adapter never selects engines, shells out, retries, validates evidence,
    or promotes snippets. The callable receives one immutable-plan query as a
    plain mapping whose route mode was already selected by ResearchPlanner.
    """

    def __init__(
        self,
        query_executor: ResearchQueryExecutor,
        *,
        max_errors: int = 20,
        max_error_chars: int = 240,
    ) -> None:
        self._execute_query = query_executor
        self._max_errors = max(0, max_errors)
        self._max_error_chars = max(16, max_error_chars)

    @staticmethod
    def _candidate(value: object, query: Mapping[str, object]) -> dict | None:
        if not isinstance(value, Mapping):
            return None
        # Raw discovery metadata only. Validator/Adjudicator owns every
        # evidence/quote/source promotion in S5.
        allowed = {
            "url", "canonical_url", "title", "snippet", "content", "content_hash",
            "published_at", "fetched_at", "source_kind", "authority_relation", "publisher",
            "publisher_group", "quote_candidates", "stance",
            "query_uid", "route", "provider_confidence", "rationale",
        }
        item = {str(key): nested for key, nested in value.items() if str(key) in allowed}
        if not item.get("url") and item.get("canonical_url"):
            item["url"] = item["canonical_url"]
        item["query_uid"] = str(query.get("query_uid") or "")
        item["route_mode"] = str(query.get("mode") or "")
        item["validation_status"] = "untrusted"
        item["snippet_only"] = bool(item.get("snippet") and not item.get("content"))
        content = item.get("content")
        if isinstance(content, str) and content and not item.get("content_hash"):
            item["content_hash"] = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
        raw_quotes = item.get("quote_candidates")
        if isinstance(raw_quotes, (tuple, list)):
            normalized_quotes = []
            for raw_quote in raw_quotes:
                if not isinstance(raw_quote, Mapping):
                    normalized_quotes.append(raw_quote)
                    continue
                quote = dict(raw_quote)
                quote_text = quote.get("quote_text")
                if isinstance(quote_text, str) and quote_text and not quote.get("quote_hash"):
                    quote["quote_hash"] = (
                        "sha256:" + hashlib.sha256(quote_text.encode("utf-8")).hexdigest()
                    )
                normalized_quotes.append(quote)
            item["quote_candidates"] = tuple(normalized_quotes)
            # S5 validator consumes the canonical raw-run field ``quotes``;
            # retain discovery-facing ``quote_candidates`` for provenance while
            # bridging the same untrusted records without promoting evidence.
            item["quotes"] = tuple(normalized_quotes)
        identity = "|".join((
            item["query_uid"],
            str(item.get("canonical_url") or item.get("url") or ""),
            str(item.get("content_hash") or ""),
            str(item.get("snippet") or ""),
        ))
        item["candidate_uid"] = "cand_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        return item

    @staticmethod
    def _execution_ledger(
        plan: ResearchPlan,
        *,
        query_count: int,
        candidate_count: int,
        source_count: int,
        elapsed_seconds: float,
        successes: int,
    ) -> dict:
        return {
            "provider": "hermes_wrr",
            "query_count": query_count,
            "successful_query_count": successes,
            "fetch_count": candidate_count,
            "source_count": source_count,
            "elapsed_seconds": max(0.0, round(elapsed_seconds, 6)),
            "topic_count": 0,
            "knowledge_expansion_count": 0,
            "research_claim_count": 0,
            # Freshness decisions consume this recorded run input only. The
            # planner timestamp is stable and already bound into the plan hash.
            "started_at": plan.created_at,
            "completed_at": plan.created_at,
        }

    def execute(self, plan: ResearchPlan) -> RawResearchRun:
        validate_research_plan(plan)
        if not plan.queries:
            return finalize_raw_research_run(RawResearchRun(
                schema_version=RAW_RESEARCH_RUN_SCHEMA_VERSION,
                run_id="raw_not_requested", plan_semantic_hash=plan.plan_semantic_hash,
                capability_available=bool(plan.capability_snapshot.get("available")),
                attempted=False, executed=False, status="not_requested",
                validated_evidence_count=0,
                execution=self._execution_ledger(
                    plan, query_count=0, candidate_count=0, source_count=0,
                    elapsed_seconds=0.0, successes=0,
                ),
                raw_research={"input_hashes": {
                    "plan_semantic_hash": plan.plan_semantic_hash,
                    "evidence_bundle_hash": plan.evidence_bundle_hash,
                    "claim_bundle_hash": plan.claim_bundle_hash,
                }},
            ))

        started = time.monotonic()
        candidates = []
        trace = []
        errors = []
        successes = 0
        source_cap = max(0, plan.budget.max_sources)
        for query in plan.queries[: plan.budget.max_queries]:
            query_dict = dict(query)
            try:
                result = self._execute_query(query_dict)
                if not isinstance(result, Mapping):
                    raise TypeError("WRR query executor returned non-mapping")
                successes += 1
                trace.append({"query_uid": query.get("query_uid"),
                              "mode": query.get("mode"), "status": "completed"})
                raw_candidates = result.get("candidates") or result.get("results") or ()
                if isinstance(raw_candidates, (tuple, list)):
                    for raw in raw_candidates:
                        candidate = self._candidate(raw, query)
                        if candidate is not None and len(candidates) < source_cap:
                            candidates.append(candidate)
            except Exception as exc:  # WRR owns retries; adapter records once.
                trace.append({"query_uid": query.get("query_uid"),
                              "mode": query.get("mode"), "status": "failed"})
                if len(errors) < self._max_errors:
                    safe = f"{type(exc).__name__}: {exc}"[: self._max_error_chars]
                    errors.append({"code": "query_failed", "query_uid": query.get("query_uid"),
                                   "safe_message": safe})

        status = "completed" if successes == len(plan.queries) else "partial" if successes else "failed"
        source_identities = {
            _canonical_public_url(str(candidate.get("canonical_url") or candidate.get("url") or ""))
            for candidate in candidates
            if str(candidate.get("content_hash") or "")
        }
        digest = hashlib.sha256((plan.plan_semantic_hash + "|wrr").encode()).hexdigest()[:20]
        staged_run = finalize_raw_research_run(RawResearchRun(
            schema_version=RAW_RESEARCH_RUN_SCHEMA_VERSION,
            run_id=f"raw_{digest}", plan_semantic_hash=plan.plan_semantic_hash,
            capability_available=bool(plan.capability_snapshot.get("available")),
            attempted=True, executed=True, status=status, validated_evidence_count=0,
            route_trace=tuple(trace),
            execution=self._execution_ledger(
                plan,
                query_count=len(trace),
                candidate_count=len(candidates),
                source_count=len(source_identities),
                elapsed_seconds=time.monotonic() - started,
                successes=successes,
            ),
            raw_research={
                "input_hashes": {
                    "plan_semantic_hash": plan.plan_semantic_hash,
                    "evidence_bundle_hash": plan.evidence_bundle_hash,
                    "claim_bundle_hash": plan.claim_bundle_hash,
                },
                "candidates": tuple(candidates),
                "candidate_kind": "untrusted_discovery",
            },
            errors=tuple(errors),
        ))
        return finalize_raw_research_run(staged_run)


__all__ = ["HermesWRRAdapter"]
