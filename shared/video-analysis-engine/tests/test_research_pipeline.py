#!/usr/bin/env python3
"""S4 WRR adapter and main orchestration boundary."""
from dataclasses import replace

import generate_report as gr
import research_contract as rc
import research_pipeline as rp


def _results(tmp_path):
    jp = tmp_path / "BVcompat_subtitle.json"
    jp.write_text(
        '{"body":[{"from":0,"to":2,"content":"开场介绍核心观点"},'
        '{"from":2,"to":5,"content":"进一步解释方法和价值"},'
        '{"from":5,"to":8,"content":"总结对观众的启发"}]}',
        encoding="utf-8",
    )
    return {
        "bvid": "BVcompat",
        "title": "backward compat",
        "subtitle": {"method": "official", "json_path": str(jp), "language": "zh"},
        "comments": {"hot_comments": [{"content": "这个观点很有启发", "like": 10, "user": {"name": "u"}}]},
        "danmaku": {"data": [{"text": "学到了", "time_sec": 3}]},
    }


def _plan():
    return rp.build_research_plan(
        evidence_bundle_hash="sha256:evidence",
        claim_bundle={"claim_bundle_semantic_hash": "sha256:claims", "claims": []},
        canonical_id="BV1", platform="bilibili", report_mode="sparse",
        research_policy="auto",
        capability_snapshot={"available": True, "route": "hermes_wrr"},
        created_at="2026-07-14T00:00:00Z", plan_id="rp-s4",
        topic_hints=("检索增强",),
    )


def _report():
    return {
        "frontmatter": {"video_id": "BV1", "platform": "bilibili"},
        "report_plan": {"mode": "sparse"},
        "claim_bundle": {"claim_bundle_semantic_hash": "sha256:claims", "claims": []},
        "sections": {"§3 评论分析": "baseline"},
    }


def _context():
    return {
        "evidence_bundle_hash": "sha256:evidence",
        "created_at": "2026-07-14T00:00:00Z",
        "plan_id": "rp-s4",
        "capability_snapshot": {"available": True, "route": "hermes_wrr"},
        "topic_hints": ("检索增强",),
    }


def test_adapter_passes_declared_modes_once_and_keeps_snippets_raw_only():
    from research_wrr_adapter import HermesWRRAdapter
    calls = []
    def executor(query):
        calls.append(dict(query))
        return {"candidates": [{"url": "https://example.com", "snippet": "search-only",
                                 "quote_candidates": [{"quote_text": "raw candidate only"}],
                                 "quotes": [{"verbatim_quote": "must be stripped"}],
                                 "validated_research": {"sources": ["must not pass"]}}]}
    plan = _plan()
    raw = rp.execute_research_once(plan, HermesWRRAdapter(executor))
    assert [call["mode"] for call in calls] == [query["mode"] for query in plan.queries]
    assert len(calls) == len(plan.queries)
    candidate = raw.raw_research["candidates"][0]
    assert candidate["validation_status"] == "untrusted"
    assert candidate["snippet_only"] is True
    assert candidate["quote_candidates"][0]["quote_text"] == "raw candidate only"
    # ``quotes`` is the canonical *untrusted* raw-run bridge consumed by S5;
    # it mirrors discovery-facing quote_candidates and never promotes evidence.
    assert candidate["quotes"] == candidate["quote_candidates"]
    assert "validated_research" not in candidate
    assert raw.validated_evidence_count == 0
    assert raw.raw_research["input_hashes"] == {
        "plan_semantic_hash": plan.plan_semantic_hash,
        "evidence_bundle_hash": plan.evidence_bundle_hash,
        "claim_bundle_hash": plan.claim_bundle_hash,
    }
    assert set(raw.execution) >= {
        "query_count", "fetch_count", "source_count", "elapsed_seconds",
        "topic_count", "knowledge_expansion_count", "research_claim_count",
        "started_at", "completed_at",
    }
    # Fetches count raw discovery candidates; source_count counts materializable
    # canonical sources, and snippet-only candidates have no content hash.
    assert raw.execution["fetch_count"] == len(raw.raw_research["candidates"])
    assert raw.execution["source_count"] == 0
    assert candidate["candidate_uid"].startswith("cand_")


def test_adapter_does_not_retry_failed_query_and_bounds_safe_errors():
    from research_wrr_adapter import HermesWRRAdapter
    calls = []
    def executor(query):
        calls.append(query["query_uid"])
        raise RuntimeError("x" * 1000)
    raw = HermesWRRAdapter(executor, max_errors=1, max_error_chars=80).execute(_plan())
    assert len(calls) == len(_plan().queries)
    assert len(raw.errors) == 1
    assert len(raw.errors[0]["safe_message"]) <= 80
    assert raw.status == "failed" and raw.attempted and raw.executed


def test_adapter_not_requested_run_still_binds_all_input_hashes():
    from research_wrr_adapter import HermesWRRAdapter
    plan = _plan()
    plan = rc.finalize_research_plan(replace(plan, queries=()))
    raw = HermesWRRAdapter(lambda _query: {}).execute(plan)
    assert raw.status == "not_requested"
    assert raw.raw_research["input_hashes"] == {
        "plan_semantic_hash": plan.plan_semantic_hash,
        "evidence_bundle_hash": plan.evidence_bundle_hash,
        "claim_bundle_hash": plan.claim_bundle_hash,
    }
    assert raw.execution["query_count"] == 0
    assert raw.execution["fetch_count"] == raw.execution["source_count"] == 0
    assert set(raw.execution) >= {
        "elapsed_seconds", "topic_count", "knowledge_expansion_count",
        "research_claim_count", "started_at", "completed_at",
    }


def test_orchestration_calls_provider_once_and_never_projects_raw_candidates():
    class Provider:
        def __init__(self): self.calls = 0
        def execute(self, plan):
            self.calls += 1
            return rc.finalize_raw_research_run(rc.RawResearchRun(
                schema_version=rc.RAW_RESEARCH_RUN_SCHEMA_VERSION,
                run_id="raw-s4", plan_semantic_hash=plan.plan_semantic_hash,
                capability_available=True, attempted=True, executed=True,
                status="completed", validated_evidence_count=0,
                raw_research={"candidates": [{"snippet": "RAW MUST STAY PRIVATE"}]},
            ))
    report = _report(); before = dict(report["sections"]); provider = Provider()
    result = gr.orchestrate_research(report, research_provider=provider,
                                     research_context=_context(), research_policy="auto")
    assert provider.calls == 1
    assert result["research_plan"].claim_bundle_hash == "sha256:claims"
    assert result["raw_research_run"].validated_evidence_count == 0
    assert report["sections"] == before
    assert "RAW MUST STAY PRIVATE" not in str(report["sections"])
    assert "RAW MUST STAY PRIVATE" not in str(report.get("fact_checks", ""))


def test_orchestration_validates_and_archives_without_projecting_raw(tmp_path):
    from research_archive import ResearchArchive
    from research_wrr_adapter import HermesWRRAdapter

    report = _report()
    report["claim_bundle"] = {
        "claim_bundle_semantic_hash": "sha256:" + "c" * 64,
        "claims": ({
            "claim_uid": "claim-1", "text": "事实主张成立", "risk": "P2",
        },),
    }
    raw_marker = "PRIVATE-RAW-SNAPSHOT-MARKER"

    def executor(query):
        claim_uid = tuple(query.get("claim_uids") or ("claim-1",))[0]
        quote = "事实主张成立"
        content = f"官方来源正文明确说明{quote}。{raw_marker}"
        return {"candidates": [{
            "url": f"https://{query['query_uid']}.example/doc",
            "title": "官方说明", "publisher": str(query["query_uid"]),
            "source_kind": "official_doc", "content": content,
            "quote_candidates": ({"claim_uid": claim_uid, "quote_text": quote},),
        }]}

    repo = tmp_path / "repo"; repo.mkdir()
    vault = tmp_path / "vault"; vault.mkdir()
    archive = ResearchArchive(
        tmp_path / "private" / "research", forbidden_roots=(repo, vault)
    )
    artifacts = gr.orchestrate_research(
        report,
        research_provider=HermesWRRAdapter(executor),
        research_context=_context(),
        research_policy="auto",
        research_archive=archive,
    )

    bundle = artifacts["research_bundle"]
    assert bundle.publication_disposition in {"pass", "degraded", "block"}
    assert artifacts["archive_bundle_hash"].startswith("sha256:")
    assert archive.read_bundle(artifacts["archive_bundle_hash"])["bundle_id"] == bundle.bundle_id
    assert artifacts["archive_source_hashes"]
    assert raw_marker in archive.read_source(artifacts["archive_source_hashes"][0])
    assert raw_marker not in str(report.get("sections", ""))
    assert raw_marker not in str(report.get("fact_checks", ""))
    assert report["research"]["validated_evidence_count"] >= 1
    from video_analysis_engine import write_appendix_section
    external = report["evidence_gate"]["sources"]["external_research"]
    assert external["available"] is True
    assert external["validated_evidence_count"] == report["research"]["validated_evidence_count"]
    assert "未进行外部检索" not in write_appendix_section(report)


def test_legacy_context_never_calls_provider_or_claims_execution():
    class Forbidden:
        def execute(self, plan): raise AssertionError("must not call provider")
    report = _report()
    result = gr.orchestrate_research(report, research_provider=Forbidden(),
                                     research_context=None, research_policy="auto")
    assert result == {"status": "unavailable", "transport": "legacy_untrusted",
                      "attempted": False, "executed": False,
                      "validated_evidence_count": 0}


def test_canonical_context_without_provider_records_unavailable():
    result = gr.orchestrate_research(_report(), research_provider=None,
                                     research_context=_context(), research_policy="auto")
    raw = result["raw_research_run"]
    assert raw.status == "unavailable"
    assert not raw.attempted and not raw.executed and raw.validated_evidence_count == 0


def test_adapter_ledger_counts_only_budgeted_attempts():
    from research_wrr_adapter import HermesWRRAdapter
    plan = _plan()
    assert len(plan.queries) > 1
    plan = rc.finalize_research_plan(replace(
        plan, budget=replace(plan.budget, max_queries=1)
    ))
    calls = []
    raw = HermesWRRAdapter(lambda query: calls.append(query) or {}).execute(plan)
    assert len(calls) == 1
    assert raw.execution["query_count"] == 1
    bundle = rc.validate_and_adjudicate_research(plan, raw)
    assert bundle.execution["query_count"] == 1


def test_report_markdown_backward_compatible_and_zero_network_by_default(tmp_path):
    """原 report_markdown 兼容：新参数可选，默认零网络、不改 Markdown、不声称 research。"""
    class ExplodingProvider:
        def execute(self, plan):
            raise AssertionError("default report_markdown must not touch the network")

    # 1) 原始签名（无任何 research 参数）仍产出非空 Markdown 与 report dict。
    baseline_md, report = gr.report_markdown(_results(tmp_path), run_fact_check=False, provider=None)
    assert isinstance(baseline_md, str) and baseline_md
    assert report["frontmatter"]["video_id"] == "BVcompat"
    # 无 canonical context → 明确 legacy_untrusted / unavailable，绝不声称 executed。
    assert report["research"] == {
        "status": "unavailable", "transport": "legacy_untrusted",
        "attempted": False, "executed": False, "validated_evidence_count": 0,
    }
    assert "research_artifacts" not in report

    # 2) 即使注入 provider，但缺 canonical research_context → 零网络（provider 不被调用）。
    guarded_md, guarded = gr.report_markdown(
        _results(tmp_path), run_fact_check=False, provider=None,
        research_provider=ExplodingProvider(), research_context=None, research_policy="auto",
    )
    assert guarded["research"]["transport"] == "legacy_untrusted"
    assert "research_artifacts" not in guarded
    # research 编排绝不改变已渲染的 Markdown 正文。
    assert guarded_md == baseline_md


def test_report_markdown_binds_research_plan_to_final_claim_bundle(tmp_path, monkeypatch):
    """canonical-context 回归：research_plan 必须绑定 assemble 之后的最终 ClaimBundle，
    而非 analyze_video 初始 bundle。旧实现在 assemble 前编排 → RED。"""
    FINAL_HASH = "sha256:" + "f" * 64
    RAW_SECRET = "RAW-CANDIDATE-MUST-STAY-PRIVATE"

    real_assemble = gr.assemble_draft_report_slice

    def assemble_with_different_final_bundle(report, **kwargs):
        # 保留真实草稿与真实 claims，仅改写最终 ClaimBundle 的语义哈希，
        # 使最终 bundle 与 analyze_video 初始 bundle 必然不同。
        draft = real_assemble(report, **kwargs)
        initial_hash = (report.get("claim_bundle") or {}).get("claim_bundle_semantic_hash")
        assert initial_hash and initial_hash != FINAL_HASH  # 保证 RED 有意义
        draft.claim_bundle = {**(draft.claim_bundle or {}),
                              "claim_bundle_semantic_hash": FINAL_HASH}
        return draft

    monkeypatch.setattr(gr, "assemble_draft_report_slice",
                        assemble_with_different_final_bundle)

    captured = {}

    class CapturingProvider:
        def __init__(self):
            self.calls = 0

        def execute(self, plan):
            self.calls += 1
            captured["plan"] = plan
            return rc.finalize_raw_research_run(rc.RawResearchRun(
                schema_version=rc.RAW_RESEARCH_RUN_SCHEMA_VERSION,
                run_id="raw-followup", plan_semantic_hash=plan.plan_semantic_hash,
                capability_available=True, attempted=True, executed=True,
                status="completed", validated_evidence_count=0,
                raw_research={"candidates": [{"snippet": RAW_SECRET}]},
            ))

    provider = CapturingProvider()
    context = {
        "evidence_bundle_hash": "sha256:evidence",
        "created_at": "2026-07-14T00:00:00Z",
        "plan_id": "rp-s4-followup",
        "capability_snapshot": {"available": True, "route": "hermes_wrr"},
        "canonical_id": "BVcompat", "platform": "bilibili",
    }
    markdown, report = gr.report_markdown(
        _results(tmp_path), run_fact_check=False, provider=None,
        research_provider=provider, research_context=context, research_policy="auto",
    )

    # provider 恰好一次。
    assert provider.calls == 1
    # research_plan 绑定最终 ClaimBundle（assemble 之后），而非初始 bundle —— 核心断言。
    assert captured["plan"].claim_bundle_hash == FINAL_HASH
    assert report["claim_bundle"]["claim_bundle_semantic_hash"] == FINAL_HASH
    assert report["research_artifacts"]["research_plan"].claim_bundle_hash == FINAL_HASH
    # canonical 编排语义正确。
    assert report["research"]["transport"] == "canonical_evidence_bundle"
    assert report["research_artifacts"]["raw_research_run"].validated_evidence_count == 0
    # RawResearchRun 原始候选仅作私有产物，绝不投影进 Markdown / fact_checks / sections。
    assert RAW_SECRET not in markdown
    assert RAW_SECRET not in str(report.get("fact_checks", ""))
    assert RAW_SECRET not in str(report.get("sections", ""))
    assert RAW_SECRET not in str(report.get("claim_bundle", ""))
