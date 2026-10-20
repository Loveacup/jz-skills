#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure contracts for WRR research artifacts.

This module performs no network or filesystem I/O. It defines immutable
ResearchPlan, ResearchBundle, and ResearchProjectionPlan envelopes plus the
canonical semantic/audit hashes that bind them together.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import List, Mapping, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from evidence_contract import canonical_json_bytes, semantic_sha256


RESEARCH_PLAN_SCHEMA_VERSION = "research-plan/1.0"
RESEARCH_BUNDLE_SCHEMA_VERSION = "research-bundle/1.0"
RESEARCH_PROJECTION_SCHEMA_VERSION = "research-projection/1.0"
RAW_RESEARCH_RUN_SCHEMA_VERSION = "raw-research-run/1.0"
RESEARCH_VALIDATOR_RULE_VERSION = "research-validator/1"
RESEARCH_ADJUDICATOR_RULE_VERSION = "research-adjudicator/1"
RESEARCH_FRESHNESS_RULE_VERSION = "research-freshness/1"
RESEARCH_SUITABILITY_RULE_VERSION = "research-suitability/1"
RESEARCH_INDEPENDENCE_RULE_VERSION = "research-independence/1"

RESEARCH_STATUSES: Tuple[str, ...] = (
    "not_requested",
    "unavailable",
    "completed",
    "partial",
    "failed",
    "blocked",
    "invalid",
)
RESEARCH_POLICIES: Tuple[str, ...] = ("auto", "force", "deep", "off")
REPORT_MODES: Tuple[str, ...] = ("sparse", "condensed", "full")
PUBLICATION_DISPOSITIONS: Tuple[str, ...] = ("pass", "degraded", "block")

_PRIVATE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "cookies",
        "headers",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "raw_response",
        "raw_payload",
        "signed_url",
    }
)
_SENSITIVE_MARKERS: Tuple[str, ...] = (
    "authorization=",
    "bearer ",
    "cookie=",
    "token=",
    "access_token=",
    "refresh_token=",
    "api_key=",
    "x-amz-signature=",
    "x-goog-signature=",
)


class ResearchContractViolation(Exception):
    """A research artifact violates schema, hash, or safety invariants."""


_VALIDATED_UID_FIELDS = {
    "sources": "source_uid",
    "quotes": "quote_uid",
    "claim_source_assessments": "assessment_uid",
    "claim_results": "claim_uid",
    "entity_results": "entity_uid",
    "research_claims": "research_claim_uid",
    "knowledge_expansions": "expansion_uid",
}


def _freeze(value: object) -> object:
    """Defensively copy nested containers into immutable equivalents."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(nested) for key, nested in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _freeze_fields(instance: object, names: Tuple[str, ...]) -> None:
    for name in names:
        object.__setattr__(instance, name, _freeze(getattr(instance, name)))


def _dataclass_payload(value: object) -> Mapping[str, object]:
    if not is_dataclass(value) or isinstance(value, type):
        raise ResearchContractViolation("artifact 必须是 dataclass instance")
    return {item.name: getattr(value, item.name) for item in fields(value)}


def _normalize_validated_value(value: object, field_name: str = "") -> object:
    if isinstance(value, Mapping):
        normalized = {}
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _VALIDATED_UID_FIELDS:
                uid_field = _VALIDATED_UID_FIELDS[key_text]
                if not isinstance(nested, (tuple, list)):
                    raise ResearchContractViolation(f"{key_text} 必须是 UID collection")
                records = []
                seen = set()
                for record in nested:
                    if not isinstance(record, Mapping):
                        raise ResearchContractViolation(f"{key_text} UID collection 项必须是 mapping")
                    uid = str(record.get(uid_field) or "")
                    if not uid:
                        raise ResearchContractViolation(f"{key_text} 缺少稳定 UID {uid_field}")
                    if uid in seen:
                        raise ResearchContractViolation(f"{key_text} 存在重复 UID {uid}")
                    seen.add(uid)
                    records.append(_normalize_validated_value(record, key_text))
                normalized[key_text] = sorted(
                    records,
                    key=lambda item: str(item.get(uid_field, "")),
                )
            else:
                normalized[key_text] = _normalize_validated_value(nested, key_text)
        return normalized
    if isinstance(value, (tuple, list)):
        normalized_items = [
            _normalize_validated_value(item, field_name) for item in value
        ]
        if field_name.endswith("_uids"):
            if len(set(str(item) for item in normalized_items)) != len(normalized_items):
                raise ResearchContractViolation(f"{field_name} 存在重复 UID")
            return sorted(normalized_items, key=str)
        return normalized_items
    return value


def _normalize_validated_research(value: Mapping[str, object]) -> Mapping[str, object]:
    normalized = _normalize_validated_value(value, "validated_research")
    if not isinstance(normalized, Mapping):  # pragma: no cover - defensive
        raise ResearchContractViolation("validated_research 必须是 mapping")
    return normalized


def _assert_no_sensitive_payload(value: object, path: str = "artifact") -> None:
    if is_dataclass(value) and not isinstance(value, type):
        _assert_no_sensitive_payload(_dataclass_payload(value), path)
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _PRIVATE_KEYS:
                raise ResearchContractViolation(f"{path} 含敏感字段 {key!r}")
            _assert_no_sensitive_payload(nested, f"{path}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, nested in enumerate(value):
            _assert_no_sensitive_payload(nested, f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in _SENSITIVE_MARKERS):
            raise ResearchContractViolation(f"{path} 含敏感凭据或签名痕迹")


def _sorted_records(records: Tuple[Mapping[str, object], ...], key: str):
    return sorted(records, key=lambda item: str(item.get(key, "")))


def _projection_sort_key(item: Mapping[str, object]):
    priority = item.get("priority", 0)
    numeric_priority = float(priority) if isinstance(priority, (int, float)) else 0.0
    return (
        str(item.get("target_section", "")),
        -numeric_priority,
        str(item.get("entry_uid", "")),
    )


def _require_hash(value: str, field_name: str) -> None:
    if not value or not str(value).startswith("sha256:"):
        raise ResearchContractViolation(f"{field_name} 必须是 sha256 hash")


@dataclass(frozen=True)
class ResearchBudget:
    max_queries: int
    max_fetches: int
    max_sources: int
    max_elapsed_seconds: int
    cross_check_depth: int
    max_topics: int
    max_knowledge_expansions: int
    max_research_claims: int
    p0_coverage: float
    adopted_p1_coverage: float
    p2_coverage: float
    freshness_policy_id: str


@dataclass(frozen=True)
class ResearchPlan:
    schema_version: str
    plan_id: str
    created_at: str
    planner_version: str
    evidence_bundle_hash: str
    claim_bundle_hash: str
    canonical_id: str
    platform: str
    report_mode: str
    research_policy: str
    capability_snapshot: Mapping[str, object]
    verification_enabled: bool
    knowledge_expansion_enabled: bool
    budget: ResearchBudget
    entities: Tuple[Mapping[str, object], ...] = ()
    topics: Tuple[Mapping[str, object], ...] = ()
    claims: Tuple[Mapping[str, object], ...] = ()
    queries: Tuple[Mapping[str, object], ...] = ()
    expansion_candidates: Tuple[Mapping[str, object], ...] = ()
    stop_conditions: Mapping[str, object] = field(default_factory=dict)
    plan_semantic_hash: str = ""

    def __post_init__(self) -> None:
        _freeze_fields(
            self,
            (
                "capability_snapshot",
                "entities",
                "topics",
                "claims",
                "queries",
                "expansion_candidates",
                "stop_conditions",
            ),
        )


@dataclass(frozen=True)
class RawResearchRun:
    schema_version: str
    run_id: str
    plan_semantic_hash: str
    capability_available: bool
    attempted: bool
    executed: bool
    status: str
    validated_evidence_count: int
    route_trace: Tuple[object, ...] = ()
    execution: Mapping[str, object] = field(default_factory=dict)
    raw_research: Mapping[str, object] = field(default_factory=dict)
    errors: Tuple[Mapping[str, object], ...] = ()
    raw_hash: str = ""

    def __post_init__(self) -> None:
        _freeze_fields(self, ("route_trace", "execution", "raw_research", "errors"))


@dataclass(frozen=True)
class ResearchBundle:
    schema_version: str
    bundle_id: str
    plan_id: str
    plan_semantic_hash: str
    evidence_bundle_hash: str
    claim_bundle_hash: str
    attempted: bool
    executed: bool
    status: str
    publication_disposition: str
    started_at: str
    completed_at: str
    wrr_version: str
    execution: Mapping[str, object]
    raw_research: Mapping[str, object]
    validated_research: Mapping[str, object]
    coverage: Mapping[str, object]
    conflicts: Tuple[Mapping[str, object], ...] = ()
    unresolved: Tuple[Mapping[str, object], ...] = ()
    errors: Tuple[Mapping[str, object], ...] = ()
    rule_versions: Mapping[str, object] = field(default_factory=dict)
    raw_hash: str = ""
    validated_semantic_hash: str = ""
    audit_artifact_hash: str = ""

    def __post_init__(self) -> None:
        _freeze_fields(
            self,
            (
                "execution",
                "raw_research",
                "validated_research",
                "coverage",
                "conflicts",
                "unresolved",
                "errors",
                "rule_versions",
            ),
        )


@dataclass(frozen=True)
class ResearchProjectionPlan:
    schema_version: str
    projection_id: str
    created_at: str
    projector_version: str
    evidence_bundle_hash: str
    claim_bundle_hash: str
    research_bundle_hash: str
    report_plan_hash: str
    report_mode: str
    section_budgets: Mapping[str, object]
    entries: Tuple[Mapping[str, object], ...] = ()
    omissions: Tuple[Mapping[str, object], ...] = ()
    projection_semantic_hash: str = ""

    def __post_init__(self) -> None:
        _freeze_fields(self, ("section_budgets", "entries", "omissions"))


def _validate_budget(budget: ResearchBudget) -> None:
    positive_fields = (
        "max_queries",
        "max_fetches",
        "max_sources",
        "max_elapsed_seconds",
        "cross_check_depth",
        "max_topics",
        "max_knowledge_expansions",
        "max_research_claims",
    )
    for name in positive_fields:
        if getattr(budget, name) < 0:
            raise ResearchContractViolation(f"budget.{name} 不得为负数")
    for name in ("p0_coverage", "adopted_p1_coverage", "p2_coverage"):
        value = getattr(budget, name)
        if not 0.0 <= value <= 1.0:
            raise ResearchContractViolation(f"budget.{name} 必须在 0..1")
    if not budget.freshness_policy_id:
        raise ResearchContractViolation("budget.freshness_policy_id 不得为空")


def research_plan_semantic_payload(plan: ResearchPlan) -> Mapping[str, object]:
    capability = dict(plan.capability_snapshot)
    capability.pop("checked_at", None)
    capability.pop("reason", None)
    return {
        "schema_version": plan.schema_version,
        "planner_version": plan.planner_version,
        "input": {
            "evidence_bundle_hash": plan.evidence_bundle_hash,
            "claim_bundle_hash": plan.claim_bundle_hash,
            "canonical_id": plan.canonical_id,
            "platform": plan.platform,
            "report_mode": plan.report_mode,
            "research_policy": plan.research_policy,
        },
        "capability_snapshot": capability,
        "lanes": {
            "verification_enabled": plan.verification_enabled,
            "knowledge_expansion_enabled": plan.knowledge_expansion_enabled,
        },
        "budget": asdict(plan.budget),
        "entities": _sorted_records(plan.entities, "entity_uid"),
        "topics": _sorted_records(plan.topics, "topic_uid"),
        "claims": _sorted_records(plan.claims, "claim_uid"),
        # Query order is semantic: priority/execution order is preserved.
        "queries": plan.queries,
        "expansion_candidates": _sorted_records(
            plan.expansion_candidates, "candidate_uid"
        ),
        "stop_conditions": plan.stop_conditions,
    }


def _validate_plan_shape(plan: ResearchPlan) -> None:
    if plan.schema_version != RESEARCH_PLAN_SCHEMA_VERSION:
        raise ResearchContractViolation("ResearchPlan schema_version 不兼容")
    if plan.research_policy not in RESEARCH_POLICIES:
        raise ResearchContractViolation("ResearchPlan research_policy 非法")
    if plan.report_mode not in REPORT_MODES:
        raise ResearchContractViolation("ResearchPlan report_mode 非法")
    for name, value in (
        ("evidence_bundle_hash", plan.evidence_bundle_hash),
        ("claim_bundle_hash", plan.claim_bundle_hash),
    ):
        _require_hash(value, name)
    if not (plan.plan_id and plan.canonical_id and plan.platform and plan.planner_version):
        raise ResearchContractViolation("ResearchPlan 身份字段不得为空")
    _validate_budget(plan.budget)
    _assert_no_sensitive_payload(plan)


def finalize_research_plan(plan: ResearchPlan) -> ResearchPlan:
    _validate_plan_shape(plan)
    return replace(
        plan,
        plan_semantic_hash=semantic_sha256(research_plan_semantic_payload(plan)),
    )


def validate_research_plan(plan: ResearchPlan) -> None:
    _validate_plan_shape(plan)
    expected = semantic_sha256(research_plan_semantic_payload(plan))
    if plan.plan_semantic_hash != expected:
        raise ResearchContractViolation("plan_semantic_hash 不匹配")


def raw_research_run_payload(run: RawResearchRun) -> Mapping[str, object]:
    return {
        "schema_version": run.schema_version,
        "plan_semantic_hash": run.plan_semantic_hash,
        "capability_available": run.capability_available,
        "attempted": run.attempted,
        "executed": run.executed,
        "status": run.status,
        "validated_evidence_count": run.validated_evidence_count,
        "route_trace": run.route_trace,
        "execution": run.execution,
        "raw_research": run.raw_research,
        "errors": run.errors,
    }


def _validate_raw_run_shape(run: RawResearchRun) -> None:
    if run.schema_version != RAW_RESEARCH_RUN_SCHEMA_VERSION:
        raise ResearchContractViolation("RawResearchRun schema_version 不兼容")
    _require_hash(run.plan_semantic_hash, "plan_semantic_hash")
    if run.executed and not run.attempted:
        raise ResearchContractViolation("executed=true 要求 attempted=true")
    if run.validated_evidence_count < 0:
        raise ResearchContractViolation("validated_evidence_count 不得为负数")
    if not run.capability_available and (run.attempted or run.executed):
        raise ResearchContractViolation("capability unavailable 不得声明执行")
    _assert_no_sensitive_payload(run)


def finalize_raw_research_run(run: RawResearchRun) -> RawResearchRun:
    _validate_raw_run_shape(run)
    try:
        raw_hash = semantic_sha256(raw_research_run_payload(run))
    except (TypeError, ValueError) as exc:
        raise ResearchContractViolation(
            "RawResearchRun 含不可 canonicalize 的非有限或非法值"
        ) from exc
    return replace(run, raw_hash=raw_hash)


def validate_raw_research_run(run: RawResearchRun) -> None:
    _validate_raw_run_shape(run)
    try:
        expected = semantic_sha256(raw_research_run_payload(run))
    except (TypeError, ValueError) as exc:
        raise ResearchContractViolation(
            "RawResearchRun 含不可 canonicalize 的非有限或非法值"
        ) from exc
    if run.raw_hash != expected:
        raise ResearchContractViolation("RawResearchRun raw_hash 不匹配")


def research_bundle_raw_payload(bundle: ResearchBundle) -> Mapping[str, object]:
    """Normative raw envelope: candidates + ordered route trace + safe errors.

    Snapshot content hashes remain inside ``raw_research``. Latency, counters,
    local paths, and all secret material are excluded.
    """
    return {
        "raw_research": bundle.raw_research,
        "route_trace": bundle.execution.get("route_trace", ()),
        "provider_errors": bundle.errors,
    }


def research_bundle_validated_payload(bundle: ResearchBundle) -> Mapping[str, object]:
    normalized_validated = _normalize_validated_research(bundle.validated_research)
    return {
        "schema_version": bundle.schema_version,
        "rule_versions": bundle.rule_versions,
        "input_hashes": {
            "plan_semantic_hash": bundle.plan_semantic_hash,
            "evidence_bundle_hash": bundle.evidence_bundle_hash,
            "claim_bundle_hash": bundle.claim_bundle_hash,
        },
        "status": bundle.status,
        "publication_disposition": bundle.publication_disposition,
        "validated_research": normalized_validated,
        "coverage": bundle.coverage,
        "conflicts": _sorted_records(bundle.conflicts, "conflict_uid"),
        "unresolved": _sorted_records(bundle.unresolved, "subject_uid"),
    }


def research_bundle_audit_payload(bundle: ResearchBundle) -> Mapping[str, object]:
    payload = dict(_dataclass_payload(bundle))
    payload.pop("audit_artifact_hash", None)
    return payload


def _validate_bundle_shape(bundle: ResearchBundle) -> None:
    if bundle.schema_version != RESEARCH_BUNDLE_SCHEMA_VERSION:
        raise ResearchContractViolation("ResearchBundle schema_version 不兼容")
    if bundle.status not in RESEARCH_STATUSES:
        raise ResearchContractViolation(f"ResearchBundle status 非法: {bundle.status!r}")
    if bundle.publication_disposition not in PUBLICATION_DISPOSITIONS:
        raise ResearchContractViolation("ResearchBundle publication_disposition 非法")
    if bundle.executed and not bundle.attempted:
        raise ResearchContractViolation("executed=true 要求 attempted=true")
    if bundle.status in ("completed", "partial") and not bundle.executed:
        raise ResearchContractViolation(f"status={bundle.status} 要求 executed=true")
    for name, value in (
        ("plan_semantic_hash", bundle.plan_semantic_hash),
        ("evidence_bundle_hash", bundle.evidence_bundle_hash),
        ("claim_bundle_hash", bundle.claim_bundle_hash),
    ):
        _require_hash(value, name)
    if not (bundle.bundle_id and bundle.plan_id):
        raise ResearchContractViolation("ResearchBundle 身份字段不得为空")
    _normalize_validated_research(bundle.validated_research)
    _assert_no_sensitive_payload(bundle)


def finalize_research_bundle(bundle: ResearchBundle) -> ResearchBundle:
    _validate_bundle_shape(bundle)
    raw_hash = semantic_sha256(research_bundle_raw_payload(bundle))
    staged = replace(bundle, raw_hash=raw_hash)
    validated_hash = semantic_sha256(research_bundle_validated_payload(staged))
    staged = replace(staged, validated_semantic_hash=validated_hash)
    audit_hash = semantic_sha256(research_bundle_audit_payload(staged))
    return replace(staged, audit_artifact_hash=audit_hash)


def validate_research_bundle(bundle: ResearchBundle) -> None:
    _validate_bundle_shape(bundle)
    expected_raw = semantic_sha256(research_bundle_raw_payload(bundle))
    if bundle.raw_hash != expected_raw:
        raise ResearchContractViolation("raw_hash 不匹配")
    expected_validated = semantic_sha256(research_bundle_validated_payload(bundle))
    if bundle.validated_semantic_hash != expected_validated:
        raise ResearchContractViolation("validated_semantic_hash 不匹配")
    expected_audit = semantic_sha256(research_bundle_audit_payload(bundle))
    if bundle.audit_artifact_hash != expected_audit:
        raise ResearchContractViolation("audit_artifact_hash 不匹配")


def _research_uid(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


def research_content_hash(text: str) -> str:
    if not isinstance(text, str):
        raise ResearchContractViolation("research content 必须是 text")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def _snapshot_hash(text: str) -> str:
    return research_content_hash(text)


def _canonical_public_url(value: object) -> str:
    try:
        parsed = urlsplit(str(value or "").strip())
        port = parsed.port
    except ValueError as exc:
        raise ResearchContractViolation("candidate canonical_url 非法") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ResearchContractViolation("candidate canonical_url 必须是公开 HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ResearchContractViolation("candidate canonical_url 不得含凭据")
    host = parsed.hostname.lower()
    default_port = (parsed.scheme.lower() == "https" and port == 443) or (
        parsed.scheme.lower() == "http" and port == 80
    )
    netloc = host if port is None or default_port else f"{host}:{port}"
    query = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower().replace("-", "_")
        if any(marker in lowered for marker in (
            "token", "signature", "credential", "authorization", "apikey",
            "api_key", "signed", "x_amz_", "x_goog_", "sig", "session",
            "cookie", "password", "secret",
        )):
            raise ResearchContractViolation("candidate canonical_url signed credential forbidden")
        if lowered.startswith("utm_") or lowered in {"fbclid", "gclid", "ref", "ref_src"}:
            continue
        query.append((key, val))
    query.sort()
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", urlencode(query), ""))


def canonical_research_url(value: object) -> str:
    return _canonical_public_url(value)


def _parse_utc(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_fixture_candidates(candidates: Tuple[object, ...]) -> bool:
    """Distinguish the fixture snapshot schema from the Hermes adapter schema."""
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        if any(key in item for key in ("query_uid", "canonical_url", "content", "quote_candidates")):
            return False
        if "url" in item and "quotes" in item:
            return True
    return False


def _classify_candidate_url(value: object) -> Tuple[Optional[str], Optional[str]]:
    """Return (canonical_url, rejection_reason). Exactly one is non-None."""
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        _ = parsed.port
    except ValueError:
        return None, "invalid_url"
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None, "invalid_url"
    if parsed.username is not None or parsed.password is not None:
        return None, "url_credentials"
    for key, _val in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower().replace("-", "_")
        if any(marker in lowered for marker in (
            "token", "signature", "credential", "authorization", "apikey",
            "api_key", "signed", "x_amz_", "x_goog_", "sig", "session",
            "cookie", "password", "secret",
        )):
            return None, "url_signed_token"
    try:
        return _canonical_public_url(raw), None
    except ResearchContractViolation:
        return None, "invalid_url"


def _classify_fixture_quote(quote: object) -> Optional[str]:
    """Return a rejection reason for a snapshot-schema quote, or None if accepted."""
    if not isinstance(quote, Mapping):
        return "invalid_quote"
    snapshot = quote.get("snapshot")
    if not isinstance(snapshot, Mapping) or not snapshot:
        return "snippet_only" if quote.get("snippet") else "missing_snapshot"
    quote_hash = str(quote.get("quote_hash") or "")
    snapshot_hash = str(snapshot.get("snapshot_hash") or "")
    if not quote_hash or not snapshot_hash:
        return "missing_hash"
    snapshot_text = str(snapshot.get("text") or "")
    if research_content_hash(snapshot_text) != snapshot_hash:
        return "snapshot_hash_mismatch"
    quote_text = str(quote.get("quote") or "")
    if research_content_hash(quote_text) != quote_hash:
        return "quote_hash_mismatch"
    if quote_text not in snapshot_text:
        return "quote_not_in_snapshot"
    priority = str(quote.get("priority") or "P2")
    full_required = priority == "P0" or (
        priority == "P1" and (bool(quote.get("mutable")) or bool(quote.get("conflicting")))
    )
    if full_required and str(snapshot.get("mode") or "") != "full":
        return "snapshot_not_full"
    return None


_HARD_COUNTERS: Tuple[str, ...] = (
    "query_count",
    "fetch_count",
    "source_count",
    "elapsed_seconds",
    "topic_count",
    "knowledge_expansion_count",
    "research_claim_count",
)


def _validate_conservative_counters(
    execution: Mapping[str, object], budget: ResearchBudget
) -> None:
    """Every hard counter must exist, be finite, non-negative, and within budget.

    Missing / NaN / inf / negative counters fail closed instead of silently
    truncating (Codex blocker: fail-open execution counters).
    """
    limits = {
        "query_count": budget.max_queries,
        "fetch_count": budget.max_fetches,
        "source_count": budget.max_sources,
        "elapsed_seconds": budget.max_elapsed_seconds,
        "topic_count": budget.max_topics,
        "knowledge_expansion_count": budget.max_knowledge_expansions,
        "research_claim_count": budget.max_research_claims,
    }
    for key in _HARD_COUNTERS:
        if key not in execution:
            raise ResearchContractViolation(f"execution 缺少 hard counter {key}")
        value = execution[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ResearchContractViolation(f"execution hard counter {key} 必须是有限数值")
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            raise ResearchContractViolation(f"execution hard counter {key} 必须有限")
        if numeric < 0:
            raise ResearchContractViolation(f"execution hard counter {key} 不得为负数")
        if key != "elapsed_seconds" and not numeric.is_integer():
            raise ResearchContractViolation(f"execution hard counter {key} 必须是整数")
        if numeric > limits[key]:
            raise ResearchContractViolation(f"budget/预算 exceeded: {key}")


def _hermes_to_fixture_candidate(candidate: Mapping[str, object]) -> Mapping[str, object]:
    """Project a Hermes-adapter candidate onto the shared snapshot-quote schema.

    The fetched ``content`` is the candidate's single snapshot; each quote
    reuses it. This forces Hermes candidates through the exact same
    snippet/missing/hash/quote/full-snapshot rules as fixture candidates.
    """
    content = str(candidate.get("content") or "")
    content_hash = str(candidate.get("content_hash") or "")
    snapshot_mode = str(candidate.get("snapshot_mode") or "full")
    snippet_only = bool(candidate.get("snippet_only"))
    quotes: List[Mapping[str, object]] = []
    for quote in candidate.get("quote_candidates", ()):
        if not isinstance(quote, Mapping):
            quotes.append({"quote": "", "quote_hash": ""})
            continue
        projected = {
            "quote": str(quote.get("quote_text") or ""),
            "quote_hash": str(quote.get("quote_hash") or ""),
            "priority": str(quote.get("priority") or "P2"),
            "mutable": bool(quote.get("mutable")),
            "conflicting": bool(quote.get("conflicting")),
            "claim_uid": str(quote.get("claim_uid") or ""),
        }
        if snippet_only:
            projected["snippet"] = content[:8]
        elif content:
            projected["snapshot"] = {
                "mode": snapshot_mode,
                "text": content,
                "snapshot_hash": content_hash,
            }
        quotes.append(projected)
    return {
        "candidate_uid": str(candidate.get("candidate_uid") or ""),
        "url": candidate.get("url"),
        "content_hash": content_hash,
        "quotes": quotes,
    }


# --- S5A-2a semantic layer: freshness / suitability / independence / social ---
# All four assessors are pure and deterministic. Freshness reads only the run's
# completed_at reference plus candidate/claim fields — never a wall clock.

_TIMELESS_TEMPORAL_CLASSES: frozenset = frozenset({"stable", "timeless"})
_WINDOWED_TEMPORAL_CLASSES: frozenset = frozenset({"current", "breaking", "versioned"})
_AUTHORITATIVE_SOURCE_KINDS: frozenset = frozenset({
    "official_doc", "official", "standards_body", "peer_reviewed",
    "encyclopedia", "news_agency", "government", "academic",
})
_SOCIAL_SOURCE_KINDS: frozenset = frozenset({"social_post", "forum", "video", "ugc"})
_WEAK_SOURCE_KINDS: frozenset = frozenset({"blog", "opinion", "aggregator"})
_CONTEXTUAL_CLAIM_CLASSES: frozenset = frozenset({"opinion", "audience", "self_report"})
_SUITABILITY_ORDER = {"invalid": 0, "weak": 1, "acceptable": 2, "strong": 3}
_INDEPENDENCE_LINK_FIELDS: Tuple[str, ...] = (
    "syndicated_from", "derived_from", "translation_of",
)


def _assess_freshness(
    temporal_class: str, window_days: object, published_at: object, reference_at: object
) -> str:
    """Deterministic freshness status; stable/timeless never fail on missing dates."""
    tclass = str(temporal_class or "stable")
    if tclass in _TIMELESS_TEMPORAL_CLASSES:
        return "timeless"
    if tclass not in _WINDOWED_TEMPORAL_CLASSES:
        return "unverifiable"
    published = _parse_utc(published_at)
    reference = _parse_utc(reference_at)
    if published is None or reference is None:
        return "unverifiable"
    if published > reference:
        return "unverifiable"
    try:
        window = int(str(window_days if window_days is not None else 30))
    except (TypeError, ValueError):
        window = 30
    if (reference - published).total_seconds() <= max(window, 0) * 86400:
        return "fresh"
    return "stale"


def _min_suitability(grades: Tuple[str, ...]) -> str:
    return min(grades, key=lambda grade: _SUITABILITY_ORDER[grade])


def _assess_suitability(
    source_kind: str, authority_relation: str, quality: str, access: str,
    freshness_status: str,
) -> str:
    """Fold orthogonal fields into a single grade without discarding the fields.

    Access gates hard: material we cannot independently reach is ``invalid``.
    Every other field contributes a grade and the most conservative one wins.
    """
    if str(access or "public") == "restricted":
        return "invalid"
    grades = []
    kind = str(source_kind or "unknown")
    if kind in _AUTHORITATIVE_SOURCE_KINDS:
        grades.append("strong")
    elif kind in _SOCIAL_SOURCE_KINDS or kind in _WEAK_SOURCE_KINDS:
        grades.append("weak")
    else:
        grades.append("acceptable")
    relation = str(authority_relation or "unknown")
    if relation == "primary":
        grades.append("strong")
    elif relation in {"secondary", "independent"}:
        grades.append("acceptable")
    elif relation in {"affiliated", "self"}:
        grades.append("weak")
    else:
        grades.append("acceptable")
    grade_quality = str(quality or "unknown")
    if grade_quality == "high":
        grades.append("strong")
    elif grade_quality == "medium":
        grades.append("acceptable")
    elif grade_quality == "low":
        grades.append("weak")
    else:
        grades.append("acceptable")
    if freshness_status == "stale":
        grades.append("weak")
    elif freshness_status == "unverifiable":
        grades.append("acceptable")
    return _min_suitability(tuple(grades))


def _assess_relation(
    proposed_relation: str, source_kind: str, claim_class: str, suitability: str
) -> Tuple[str, str, str]:
    """Return (role, validated_relation, validation_reason).

    Social/UGC sources may only serve a factual claim as contextual signal, never
    as support. Opinion/audience/self-report claims are contextual by nature.
    """
    proposed = str(proposed_relation or "supports")
    kind = str(source_kind or "unknown")
    klass = str(claim_class or "factual")
    is_social = kind in _SOCIAL_SOURCE_KINDS
    if suitability == "invalid":
        role = "social" if is_social else "support"
        return role, "unsuitable", "suitability_invalid"
    if klass in _CONTEXTUAL_CLAIM_CLASSES:
        # Opinion/audience/self-report claims are contextual by nature; this holds
        # even when the source is social (social sources may serve as contextual).
        return "contextual", "contextual", "contextual_claim_class"
    if is_social:
        return "social", "contextual", "social_restricted_to_contextual"
    return "support", proposed, "accepted_as_proposed"


def _source_metadata(candidate: Mapping[str, object]) -> Mapping[str, str]:
    publisher = str(candidate.get("publisher") or "")
    return {
        "source_kind": str(candidate.get("source_kind") or "unknown"),
        "authority_relation": str(candidate.get("authority_relation") or "unknown"),
        "quality": str(candidate.get("quality") or "unknown"),
        "access": str(candidate.get("access") or "public"),
        "publisher": publisher,
        "publisher_group": str(candidate.get("publisher_group") or publisher or ""),
        "published_at": str(candidate.get("published_at") or ""),
        "stance": str(candidate.get("stance") or "supports"),
        "syndicated_from": str(candidate.get("syndicated_from") or ""),
        "derived_from": str(candidate.get("derived_from") or ""),
        "translation_of": str(candidate.get("translation_of") or ""),
    }


def _safe_canonical_link(value: str) -> str:
    try:
        return _canonical_public_url(value)
    except ResearchContractViolation:
        return str(value or "").strip()


def _independence_group_map(sources: Mapping[str, Mapping[str, object]]) -> Mapping[str, str]:
    """Union sources sharing publisher(_group)/content_hash/explicit lineage links.

    URL count is not independence count. The group UID hashes the sorted member
    source_uids, so input order never affects it.
    """
    uids = sorted(sources)
    parent = {uid: uid for uid in uids}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[max(root_left, root_right)] = min(root_left, root_right)

    buckets: dict = {}
    for uid in uids:
        meta = sources[uid]["meta"]
        for key in ("publisher_group", "publisher"):
            token = meta.get(key) or ""
            if token:
                buckets.setdefault((key, token), []).append(uid)
        buckets.setdefault(("content_hash", sources[uid]["content_hash"]), []).append(uid)
    for members in buckets.values():
        for other in members[1:]:
            union(members[0], other)

    url_to_uid = {sources[uid]["canonical_url"]: uid for uid in uids}
    for uid in uids:
        meta = sources[uid]["meta"]
        for field_name in _INDEPENDENCE_LINK_FIELDS:
            target = str(meta.get(field_name) or "")
            if not target:
                continue
            resolved = url_to_uid.get(_safe_canonical_link(target))
            if resolved is not None:
                union(uid, resolved)

    components: dict = {}
    for uid in uids:
        components.setdefault(find(uid), []).append(uid)
    group_uid: dict = {}
    for members in components.values():
        members_sorted = sorted(members)
        guid = _research_uid("indep", *members_sorted)
        for uid in members_sorted:
            group_uid[uid] = guid
    return group_uid


# --- S5A-2b adjudication layer: consume A2a assessments -> five-state verdict ---
# Only strong/acceptable, quote-backed supports/contradicts/contextual assessments
# are consumable, and support/contradict strength is counted per independence_group
# — never per URL. Everything below is pure and input-order independent.

_ADJ_CONSUMABLE_SUITABILITY: frozenset = frozenset({"strong", "acceptable"})
_ADJ_CONSUMABLE_RELATIONS: frozenset = frozenset({"supports", "contradicts", "contextual"})
_FRESH_STATUSES: frozenset = frozenset({"fresh", "timeless"})
_PUBLICATION_QUALIFIERS: Mapping[str, Tuple[str, str]] = {
    "supported": ("keep", ""),
    "mixed": ("qualify", "conflicting_evidence"),
    "contradicted": ("drop", "contradicted"),
    "stale": ("drop", "stale_evidence"),
    "unresolved": ("drop", "insufficient_evidence"),
}


def _required_publisher_count(claim: Mapping[str, object]) -> int:
    """Default independent-publisher gate by risk (P0/P1=2, P2/P3=1); explicit wins."""
    explicit = claim.get("min_independent_publishers")
    if explicit is not None:
        try:
            return max(1, int(explicit))
        except (TypeError, ValueError):
            pass
    risk = str(claim.get("risk") or "P2").upper()
    return 2 if risk in ("P0", "P1") else 1


def _publication_action(verdict: str, required_for_publication: bool) -> Tuple[str, str]:
    """Map verdict -> (action, qualifier); required claims escalate to block."""
    action, qualifier = _PUBLICATION_QUALIFIERS[verdict]
    if required_for_publication and verdict != "supported":
        return "block", "required_claim_" + verdict
    return action, qualifier


def _adjudication_confidence(
    verdict: str, n_support: int, n_contradict: int, required: int
) -> float:
    """Deterministic 0..1 confidence; higher for stronger resolved verdicts."""
    req = max(required, 1)
    if verdict == "supported":
        return round(min(1.0, 0.6 + 0.2 * (n_support - req + 1)), 4)
    if verdict == "contradicted":
        return round(min(1.0, 0.6 + 0.2 * (n_contradict - req + 1)), 4)
    if verdict == "mixed":
        return 0.5
    if verdict == "stale":
        return 0.25
    return 0.1


def _adjudicate_conservative(
    plan: ResearchPlan,
    run: RawResearchRun,
    candidates: Tuple[object, ...],
    *,
    started_at: str,
    completed_at: str,
    wrr_version: str,
    bundle_id: str,
) -> ResearchBundle:
    """Validate snapshot-schema candidates; adjudication stays conservatively blocked.

    Source identity is the canonical URL alone. Distinct content hashes for one
    canonical URL collapse to the minimal ``candidate_uid`` representative, with
    the conflicting siblings recorded as stable rejections. Duplicate or missing
    ``candidate_uid`` fail closed. Rejected material never enters
    ``validated_research`` — the detailed ledger lives only in the audit.
    """
    rejections: List[Mapping[str, object]] = []
    groups: dict = {}
    seen_uids = set()
    if any(not isinstance(item, Mapping) for item in candidates):
        raise ResearchContractViolation("raw candidate 必须是 mapping")
    mapping_candidates: Tuple[Mapping[str, object], ...] = tuple(
        item for item in candidates if isinstance(item, Mapping)
    )
    for candidate in sorted(
        mapping_candidates,
        key=lambda item: str(item.get("candidate_uid") or ""),
    ):
        candidate_uid = str(candidate.get("candidate_uid") or "")
        if not candidate_uid:
            raise ResearchContractViolation("candidate 缺少稳定 candidate_uid")
        if candidate_uid in seen_uids:
            raise ResearchContractViolation(f"candidate_uid 重复: {candidate_uid}")
        seen_uids.add(candidate_uid)
        canonical_url, url_reason = _classify_candidate_url(candidate.get("url"))
        if url_reason is not None:
            rejections.append({
                "candidate_uid": candidate_uid, "stage": "url",
                "quote_index": -1, "reason": url_reason,
            })
            continue
        content_hash = str(candidate.get("content_hash") or "")
        if not _is_sha256_digest(content_hash):
            rejections.append({
                "candidate_uid": candidate_uid, "stage": "content",
                "quote_index": -1, "reason": "missing_content_hash",
            })
            continue
        groups.setdefault(canonical_url, []).append(
            (candidate_uid, content_hash, candidate.get("quotes", ()), candidate)
        )

    source_groups: dict = {}
    for canonical_url in sorted(groups):
        members = sorted(groups[canonical_url], key=lambda member: member[0])
        representative_uid, representative_hash, _, representative_candidate = members[0]
        source_uid = _research_uid("src", canonical_url)
        accepted_quotes: dict = {}
        for candidate_uid, content_hash, quotes, _member_candidate in members:
            if content_hash != representative_hash:
                # canonical URL is identity; a divergent content hash cannot
                # silently become a second source or overwrite the representative.
                rejections.append({
                    "candidate_uid": candidate_uid, "stage": "content",
                    "quote_index": -1, "reason": "content_hash_conflict",
                })
                continue
            for index, quote in enumerate(quotes):
                reason = _classify_fixture_quote(quote)
                if reason is not None:
                    rejections.append({
                        "candidate_uid": candidate_uid, "stage": "quote",
                        "quote_index": index, "reason": reason,
                    })
                    continue
                quote_hash = str(quote.get("quote_hash") or "")
                claim_uid = str(quote.get("claim_uid") or "")
                # The same verbatim quote may legitimately support multiple
                # claims. Claim identity is therefore part of the association
                # UID so dictionary insertion cannot overwrite another claim.
                quote_uid = _research_uid("quote", source_uid, claim_uid, quote_hash)
                accepted_quotes[quote_uid] = {
                    "quote_uid": quote_uid, "source_uid": source_uid,
                    "quote_hash": quote_hash, "verbatim_quote": str(quote.get("quote") or ""),
                    "priority": str(quote.get("priority") or "P2"),
                    "snapshot_hash": str((quote.get("snapshot") or {}).get("snapshot_hash") or ""),
                    "claim_uid": claim_uid,
                }
        if not accepted_quotes:
            continue
        source_groups[source_uid] = {
            "source_uid": source_uid, "canonical_url": canonical_url,
            "content_hash": representative_hash,
            "representative_candidate_uid": representative_uid,
            "meta": _source_metadata(representative_candidate),
            "quotes": accepted_quotes,
        }

    # Independence is derived once over the accepted source set — canonical URL
    # count is not the same as independent-source count.
    independence = _independence_group_map(source_groups)
    claims_by_uid = {
        str(item.get("claim_uid") or ""): item
        for item in plan.claims
        if str(item.get("claim_uid") or "")
    }

    sources_list = []
    quotes_list = []
    accepted_assessments: List[Mapping[str, object]] = []
    assessment_rejections: List[Mapping[str, object]] = []
    for source_uid in sorted(source_groups):
        group = source_groups[source_uid]
        meta = group["meta"]
        independence_group = independence[source_uid]
        sources_list.append({
            "source_uid": source_uid,
            "canonical_url": group["canonical_url"],
            "content_hash": group["content_hash"],
            "representative_candidate_uid": group["representative_candidate_uid"],
            "source_kind": meta["source_kind"],
            "publisher": meta["publisher"],
            "publisher_group": meta["publisher_group"],
            "published_at": meta["published_at"],
            "independence_group": independence_group,
        })
        quotes_list.extend(group["quotes"].values())

        # Group accepted quotes by the claim they back; each (claim, source) pair
        # becomes one quote-backed assessment.
        claim_quote_uids: dict = {}
        for quote_uid, record in group["quotes"].items():
            claim_uid = str(record.get("claim_uid") or "")
            if not claim_uid:
                continue
            claim_quote_uids.setdefault(claim_uid, set()).add(quote_uid)
        for claim_uid in sorted(claim_quote_uids):
            claim = claims_by_uid.get(claim_uid)
            quote_uids = tuple(sorted(claim_quote_uids[claim_uid]))
            assessment_uid = _research_uid("assessment", claim_uid, source_uid)
            if claim is None:
                assessment_rejections.append({
                    "assessment_uid": assessment_uid, "claim_uid": claim_uid,
                    "source_uid": source_uid, "suitability": "invalid",
                    "validated_relation": "unsuitable",
                    "validation_reason": "unknown_claim",
                })
                continue
            freshness_status = _assess_freshness(
                claim.get("temporal_class"), claim.get("freshness_window_days"),
                meta["published_at"], completed_at,
            )
            suitability = _assess_suitability(
                meta["source_kind"], meta["authority_relation"], meta["quality"],
                meta["access"], freshness_status,
            )
            role, validated_relation, validation_reason = _assess_relation(
                meta["stance"], meta["source_kind"],
                str(claim.get("claim_class") or "factual"), suitability,
            )
            record = {
                "assessment_uid": assessment_uid,
                "claim_uid": claim_uid,
                "source_uid": source_uid,
                "quote_uids": quote_uids,
                "role": role,
                "suitability": suitability,
                "suitability_factors": {
                    "source_kind": meta["source_kind"],
                    "authority_relation": meta["authority_relation"],
                    "quality": meta["quality"],
                    "access": meta["access"],
                    "freshness": freshness_status,
                },
                "proposed_relation": meta["stance"],
                "validated_relation": validated_relation,
                "validation_reason": validation_reason,
                "freshness_status": freshness_status,
                "independence_group": independence_group,
            }
            if suitability == "invalid":
                assessment_rejections.append(record)
            else:
                accepted_assessments.append(record)

    accepted_assessments.sort(key=lambda item: str(item["assessment_uid"]))
    assessment_rejections.sort(key=lambda item: str(item["assessment_uid"]))

    # Only quotes referenced by accepted, known-claim assessments cross into
    # validated research. Unknown/unbound claim and invalid-suitability material
    # remains audit-only so every reverse reference closes.
    validated_quote_uids = set()
    for assessment in accepted_assessments:
        quote_uids_value = assessment.get("quote_uids", ())
        if isinstance(quote_uids_value, (tuple, list)):
            validated_quote_uids.update(str(uid) for uid in quote_uids_value)
    quotes_list = [
        quote for quote in quotes_list
        if str(quote.get("quote_uid") or "") in validated_quote_uids
    ]

    declared_source = run.execution.get("source_count")
    if declared_source is not None:
        try:
            declared_source_number = float(str(declared_source))
        except (TypeError, ValueError) as exc:
            raise ResearchContractViolation("execution source_count 非法") from exc
        if (not math.isfinite(declared_source_number)
                or not declared_source_number.is_integer()
                or declared_source_number != len(sources_list)):
            raise ResearchContractViolation("execution source_count 闭合失败")

    sorted_rejections = sorted(
        rejections,
        key=lambda item: (
            str(item["candidate_uid"]), int(item["quote_index"]), str(item["reason"]),
        ),
    )
    # --- S5A-2b: deterministic five-state adjudication ----------------------
    assessments_by_claim: dict = {}
    for record in accepted_assessments:
        assessments_by_claim.setdefault(str(record["claim_uid"]), []).append(record)

    claim_results: List[Mapping[str, object]] = []
    conflicts_list: List[Mapping[str, object]] = []
    unresolved_records: List[Mapping[str, object]] = []
    # [total, resolved] tallies per risk bucket; P3 folds into the P2 gate.
    risk_tally: dict = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0]}

    for claim_uid in sorted(claims_by_uid):
        claim = claims_by_uid[claim_uid]
        required = _required_publisher_count(claim)
        required_for_pub = bool(claim.get("required_for_publication"))
        claim_assessments = assessments_by_claim.get(claim_uid, [])

        def _consumable_for_adjudication(assessment: Mapping[str, object]) -> bool:
            relation = assessment["validated_relation"]
            if relation not in _ADJ_CONSUMABLE_RELATIONS:
                return False
            if assessment["suitability"] in _ADJ_CONSUMABLE_SUITABILITY:
                return True
            # A source whose only weak dimension is stale freshness must remain
            # visible to adjudication so it can yield the explicit ``stale``
            # verdict. Genuinely weak source kind/authority/quality stays excluded.
            factors = assessment.get("suitability_factors") or {}
            if (relation == "supports"
                    and assessment.get("freshness_status") == "stale"
                    and isinstance(factors, Mapping)):
                non_temporal = _assess_suitability(
                    str(factors.get("source_kind") or "unknown"),
                    str(factors.get("authority_relation") or "unknown"),
                    str(factors.get("quality") or "unknown"),
                    str(factors.get("access") or "public"),
                    "fresh",
                )
                return non_temporal in _ADJ_CONSUMABLE_SUITABILITY
            return False

        consumed = [
            assessment for assessment in claim_assessments
            if _consumable_for_adjudication(assessment)
        ]
        consumed_uid_set = {str(a["assessment_uid"]) for a in consumed}
        rejected_uids = tuple(sorted(
            str(a["assessment_uid"]) for a in claim_assessments
            if str(a["assessment_uid"]) not in consumed_uid_set
        ))

        support_fresh: dict = {}
        support_stale: dict = {}
        support_unverifiable: dict = {}
        contradict_valid: dict = {}
        supporting_quotes: set = set()
        contradicting_quotes: set = set()
        contextual_quotes: set = set()
        for a in consumed:
            group = str(a["independence_group"])
            fresh = a["freshness_status"] in _FRESH_STATUSES
            relation = a["validated_relation"]
            if relation == "supports":
                supporting_quotes.update(a["quote_uids"])
                if fresh:
                    support_fresh[group] = True
                elif a["freshness_status"] == "stale":
                    support_stale.setdefault(group, True)
                else:
                    support_unverifiable.setdefault(group, True)
            elif relation == "contradicts":
                contradicting_quotes.update(a["quote_uids"])
                if fresh:
                    contradict_valid[group] = True
            else:  # contextual
                contextual_quotes.update(a["quote_uids"])

        # A fresh support group is never also counted as stale/unverifiable.
        stale_groups = {g for g in support_stale if g not in support_fresh}
        n_support = len(support_fresh)
        n_contradict = len(contradict_valid)
        n_stale = len(stale_groups)

        if n_support >= 1 and n_contradict >= 1:
            verdict = "mixed"  # never let a support majority swallow a live conflict
        elif n_support >= required and n_contradict == 0:
            verdict = "supported"
        elif n_contradict >= required and n_support == 0:
            verdict = "contradicted"
        elif n_support == 0 and n_contradict == 0 and n_stale >= required:
            verdict = "stale"
        else:
            verdict = "unresolved"

        conflict_present = n_support >= 1 and n_contradict >= 1
        freshness_satisfied = n_support >= 1
        resolved = verdict != "unresolved"
        action, qualifier = _publication_action(verdict, required_for_pub)
        confidence = _adjudication_confidence(verdict, n_support, n_contradict, required)

        claim_results.append({
            "claim_uid": claim_uid,
            "verdict": verdict,
            "confidence": confidence,
            "supporting_quote_uids": tuple(sorted(supporting_quotes)),
            "contradicting_quote_uids": tuple(sorted(contradicting_quotes)),
            "contextual_quote_uids": tuple(sorted(contextual_quotes)),
            "independent_publisher_count": n_support,
            "required_publisher_count": required,
            "freshness_satisfied": freshness_satisfied,
            "adjudication": {
                "rule_version": RESEARCH_ADJUDICATOR_RULE_VERSION,
                "accepted_assessment_uids": tuple(sorted(consumed_uid_set)),
                "rejected_assessment_uids": rejected_uids,
                "conflict_present": conflict_present,
                "coverage_passed": resolved,
            },
            "publication_action": action,
            "qualifier": qualifier,
            "checked_at": completed_at,
        })
        if conflict_present:
            conflict_uids = tuple(sorted(
                str(a["assessment_uid"]) for a in consumed
                if a["validated_relation"] in ("supports", "contradicts")
            ))
            conflicts_list.append({
                "conflict_uid": _research_uid("conflict", claim_uid),
                "subject_uid": claim_uid,
                "assessment_uids": conflict_uids,
            })
        if not resolved:
            if n_support or n_stale:
                reason = "insufficient_independent_publishers"
            elif support_unverifiable:
                reason = "unverifiable_required_freshness"
            else:
                reason = "insufficient_supporting_evidence"
            unresolved_records.append({"subject_uid": claim_uid, "reason": reason})

        risk = str(claim.get("risk") or "P2").upper()
        bucket = "P0" if risk == "P0" else ("P1" if risk == "P1" else "P2")
        if bucket == "P1" and claim.get("adopted") is False:
            pass  # unadopted P1 claims are outside the adopted-P1 coverage lane
        else:
            risk_tally[bucket][0] += 1
            if resolved:
                risk_tally[bucket][1] += 1

    claim_results.sort(key=lambda item: str(item["claim_uid"]))
    conflicts_list.sort(key=lambda item: str(item["conflict_uid"]))
    unresolved_records.sort(key=lambda item: str(item["subject_uid"]))

    p0_total, p0_resolved = risk_tally["P0"]
    p1_total, p1_resolved = risk_tally["P1"]
    p2_total, p2_resolved = risk_tally["P2"]
    p2_ratio = (p2_resolved / p2_total) if p2_total else 0.0
    p0_gate = p0_total == 0 or (p0_resolved / p0_total) >= plan.budget.p0_coverage
    p1_gate = p1_total == 0 or (p1_resolved / p1_total) >= plan.budget.adopted_p1_coverage
    p2_gate = p2_total == 0 or p2_ratio >= plan.budget.p2_coverage
    gate_passed = bool(p0_gate and p1_gate and p2_gate)

    actions = [str(item["publication_action"]) for item in claim_results]
    if not claim_results:
        disposition = "block"  # no claim results -> nothing verified -> block
    elif any(a == "block" for a in actions):
        disposition = "block"
    elif any(a in ("qualify", "drop") for a in actions):
        disposition = "degraded"
    else:
        disposition = "pass"

    coverage = {
        "verification": {
            "p0_total": p0_total, "p0_resolved": p0_resolved,
            "adopted_p1_total": p1_total, "adopted_p1_resolved": p1_resolved,
            "p2_total": p2_total, "p2_resolved": p2_resolved,
            "p2_ratio": p2_ratio, "gate_passed": gate_passed,
        },
        "expansion": {
            "expansion_total": int(run.execution.get("knowledge_expansion_count") or 0),
            "grounded": 0, "gate_passed": True,
        },
        "adjudication_mode": "resolved",
    }
    unresolved = tuple(unresolved_records)
    conflicts = tuple(conflicts_list)
    validated = {
        "sources": tuple(sources_list),
        "quotes": tuple(quotes_list),
        "claim_source_assessments": tuple(accepted_assessments),
        "claim_results": tuple(claim_results),
        "audit_metadata": {
            "validator_version": RESEARCH_VALIDATOR_RULE_VERSION,
            "adjudicator_version": RESEARCH_ADJUDICATOR_RULE_VERSION,
            "freshness_version": RESEARCH_FRESHNESS_RULE_VERSION,
            "suitability_version": RESEARCH_SUITABILITY_RULE_VERSION,
            "independence_version": RESEARCH_INDEPENDENCE_RULE_VERSION,
            "adjudication_mode": "resolved",
        },
    }
    execution_summary = {key: run.execution.get(key) for key in _HARD_COUNTERS}
    sanitized_raw = {
        "input_hashes": {
            key: str(value)
            for key, value in run.raw_research.get("input_hashes", {}).items()
        },
        "accepted_sources": tuple(sources_list),
        "validation_audit": {
            "rejections": tuple(sorted_rejections),
            "assessment_rejections": tuple(assessment_rejections),
        },
        "execution_summary": execution_summary,
    }
    # bundle_id binds to the canonical (input-order-independent) raw payload,
    # never to run.raw_hash which is sensitive to candidate input order.
    resolved_bundle_id = bundle_id or _research_uid(
        "bundle", plan.plan_semantic_hash, semantic_sha256(sanitized_raw)
    )
    bundle = ResearchBundle(
        schema_version=RESEARCH_BUNDLE_SCHEMA_VERSION,
        bundle_id=resolved_bundle_id, plan_id=plan.plan_id,
        plan_semantic_hash=plan.plan_semantic_hash,
        evidence_bundle_hash=plan.evidence_bundle_hash,
        claim_bundle_hash=plan.claim_bundle_hash,
        attempted=run.attempted, executed=run.executed,
        status=run.status if run.status in RESEARCH_STATUSES else "invalid",
        publication_disposition=disposition,
        started_at=started_at, completed_at=completed_at, wrr_version=wrr_version,
        execution={**dict(run.execution), "route_trace": run.route_trace},
        raw_research=sanitized_raw,
        validated_research=validated,
        coverage=coverage,
        conflicts=conflicts, unresolved=unresolved, errors=run.errors,
        rule_versions={
            "validator": RESEARCH_VALIDATOR_RULE_VERSION,
            "adjudicator": RESEARCH_ADJUDICATOR_RULE_VERSION,
            "freshness": RESEARCH_FRESHNESS_RULE_VERSION,
            "suitability": RESEARCH_SUITABILITY_RULE_VERSION,
            "independence": RESEARCH_INDEPENDENCE_RULE_VERSION,
        },
    )
    return finalize_research_bundle(bundle)


def validate_and_adjudicate_research(
    plan: ResearchPlan,
    run: RawResearchRun,
    *,
    bundle_id: str = "",
    started_at: str = "",
    completed_at: str = "",
    wrr_version: str = "hermes-wrr/1",
) -> ResearchBundle:
    """Validate one untrusted raw run and deterministically adjudicate claims."""
    validate_research_plan(plan)
    validate_raw_research_run(run)
    if run.plan_semantic_hash != plan.plan_semantic_hash:
        raise ResearchContractViolation("plan/run plan_semantic_hash 绑定不匹配")
    if run.validated_evidence_count != 0:
        raise ResearchContractViolation("raw provider 不得自报 validated evidence")

    queries = {str(item.get("query_uid") or ""): item for item in plan.queries}
    claims = {str(item.get("claim_uid") or ""): item for item in plan.claims}
    input_hashes = run.raw_research.get("input_hashes")
    expected_input_hashes = {
        "plan_semantic_hash": plan.plan_semantic_hash,
        "evidence_bundle_hash": plan.evidence_bundle_hash,
        "claim_bundle_hash": plan.claim_bundle_hash,
    }
    if not isinstance(input_hashes, Mapping) or any(
        str(input_hashes.get(key) or "") != value
        for key, value in expected_input_hashes.items()
    ):
        raise ResearchContractViolation("raw_research.input_hashes 未闭合")
    budget_fields = {
        "query_count": plan.budget.max_queries,
        "fetch_count": plan.budget.max_fetches,
        "source_count": plan.budget.max_sources,
        "elapsed_seconds": plan.budget.max_elapsed_seconds,
        "topic_count": plan.budget.max_topics,
        "knowledge_expansion_count": plan.budget.max_knowledge_expansions,
        "research_claim_count": plan.budget.max_research_claims,
    }
    for key, limit in budget_fields.items():
        if key in run.execution:
            try:
                value = float(run.execution[key])
            except (TypeError, ValueError) as exc:
                raise ResearchContractViolation(f"budget {key} 非法") from exc
            if value > limit:
                raise ResearchContractViolation(f"budget/预算 exceeded: {key}")
    raw_candidates_value = run.raw_research.get("candidates", ())
    if not isinstance(raw_candidates_value, (tuple, list)):
        raise ResearchContractViolation("raw candidates 必须是 collection")
    raw_candidates = tuple(raw_candidates_value)
    if any(not isinstance(item, Mapping) for item in raw_candidates):
        raise ResearchContractViolation("raw candidate 必须是 mapping")
    if "fetch_count" in run.execution:
        try:
            declared_fetch = float(str(run.execution["fetch_count"]))
        except (TypeError, ValueError):
            declared_fetch = None
        if (declared_fetch is None or not math.isfinite(declared_fetch)
                or not declared_fetch.is_integer()
                or declared_fetch != len(raw_candidates)):
            raise ResearchContractViolation("fetch_count 闭合失败")
    if len(raw_candidates) > plan.budget.max_sources:
        raise ResearchContractViolation("raw candidates 超过 max_sources budget")

    mappings: Tuple[Mapping[str, object], ...] = tuple(
        item for item in raw_candidates if isinstance(item, Mapping)
    )
    # The legacy claim-adjudication path keys candidates by canonical_url; the
    # conservative S5A path keys them by url. Only the conservative path enforces
    # strict hard-counter closure (the legacy path predates execution counters).
    is_legacy = any("canonical_url" in item for item in mappings)
    if not is_legacy:
        _validate_conservative_counters(run.execution, plan.budget)
        if _is_fixture_candidates(raw_candidates):
            conservative_candidates: Tuple[object, ...] = mappings
        else:
            conservative_candidates = tuple(
                _hermes_to_fixture_candidate(item) for item in mappings
            )
        return _adjudicate_conservative(
            plan, run, conservative_candidates,
            started_at=str(run.execution.get("started_at") or "") or plan.created_at,
            completed_at=str(run.execution.get("completed_at") or "") or plan.created_at,
            wrr_version=wrr_version,
            bundle_id=bundle_id,
        )

    sources = {}
    quotes = {}
    assessments = {}
    rejection_summary = {}
    for candidate in sorted(
        (item for item in raw_candidates if isinstance(item, Mapping)),
        key=lambda item: str(item.get("candidate_uid") or item.get("canonical_url") or ""),
    ):
        query = queries.get(str(candidate.get("query_uid") or ""))
        if not query:
            rejection_summary["unknown_query"] = rejection_summary.get("unknown_query", 0) + 1
            continue
        claim_uids = tuple(str(uid) for uid in query.get("claim_uids", ()) if str(uid) in claims)
        if not claim_uids:
            continue
        try:
            canonical_url = _canonical_public_url(candidate.get("canonical_url"))
        except ResearchContractViolation:
            rejection_summary["invalid_url"] = rejection_summary.get("invalid_url", 0) + 1
            continue
        source_uid = _research_uid("source", canonical_url)
        content = str(candidate.get("content") or "")
        expected_content_hash = _snapshot_hash(content)
        content_hash = str(candidate.get("content_hash") or "")
        sources[source_uid] = {
            "source_uid": source_uid,
            "canonical_url": canonical_url,
            "title": str(candidate.get("title") or ""),
            "publisher": str(candidate.get("publisher") or ""),
            "publisher_group": str(candidate.get("publisher_group") or candidate.get("publisher") or source_uid),
            "source_kind": str(candidate.get("source_kind") or "unknown"),
            "published_at": str(candidate.get("published_at") or ""),
            "fetched_at": str(candidate.get("fetched_at") or ""),
            "snapshot_hash": content_hash,
        }
        for claim_uid in claim_uids:
            assessment_uid = _research_uid("assessment", claim_uid, source_uid)
            reasons = []
            if candidate.get("snippet_only") or not content:
                reasons.append("snippet_only")
            if content_hash != expected_content_hash:
                reasons.append("snapshot_hash_mismatch")
            claim = claims[claim_uid]
            required = bool(claim.get("required_for_publication"))
            temporal_class = str(claim.get("temporal_class") or "stable")
            if temporal_class in {"breaking", "current", "versioned"}:
                published = _parse_utc(candidate.get("published_at"))
                reference = _parse_utc(completed_at or plan.created_at)
                try:
                    window_days = int(str(claim.get("freshness_window_days") or 30))
                except ValueError:
                    window_days = 30
                if published is None or reference is None:
                    reasons.append("freshness_unverifiable")
                elif (reference - published).total_seconds() > max(window_days, 0) * 86400:
                    reasons.append("stale_source")
            if required and str(candidate.get("source_kind") or "").lower() in {"social", "forum", "ugc"}:
                reasons.append("social_only_unsuitable")

            accepted_quote_uids = []
            for quote in candidate.get("quote_candidates", ()):
                if not isinstance(quote, Mapping) or str(quote.get("claim_uid") or "") != claim_uid:
                    continue
                text = str(quote.get("quote_text") or "")
                start, end = quote.get("start"), quote.get("end")
                if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
                    continue
                if content[start:end] != text or str(quote.get("quote_hash") or "") != _snapshot_hash(text):
                    continue
                quote_uid = _research_uid("quote", source_uid, claim_uid, start, end, text)
                quotes[quote_uid] = {
                    "quote_uid": quote_uid, "source_uid": source_uid,
                    "claim_uid": claim_uid, "quote_text": text,
                    "start": start, "end": end, "quote_hash": _snapshot_hash(text),
                }
                accepted_quote_uids.append(quote_uid)
            if not accepted_quote_uids:
                reasons.append("no_verifiable_quote")
            verdict = "rejected" if reasons else "accepted"
            if reasons:
                for reason in reasons:
                    rejection_summary[reason] = rejection_summary.get(reason, 0) + 1
            record = {
                "assessment_uid": assessment_uid, "claim_uid": claim_uid,
                "source_uid": source_uid, "verdict": verdict,
                "stance": str(candidate.get("stance") or "supports"),
                "quote_uids": tuple(sorted(accepted_quote_uids)) if verdict == "accepted" else (),
                "reasons": tuple(sorted(set(reasons))),
            }
            previous = assessments.get(assessment_uid)
            if previous is None or (previous["verdict"] == "rejected" and verdict == "accepted"):
                assessments[assessment_uid] = record

    # Quotes from rejected/deduplicated assessments cannot survive closure.
    accepted_quote_uids = {
        uid for item in assessments.values() if item["verdict"] == "accepted"
        for uid in item["quote_uids"]
    }
    quotes = {uid: item for uid, item in quotes.items() if uid in accepted_quote_uids}

    claim_results = []
    conflicts = []
    unresolved = []
    for claim_uid, claim in sorted(claims.items()):
        accepted = [
            item for item in assessments.values()
            if item["claim_uid"] == claim_uid and item["verdict"] == "accepted"
        ]
        groups = {
            str(sources[item["source_uid"]].get("publisher_group") or item["source_uid"])
            for item in accepted
        }
        required_publishers = int(claim.get("min_independent_publishers") or 1)
        stances = {str(item.get("stance") or "supports") for item in accepted}
        conflicted = "supports" in stances and "contradicts" in stances
        corroborated = len(groups) >= required_publishers and not conflicted
        verdict = "corroborated" if corroborated else "unresolved"
        accepted_uids = tuple(sorted(item["assessment_uid"] for item in accepted))
        claim_results.append({
            "claim_uid": claim_uid, "verdict": verdict,
            "risk": str(claim.get("risk") or "P2"),
            "required_publishers": required_publishers,
            "publisher_groups": tuple(sorted(groups)),
            "accepted_assessment_uids": accepted_uids,
            "action": "add_context" if corroborated else "do_not_publish_research",
        })
        if conflicted:
            conflicts.append({
                "conflict_uid": _research_uid("conflict", claim_uid),
                "subject_uid": claim_uid, "assessment_uids": accepted_uids,
            })
        if not corroborated:
            unresolved.append({"subject_uid": claim_uid, "reason": "insufficient_independent_validation"})

    required_unresolved = any(
        item["verdict"] != "corroborated" and bool(claims[item["claim_uid"]].get("required_for_publication"))
        for item in claim_results
    )
    validated = {
        "sources": tuple(sources.values()),
        "quotes": tuple(quotes.values()),
        "claim_source_assessments": tuple(assessments.values()),
        "claim_results": tuple(claim_results),
        "entity_results": (), "research_claims": (), "knowledge_expansions": (),
        "audit_metadata": {
            "validator_version": "research-validator/1",
            "adjudicator_version": "research-adjudicator/1",
            "rejection_summary": rejection_summary,
        },
    }
    # bundle_id binds to the canonical (order-independent) validated payload,
    # never to run.raw_hash which is sensitive to candidate input order.
    legacy_key = semantic_sha256({
        "sources": _sorted_records(tuple(sources.values()), "source_uid"),
        "assessments": _sorted_records(tuple(assessments.values()), "assessment_uid"),
        "claim_results": _sorted_records(tuple(claim_results), "claim_uid"),
    })
    # required_unresolved participates in coverage only; S5A publication is
    # unconditionally blocked until A2 opens adjudication.
    _ = required_unresolved
    bundle = ResearchBundle(
        schema_version=RESEARCH_BUNDLE_SCHEMA_VERSION,
        bundle_id=bundle_id or _research_uid("bundle", plan.plan_semantic_hash, legacy_key),
        plan_id=plan.plan_id,
        plan_semantic_hash=plan.plan_semantic_hash,
        evidence_bundle_hash=plan.evidence_bundle_hash,
        claim_bundle_hash=plan.claim_bundle_hash,
        attempted=run.attempted, executed=run.executed,
        status=run.status if run.status in RESEARCH_STATUSES else "invalid",
        publication_disposition="block",  # S5A: adjudication opens in A2
        started_at=started_at or plan.created_at,
        completed_at=completed_at or plan.created_at,
        wrr_version=wrr_version,
        execution={**dict(run.execution), "route_trace": run.route_trace},
        raw_research=run.raw_research,
        validated_research=validated,
        coverage={
            "claims_total": len(claim_results),
            "claims_corroborated": sum(item["verdict"] == "corroborated" for item in claim_results),
        },
        conflicts=tuple(conflicts), unresolved=tuple(unresolved), errors=run.errors,
        rule_versions={"validator": "1", "adjudicator": "1"},
    )
    return finalize_research_bundle(bundle)


def research_projection_semantic_payload(
    projection: ResearchProjectionPlan,
) -> Mapping[str, object]:
    return {
        "schema_version": projection.schema_version,
        "projector_version": projection.projector_version,
        "input_hashes": {
            "evidence_bundle_hash": projection.evidence_bundle_hash,
            "claim_bundle_hash": projection.claim_bundle_hash,
            "research_bundle_hash": projection.research_bundle_hash,
            "report_plan_hash": projection.report_plan_hash,
        },
        "report_mode": projection.report_mode,
        "section_budgets": projection.section_budgets,
        "entries": sorted(projection.entries, key=_projection_sort_key),
        "omissions": _sorted_records(projection.omissions, "object_uid"),
    }


def _validate_projection_shape(projection: ResearchProjectionPlan) -> None:
    if projection.schema_version != RESEARCH_PROJECTION_SCHEMA_VERSION:
        raise ResearchContractViolation("ResearchProjectionPlan schema_version 不兼容")
    if projection.report_mode not in REPORT_MODES:
        raise ResearchContractViolation("ResearchProjectionPlan report_mode 非法")
    for name, value in (
        ("evidence_bundle_hash", projection.evidence_bundle_hash),
        ("claim_bundle_hash", projection.claim_bundle_hash),
        ("research_bundle_hash", projection.research_bundle_hash),
        ("report_plan_hash", projection.report_plan_hash),
    ):
        _require_hash(value, name)
    if not (projection.projection_id and projection.projector_version):
        raise ResearchContractViolation("ResearchProjectionPlan 身份字段不得为空")
    _assert_no_sensitive_payload(projection)


def finalize_research_projection(
    projection: ResearchProjectionPlan,
) -> ResearchProjectionPlan:
    _validate_projection_shape(projection)
    return replace(
        projection,
        projection_semantic_hash=semantic_sha256(
            research_projection_semantic_payload(projection)
        ),
    )


def validate_research_projection(projection: ResearchProjectionPlan) -> None:
    _validate_projection_shape(projection)
    expected = semantic_sha256(research_projection_semantic_payload(projection))
    if projection.projection_semantic_hash != expected:
        raise ResearchContractViolation("projection_semantic_hash 不匹配")


__all__ = [
    "RESEARCH_PLAN_SCHEMA_VERSION",
    "RESEARCH_BUNDLE_SCHEMA_VERSION",
    "RESEARCH_PROJECTION_SCHEMA_VERSION",
    "RAW_RESEARCH_RUN_SCHEMA_VERSION",
    "RESEARCH_STATUSES",
    "RESEARCH_VALIDATOR_RULE_VERSION",
    "RESEARCH_ADJUDICATOR_RULE_VERSION",
    "RESEARCH_FRESHNESS_RULE_VERSION",
    "RESEARCH_SUITABILITY_RULE_VERSION",
    "RESEARCH_INDEPENDENCE_RULE_VERSION",
    "RESEARCH_POLICIES",
    "REPORT_MODES",
    "PUBLICATION_DISPOSITIONS",
    "ResearchContractViolation",
    "ResearchBudget",
    "ResearchPlan",
    "RawResearchRun",
    "ResearchBundle",
    "ResearchProjectionPlan",
    "research_plan_semantic_payload",
    "finalize_research_plan",
    "validate_research_plan",
    "raw_research_run_payload",
    "finalize_raw_research_run",
    "validate_raw_research_run",
    "research_bundle_raw_payload",
    "research_bundle_validated_payload",
    "research_bundle_audit_payload",
    "finalize_research_bundle",
    "validate_research_bundle",
    "validate_and_adjudicate_research",
    "canonical_research_url",
    "research_content_hash",
    "research_projection_semantic_payload",
    "finalize_research_projection",
    "validate_research_projection",
    "canonical_json_bytes",
]
