# -*- coding: utf-8 -*-
"""S7: nine report-aware research publication gates."""

from dataclasses import replace

import pytest
import research_contract as rc
import research_projection as rp
from research_pipeline import build_research_plan
from verify_publishable_report import evaluate_publishable_report, evaluate_research_gates


def _markdown(extra=""):
    return (
        "## 0. 元信息\n\n### 视频元信息\n\n- **标题**：示例\n\n"
        "## 1. 逻辑链\n\n| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |\n"
        "| --- | --- | --- | --- | --- |\n| 0:00 | 起点 | 提出问题 | 示例 |  |\n\n"
        "## 2. 弹幕信号\n\n正文示例。\n\n## 2.5 评论\n\n正文示例。\n\n"
        "## 3. 核心洞察\n\n### 💡 洞察：外部核查\n\n"
        "视频主张已由外部资料核查，正文保持明确的证据边界和来源引用。\n\n"
        "### 外部研究补充\n\n- C1：外部来源支持该视频主张 [R1]"
        f"{extra}\n\n"
        "## 4. 深度拆解\n\n### 模块 1: 主要功能模块\n\n"
        "这个模块使用足够长的描述满足正式报告结构和最低内容门槛要求。\n\n"
        "## 5. 高光时刻\n\n> \"这是一个高光引用段落。\"\n\n"
        "## 6. 知识图谱\n\n- [[示例概念]]\n\n"
        "## 7. 批判与行动\n\n### 独特价值\n\n- 独特视角展示\n\n"
        "### 局限\n\n- 证据来源单一\n\n### 可行动\n\n- 保持核查。\n\n"
        "## 8. 附录\n\n正文示例。\n"
    )


def _report(*, social=False, stale=False, conflict=False, blocked=False,
            missing_archive=False, bad_summary_hash=False,
            corrupt_records=False, unbound_records=False, degraded=False,
            missing_qualifier=False, bad_coverage=False):
    claim_bundle = {
        "claim_bundle_semantic_hash": "sha256:claims",
        "claims": [{
            "claim_uid": "claim-1", "text": "视频主张", "risk": "P2",
            "temporal_class": "current" if stale else "stable",
        }],
    }
    plan = build_research_plan(
        evidence_bundle_hash="sha256:evidence",
        claim_bundle=claim_bundle,
        canonical_id="BVgate",
        platform="bilibili",
        report_mode="full",
        research_policy="auto",
        capability_snapshot={"available": True, "route": "fixture"},
        created_at="2026-07-14T00:00:00Z",
        plan_id="plan-gate",
    )
    source = {
        "source_uid": "src-1",
        "content_hash": "sha256:source",
        "title": "来源",
        "source_kind": "social" if social else "official",
    }
    quote = {
        "quote_uid": "quote-1",
        "source_uid": "src-1",
        "verbatim_quote": "外部资料支持该主张",
    }
    claim_result = {
        "claim_uid": "claim-1",
        "verdict": "stale" if stale else "supported",
        "publication_action": "qualify" if degraded else "keep",
        "qualifier": "需保留时效限定" if degraded and not missing_qualifier else "",
        "supporting_quote_uids": ("quote-1",),
        "confidence": 0.8,
    }
    bundle = rc.finalize_research_bundle(rc.ResearchBundle(
        schema_version=rc.RESEARCH_BUNDLE_SCHEMA_VERSION,
        bundle_id="bundle-gate",
        plan_id=plan.plan_id,
        plan_semantic_hash=plan.plan_semantic_hash,
        evidence_bundle_hash=plan.evidence_bundle_hash,
        claim_bundle_hash=plan.claim_bundle_hash,
        attempted=True,
        executed=True,
        status="blocked" if blocked else "completed",
        publication_disposition="block" if blocked else ("degraded" if degraded else "pass"),
        started_at="2026-07-14T00:00:00Z",
        completed_at="2026-07-14T00:00:01Z",
        wrr_version="fixture/1",
        execution={"query_count": 1},
        raw_research={"input_hashes": {
            "plan_semantic_hash": plan.plan_semantic_hash,
            "evidence_bundle_hash": plan.evidence_bundle_hash,
            "claim_bundle_hash": plan.claim_bundle_hash,
        }},
        validated_research={
            "sources": (source,),
            "quotes": (quote,),
            "claim_source_assessments": ({
                "assessment_uid": "assessment-1", "claim_uid": "claim-1",
                "source_uid": "src-1", "quote_uids": ("quote-1",),
                "suitability": "strong", "freshness_status": "fresh",
                "validated_relation": "supports",
            },),
            "claim_results": (claim_result,),
            "research_claims": (),
            "entity_results": (),
            "knowledge_expansions": (),
        },
        coverage={"verification": {
            "p0_total": 0, "p0_resolved": 0,
            "adopted_p1_total": 0, "adopted_p1_resolved": 0,
            "p2_total": 1, "p2_resolved": 0 if bad_coverage else 1,
            "p2_ratio": 0.0 if bad_coverage else 1.0,
            "gate_passed": not bad_coverage,
        }},
        conflicts=({"subject_uid": "claim-1", "reason": "source_conflict"},) if conflict else (),
        unresolved=(),
        errors=(),
        rule_versions={"validator": "1", "adjudicator": "1"},
    ))
    report_plan = {"mode": "full", "sections": []}
    projection = rp.build_research_projection(
        bundle,
        report_plan_hash=rc.semantic_sha256(report_plan),
        report_mode="full",
        projection_id="projection-gate",
        created_at="2026-07-14T00:00:02Z",
    )
    records = rp.materialize_research_projection(projection, bundle)
    if corrupt_records:
        records = {**records, "3": [{**records["3"][0], "display_text": "tampered"}]}
    if unbound_records:
        records = {**records, "3": [{**records["3"][0], "object_type": "research_claim",
                                       "object_uid": "rc-orphan"}]}
    artifacts = {
        "research_plan": plan,
        "research_bundle": bundle,
        "research_projection": projection,
        "research_projection_records": records,
    }
    if not missing_archive:
        artifacts.update({
            "archive_bundle_hash": bundle.audit_artifact_hash,
            "archive_source_hashes": ("sha256:source",),
        })
    return {
        "report_plan": report_plan,
        "research": {
            "status": bundle.status,
            "attempted": True,
            "executed": True,
            "validated_evidence_count": 1,
            "publication_disposition": bundle.publication_disposition,
            "validated_semantic_hash": (
                "sha256:bad" if bad_summary_hash else bundle.validated_semantic_hash
            ),
            "audit_artifact_hash": bundle.audit_artifact_hash,
        },
        "research_artifacts": artifacts,
    }


GATES = {
    "P0_RESEARCH_ARTIFACT_INTEGRITY",
    "P0_RESEARCH_REFERENCE_INTEGRITY",
    "P0_RESEARCH_CLAIM_BINDING",
    "P0_RESEARCH_SOURCE_SUITABILITY",
    "P0_RESEARCH_FRESHNESS",
    "P0_RESEARCH_CONFLICT",
    "P0_RESEARCH_COVERAGE",
    "P0_RESEARCH_PROJECTION_FIDELITY",
    "P0_RESEARCH_ARCHIVE_INTEGRITY",
    "P0_RESEARCH_PUBLIC_PATH_SAFETY",
}


def test_all_nine_research_gates_pass_and_are_publicly_observable():
    report = _report()
    research = evaluate_research_gates(_markdown(), report)
    assert set(research) == GATES
    assert all(gate["pass"] for gate in research.values())
    public, passed = evaluate_publishable_report(_markdown(), report)
    assert GATES <= set(public)
    assert passed is True


def test_artifact_integrity_rejects_summary_hash_mismatch():
    assert not evaluate_research_gates(_markdown(), _report(bad_summary_hash=True))[
        "P0_RESEARCH_ARTIFACT_INTEGRITY"]["pass"]


def test_reference_integrity_rejects_unknown_markdown_reference():
    assert not evaluate_research_gates(_markdown(" [R99]"), _report())[
        "P0_RESEARCH_REFERENCE_INTEGRITY"]["pass"]


def test_claim_binding_rejects_unanchored_research_text():
    assert not evaluate_research_gates(_markdown(), _report(unbound_records=True))[
        "P0_RESEARCH_CLAIM_BINDING"]["pass"]


def test_source_suitability_rejects_social_only_factual_support():
    assert not evaluate_research_gates(_markdown(), _report(social=True))[
        "P0_RESEARCH_SOURCE_SUITABILITY"]["pass"]


def test_freshness_rejects_stale_adopted_claim():
    assert not evaluate_research_gates(_markdown(), _report(stale=True))[
        "P0_RESEARCH_FRESHNESS"]["pass"]


def test_conflict_rejects_flattened_pass_disposition():
    assert not evaluate_research_gates(_markdown(), _report(conflict=True))[
        "P0_RESEARCH_CONFLICT"]["pass"]


def test_coverage_rejects_blocked_bundle():
    assert not evaluate_research_gates(_markdown(), _report(blocked=True))[
        "P0_RESEARCH_COVERAGE"
    ]["pass"]


def test_coverage_rejects_failed_verification_gate():
    assert not evaluate_research_gates(_markdown(), _report(bad_coverage=True))[
        "P0_RESEARCH_COVERAGE"
    ]["pass"]


def test_degraded_requires_nonempty_qualifier_for_retained_claim():
    assert not evaluate_research_gates(_markdown(), _report(
        degraded=True, missing_qualifier=True
    ))["P0_RESEARCH_COVERAGE"]["pass"]


def test_public_research_gate_rejects_private_absolute_path():
    gates = evaluate_research_gates(
        _markdown("\n/Users/alex/private/source.json"), _report()
    )
    assert not gates["P0_RESEARCH_PUBLIC_PATH_SAFETY"]["pass"]


def test_public_research_gate_does_not_mistake_url_for_private_path():
    gates = evaluate_research_gates(
        _markdown("\nhttps://example.com/Users/alex/reference"), _report()
    )
    assert gates["P0_RESEARCH_PUBLIC_PATH_SAFETY"]["pass"]


def test_public_research_gate_rejects_tmp_absolute_path():
    gates = evaluate_research_gates(_markdown("\n/tmp/private/source.json"), _report())
    assert not gates["P0_RESEARCH_PUBLIC_PATH_SAFETY"]["pass"]


def test_partial_research_artifacts_fail_closed_even_if_execution_flag_is_false():
    report = _report()
    report["research"]["executed"] = False
    report["research_artifacts"].pop("research_projection")
    gates = evaluate_research_gates(_markdown().replace("[R1]", ""), report)
    assert not gates["P0_RESEARCH_ARTIFACT_INTEGRITY"]["pass"]


def test_degraded_qualifier_must_be_visible_in_public_markdown():
    gates = evaluate_research_gates(_markdown(), _report(degraded=True))
    assert not gates["P0_RESEARCH_COVERAGE"]["pass"]
    gates = evaluate_research_gates(
        _markdown("\n需保留时效限定"), _report(degraded=True)
    )
    assert gates["P0_RESEARCH_COVERAGE"]["pass"]


def test_projection_fidelity_rejects_tampered_materialization():
    assert not evaluate_research_gates(_markdown(), _report(corrupt_records=True))[
        "P0_RESEARCH_PROJECTION_FIDELITY"
    ]["pass"]


def test_archive_integrity_requires_bundle_and_source_hashes():
    assert not evaluate_research_gates(_markdown(), _report(missing_archive=True))[
        "P0_RESEARCH_ARCHIVE_INTEGRITY"]["pass"]


@pytest.mark.parametrize("mode", ["full", "condensed"])
def test_final_markdown_claim_substitution_fails_even_with_retained_tags(mode):
    from video_analysis_engine import _render_research_projection_section
    report = _report()
    report["report_plan"]["mode"] = mode
    bundle = report["research_artifacts"]["research_bundle"]
    projection = rp.build_research_projection(
        bundle, report_plan_hash=rc.semantic_sha256(report["report_plan"]),
        report_mode=mode,
    )
    report["research_artifacts"]["research_projection"] = projection
    report["research_artifacts"]["research_projection_records"] = (
        rp.materialize_research_projection(projection, bundle)
    )
    block = _render_research_projection_section(report, "3")
    markdown = _markdown().replace(
        "### 外部研究补充\n\n- C1：外部来源支持该视频主张 [R1]", block
    )
    assert evaluate_research_gates(markdown, report)[
        "P0_RESEARCH_PROJECTION_FIDELITY"]["pass"]
    tampered = markdown.replace("外部来源支持该视频主张", "未经验证的新主张已被证实")
    assert not evaluate_research_gates(tampered, report)[
        "P0_RESEARCH_PROJECTION_FIDELITY"]["pass"]


@pytest.mark.parametrize("executed,referenced", [(False, False), (False, True), (True, False)])
def test_plan_only_degrades_safely_only_without_execution_or_citations(executed, referenced):
    report = _report()
    report["research"]["executed"] = executed
    report["research_artifacts"] = {
        "research_plan": report["research_artifacts"]["research_plan"]
    }
    gates = evaluate_research_gates("[R1]" if referenced else "仅视频证据", report)
    assert all(g["pass"] for g in gates.values()) is (not executed and not referenced)


def test_mixed_projection_renders_required_qualifier():
    from video_analysis_engine import _render_research_projection_section
    report = _report(degraded=True)
    artifacts = report["research_artifacts"]
    bundle = artifacts["research_bundle"]
    result = dict(bundle.validated_research["claim_results"][0])
    result.update(verdict="mixed", qualifier="conflicting_evidence")
    bundle = rc.finalize_research_bundle(replace(
        bundle, validated_research={**bundle.validated_research, "claim_results": (result,)}
    ))
    artifacts["research_bundle"] = bundle
    projection = rp.build_research_projection(
        bundle, report_plan_hash=rc.semantic_sha256(report["report_plan"]), report_mode="full"
    )
    artifacts["research_projection"] = projection
    artifacts["research_projection_records"] = rp.materialize_research_projection(projection, bundle)
    markdown = _render_research_projection_section(report, "3")
    assert "conflicting_evidence" in markdown
    assert evaluate_research_gates(markdown, report)["P0_RESEARCH_COVERAGE"]["pass"]
