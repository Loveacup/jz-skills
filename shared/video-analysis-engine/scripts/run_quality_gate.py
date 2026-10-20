#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2-E/P2-F quality gate harness: fetch_all JSON → report → gates.

This script is deliberately deterministic by default (`--writer-provider fixture`):
it exercises the same generate_report/render/verify/coherence pipeline without
network calls or LLM tokens. Use `--writer-provider cli` for a real model-backed
sample smoke. P2-F adds fallback-warning detection so real sample runs can fail
when the LLM writer silently falls back to skeleton output.
"""

import argparse
import hashlib
import json
import sys
import warnings
from pathlib import Path
from typing import Callable, Dict, Any, Mapping, Optional, Tuple

# Allow running as `python scripts/run_quality_gate.py` from repo root.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_report
import research_publish_gate
import verify_report
import verify_publishable_report
from research_archive import ResearchArchive
from research_wrr_adapter import HermesWRRAdapter
from video_analysis_engine import check_report_coherence

WriterProvider = Callable[[str, str], str]


def _repeat_sentence(seed: str, citation: str, min_chars: int) -> str:
    """Create citation-bearing Chinese prose long enough for static gates."""
    sentence = (
        f"{seed}这段分析严格基于现有证据{citation}，先说明现象，再解释机制，"
        "最后落到对观看者可验证的启发；它不补写视频没有给出的事实，只把证据中已经出现的"
        "时间、行动、角色和因果关系组织成清晰段落。证据边界是：该判断只覆盖当前转录与已采集信号，"
        "不能外推为视频之外的普遍事实。"
    )
    out = []
    while len("".join(out)) < min_chars:
        out.append(sentence)
    return "".join(out)


def fixture_writer_provider(system: str, user: str) -> str:
    """Deterministic provider that returns verify_report-compatible sections.

    It is not a content-quality substitute for real LLM output. Its job is to
    catch pipeline regressions: prompt routing, section formatting, static gates,
    and coherence validation.
    """
    if "洞察" in system and "💡" in system:
        parts = []
        for i in range(1, 4):
            parts.append(f"### 💡 洞察 {i}：证据驱动的关键判断 [E{i}]")
            parts.append(_repeat_sentence(f"第{i}个洞察指出，", f"[E{i}]", 230))
        return "\n".join(parts) + "\n"

    if "模块" in system and ("Deep Dive" in user or "深度" in system or "模块 N" in system):
        parts = []
        for i in range(1, 4):
            parts.append(f"### 模块 {i}：结构化拆解层 {i} [E{i}]")
            parts.append(_repeat_sentence(f"模块{i}从叙事结构、证据链和行动后果三个角度展开，", f"[E{i}]", 560))
        return "\n".join(parts) + "\n"

    if "独特价值" in system and "可行动" in system:
        return """### 独特价值 [E1]
基于当前转录证据，这些价值判断成立，因为每一项都能回指可检查的内容锚点。证据边界是：它们只说明本视频的表达效果，不自动证明外部事实完整无误。

- 这份内容把分散现象压缩成可追踪的问题链，让观看者能从证据而不是情绪出发理解主题 [E1]
- 它把历史事实、商业动机和用户后果放在同一张图里，适合转化为后续知识笔记 [E2]
- 它保留了足够多的原文锚点，方便复核关键判断是否真的来自视频内容 [E3]

### 局限与偏见 [E2]
- 从现有证据只能看出视频自身的叙事重点，不能自动证明所有背景事实都完整无误 [E2]
- 评论和弹幕样本数量有限，观众反馈只能作为辅助信号，不能替代事实核查 [E3]

### 可行动项 [E3]
1. 先把核心概念拆成可复查的 claim 清单，再逐条补外部资料验证 [E1]
2. 把高光引文与时间戳保留到 Obsidian，作为后续主题研究入口 [E2]
3. 对商业动机、技术演化、用户影响分别建立链接，避免只留下单线故事 [E3]
"""

    # Fail closed: an unknown prompt should make validation fail, not hide routing bugs.
    return "fixture provider received an unknown writer prompt without valid section format"


def resolve_quality_provider(name: str) -> Optional[WriterProvider]:
    if name == "none":
        return None
    if name == "fixture":
        return fixture_writer_provider
    args = argparse.Namespace(writer_provider=name)
    return generate_report.resolve_writer_provider(args)


def _load_results(input_path: str) -> Dict[str, Any]:
    text = Path(input_path).read_text(encoding="utf-8")
    parsed = generate_report.parse_result_json(text)
    if parsed is None:
        raise ValueError(f"无法解析 fetch_all JSON: {input_path}")
    return parsed


class _PlanBoundFixtureResearchProvider:
    """Offline fixture provider that binds raw data to the plan at execution time."""

    def __init__(self, fixture: Dict[str, Any]) -> None:
        self._fixture = fixture

    def execute(self, plan):
        claim_by_uid = {
            str(item.get("claim_uid") or ""): item
            for item in plan.claims
        }
        # Globally schedule the shared source budget before the adapter runs.
        emissions_by_query = self._plan_emissions(plan, claim_by_uid)

        def executor(query):
            query_uid = str(query.get("query_uid") or "")
            return {"candidates": list(emissions_by_query.get(query_uid, ()))}
        return HermesWRRAdapter(executor).execute(plan)

    def _plan_emissions(self, plan, claim_by_uid):
        """Schedule the shared source budget in two rounds so no claim is starved.

        ``HermesWRRAdapter`` appends candidates across queries in query order and
        hard-caps the total at ``budget.max_sources``. Binding each claim's full
        primary+independent bundle up front lets a grounding query covering many
        P2 claims spend two slots per claim, exhausting the budget before the tail
        claims are reached and leaving them with *no* source at all.

        Instead we drain the budget in two ordered rounds. Round one emits a
        single ``primary`` for every claim (P0-P3) so each claim is grounded once;
        round two emits an ``independent`` only for the P0/P1 claims that require a
        second publisher. Within each round we walk queries in plan order and
        claims in stable order, and each (claim, relation) candidate is emitted at
        most once even when a claim appears in several queries. The cap is applied
        across the concatenated rounds, so tail claims keep their primary before
        any claim receives a second source, and the total never exceeds
        ``max_sources``.
        """
        max_sources = max(0, int(plan.budget.max_sources))
        primary_round = []
        independent_round = []
        seen_primary = set()
        seen_independent = set()
        for query in plan.queries[: plan.budget.max_queries]:
            query_uid = str(query.get("query_uid") or "")
            # No per-query claim slice: the ``max_sources`` cap below is the only
            # bound, so a wide grounding query cannot strand its tail claims.
            claim_uids = tuple(sorted(
                str(uid) for uid in query.get("claim_uids") or () if uid
            ))
            for claim_uid in claim_uids:
                candidates = self._bind_bundle(query, claim_uid, claim_by_uid)
                if not candidates:
                    continue
                risk = str((claim_by_uid.get(claim_uid) or {}).get("risk") or "P2").upper()
                for candidate in candidates:
                    relation = str(candidate.get("authority_relation") or "").lower()
                    if relation == "primary":
                        if claim_uid in seen_primary:
                            continue
                        seen_primary.add(claim_uid)
                        primary_round.append((query_uid, candidate))
                    else:
                        # Only P0/P1 claims earn a second publisher, and only once.
                        if risk not in {"P0", "P1"} or claim_uid in seen_independent:
                            continue
                        seen_independent.add(claim_uid)
                        independent_round.append((query_uid, candidate))

        emissions = {}
        used = 0
        for query_uid, candidate in (*primary_round, *independent_round):
            if used >= max_sources:
                break
            emissions.setdefault(query_uid, []).append(candidate)
            used += 1
        return emissions

    def _bind_bundle(self, query, claim_uid, claim_by_uid):
        """Bind one claim's fixture bundle, kept primary->independent."""
        bundle = []
        for candidate in self._fixture.get("candidates", ()):
            if not isinstance(candidate, Mapping):
                continue
            item = _bind_fixture_value(candidate, query, claim_uid)
            claim = claim_by_uid.get(claim_uid) or {}
            statement = str(claim.get("statement") or claim.get("text") or "")
            priority = str(claim.get("risk") or "P2")
            if statement:
                item["content"] = (
                    statement + " PRIVATE-RAW-FIXTURE-MARKER "
                    + str(item.get("authority_relation") or "unknown")
                )
            snapshot_text = str(item.get("content") or "")
            for quote in item.get("quote_candidates", ()) or ():
                if isinstance(quote, dict):
                    quote_text = statement or str(quote.get("quote_text") or "")
                    snapshot_text = quote_text + " PRIVATE-RAW-FIXTURE-MARKER"
                    quote_hash = "sha256:" + hashlib.sha256(quote_text.encode("utf-8")).hexdigest()
                    snapshot_hash = "sha256:" + hashlib.sha256(snapshot_text.encode("utf-8")).hexdigest()
                    quote["quote_text"] = quote_text
                    quote["quote"] = quote_text
                    quote["quote_hash"] = quote_hash
                    quote["priority"] = priority
                    quote["snapshot"] = {
                        "text": snapshot_text,
                        "snapshot_hash": snapshot_hash,
                        "mode": "full",
                    }
            bundle.append(item)
        # Every bundle keeps primary before independent; stable within equal ranks.
        bundle.sort(key=lambda entry: 0 if str(entry.get("authority_relation") or "").lower() == "primary" else 1)
        return bundle


def _bind_fixture_value(value: Any, query: Mapping[str, object], claim_uid: str) -> Any:
    """Bind fixture placeholders only to the current immutable plan/query IDs."""
    if isinstance(value, Mapping):
        return {str(key): _bind_fixture_value(nested, query, claim_uid)
                for key, nested in value.items()}
    if isinstance(value, (tuple, list)):
        return [_bind_fixture_value(item, query, claim_uid) for item in value]
    if not isinstance(value, str):
        return value
    return (value.replace("$QUERY_UID", str(query.get("query_uid") or ""))
                 .replace("$QUERY_CLAIM", claim_uid))


def _load_canonical_research_context(path: str) -> Dict[str, Any]:
    context = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(context, dict):
        raise ValueError("research context must be a JSON object")
    required = ("canonical_id", "platform", "evidence_bundle_hash", "created_at", "plan_id")
    missing = [key for key in required if not str(context.get(key) or "").strip()]
    if missing:
        raise ValueError("canonical research context missing: " + ", ".join(missing))
    return context


def _resolve_research_lane(
    *, provider: Optional[str], context_path: Optional[str], fixture_path: Optional[str],
    archive_dir: Optional[str], allow_network: bool,
):
    if provider is None:
        return None, None, None
    if provider not in {"fixture", "real"}:
        raise ValueError("research_provider must be fixture, real, or None")
    if provider == "real":
        if not allow_network:
            raise ValueError("real research requires explicit --allow-network-research")
        raise ValueError("real research provider is not configured in the deterministic quality gate")
    if not context_path or not fixture_path or not archive_dir:
        raise ValueError("fixture research requires context, fixture, and private archive")
    context = _load_canonical_research_context(context_path)
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    if not isinstance(fixture, dict):
        raise ValueError("research fixture must be a JSON object")
    archive_root = Path(archive_dir).resolve()
    public_roots = (str(Path.cwd().resolve()),)
    return _PlanBoundFixtureResearchProvider(fixture), context, ResearchArchive(
        str(archive_root), forbidden_roots=public_roots,
    )


def run_quality_gate(
    input_path: str,
    output_path: str,
    *,
    writer_provider: str = "fixture",
    mode: str = "full",
    run_fact_check: bool = False,
    fail_on_fallback_warning: bool = False,
    publishable_gate: bool = False,
    section_qa_gate: bool = False,  # Phase 4: 可选 section QA gate
    depth_profile: str = "standard",  # Phase 5: depth profile
    claim_qa_gate: bool = False,  # Phase 5: claim QA gate (D6-D8)
    research_provider: Optional[str] = None,
    research_context: Optional[str] = None,
    research_fixture: Optional[str] = None,
    research_archive_dir: Optional[str] = None,
    allow_network_research: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    """Run the report quality gate and return (passed, summary).

    Research is opt-in. This boundary validates private inputs before any
    provider could be initialized, keeping the default release lane offline.
    """
    research_runtime_provider, resolved_research_context, research_archive = _resolve_research_lane(
        provider=research_provider, context_path=research_context,
        fixture_path=research_fixture, archive_dir=research_archive_dir,
        allow_network=allow_network_research,
    )
    results = _load_results(input_path)
    provider = resolve_quality_provider(writer_provider)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        markdown, report = generate_report.report_markdown(
            results,
            run_fact_check=run_fact_check,
            provider=provider,
            depth_profile=depth_profile,
            claim_qa_gate=claim_qa_gate,
            mode=mode,
            research_provider=research_runtime_provider,
            research_context=resolved_research_context,
            research_archive=research_archive,
        )
    warning_messages = [str(w.message) for w in caught]
    # Merge assembly-path draft_warnings (stored in report by generate_report).
    # Normalize to legacy warnings.warn format so fallback classifiers remain consistent.
    for draft_msg in (report.get('draft_warnings') or []):
        normalized = draft_msg
        if 'LLM writer validation failed:' in draft_msg and 'falling back to skeleton' not in draft_msg:
            normalized = draft_msg.replace(
                'LLM writer validation failed:', 'LLM writer validation failed, falling back to skeleton:', 1
            )
        elif 'LLM writer failed:' in draft_msg and 'falling back to skeleton' not in draft_msg:
            normalized = draft_msg.replace(
                'LLM writer failed:', 'LLM writer failed, falling back to skeleton:', 1
            )
        if normalized not in warning_messages:
            warning_messages.append(normalized)
    fallback_warnings = [
        msg for msg in warning_messages
        if "falling back to skeleton" in msg
        or ("LLM writer" in msg and "fallback" in msg.lower())
        or "LLM writer validation failed" in msg
        or "LLM writer failed" in msg
    ]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(markdown, encoding="utf-8")

    effective_mode = (report.get('report_plan') or {}).get('mode', mode)
    verify_results, verify_passed = verify_report.evaluate(markdown, effective_mode)
    coherence = check_report_coherence(markdown)
    publishable_results = None
    publishable_passed = None
    publishable_failed_codes = []
    if publishable_gate:
        publishable_results, publishable_passed = verify_publishable_report.evaluate_publishable_report(markdown, report)
        publishable_failed_codes = [
            code for code, gate in publishable_results.items()
            if not gate.get("pass")
        ]
    research_gates = None
    research_gate_passed = None
    if research_provider == "fixture":
        research_gates = research_publish_gate.evaluate_research_gates(markdown, report)
        research_gate_passed = all(gate.get("pass") for gate in research_gates.values())
    failed_due_to_fallback_warning = bool(fail_on_fallback_warning and fallback_warnings)
    failed_due_to_publishable_gate = bool(publishable_gate and not publishable_passed)

    # Phase 4: section QA gate 逻辑
    section_qa = report.get("section_qa", {})
    section_qa_failed = False
    if section_qa_gate:
        # 检查所有 section QA 是否有 P0 blockers
        for sid, qa in section_qa.items():
            if qa.get("blockers"):
                section_qa_failed = True
                break
    section_qa_gate_passed = not section_qa_failed
    failed_due_to_section_qa_gate = bool(section_qa_gate and section_qa_failed)

    # Phase 5: claim QA gate 逻辑 (D6-D8)
    claim_qa_failed = False
    claim_qa_gate_passed = True
    if claim_qa_gate:
        # 检查 §3/§4/§7 的 D6-D8 dimensions
        for sid in ("3", "4", "7"):
            qa = section_qa.get(sid)
            if not qa:
                continue
            for dim in qa.get("dimensions", []):
                dim_name = dim.get("dimension", "")
                if dim_name in ("warrant-present", "rebuttal-or-boundary", "actionability"):
                    if not dim.get("passed"):
                        claim_qa_failed = True
                        break
            if claim_qa_failed:
                break
        claim_qa_gate_passed = not claim_qa_failed
    failed_due_to_claim_qa_gate = bool(claim_qa_gate and claim_qa_failed)

    # Extract claim bundle stats
    claim_bundle = report.get("claim_bundle") or {}
    claim_bundle_stats = {
        "claims_count": len(claim_bundle.get("claims", [])),
        "insights_count": len(claim_bundle.get("insights", [])),
        "audit_log_count": len(claim_bundle.get("audit_log", [])),
    }

    passed = bool(
        verify_passed
        and coherence.passed
        and not failed_due_to_fallback_warning
        and not failed_due_to_publishable_gate
        and not failed_due_to_section_qa_gate
        and not failed_due_to_claim_qa_gate
        and research_gate_passed is not False
    )
    public_input_path = input_path
    public_output_path = output_path
    if research_provider == "fixture":
        # The fixture lane exposes a public summary; archive and temp roots are
        # deliberately not disclosed there.
        public_input_path = Path(input_path).name
        public_output_path = Path(output_path).name
    summary = {
        "passed": passed,
        "input_path": public_input_path,
        "output_path": public_output_path,
        "writer_provider": writer_provider,
        "mode": mode,
        "requested_mode": mode,
        "effective_mode": effective_mode,
        "markdown_chars": len(markdown),
        "video_id": report.get("frontmatter", {}).get("video_id"),
        "fail_on_fallback_warning": fail_on_fallback_warning,
        "warnings": warning_messages,
        "fallback_warnings": fallback_warnings,
        "fallback_warning_count": len(fallback_warnings),
        "failed_due_to_fallback_warning": failed_due_to_fallback_warning,
        "publishable_gate": publishable_gate,
        "publishable_passed": publishable_passed,
        "publishable_failed_codes": publishable_failed_codes,
        "publishable_gates": publishable_results,
        "failed_due_to_publishable_gate": failed_due_to_publishable_gate,
        "section_qa_gate": section_qa_gate,  # Phase 4: section QA gate 开关
        "section_qa_gate_passed": section_qa_gate_passed,  # Phase 4: section QA gate 是否通过
        "failed_due_to_section_qa_gate": failed_due_to_section_qa_gate,  # Phase 4: 是否因 section QA gate 失败
        "depth_profile": depth_profile,  # Phase 5: depth profile
        "claim_bundle_stats": claim_bundle_stats,  # Phase 5: claim bundle 统计
        "claim_qa_gate_passed": claim_qa_gate_passed,  # Phase 5: claim QA gate 是否通过
        "failed_due_to_claim_qa_gate": failed_due_to_claim_qa_gate,  # Phase 5: 是否因 claim QA gate 失败
        "verify_passed": verify_passed,
        "verify_gates": verify_results,
        "coherence_passed": coherence.passed,
        "coherence_issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "section_id": issue.section_id,
                "message": issue.message,
            }
            for issue in coherence.issues
        ],
        "section_qa": section_qa,  # Phase 3: QA 元数据暴露
        "research": report.get("research"),
        "research_gate_passed": research_gate_passed,
        "research_gates": research_gates,
        "research_artifact_hashes": {
            key: value for key, value in (report.get("research_artifacts") or {}).items()
            if key.endswith("_hash") or key == "archive_source_hashes"
        },
    }
    return passed, summary


# ---------------------------------------------------------------------------
# P6-R: explicit, side-effect-free corpus manifest runner.
#
# The corpus runner is a *frame* for a pre-release real-sample corpus, not a
# generator. Without --execute it only loads/validates/selects samples and
# emits a JSON summary: it never calls report_markdown, reads an input file,
# downloads, or invokes an LLM. Only --execute runs the existing single-sample
# run_quality_gate on samples whose declared local input actually exists; it
# must never auto-download to backfill a missing cache.
# ---------------------------------------------------------------------------

CORPUS_SCHEMA_VERSION = 1

# candidate is the only entry state; the rest form the manual/machine lifecycle.
CORPUS_STATUSES = (
    "candidate",
    "input_ready",
    "generated",
    "qa_passed",
    "qa_failed",
    "review_pending",
    "accepted_gold",
    "rejected",
    "retired",
)

# accepted_gold is the only status permitted into the blocking release lane, and
# only when these manual/explicit acceptance fields are all present.
GOLD_REVIEW_FIELDS = ("reviewed_by", "reviewed_at", "verdict_source")

LANE_STATUS = {
    "candidates": "candidate",
    "ready": "input_ready",
    "blocking": "accepted_gold",
}


def load_corpus_manifest(path: str) -> Dict[str, Any]:
    """Load and JSON-parse a corpus manifest (no validation, no side effects)."""
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def _nonempty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def validate_corpus_manifest(manifest: Dict[str, Any]) -> list:
    """Return a list of human-readable schema/state-machine violations.

    An empty list means the manifest is valid. The key invariant this enforces:
    a sample may only claim ``accepted_gold`` when it carries complete manual
    acceptance evidence (reviewed_by/reviewed_at/verdict_source). No fake gold.
    """
    errors: list = []
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    if manifest.get("schema_version") != CORPUS_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {CORPUS_SCHEMA_VERSION}, "
            f"got {manifest.get('schema_version')!r}"
        )
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        errors.append("manifest.samples must be a non-empty list")
        return errors

    seen_ids = set()
    for idx, sample in enumerate(samples):
        sid = sample.get("id") or f"<index {idx}>"
        if not _nonempty(sample.get("id")):
            errors.append(f"sample[{idx}] is missing an id")
        elif sid in seen_ids:
            errors.append(f"sample {sid}: duplicate id")
        else:
            seen_ids.add(sid)
        if not _nonempty(sample.get("bvid")):
            errors.append(f"sample {sid}: missing bvid")

        rubric = sample.get("rubric") or {}
        status = rubric.get("status")
        if status not in CORPUS_STATUSES:
            errors.append(f"sample {sid}: unknown rubric.status {status!r}")
        if status == "accepted_gold":
            missing = [f for f in GOLD_REVIEW_FIELDS if not _nonempty(rubric.get(f))]
            if missing:
                errors.append(
                    f"sample {sid}: accepted_gold requires {', '.join(GOLD_REVIEW_FIELDS)}; "
                    f"missing {', '.join(missing)}"
                )
        if "input" not in sample or not isinstance(sample["input"], dict):
            errors.append(f"sample {sid}: missing input block")
    return errors


def _resolve_manifest_locator(value: Any, manifest_path: str) -> Path:
    """Resolve portable skill:// locators while preserving absolute legacy paths."""
    raw = str(value or "")
    if raw.startswith("skill://"):
        skill_root = Path(manifest_path).resolve().parent.parent
        return skill_root / raw.removeprefix("skill://").lstrip("/")
    return Path(raw)


def _sample_input_path(sample: Dict[str, Any], manifest_path: str = "") -> str:
    raw = (sample.get("input") or {}).get("fetch_all_json_path") or ""
    if not raw or not manifest_path:
        return raw
    return str(_resolve_manifest_locator(raw, manifest_path))


def _is_blocking_complete(sample: Dict[str, Any], manifest_path: str = "") -> bool:
    """A blocking-lane sample must be reproducible and auditable, not just gold."""
    rubric = sample.get("rubric") or {}
    if rubric.get("status") != "accepted_gold":
        return False
    if any(not _nonempty(rubric.get(f)) for f in GOLD_REVIEW_FIELDS):
        return False
    input_path = _sample_input_path(sample, manifest_path)
    if not input_path or not Path(input_path).exists():
        return False
    summary_raw = (sample.get("run") or {}).get("summary_json_path")
    if not _nonempty(summary_raw):
        return False
    summary_path = _resolve_manifest_locator(summary_raw, manifest_path) if manifest_path else Path(str(summary_raw))
    if not summary_path.exists():
        return False
    return True


def select_lane_samples(manifest: Dict[str, Any], lane: str, manifest_path: str = "") -> list:
    """Filter samples for a lane. Blocking only ever yields complete accepted_gold."""
    if lane not in LANE_STATUS:
        raise ValueError(f"unknown lane {lane!r}; expected one of {sorted(LANE_STATUS)}")
    samples = manifest.get("samples") or []
    if lane == "blocking":
        return [s for s in samples if _is_blocking_complete(s, manifest_path)]
    wanted = LANE_STATUS[lane]
    return [s for s in samples if (s.get("rubric") or {}).get("status") == wanted]


def _selected_view(sample: Dict[str, Any]) -> Dict[str, Any]:
    rubric = sample.get("rubric") or {}
    inp = sample.get("input") or {}
    return {
        "id": sample.get("id"),
        "bvid": sample.get("bvid"),
        "category": sample.get("category"),
        "status": rubric.get("status"),
        "input_path": inp.get("fetch_all_json_path") or "",
        "cache_status": inp.get("cache_status"),
    }


def run_corpus_manifest(
    manifest_path: str,
    *,
    lane: str = "candidates",
    execute: bool = False,
    writer_provider: str = "fixture",
    mode: str = "full",
    publishable_gate: bool = False,
    fail_on_fallback_warning: bool = False,
    run_fact_check: bool = False,
    section_qa_gate: bool = False,
    depth_profile: str = "claim-first-full",
    claim_qa_gate: bool = False,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate/select the manifest and, only when execute=True, run the gate.

    Returns a JSON-serialisable summary. Without execute this touches no input
    files and never calls report_markdown.
    """
    manifest = load_corpus_manifest(manifest_path)
    errors = validate_corpus_manifest(manifest)
    valid = not errors

    samples = manifest.get("samples") or []
    status_distribution: Dict[str, int] = {}
    for s in samples:
        status = (s.get("rubric") or {}).get("status", "<none>")
        status_distribution[status] = status_distribution.get(status, 0) + 1

    selected = select_lane_samples(manifest, lane, manifest_path) if valid else []

    summary: Dict[str, Any] = {
        "mode": "corpus-manifest",
        "manifest_path": manifest_path,
        "schema_version": manifest.get("schema_version"),
        "name": manifest.get("name"),
        "lane": lane,
        "execute": execute,
        "writer_provider": writer_provider,
        "depth_profile": depth_profile,
        "valid": valid,
        "validation_errors": errors,
        "total_samples": len(samples),
        "status_distribution": status_distribution,
        "selected_count": len(selected),
        "selected": [_selected_view(s) for s in selected],
        "executed": False,
        "results": [],
    }

    if not valid or not execute:
        return summary

    out_root = Path(output_dir) if output_dir else Path("/tmp/p6r-corpus-out")
    results = []
    all_passed = True
    for sample in selected:
        sid = sample.get("id")
        bvid = sample.get("bvid")
        input_path = _sample_input_path(sample, manifest_path)
        record: Dict[str, Any] = {
            "id": sid,
            "bvid": bvid,
            "executed": False,
            "passed": False,
            "error": None,
            "output_path": None,
            "summary": None,
        }
        # No input path or a missing file fails clean — never auto-download.
        if not input_path:
            record["error"] = "sample has no input.fetch_all_json_path; refusing to download"
        elif not Path(input_path).exists():
            record["error"] = f"input file does not exist: {input_path}; refusing to auto-download"
        else:
            output_path = str(out_root / f"{sid}_report.md")
            try:
                passed, sample_summary = run_quality_gate(
                    input_path,
                    output_path,
                    writer_provider=writer_provider,
                    mode=mode,
                    run_fact_check=run_fact_check,
                    publishable_gate=publishable_gate,
                    fail_on_fallback_warning=fail_on_fallback_warning,
                    section_qa_gate=section_qa_gate,
                    depth_profile=depth_profile,
                    claim_qa_gate=claim_qa_gate,
                )
                record["executed"] = True
                record["passed"] = bool(passed)
                record["output_path"] = output_path
                record["summary"] = sample_summary
            except Exception as exc:  # surface per-sample failures without aborting the batch
                record["error"] = f"run_quality_gate failed: {exc}"
        if not record["passed"]:
            all_passed = False
        results.append(record)

    summary["executed"] = True
    summary["results"] = results
    summary["all_passed"] = all_passed
    return summary


def _print_corpus_summary(summary: Dict[str, Any]) -> None:
    mark = "✅" if summary["valid"] else "❌"
    print(f"{mark} corpus manifest {'VALID' if summary['valid'] else 'INVALID'}")
    print(f"   manifest: {summary['manifest_path']}")
    print(f"   lane    : {summary['lane']} (execute={summary['execute']})")
    print(f"   samples : {summary['total_samples']} total, {summary['selected_count']} selected")
    print(f"   status  : {summary['status_distribution']}")
    for err in summary["validation_errors"]:
        print(f"   invalid: {err}")
    if summary["executed"]:
        for res in summary["results"]:
            status = "PASS" if res["passed"] else ("ERROR" if res["error"] else "FAIL")
            detail = res["error"] or res.get("output_path") or ""
            print(f"   run {res['id']}: {status} — {detail}")


def _corpus_exit_code(summary: Dict[str, Any]) -> int:
    if not summary["valid"]:
        return 2
    if summary["executed"]:
        return 0 if summary.get("all_passed") else 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Bilibili report quality gates end-to-end."
    )
    parser.add_argument("--input", help="fetch_all JSON path (single-sample mode)")
    parser.add_argument(
        "--corpus-manifest",
        dest="corpus_manifest",
        help="P6-R corpus manifest JSON path; validates/selects samples without side effects unless --execute",
    )
    parser.add_argument(
        "--lane",
        choices=("candidates", "ready", "blocking"),
        default="candidates",
        help="corpus lane: candidates=all candidate, ready=input_ready, blocking=complete accepted_gold",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="corpus mode: actually run the gate on selected samples whose local input exists (no auto-download)",
    )
    parser.add_argument("--output", help="report output path")
    parser.add_argument(
        "--writer-provider",
        choices=("fixture", "none", "cli", "deepseek"),
        default="fixture",
        help="fixture is deterministic/no-token; cli/deepseek exercise real LLM writer providers",
    )
    parser.add_argument("--mode", choices=("auto", "sparse", "condensed", "full"), default="full")
    parser.add_argument(
        "--run-fact-check",
        action="store_true",
        help="Allow generate_report to run fact_check_wrr extraction; default is off for deterministic CI",
    )
    parser.add_argument(
        "--fail-on-fallback-warning",
        action="store_true",
        help="Fail if LLM writer validation/error warnings show fallback to skeleton; recommended for real sample smoke",
    )
    parser.add_argument(
        "--publishable",
        action="store_true",
        help="Run the stricter publishable Obsidian note gate. This is opt-in; default gate is engineering-only.",
    )
    parser.add_argument(
        "--section-qa-gate",
        action="store_true",
        help="Phase 4: Enable section-level content quality gate (P0 blockers fail the report).",
    )
    parser.add_argument(
        "--depth-profile",
        choices=("standard", "v24-full", "claim-first-full"),
        default=None,
        help="Depth profile. Single-sample default=standard; corpus default=claim-first-full.",
    )
    parser.add_argument(
        "--claim-qa-gate",
        action="store_true",
        help="Phase 5: Enable claim QA gate (D6-D8: warrant/rebuttal/actionability for §3/§4/§7).",
    )
    parser.add_argument(
        "--research-provider", choices=("fixture", "real"),
        help="Explicit research lane; fixture is offline and requires all private inputs.",
    )
    parser.add_argument("--research-context", help="Canonical research-context JSON path (private input).")
    parser.add_argument("--research-fixture", help="Offline research fixture JSON path (private input).")
    parser.add_argument("--research-archive-dir", help="Private ResearchArchive directory.")
    parser.add_argument(
        "--allow-network-research", action="store_true",
        help="Required before a real provider could be used; no real provider is implemented here.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    # P6-R corpus manifest mode: does not touch --input single-sample behaviour.
    if args.corpus_manifest:
        try:
            summary = run_corpus_manifest(
                args.corpus_manifest,
                lane=args.lane,
                execute=args.execute,
                writer_provider=args.writer_provider,
                mode=args.mode,
                publishable_gate=args.publishable,
                fail_on_fallback_warning=args.fail_on_fallback_warning,
                run_fact_check=args.run_fact_check,
                section_qa_gate=args.section_qa_gate,
                depth_profile=args.depth_profile or "claim-first-full",
                claim_qa_gate=args.claim_qa_gate,
            )
        except Exception as exc:
            print(f"❌ corpus manifest failed to load: {exc}", file=sys.stderr)
            if args.as_json:
                print("RESULT_JSON_START")
                print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
                print("RESULT_JSON_END")
            sys.exit(2)
        _print_corpus_summary(summary)
        if args.as_json:
            print("RESULT_JSON_START")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print("RESULT_JSON_END")
        sys.exit(_corpus_exit_code(summary))

    if not args.input:
        parser.error("either --input (single-sample) or --corpus-manifest is required")

    output = args.output
    if not output:
        stem = Path(args.input).stem.replace("_fetch_all", "")
        output = f"/tmp/{stem}_quality_gate_report.md"

    try:
        passed, summary = run_quality_gate(
            args.input,
            output,
            writer_provider=args.writer_provider,
            mode=args.mode,
            run_fact_check=args.run_fact_check,
            fail_on_fallback_warning=args.fail_on_fallback_warning,
            publishable_gate=args.publishable,
            section_qa_gate=args.section_qa_gate,  # Phase 4
            depth_profile=args.depth_profile or "standard",  # preserve legacy single-sample default
            claim_qa_gate=args.claim_qa_gate,  # Phase 5
            research_provider=args.research_provider,
            research_context=args.research_context,
            research_fixture=args.research_fixture,
            research_archive_dir=args.research_archive_dir,
            allow_network_research=args.allow_network_research,
        )
    except Exception as exc:
        print(f"❌ quality gate failed before evaluation: {exc}", file=sys.stderr)
        if args.as_json:
            print("RESULT_JSON_START")
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
            print("RESULT_JSON_END")
        sys.exit(2)

    mark = "✅" if passed else "❌"
    print(f"{mark} quality gate {'PASS' if passed else 'FAIL'}")
    print(f"   input : {summary['input_path']}")
    print(f"   output: {summary['output_path']} ({summary['markdown_chars']} chars)")
    print(f"   verify_report: {summary['verify_passed']}")
    print(f"   coherence    : {summary['coherence_passed']} ({len(summary['coherence_issues'])} issues)")
    if summary["publishable_gate"]:
        print(
            f"   publishable  : {summary['publishable_passed']}"
            f" ({len(summary['publishable_failed_codes'])} failed gates)"
        )
    print(
        f"   fallback warn: {summary['fallback_warning_count']}"
        + (" (fail-on-fallback enabled)" if summary["fail_on_fallback_warning"] else "")
    )
    for gid, gate in summary["verify_gates"].items():
        status = "PASS" if gate["pass"] else "FAIL"
        print(f"   {gid}: {status} — {gate['measured']}")
    if summary["coherence_issues"]:
        for issue in summary["coherence_issues"]:
            print(f"   coherence {issue['severity']} {issue['code']}: {issue['message']}")
    if summary["fallback_warnings"]:
        for msg in summary["fallback_warnings"]:
            print(f"   fallback warning: {msg}")

    if args.as_json:
        print("RESULT_JSON_START")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
