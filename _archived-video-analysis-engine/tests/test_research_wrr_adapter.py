# -*- coding: utf-8 -*-
"""HermesWRRAdapter raw-output contract: discovery metadata passthrough.

Guards the narrow allowlist seam in ``HermesWRRAdapter._candidate``. The
validator/adjudicator in S5 reads ``authority_relation`` off each raw candidate
to compute independence groups; if the adapter drops the field the fixture's
``independent`` source becomes unusable and coverage fails closed. This test
pins that primary/independent candidates keep ``authority_relation`` verbatim
across the adapter's raw output.
"""
import research_pipeline as rp


def _claims():
    return {
        "schema_version": "claim-bundle/1.0",
        "claim_bundle_semantic_hash": "sha256:claims",
        "claims": [{"claim_uid": "claim-1", "risk": "P1", "text": "当前排名第一",
                    "evidence_locations": ["3:E1"], "support_scope": "video_evidence"}],
        "insights": [], "audit_log": [],
    }


def _plan():
    return rp.build_research_plan(
        evidence_bundle_hash="sha256:evidence", claim_bundle=_claims(),
        canonical_id="BV1", platform="bilibili", report_mode="full",
        research_policy="auto",
        capability_snapshot={"available": True, "route": "hermes_wrr", "checked_at": "now"},
        created_at="2026-07-14T00:00:00Z", plan_id="rp-fixed",
        topic_hints=("检索增强生成",),
    )


def test_adapter_preserves_authority_relation_for_primary_and_independent():
    from research_wrr_adapter import HermesWRRAdapter

    plan = _plan()

    def executor(query):
        # WRR-owned raw discovery output: one primary + one independent source.
        return {"candidates": [
            {"url": "https://primary.example/a", "content": "甲",
             "authority_relation": "primary"},
            {"url": "https://independent.example/b", "content": "乙",
             "authority_relation": "independent"},
        ]}

    raw = HermesWRRAdapter(executor).execute(plan)
    candidates = raw.raw_research["candidates"]

    relations = {c["url"]: c.get("authority_relation") for c in candidates}
    assert relations["https://primary.example/a"] == "primary"
    assert relations["https://independent.example/b"] == "independent"
