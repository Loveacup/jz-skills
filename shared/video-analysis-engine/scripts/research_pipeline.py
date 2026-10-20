#!/usr/bin/env python3
"""Pure ResearchPlanner and one-shot ResearchProvider seam (S3)."""
from __future__ import annotations

import hashlib
from typing import Mapping, Optional, Protocol, Tuple

from research_contract import (
    RAW_RESEARCH_RUN_SCHEMA_VERSION,
    RESEARCH_PLAN_SCHEMA_VERSION,
    RawResearchRun,
    ResearchBudget,
    ResearchContractViolation,
    ResearchPlan,
    finalize_raw_research_run,
    finalize_research_plan,
    validate_raw_research_run,
    validate_research_plan,
)


class ResearchProvider(Protocol):
    def execute(self, plan: ResearchPlan) -> RawResearchRun: ...


_MODE_BUDGETS = {
    "sparse": (4, 6, 6, 60, 2, 2, 4),
    "condensed": (8, 12, 10, 120, 3, 5, 10),
    "full": (16, 24, 20, 240, 5, 10, 20),
}


def _uid(prefix: str, *parts: str) -> str:
    return prefix + "_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def _budget(mode: str, policy: str) -> ResearchBudget:
    if mode not in _MODE_BUDGETS:
        raise ResearchContractViolation(f"unsupported report_mode: {mode}")
    q, f, s, sec, topics, units, claims = _MODE_BUDGETS[mode]
    if policy == "deep":
        q, f, s, sec, topics, units, claims = 32, 36, 30, 360, 8, 16, 32
    if policy == "off":
        q = f = s = sec = topics = units = claims = 0
    return ResearchBudget(q, f, s, sec, 2, topics, units, claims, 1.0, 1.0, 0.5, "default-v1")


def build_research_plan(
    *, evidence_bundle_hash: str, claim_bundle: Mapping[str, object],
    canonical_id: str, platform: str, report_mode: str,
    research_policy: str, capability_snapshot: Mapping[str, object],
    created_at: str, plan_id: str, topic_hints: Tuple[str, ...] = (),
) -> ResearchPlan:
    claim_hash = str(claim_bundle.get("claim_bundle_semantic_hash") or "")
    if not claim_hash.startswith("sha256:"):
        raise ResearchContractViolation("claim_bundle_semantic_hash 必须是 sha256 hash")
    if research_policy not in {"auto", "force", "deep", "off"}:
        raise ResearchContractViolation("unsupported research_policy")

    disabled = research_policy == "off"
    raw_claims = claim_bundle.get("claims")
    raw_claims = raw_claims if isinstance(raw_claims, (tuple, list)) else ()
    normalized_claims = [item for item in raw_claims if isinstance(item, Mapping)]
    normalized_claims.sort(key=lambda item: str(item.get("claim_uid") or ""))
    claim_uids = [str(item.get("claim_uid") or "") for item in normalized_claims]
    non_empty_uids = [uid for uid in claim_uids if uid]
    if len(non_empty_uids) != len(set(non_empty_uids)):
        raise ResearchContractViolation("duplicate claim_uid")
    contextual_claim_uids = tuple(
        str(item.get("claim_uid") or "")
        for item in normalized_claims
        if str(item.get("claim_uid") or "")
        and str(item.get("risk") or "P2") not in {"P0", "P1"}
    )
    requests = []
    queries = []
    if not disabled:
        queries.append({
            "query_uid": _uid("query", canonical_id, "grounding"),
            "display_id": "Q1", "lane": "verification", "mode": "grounding",
            "query": f"{canonical_id} {platform} 基础背景与来源核实",
            "claim_uids": contextual_claim_uids, "entity_uids": (), "topic_uids": (),
            "priority": 100, "optional": False,
        })
        for item in normalized_claims:
            if not isinstance(item, Mapping):
                continue
            claim_uid = str(item.get("claim_uid") or "")
            risk = str(item.get("risk") or "P2")
            if not claim_uid:
                continue
            required = risk in {"P0", "P1"}
            temporal_class = str(item.get("temporal_class") or "stable")
            if temporal_class not in {"breaking", "current", "versioned", "historical", "stable"}:
                raise ResearchContractViolation("unsupported temporal_class")
            try:
                freshness_window_days = int(item.get("freshness_window_days") or (30 if temporal_class in {"breaking", "current", "versioned"} else 0))
            except (TypeError, ValueError) as exc:
                raise ResearchContractViolation("freshness_window_days 必须是非负整数") from exc
            if freshness_window_days < 0:
                raise ResearchContractViolation("freshness_window_days 必须是非负整数")
            requests.append({
                "claim_uid": claim_uid, "risk": risk,
                "temporal_class": temporal_class,
                "freshness_window_days": freshness_window_days,
                "verification_goals": ("verify", "freshness") if required else ("contextualize",),
                "required_source_relations": ("first_party", "independent") if required else ("independent",),
                "min_independent_publishers": 2 if required else 1,
                "required_for_publication": required,
                "priority": 95 if risk == "P0" else 85 if risk == "P1" else 50,
            })
            if required:
                text = str(item.get("text") or claim_uid)
                queries.append({
                    "query_uid": _uid("query", claim_uid, "verify"),
                    "display_id": f"Q{len(queries)+1}", "lane": "verification", "mode": "research",
                    "query": text, "claim_uids": (claim_uid,), "entity_uids": (), "topic_uids": (),
                    "temporal_class": temporal_class, "freshness_window_days": freshness_window_days,
                    "priority": 95 if risk == "P0" else 85, "optional": False,
                })

    topics = []
    candidates = []
    if not disabled:
        for hint in sorted(set(topic_hints)):
            topic_uid = _uid("topic", hint)
            topics.append({"topic_uid": topic_uid, "label": hint, "relevance": 1.0,
                           "expansion_goals": ("definition", "mechanism", "application")})
            candidates.append({"candidate_uid": _uid("kxc", topic_uid, "mechanism"),
                               "topic_uid": topic_uid, "dimension": "mechanism",
                               "question": f"{hint} 的定义、机制与应用边界是什么？",
                               "total_score": 0.9, "selected": True})
            queries.append({
                "query_uid": _uid("query", topic_uid, "expand"),
                "display_id": f"Q{len(queries)+1}", "lane": "knowledge_expansion", "mode": "discovery",
                "query": f"{hint} 定义 机制 应用 边界", "claim_uids": (), "entity_uids": (),
                "topic_uids": (topic_uid,), "priority": 70, "optional": True,
            })

    queries.sort(key=lambda q: (-int(q["priority"]), str(q["query_uid"])))
    for index, query in enumerate(queries, 1):
        query["display_id"] = f"Q{index}"
    stop = {
        "research_disabled": disabled,
        "fail_on_coverage_miss": research_policy in {"force", "deep"},
        "require_all_p0_resolved": research_policy != "off",
    }
    return finalize_research_plan(ResearchPlan(
        schema_version=RESEARCH_PLAN_SCHEMA_VERSION, plan_id=plan_id,
        created_at=created_at, planner_version="research-planner/1",
        evidence_bundle_hash=evidence_bundle_hash, claim_bundle_hash=claim_hash,
        canonical_id=canonical_id, platform=platform, report_mode=report_mode,
        research_policy=research_policy, capability_snapshot=capability_snapshot,
        verification_enabled=not disabled, knowledge_expansion_enabled=not disabled,
        budget=_budget(report_mode, research_policy), topics=tuple(topics),
        claims=tuple(requests), queries=tuple(queries),
        expansion_candidates=tuple(candidates), stop_conditions=stop,
    ))


def _unavailable(plan: ResearchPlan) -> RawResearchRun:
    return finalize_raw_research_run(RawResearchRun(
        schema_version=RAW_RESEARCH_RUN_SCHEMA_VERSION, run_id="raw_unavailable",
        plan_semantic_hash=plan.plan_semantic_hash, capability_available=False,
        attempted=False, executed=False, status="unavailable", validated_evidence_count=0,
        errors=({"code": "provider_unavailable", "safe_message": "no provider injected"},),
    ))


def execute_research_once(plan: ResearchPlan, provider: Optional[ResearchProvider]) -> RawResearchRun:
    validate_research_plan(plan)
    if provider is None:
        return _unavailable(plan)
    run = provider.execute(plan)  # exactly once; no retry/routing/fallback here
    if not isinstance(run, RawResearchRun):
        raise ResearchContractViolation("provider must return RawResearchRun")
    validate_raw_research_run(run)
    if run.plan_semantic_hash != plan.plan_semantic_hash:
        raise ResearchContractViolation("plan_semantic_hash mismatch")
    return run


class FixtureResearchProvider:
    def __init__(
        self, fixture: Mapping[str, object], *, plan_semantic_hash: str
    ) -> None:
        self._run = finalize_raw_research_run(RawResearchRun(
            schema_version=RAW_RESEARCH_RUN_SCHEMA_VERSION,
            run_id=_uid("raw", plan_semantic_hash, "fixture"),
            plan_semantic_hash=plan_semantic_hash, capability_available=True,
            attempted=True, executed=True, status="completed", validated_evidence_count=0,
            route_trace=("fixture",), execution={"provider": "fixture"},
            raw_research=fixture,
        ))

    def execute(self, plan: ResearchPlan) -> RawResearchRun:
        if self._run.plan_semantic_hash != plan.plan_semantic_hash:
            raise ResearchContractViolation("plan_semantic_hash mismatch")
        validate_raw_research_run(self._run)
        return self._run


class ArchivedResearchProvider:
    def __init__(self, archived_run: RawResearchRun):
        self._run = archived_run
        validate_raw_research_run(archived_run)

    def execute(self, plan: ResearchPlan) -> RawResearchRun:
        validate_raw_research_run(self._run)
        if self._run.plan_semantic_hash != plan.plan_semantic_hash:
            raise ResearchContractViolation("plan_semantic_hash mismatch")
        return self._run


__all__ = ["ResearchProvider", "build_research_plan", "execute_research_once",
           "FixtureResearchProvider", "ArchivedResearchProvider"]
