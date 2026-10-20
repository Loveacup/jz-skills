#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6a ResearchProjectionPlan builder + deterministic materializer.

Pure module — no network or filesystem I/O. It consumes a single finalized and
validated :class:`ResearchBundle` and produces distinct sparse/condensed/full
``ResearchProjectionPlan`` artifacts without mutating the bundle.

Design invariants:
- The plan binds ``evidence_bundle_hash``, ``claim_bundle_hash``,
  ``bundle.validated_semantic_hash`` (as ``research_bundle_hash``),
  ``report_plan_hash`` and ``report_mode``.
- Plan entries carry only UIDs / purpose / policy / template / budgets — never
  copied free-form research prose. Ordering and UIDs are stable, and
  ``projection_id`` / ``created_at`` are excluded from the semantic hash.
- Objects that are eligible but exceed a cap get a stable omission record with a
  reason; they are never silently dropped.
- A separate materializer resolves plan entries against the bundle into
  structured per-section records with deterministic ``[R#]`` / ``[S#]`` citation
  labels. It may read display text from the validated bundle; the plan itself
  may not copy that prose. Broken object / RC / quote references fail closed.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import research_contract as rc


PROJECTOR_VERSION = "research-projector/1"

# Sparse budgets are normative (spec §11.2). Condensed/full loosen them so the
# three projections are genuinely distinct while sharing the bundle hash.
MODE_SECTION_BUDGETS: Mapping[str, Mapping[str, Mapping[str, int]]] = {
    "sparse": {
        "3": {"max_research_items": 1, "max_chars": 220},
        "4": {"max_research_items": 1, "max_chars": 320},
        "6": {"max_entities": 3, "max_edges": 2, "max_chars": 260},
        "7": {"max_research_items": 1, "max_chars": 180},
        "report_caps": {"max_rc": 4, "max_kx": 2},
    },
    "condensed": {
        "3": {"max_research_items": 2, "max_chars": 600},
        "4": {"max_research_items": 3, "max_chars": 900},
        "6": {"max_entities": 6, "max_edges": 4, "max_chars": 700},
        "7": {"max_research_items": 2, "max_chars": 500},
        "report_caps": {"max_rc": 8, "max_kx": 4},
    },
    "full": {
        "3": {"max_research_items": 4, "max_chars": 1200},
        "4": {"max_research_items": 6, "max_chars": 1800},
        "6": {"max_entities": 12, "max_edges": 8, "max_chars": 1400},
        "7": {"max_research_items": 4, "max_chars": 1000},
        "report_caps": {"max_rc": 16, "max_kx": 8},
    },
}

# research_claims feed §3/§4/§7 (in priority order); §6 is the knowledge graph.
_RC_SECTIONS: Tuple[str, ...] = ("3", "4", "7")

_SECTION_PURPOSE = {
    "3": "surface_key_insight",
    "4": "deep_dive_support",
    "7": "critical_review",
}
_SECTION_TEMPLATE = {
    "3": "rc_key_insight",
    "4": "rc_deep_dive",
    "7": "rc_critical_review",
}


class ResearchProjectionError(Exception):
    """A projection artifact references objects absent from its bundle."""


def _entry_uid(*parts: object) -> str:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return f"pe_{digest[:24]}"


def _priority(record: Mapping[str, object]) -> float:
    value = record.get("priority", 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _sorted_by_priority(records: Sequence[Mapping[str, object]], uid_field: str):
    return sorted(records, key=lambda r: (-_priority(r), str(r.get(uid_field, ""))))


def _uids(record: Mapping[str, object], field: str) -> Tuple[str, ...]:
    values = record.get(field) or ()
    return tuple(sorted(str(v) for v in values))


def build_research_projection(
    bundle: rc.ResearchBundle,
    *,
    report_plan_hash: str,
    report_mode: str,
    projection_id: str = "",
    created_at: str = "",
    projector_version: str = PROJECTOR_VERSION,
) -> rc.ResearchProjectionPlan:
    """Project a validated bundle into a finalized ResearchProjectionPlan.

    The bundle is validated (never mutated); entries and omissions are derived
    deterministically for ``report_mode``. Only UIDs/policy/budgets enter the
    plan — no research prose.
    """
    rc.validate_research_bundle(bundle)
    if report_mode not in MODE_SECTION_BUDGETS:
        raise ResearchProjectionError(f"未知 report_mode: {report_mode!r}")

    budgets = MODE_SECTION_BUDGETS[report_mode]
    caps = budgets["report_caps"]
    vr = bundle.validated_research

    research_claims = list(vr.get("research_claims", ()) or ())
    claim_results = list(vr.get("claim_results", ()) or ())
    entity_results = list(vr.get("entity_results", ()) or ())
    knowledge_expansions = list(vr.get("knowledge_expansions", ()) or ())

    entries: List[Dict[str, object]] = []
    omissions: List[Dict[str, object]] = []

    # ── research_claims → §3/§4/§7, honoring per-section and report-wide caps ──
    rc_sorted = _sorted_by_priority(research_claims, "research_claim_uid")
    rc_cap = int(caps["max_rc"])
    used_rc = 0
    section_index = 0
    placed_rc = 0
    for claim in rc_sorted:
        placed = False
        while section_index < len(_RC_SECTIONS) and used_rc < rc_cap:
            section = _RC_SECTIONS[section_index]
            section_max = int(budgets[section]["max_research_items"])
            in_section = sum(
                1 for e in entries
                if e["target_section"] == section and e["object_type"] == "research_claim"
            )
            if in_section >= section_max:
                section_index += 1
                continue
            uid = str(claim.get("research_claim_uid", ""))
            entries.append({
                "entry_uid": _entry_uid("rc", section, uid),
                "target_section": section,
                "object_type": "research_claim",
                "object_uid": uid,
                "purpose": _SECTION_PURPOSE[section],
                "priority": _priority(claim),
                "required_video_evidence_uids": _uids(claim, "video_evidence_uids"),
                "allowed_research_claim_uids": (uid,),
                "allowed_quote_uids": _uids(claim, "supporting_quote_uids"),
                "deterministic_template_id": _SECTION_TEMPLATE[section],
                "max_chars": int(budgets[section]["max_chars"]),
                "citation_policy": "inline_required",
                "optional": False,
            })
            used_rc += 1
            placed_rc += 1
            placed = True
            break
        if not placed:
            reason = "report_rc_cap" if used_rc >= rc_cap else "section_capacity"
            omissions.append({
                "object_uid": str(claim.get("research_claim_uid", "")),
                "object_type": "research_claim",
                "reason": reason,
            })

    # ── adjudicated video-claim results → remaining §3/§4/§7 capacity ──
    projected_claim_results = [
        item for item in claim_results
        if str(item.get("publication_action") or "") in {"keep", "qualify"}
        and str(item.get("verdict") or "") not in {"", "unresolved"}
    ]
    projected_claim_results.sort(key=lambda item: str(item.get("claim_uid") or ""))
    for result in projected_claim_results:
        uid = str(result.get("claim_uid") or "")
        placed = False
        for section in _RC_SECTIONS:
            section_max = int(budgets[section]["max_research_items"])
            in_section = sum(
                1 for entry in entries if entry["target_section"] == section
                and entry["object_type"] in {"research_claim", "claim_result"}
            )
            if in_section >= section_max:
                continue
            entries.append({
                "entry_uid": _entry_uid("claim-result", section, uid),
                "target_section": section,
                "object_type": "claim_result",
                "object_uid": uid,
                "purpose": "verify_video_claim",
                "priority": _priority(result),
                "required_video_evidence_uids": _uids(
                    result, "video_evidence_uids"
                ),
                "allowed_research_claim_uids": (),
                "allowed_quote_uids": _uids(result, "supporting_quote_uids"),
                "deterministic_template_id": "claim_result_status",
                "max_chars": int(budgets[section]["max_chars"]),
                "citation_policy": "inline_required",
                "optional": False,
            })
            placed = True
            break
        if not placed:
            omissions.append({
                "object_uid": uid,
                "object_type": "claim_result",
                "reason": "section_capacity",
            })

    for result in claim_results:
        action = str(result.get("publication_action") or "")
        verdict = str(result.get("verdict") or "")
        if action in {"keep", "qualify"} and verdict not in {"", "unresolved"}:
            continue
        omissions.append({
            "object_uid": str(result.get("claim_uid") or ""),
            "object_type": "claim_result",
            "reason": "publication_block" if action == "block" else "publication_drop",
        })

    # ── entities → §6 nodes ──
    ent_max = int(budgets["6"]["max_entities"])
    for idx, ent in enumerate(_sorted_by_priority(entity_results, "entity_uid")):
        uid = str(ent.get("entity_uid", ""))
        if idx < ent_max:
            src = str(ent.get("source_uid", "") or "")
            entries.append({
                "entry_uid": _entry_uid("ent", "6", uid),
                "target_section": "6",
                "object_type": "entity_result",
                "object_uid": uid,
                "purpose": "knowledge_graph_node",
                "priority": _priority(ent),
                "required_video_evidence_uids": _uids(ent, "video_evidence_uids"),
                "allowed_research_claim_uids": _uids(ent, "research_claim_uids"),
                "allowed_quote_uids": _uids(ent, "quote_uids"),
                "deterministic_template_id": "kg_node",
                "max_chars": int(budgets["6"]["max_chars"]),
                "citation_policy": "inline_required" if src else "none",
                "optional": True,
            })
        else:
            omissions.append({
                "object_uid": uid,
                "object_type": "entity_result",
                "reason": "section_entity_cap",
            })

    # ── knowledge_expansions → §6 edges, honoring §6 max_edges + report kx cap ──
    edge_cap = min(int(budgets["6"]["max_edges"]), int(caps["max_kx"]))
    for idx, kx in enumerate(_sorted_by_priority(knowledge_expansions, "expansion_uid")):
        uid = str(kx.get("expansion_uid", ""))
        if idx < edge_cap:
            entries.append({
                "entry_uid": _entry_uid("kx", "6", uid),
                "target_section": "6",
                "object_type": "knowledge_expansion",
                "object_uid": uid,
                "purpose": "knowledge_graph_edge",
                "priority": _priority(kx),
                "required_video_evidence_uids": _uids(kx, "video_evidence_uids"),
                "allowed_research_claim_uids": _uids(kx, "research_claim_uids"),
                "allowed_quote_uids": _uids(kx, "quote_uids"),
                "deterministic_template_id": "kg_edge",
                "max_chars": int(budgets["6"]["max_chars"]),
                "citation_policy": "inline_required",
                "optional": True,
            })
        else:
            omissions.append({
                "object_uid": uid,
                "object_type": "knowledge_expansion",
                "reason": "report_kx_cap",
            })

    projection = rc.ResearchProjectionPlan(
        schema_version=rc.RESEARCH_PROJECTION_SCHEMA_VERSION,
        projection_id=projection_id or _entry_uid("proj", bundle.validated_semantic_hash, report_mode),
        created_at=created_at,
        projector_version=projector_version,
        evidence_bundle_hash=bundle.evidence_bundle_hash,
        claim_bundle_hash=bundle.claim_bundle_hash,
        research_bundle_hash=bundle.validated_semantic_hash,
        report_plan_hash=report_plan_hash,
        report_mode=report_mode,
        section_budgets=budgets,
        entries=tuple(entries),
        omissions=tuple(omissions),
    )
    projection = rc.finalize_research_projection(projection)
    rc.validate_research_projection(projection)
    return projection


def _index_by(records: Sequence[Mapping[str, object]], uid_field: str) -> Dict[str, Mapping[str, object]]:
    out: Dict[str, Mapping[str, object]] = {}
    for record in records or ():
        uid = str(record.get(uid_field, ""))
        if uid:
            out[uid] = record
    return out


def materialize_research_projection(
    projection: rc.ResearchProjectionPlan,
    bundle: rc.ResearchBundle,
) -> Dict[str, List[Dict[str, object]]]:
    """Resolve a projection's entries against its bundle into section records.

    Returns a mapping ``section -> [record, ...]`` where each record carries a
    deterministic ``[R#]`` / ``[S#]`` citation label plus display text read from
    the validated bundle. Fails closed on any unresolved object/RC/quote ref or
    a bundle whose ``validated_semantic_hash`` does not match the projection.
    """
    rc.validate_research_projection(projection)
    rc.validate_research_bundle(bundle)
    if projection.research_bundle_hash != bundle.validated_semantic_hash:
        raise ResearchProjectionError("projection 与 bundle 不匹配")

    vr = bundle.validated_research
    rc_map = _index_by(vr.get("research_claims", ()), "research_claim_uid")
    claim_result_map = _index_by(vr.get("claim_results", ()), "claim_uid")
    src_map = _index_by(vr.get("sources", ()), "source_uid")
    quote_map = _index_by(vr.get("quotes", ()), "quote_uid")
    ent_map = _index_by(vr.get("entity_results", ()), "entity_uid")
    kx_map = _index_by(vr.get("knowledge_expansions", ()), "expansion_uid")

    # Resolve every allowlisted UID before assigning labels. [R#]/[S#] are
    # source labels (research vs social/community), never research-claim labels.
    referenced_rc: set = set()
    referenced_quote: set = set()
    referenced_src: set = set()
    for entry in projection.entries:
        referenced_rc.update(
            _uids(entry, "allowed_research_claim_uids")
        )
        referenced_quote.update(_uids(entry, "allowed_quote_uids"))

    for uid in referenced_rc:
        if uid not in rc_map:
            raise ResearchProjectionError(f"未解析的 research_claim 引用: {uid}")
    for uid in referenced_quote:
        if uid not in quote_map:
            raise ResearchProjectionError(f"未解析的 quote 引用: {uid}")
        source_uid = str(quote_map[uid].get("source_uid") or "")
        if source_uid:
            referenced_src.add(source_uid)

    for entry in projection.entries:
        kind = str(entry.get("object_type") or "")
        uid = str(entry.get("object_uid") or "")
        if kind == "research_claim":
            if uid not in rc_map:
                raise ResearchProjectionError(f"未解析的 research_claim 对象: {uid}")
            referenced_src.update(_uids(rc_map[uid], "source_uids"))
        elif kind == "claim_result":
            if uid not in claim_result_map:
                raise ResearchProjectionError(f"未解析的 claim_result 对象: {uid}")
        elif kind == "entity_result":
            if uid not in ent_map:
                raise ResearchProjectionError(f"未解析的 entity_result 对象: {uid}")
            source_uid = str(ent_map[uid].get("source_uid") or "")
            if source_uid:
                referenced_src.add(source_uid)
        elif kind == "knowledge_expansion":
            if uid not in kx_map:
                raise ResearchProjectionError(f"未解析的 knowledge_expansion 对象: {uid}")
            referenced_src.update(_uids(kx_map[uid], "source_uids"))
        else:
            raise ResearchProjectionError(f"未知 object_type: {kind}")

    for uid in referenced_src:
        if uid not in src_map:
            raise ResearchProjectionError(f"未解析的 source 引用: {uid}")

    research_sources = sorted(
        uid for uid in referenced_src
        if str(src_map[uid].get("source_kind") or "research")
        not in {"social", "community", "forum"}
    )
    social_sources = sorted(set(referenced_src) - set(research_sources))
    source_label = {
        **{uid: f"[R{i + 1}]" for i, uid in enumerate(research_sources)},
        **{uid: f"[S{i + 1}]" for i, uid in enumerate(social_sources)},
    }
    rc_object_label = {
        uid: f"RC{i + 1}" for i, uid in enumerate(sorted(referenced_rc))
    }
    claim_result_label = {
        uid: f"C{i + 1}"
        for i, uid in enumerate(sorted(
            str(entry.get("object_uid") or "") for entry in projection.entries
            if entry.get("object_type") == "claim_result"
        ))
    }

    sections: Dict[str, List[Dict[str, object]]] = {}
    for entry in sorted(projection.entries, key=rc._projection_sort_key):
        section = str(entry["target_section"])
        kind = str(entry["object_type"])
        uid = str(entry["object_uid"])
        quote_uids = _uids(entry, "allowed_quote_uids")
        quote_texts = [str(quote_map[q].get("verbatim_quote", "")) for q in quote_uids]
        source_uids = {
            str(quote_map[q].get("source_uid") or "") for q in quote_uids
            if str(quote_map[q].get("source_uid") or "")
        }

        if kind == "research_claim":
            obj = rc_map[uid]
            source_uids.update(_uids(obj, "source_uids"))
            display_text = str(obj.get("statement", ""))
            object_label = rc_object_label[uid]
        elif kind == "claim_result":
            obj = claim_result_map[uid]
            verdict = str(obj.get("verdict") or "")
            display_text = {
                "supported": "外部来源支持该视频主张",
                "contradicted": "外部来源与该视频主张相矛盾",
                "mixed": "外部来源对该视频主张给出混合证据",
                "stale": "外部来源时效不足，需保留限定",
            }.get(verdict, "该视频主张已完成外部核查")
            qualifier = str(obj.get("qualifier") or "").strip()
            if obj.get("publication_action") == "qualify" and qualifier:
                display_text += f"（{qualifier}）"
            object_label = claim_result_label[uid]
        elif kind == "entity_result":
            obj = ent_map[uid]
            source_uid = str(obj.get("source_uid") or "")
            if source_uid:
                source_uids.add(source_uid)
            display_text = str(obj.get("label", ""))
            object_label = f"ENT-{uid}"
        else:
            obj = kx_map[uid]
            source_uids.update(_uids(obj, "source_uids"))
            display_text = str(obj.get("relation", ""))
            object_label = f"KX-{uid}"

        record = {
            "entry_uid": entry["entry_uid"],
            "target_section": section,
            "object_type": kind,
            "object_uid": uid,
            "object_label": object_label,
            "citation_labels": [source_label[s] for s in sorted(source_uids)],
            "display_text": display_text,
            "supporting_research_claim_labels": [
                rc_object_label[r]
                for r in _uids(entry, "allowed_research_claim_uids")
            ],
            "quote_texts": quote_texts,
            "purpose": entry.get("purpose"),
            "deterministic_template_id": entry.get("deterministic_template_id"),
        }
        sections.setdefault(section, []).append(record)

    return sections


__all__ = [
    "PROJECTOR_VERSION",
    "MODE_SECTION_BUDGETS",
    "ResearchProjectionError",
    "build_research_projection",
    "materialize_research_projection",
]
