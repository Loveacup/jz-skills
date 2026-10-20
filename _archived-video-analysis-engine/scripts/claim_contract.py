#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure serialized ClaimBundle contract used before WRR research planning."""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from typing import Any, Dict, Mapping, Sequence

from evidence_contract import semantic_sha256


CLAIM_BUNDLE_SCHEMA_VERSION = "claim-bundle/1.0"
_CLAIM_LOCATION_RE = re.compile(r"^[0-9]+:E[1-9][0-9]*$")
_AUDIENCE_SOURCES = {"comment", "comments", "danmaku", "audience"}
_VALID_SOURCES = _AUDIENCE_SOURCES | {"transcript", "metadata", "external"}
_VALID_CLAIM_TYPES = {"observed", "inferred", "recommendation"}
_PRIVATE_KEYS = {
    "authorization", "cookie", "cookies", "headers", "token", "access_token",
    "refresh_token", "api_key", "apikey", "raw_response", "raw_payload",
}
_SECRET_MARKERS = (
    "bearer ", "cookie=", "token=", "access_token=", "refresh_token=",
    "api_key=", "x-amz-signature=", "x-goog-signature=",
)


class ClaimContractViolation(ValueError):
    """Serialized ClaimBundle violates identity, evidence, or safety rules."""


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _uid(prefix: str, parts: Sequence[str]) -> str:
    material = "|".join(parts).encode("utf-8")
    return f"{prefix}_" + hashlib.sha256(material).hexdigest()[:24]


def _sequence_field(value: Mapping[str, object], name: str) -> Sequence[object]:
    raw = value.get(name)
    return raw if isinstance(raw, (tuple, list)) else ()


def _contract_version(value: Mapping[str, object]) -> int:
    raw = value.get("evidence_contract_version", 1)
    return raw if isinstance(raw, int) else 1


def stable_claim_uid(claim: Mapping[str, object]) -> str:
    claim_type = str(claim.get("claim_type") or "observed")
    text = _normalized_text(claim.get("text"))
    locations = sorted(str(item) for item in _sequence_field(claim, "evidence_locations"))
    return _uid("claim", (claim_type, text, *locations))


def stable_insight_uid(insight: Mapping[str, object], claim_uid: str) -> str:
    return _uid(
        "insight",
        (
            claim_uid,
            str(insight.get("target_section") or ""),
            _normalized_text(insight.get("text")),
        ),
    )


def _assert_safe(value: object, path: str = "claim_bundle") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _PRIVATE_KEYS:
                raise ClaimContractViolation(f"{path} contains private field {key!r}")
            _assert_safe(nested, f"{path}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, nested in enumerate(value):
            _assert_safe(nested, f"{path}[{index}]")
        return
    if isinstance(value, str) and any(marker in value.lower() for marker in _SECRET_MARKERS):
        raise ClaimContractViolation(f"{path} contains credential material")


def _assert_no_placeholder(value: object, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _assert_no_placeholder(nested, f"{path}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, nested in enumerate(value):
            _assert_no_placeholder(nested, f"{path}[{index}]")
        return
    if isinstance(value, str) and (
        "placeholder" in value.lower() or "待填证据" in value
    ):
        raise ClaimContractViolation(f"{path} contains placeholder marker")


def _strip_display_fields(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_display_fields(nested)
            for key, nested in value.items()
            if str(key) not in {"id", "display_id", "claim_id", "insight_id", "evidence_ids"}
        }
    if isinstance(value, (tuple, list)):
        return [_strip_display_fields(item) for item in value]
    return value


def _risk_for_claim(claim: Mapping[str, object], source_type: str) -> str:
    if source_type in _AUDIENCE_SOURCES:
        return "P3"
    text = _normalized_text(claim.get("text"))
    if re.search(r"医疗|药物|剂量|法律|投资|安全漏洞|死亡|致命|危险", text):
        return "P0"
    if re.search(r"\d|今天|目前|当前|最新|排名|唯一|最好|最高|最低|版本", text):
        return "P1"
    return "P2"


def _canonical_locations(record: Mapping[str, object]) -> list[str]:
    raw = record.get("evidence_locations") or ()
    if not isinstance(raw, (tuple, list)) or not raw:
        raise ClaimContractViolation("evidence_locations must be non-empty")
    locations = sorted({str(item) for item in raw})
    if len(locations) != len(raw) or any(not _CLAIM_LOCATION_RE.match(item) for item in locations):
        raise ClaimContractViolation("evidence_locations must be unique canonical section:E# pointers")
    return locations


def _finalize_claim(record: Mapping[str, object]) -> Dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ClaimContractViolation("claim record must be a mapping")
    claim = copy.deepcopy(dict(record))
    _assert_no_placeholder(claim, "claim")
    claim["text"] = _normalized_text(claim.get("text"))
    if not claim["text"]:
        raise ClaimContractViolation("claim text must be non-empty")
    source_type = str(claim.get("source_type") or "")
    claim_type = str(claim.get("claim_type") or "observed")
    if source_type not in _VALID_SOURCES:
        raise ClaimContractViolation(f"unsupported source_type: {source_type!r}")
    if claim_type not in _VALID_CLAIM_TYPES:
        raise ClaimContractViolation(f"unsupported claim_type: {claim_type!r}")
    claim["evidence_locations"] = _canonical_locations(claim)
    computed_uid = stable_claim_uid(claim)
    if claim.get("claim_uid") not in (None, "", computed_uid):
        raise ClaimContractViolation("claim_uid does not match canonical claim content")
    claim["claim_uid"] = computed_uid
    claim["risk"] = _risk_for_claim(claim, source_type)
    claim["support_scope"] = (
        "audience_signal" if source_type in _AUDIENCE_SOURCES
        else "external_evidence" if source_type == "external"
        else "video_evidence"
    )
    return claim


def _claim_match_key(record: Mapping[str, object]) -> tuple[str, tuple[str, ...]]:
    return (
        _normalized_text(record.get("text")),
        tuple(_canonical_locations(record)),
    )


def _finalize_insight(
    record: Mapping[str, object],
    claims_by_key: Mapping[tuple[str, tuple[str, ...]], Mapping[str, object]],
) -> Dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ClaimContractViolation("insight record must be a mapping")
    insight = copy.deepcopy(dict(record))
    _assert_no_placeholder(insight, "insight")
    insight["text"] = _normalized_text(insight.get("text"))
    insight["evidence_locations"] = _canonical_locations(insight)
    parent = claims_by_key.get(_claim_match_key(insight))
    if parent is None:
        raise ClaimContractViolation("insight must resolve to a grounded claim")
    claim_uid = str(parent["claim_uid"])
    computed_uid = stable_insight_uid(insight, claim_uid)
    if insight.get("insight_uid") not in (None, "", computed_uid):
        raise ClaimContractViolation("insight_uid does not match canonical insight content")
    insight["claim_uid"] = claim_uid
    insight["insight_uid"] = computed_uid
    insight["support_scope"] = parent["support_scope"]
    insight["risk"] = parent["risk"]
    return insight


def claim_bundle_semantic_payload(bundle: Mapping[str, object]) -> Mapping[str, object]:
    semantic_claims = []
    for claim in _sequence_field(bundle, "claims"):
        if not isinstance(claim, Mapping):
            raise ClaimContractViolation("claim record must be a mapping")
        semantic_claims.append({
            key: value for key, value in claim.items()
            if key not in {"id", "evidence_ids"}
        })
    semantic_insights = []
    for insight in _sequence_field(bundle, "insights"):
        if not isinstance(insight, Mapping):
            raise ClaimContractViolation("insight record must be a mapping")
        semantic_insights.append({
            key: value for key, value in insight.items()
            if key not in {"id", "evidence_ids"}
        })
    return {
        "schema_version": CLAIM_BUNDLE_SCHEMA_VERSION,
        "evidence_contract_version": _contract_version(bundle),
        "claims": sorted(semantic_claims, key=lambda item: str(item.get("claim_uid", ""))),
        "insights": sorted(semantic_insights, key=lambda item: str(item.get("insight_uid", ""))),
        "audit_log": _strip_display_fields(_sequence_field(bundle, "audit_log")),
    }


def finalize_claim_bundle_dict(payload: Mapping[str, object]) -> Dict[str, Any]:
    """Return a defensive, validated, content-addressed serialized artifact."""
    if not isinstance(payload, Mapping):
        raise ClaimContractViolation("ClaimBundle payload must be a mapping")
    _assert_safe(payload)
    raw_claims = payload.get("claims") or ()
    raw_insights = payload.get("insights") or ()
    if not isinstance(raw_claims, (tuple, list)) or not isinstance(raw_insights, (tuple, list)):
        raise ClaimContractViolation("claims and insights must be lists")

    claims = [_finalize_claim(item) for item in raw_claims]
    claim_uids = [str(item["claim_uid"]) for item in claims]
    if len(set(claim_uids)) != len(claim_uids):
        raise ClaimContractViolation("duplicate claim_uid")
    claims_by_key = {_claim_match_key(item): item for item in claims}

    insights = [_finalize_insight(item, claims_by_key) for item in raw_insights]
    insight_uids = [str(item["insight_uid"]) for item in insights]
    if len(set(insight_uids)) != len(insight_uids):
        raise ClaimContractViolation("duplicate insight_uid")

    result: Dict[str, Any] = {
        "schema_version": CLAIM_BUNDLE_SCHEMA_VERSION,
        "evidence_contract_version": _contract_version(payload),
        "claims": claims,
        "insights": insights,
        "audit_log": copy.deepcopy(list(_sequence_field(payload, "audit_log"))),
    }
    result["claim_bundle_semantic_hash"] = semantic_sha256(
        claim_bundle_semantic_payload(result)
    )
    _assert_safe(result)
    return result


def validate_claim_bundle_dict(bundle: Mapping[str, object]) -> None:
    if bundle.get("schema_version") != CLAIM_BUNDLE_SCHEMA_VERSION:
        raise ClaimContractViolation("unsupported ClaimBundle schema_version")
    expected = finalize_claim_bundle_dict(bundle)
    if bundle.get("claim_bundle_semantic_hash") != expected["claim_bundle_semantic_hash"]:
        raise ClaimContractViolation("claim_bundle_semantic_hash mismatch")


__all__ = [
    "CLAIM_BUNDLE_SCHEMA_VERSION",
    "ClaimContractViolation",
    "stable_claim_uid",
    "stable_insight_uid",
    "claim_bundle_semantic_payload",
    "finalize_claim_bundle_dict",
    "validate_claim_bundle_dict",
]
