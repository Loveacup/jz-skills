#!/usr/bin/env python3
"""Draft 2020-12 schema and semantic checks for destiny-matrix artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
except ImportError as exc:
    Draft202012Validator = None
    FormatChecker = None
    Registry = Resource = None

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
KINDS = ("intake_brief", "chart_bundle", "sources", "case_evidence", "judge_verdicts", "consistency_report", "chart_plan", "final_verdict", "runtime_trace")


def _issue(path: str, code: str, message: str) -> dict[str, str]:
    return {"path": path or "/", "code": code, "message": message}


def _schema_name(kind: str) -> str:
    return "chart_bundle.json" if kind == "chart_bundle" else f"{kind}.json"


def _registry():
    resources = {}
    for file in SCHEMA_DIR.glob("*.json"):
        try:
            schema = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        resource = Resource.from_contents(schema)
        resources[file.name] = resource
        resources[file.resolve().as_uri()] = resource
        if isinstance(schema.get("$id"), str):
            resources[schema["$id"]] = resource
    return Registry().with_resources(resources.items())


def _validate_schema(kind: str, data: Any) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        return [_issue("/", "dependency_missing", "jsonschema/reference resolver is unavailable")]
    path = SCHEMA_DIR / _schema_name(kind)
    if not path.is_file():
        return [_issue("/", "schema_missing", f"Required schema {_schema_name(kind)} is unavailable")]
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())
        issues = []
        for error in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
            pointer = "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in error.absolute_path)
            issues.append(_issue(pointer, "schema", f"schema rule failed: {error.validator or 'validation'}"))
        return issues
    except Exception as exc:
        return [_issue("/", "schema_error", f"Schema validation could not complete ({type(exc).__name__})")]


def route_topics(data: dict) -> list[str]:
    """Return required section routes; synastry lives inside relationships."""
    scope = data.get("scope", {})
    requested = scope.get("requested_topics", [])
    if scope.get("mode") == "focused":
        topics = [topic for topic in requested if topic != "synastry"]
    else:
        topics = ["personality", "bazi", "ziwei", "astrology", "synthesis", "timing", "relationships", "practice"]
        topics.extend(topic for topic in requested if topic in {"career", "wellbeing"})
    if "synastry" in requested and "relationships" not in topics:
        topics.append("relationships")
    return list(dict.fromkeys(topics))


def age_years(birth_date: str | date, as_of: str | date) -> int:
    """Return completed calendar years at the analysis date."""
    born = date.fromisoformat(birth_date) if isinstance(birth_date, str) else birth_date
    on = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def task_fingerprint(slice: dict, upstream_hashes: list, versions: dict, contract_hashes: dict, role_snapshot: dict) -> str:
    payload = {"slice": slice, "upstream_hashes": upstream_hashes, "versions": versions, "contract_hashes": contract_hashes, "role_snapshot": role_snapshot}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_dual_dates(subject: dict, path: str, issues: list[dict[str, str]]) -> None:
    lunar_date = subject.get("lunar_date")
    birth_date = subject.get("birth_date")
    if lunar_date is None:
        return
    try:
        from lunar_python import Lunar
        lunar_month = lunar_date["month"] if not lunar_date["is_leap_month"] else -lunar_date["month"]
        lunar_solar = Lunar.fromYmd(lunar_date["year"], lunar_month, lunar_date["day"]).getSolar().toYmd()
    except Exception:
        issues.append(_issue(f"{path}/lunar_date", "lunar_date_invalid", "lunar date or leap-month marker cannot be converted"))
        return
    if birth_date is None:
        return
    if subject.get("date_calendar") == "julian":
        try:
            import swisseph as swe
            year, month, day = map(int, birth_date.split("-"))
            jd = swe.julday(year, month, day, 0, swe.JUL_CAL)
            year, month, day, _ = swe.revjul(jd, swe.GREG_CAL)
            gregorian_date = f"{year:04d}-{month:02d}-{day:02d}"
        except Exception:
            issues.append(_issue(f"{path}/birth_date", "date_conversion_failed", "birth date could not be converted to Gregorian calendar"))
            return
    else:
        gregorian_date = birth_date
    if lunar_solar != gregorian_date:
        issues.append(_issue(f"{path}/lunar_date", "lunar_date_mismatch", "lunar date and Gregorian birth date resolve to different calendar days"))
def _intake(data: dict, issues: list[dict[str, str]]) -> None:
    ti = data.get("time_input", {})
    precision, start, end = ti.get("precision"), ti.get("start"), ti.get("end")
    if precision == "minute" and (not start or end is not None):
        issues.append(_issue("/time_input", "minute_shape", "minute precision requires start and forbids end"))
    if precision == "range" and (not start or not end):
        issues.append(_issue("/time_input", "range_shape", "range precision requires both start and end"))
    if precision == "branch" and not ti.get("branch_label"):
        issues.append(_issue("/time_input/branch_label", "branch_required", "branch precision requires a branch label"))
    scope = data.get("scope", {})
    requested = scope.get("requested_topics", [])
    if scope.get("mode") == "focused" and not requested:
        issues.append(_issue("/scope/requested_topics", "focused_empty", "focused scope requires at least one requested topic"))
    if scope.get("mode") == "full" and set(requested) - {"career", "wellbeing", "synastry"}:
        issues.append(_issue("/scope/requested_topics", "full_route", "full scope uses the default topics; only career, wellbeing, and synastry may be added"))
    pi = data.get("personality_input", {})
    if pi.get("construct") == "neris5" and pi.get("scores"):
        keys = set(pi["scores"])
        if keys & {"Ni", "Ne", "Si", "Se", "Ti", "Te", "Fi", "Fe"}:
            issues.append(_issue("/personality_input/scores", "construct_mismatch", "NERIS scores cannot be represented as eight-function measurements"))
    age = data.get("age_years")
    minor_mode = data.get("minor_mode")
    subject = data.get("subject", {})
    _validate_dual_dates(subject, "/subject", issues)
    birth_date = subject.get("birth_date")
    partner = data.get("synastry", {}).get("partner")
    if partner is not None:
        _validate_dual_dates(partner.get("subject", {}), "/synastry/partner/subject", issues)
    if birth_date and data.get("analysis_as_of"):
        try:
            if age != age_years(birth_date, data["analysis_as_of"]):
                issues.append(_issue("/age_years", "age_mismatch", "age_years must be calculated at analysis_as_of"))
        except ValueError:
            pass  # invalid calendar strings are already schema-format errors.
    if age is None and minor_mode is not None:
        issues.append(_issue("/minor_mode", "unknown_age_not_inferred", "unknown age must remain null; do not infer adulthood"))
    if age is not None and age < 18 and minor_mode is not True:
        issues.append(_issue("/minor_mode", "minor_mode_required", "people under 18 require minor_mode=true"))
    if age is not None and age >= 18 and minor_mode is True:
        issues.append(_issue("/minor_mode", "age_mode_mismatch", "minor_mode must reflect age at analysis_as_of"))
    syn = data.get("synastry", {})
    if syn.get("enabled") and syn.get("partner") is None and not data.get("open_gaps"):
        issues.append(_issue("/synastry/partner", "partner_missing", "enabled synastry requires partner details or a recorded open gap"))
    transcription = pi.get("transcription")
    if transcription:
        first_rows = transcription.get("first_pass", [])
        second_rows = transcription.get("second_pass", [])
        first_keys = [row["key"] for row in first_rows]
        second_keys = [row["key"] for row in second_rows]
        if len(first_keys) != len(set(first_keys)) or len(second_keys) != len(set(second_keys)):
            issues.append(_issue("/personality_input/transcription", "transcription_duplicate_key", "each transcription pass must contain one row per key"))
        first = {row["key"]: (row.get("value"), row.get("scale")) for row in first_rows}
        second = {row["key"]: (row.get("value"), row.get("scale")) for row in second_rows}
        differs = first != second
        if differs and transcription.get("status") != "needs_clarification":
            issues.append(_issue("/personality_input/transcription/status", "transcription_mismatch", "different independent transcriptions require needs_clarification"))
        if differs:
            issues.append(_issue("/personality_input/transcription", "transcription_mismatch", "transcription disagreement must be resolved from the image; averaging is prohibited"))
        elif transcription.get("status") == "verified" and not transcription.get("image_refs"):
            issues.append(_issue("/personality_input/transcription/image_refs", "image_reference_missing", "verified screenshot transcription requires image references"))
    if syn.get("enabled") and "relationships" not in route_topics(data):
        issues.append(_issue("/synastry/enabled", "synastry_route", "enabled synastry must route into relationships"))


def _cycle(nodes: set[str], edges: dict[str, set[str]]) -> bool:
    visiting: set[str] = set(); done: set[str] = set()
    def visit(node: str) -> bool:
        if node in visiting: return True
        if node in done: return False
        visiting.add(node)
        if any(visit(child) for child in edges.get(node, set()) if child in nodes): return True
        visiting.remove(node); done.add(node); return False
    return any(visit(n) for n in nodes if n not in done)


def _case_evidence(data: dict, issues: list[dict[str, str]], base_dir: str | None) -> None:
    artifacts = data.get("artifacts", []); sources = data.get("sources", []); claims = data.get("claims", [])
    aid = [x.get("artifact_id") for x in artifacts]; sid = [x.get("source_id") for x in sources]; cid = [x.get("claim_id") for x in claims]
    for name, ids in (("artifacts", aid), ("sources", sid), ("claims", cid)):
        if len(ids) != len(set(ids)): issues.append(_issue(f"/{name}", "duplicate_id", f"{name} IDs must be unique"))
    amap, smap, cmap = ({x.get("artifact_id"): x for x in artifacts}, {x.get("source_id"): x for x in sources}, {x.get("claim_id"): x for x in claims})
    for index, artifact in enumerate(artifacts):
        for claim_id in artifact.get("depends_on_claim_ids", []):
            if claim_id not in cmap: issues.append(_issue(f"/artifacts/{index}/depends_on_claim_ids", "dangling_claim", "artifact references an unknown claim"))
        for dep in artifact.get("depends_on_artifact_ids", []):
            if dep not in amap: issues.append(_issue(f"/artifacts/{index}/depends_on_artifact_ids", "dangling_artifact", "artifact references an unknown artifact"))
        p = Path(artifact.get("path", ""))
        if p.is_absolute():
            issues.append(_issue(f"/artifacts/{index}/path", "unsafe_path", "artifact paths must be relative to base_dir"))
            continue
        if base_dir is not None:
            root = Path(base_dir).resolve()
            resolved = (root / p).resolve()
            try: resolved.relative_to(root)
            except ValueError:
                issues.append(_issue(f"/artifacts/{index}/path", "unsafe_path", "artifact path escapes base_dir")); continue
            if not resolved.is_file():
                issues.append(_issue(f"/artifacts/{index}/path", "artifact_missing", "referenced artifact file is unavailable")); continue
            if hashlib.sha256(resolved.read_bytes()).hexdigest() != artifact.get("sha256"):
                issues.append(_issue(f"/artifacts/{index}/sha256", "hash_mismatch", "artifact hash does not match file"))
    for index, claim in enumerate(claims):
        for source_id in claim.get("source_ids", []):
            if source_id not in smap: issues.append(_issue(f"/claims/{index}/source_ids", "dangling_source", "claim references an unknown source"))
        for parent in claim.get("parent_claim_ids", []):
            if parent not in cmap: issues.append(_issue(f"/claims/{index}/parent_claim_ids", "dangling_claim", "claim references an unknown parent claim"))
            elif claim.get("status") == "active" and cmap[parent].get("status") in ("superseded", "rejected"):
                issues.append(_issue(f"/claims/{index}/parent_claim_ids", "stale_dependency", "active claim depends on a superseded or rejected claim"))
        for ref in claim.get("input_refs", []):
            artifact = amap.get(ref.get("artifact_id"))
            if artifact is None: issues.append(_issue(f"/claims/{index}/input_refs", "dangling_artifact", "claim references an unknown artifact"))
            elif ref.get("sha256") != artifact.get("sha256"): issues.append(_issue(f"/claims/{index}/input_refs", "hash_mismatch", "claim input reference hash differs from registered artifact"))
    if _cycle(set(cid), {c.get("claim_id"): set(c.get("parent_claim_ids", [])) for c in claims}):
        issues.append(_issue("/claims", "dependency_cycle", "claim dependency graph contains a cycle"))
    artifact_edges = {a.get("artifact_id"): set(a.get("depends_on_artifact_ids", [])) for a in artifacts}
    if _cycle(set(aid), artifact_edges): issues.append(_issue("/artifacts", "dependency_cycle", "artifact dependency graph contains a cycle"))
    invalidated = set()
    for index, correction in enumerate(data.get("corrections", [])):
        invalid = set(correction.get("invalidated_claim_ids", []))
        for claim_id in invalid | set(correction.get("replacement_claim_ids", [])):
            if claim_id not in cmap:
                issues.append(_issue(f"/corrections/{index}", "dangling_claim", "correction references an unknown claim"))
        invalidated |= invalid
    changed=True
    while changed:
        changed=False
        for claim in claims:
            if set(claim.get("parent_claim_ids", [])) & invalidated and claim.get("claim_id") not in invalidated:
                invalidated.add(claim.get("claim_id")); changed=True
    for index, claim in enumerate(claims):
        if claim.get("claim_id") in invalidated and claim.get("status") == "active":
            issues.append(_issue(f"/claims/{index}/status", "correction_not_propagated", "invalidated claim remains active"))
    affected_artifacts={a.get("artifact_id") for a in artifacts if set(a.get("depends_on_claim_ids", [])) & invalidated}
    changed=True
    while changed:
        changed=False
        for artifact in artifacts:
            if set(artifact.get("depends_on_artifact_ids", [])) & affected_artifacts and artifact.get("artifact_id") not in affected_artifacts:
                affected_artifacts.add(artifact.get("artifact_id")); changed=True
    for index, artifact in enumerate(artifacts):
        if artifact.get("artifact_id") in affected_artifacts and artifact.get("status") == "current":
            issues.append(_issue(f"/artifacts/{index}/status", "correction_not_propagated", "artifact depending on invalidated evidence remains current"))
    for index, limitation in enumerate(data.get("limitations", [])):
        for claim_id in limitation.get("affected_claim_ids", []):
            if claim_id not in cmap: issues.append(_issue(f"/limitations/{index}/affected_claim_ids", "dangling_claim", "limitation references an unknown claim"))
        if limitation.get("affected_claim_ids") and limitation.get("required_placement") == "appendix" and any(word in limitation.get("impact", "").lower() for word in ("changes conclusion", "critical", "material")):
            issues.append(_issue(f"/limitations/{index}/required_placement", "limitation_placement", "material limitations must be disclosed in opening or adjacent text"))
    for index, claim in enumerate(claims):
        parents = [cmap[p] for p in claim.get("parent_claim_ids", []) if p in cmap]
        subjects = {p.get("subject_id") for p in parents if p.get("subject_id") != "joint"}
        if len(subjects) > 1 and claim.get("subject_id") != "joint": issues.append(_issue(f"/claims/{index}/subject_id", "subject_crossing", "cross-person evidence must be marked joint"))


def _sources(data: dict, issues: list[dict[str, str]]) -> None:
    rows=data.get("sources",[]); ids=[]; quote_ids=[]
    for i,row in enumerate(rows):
        ids.append(row.get("source_id")); quote_ids.extend(q.get("quote_id") for q in row.get("quotes",[]))
        if row.get("verification_status")=="verified" and not (row.get("locator") or row.get("url")):
            issues.append(_issue(f"/sources/{i}","source_unlocated","verified source requires a locator or URL"))
        if row.get("verification_status")=="unverified" and row.get("quotes"):
            issues.append(_issue(f"/sources/{i}/quotes","unverified_quote","unverified sources cannot provide publishable quotations"))
    if len(ids)!=len(set(ids)): issues.append(_issue("/sources","duplicate_id","source_id values must be unique"))
    if len(quote_ids)!=len(set(quote_ids)): issues.append(_issue("/sources","duplicate_quote_id","quote_id values must be globally unique"))


def _chart_plan(data: dict, issues: list[dict[str, str]]) -> None:
    sections={s.get("section_id") for s in data.get("sections",[])}; rows=data.get("chart_table",[]); counts={}; seen=set()
    for i,row in enumerate(rows):
        sid=row.get("section_id"); counts[sid]=counts.get(sid,0)+1
        if sid not in sections: issues.append(_issue(f"/chart_table/{i}/section_id","unknown_section","chart must reference a declared section"))
        if row.get("chart_id")!=f"chart-{sid}-{counts[sid]:02d}": issues.append(_issue(f"/chart_table/{i}/chart_id","chart_sequence","chart IDs must be continuous within each section"))
        if row.get("chart_id") in seen: issues.append(_issue(f"/chart_table/{i}/chart_id","duplicate_id","chart IDs must be unique"))
        seen.add(row.get("chart_id"))
        if row.get("representation") in ("measured","computed") and (not row.get("unit") or not isinstance(row.get("domain"),list)):
            issues.append(_issue(f"/chart_table/{i}","numeric_chart_domain","measured and computed charts require unit and domain"))
        if row.get("representation")=="qualitative" and (row.get("unit") is not None or row.get("domain") is not None):
            issues.append(_issue(f"/chart_table/{i}","qualitative_domain","qualitative charts require null unit and domain"))
    if data.get("total",{}).get("planned")!=len(rows): issues.append(_issue("/total/planned","chart_total_mismatch","total.planned must equal chart_table row count"))
    if data.get("scope_mode")=="full" and not rows and not data.get("planning_rationale"):
        issues.append(_issue("/planning_rationale","empty_full_charts","full scope with no charts requires an explicit rationale"))


def _judge(data: dict, issues: list[dict[str, str]]) -> None:
    expected = [(row["subject_id"], row["dimension"]) for row in data.get("expected_judges", [])]
    judges = data.get("judges", [])
    actual = [(row["subject_id"], row["dimension"]) for row in judges]
    if len(expected) != len(set(expected)):
        issues.append(_issue("/expected_judges", "duplicate_expected_judge", "expected judge pairs must be unique"))
    if len(actual) != len(set(actual)):
        issues.append(_issue("/judges", "duplicate_judge", "judge pairs must be unique"))
    if set(expected) - set(actual):
        issues.append(_issue("/judges", "missing_applicable_judge", "every applicable subject/dimension requires exactly one judge"))
    if set(actual) - set(expected):
        issues.append(_issue("/judges", "unexpected_judge", "judge results must match the applicable subject/dimension set"))
    for i, judge in enumerate(judges):
        if judge.get("isolation_level") == "unavailable" and judge.get("independent_readings"):
            issues.append(_issue(f"/judges/{i}/independent_readings", "blind_review_unavailable", "cannot claim independent blind readings when input isolation is unavailable"))


def _final(data: dict, issues: list[dict[str, str]]) -> None:
    required=set("I1 I2 I3 A1 A2 A3 R1 R2 R3 D1 D2 D3 D4 P1 P2 P3".split()); rows=data.get("checklist_results",[]); ids=[r.get("id") for r in rows]
    if set(ids)!=required or len(ids)!=16: issues.append(_issue("/checklist_results","checklist_ids","all 16 checklist IDs must appear exactly once"))
    for i,row in enumerate(rows):
        if row.get("verdict")=="na" and not row.get("reason","").strip(): issues.append(_issue(f"/checklist_results/{i}/reason","na_reason","na requires a condition-specific reason"))
        if row.get("verdict")=="deferred" and not (data.get("review_phase")=="pre_export" and row.get("id") in {"P1","P2","P3"}):
            issues.append(_issue(f"/checklist_results/{i}/verdict","deferred_not_allowed","deferred is allowed only for pre_export P1-P3"))
    decision = data.get("decision")
    if data.get("review_phase") == "pre_export" and decision == "pass":
        issues.append(_issue("/decision", "pre_export_pass", "pre_export cannot produce pass"))
    if decision == "awaiting_export" and (data.get("review_phase") != "pre_export" or any(r.get("verdict") == "fail" for r in rows) or data.get("blocked_items")):
        issues.append(_issue("/decision", "invalid_awaiting_export", "awaiting_export requires pre_export, no failed checks, and no blockers"))
    if decision == "pass":
        if data.get("review_phase") != "post_export" or any(r.get("verdict") not in {"pass", "na"} for r in rows) or data.get("blocked_items"):
            issues.append(_issue("/decision", "invalid_pass", "pass requires post_export, only pass/na checks, and no blockers"))
        if not data.get("visual_qa"):
            issues.append(_issue("/visual_qa", "visual_evidence_missing", "pass requires actual visual QA evidence"))
        hashes = data.get("artifact_hashes", {})
        if not hashes.get("html") or not hashes.get("pdf"):
            issues.append(_issue("/artifact_hashes", "artifact_hash_missing", "pass requires HTML and PDF hashes"))
        exported = data.get("export_result") or {}
        if exported.get("html_sha256") != hashes.get("html"):
            issues.append(_issue("/artifact_hashes/html", "artifact_hash_mismatch", "HTML hash must match the export record"))
        if exported.get("pdf_sha256") != hashes.get("pdf"):
            issues.append(_issue("/artifact_hashes/pdf", "artifact_hash_mismatch", "PDF hash must match the export record"))
    if decision == "revise" and not data.get("revision_instructions"):
        issues.append(_issue("/revision_instructions", "revision_instructions_missing", "revise requires actionable revision instructions"))
    if decision == "blocked" and not data.get("blocked_items"):
        issues.append(_issue("/blocked_items", "blocked_reason_missing", "blocked decisions require at least one blocking item"))


def _runtime_trace(data: dict, issues: list[dict[str, str]]) -> None:
    seen=set()
    for i,task in enumerate(data.get("tasks",[])):
        events=task.get("usage_events",[])
        if not events:
            issues.append(_issue(f"/tasks/{i}/usage_events","usage_coverage","no attributable usage telemetry; report as unknown, not zero"))
        for j,event in enumerate(events):
            event_id=event.get("event_id")
            if event_id in seen: issues.append(_issue(f"/tasks/{i}/usage_events/{j}/event_id","duplicate_event_id","usage event IDs must be unique"))
            seen.add(event_id)
            if any(event.get(key) is None for key in ("input_tokens","output_tokens","cost")):
                issues.append(_issue(f"/tasks/{i}/usage_events/{j}","usage_coverage","usage event has incomplete telemetry; retain null and report partial coverage"))


def check(kind: str, data: dict, *, evidence: dict | None = None, base_dir: str | None = None) -> list[dict]:
    """Return contract issues; empty list means the artifact passed."""
    if kind not in KINDS: return [_issue("/kind","unknown_kind","unsupported contract kind")]
    issues=_validate_schema(kind,data)
    if issues: return issues
    if kind=="intake_brief": _intake(data,issues)
    elif kind=="case_evidence": _case_evidence(data,issues,base_dir)
    elif kind=="sources": _sources(data,issues)
    elif kind=="chart_plan": _chart_plan(data,issues)
    elif kind=="judge_verdicts": _judge(data,issues)
    elif kind=="consistency_report":
        discrepancies=data.get("discrepancies",[])
        by_id={row.get("id"):row for row in discrepancies}
        correction_rounds=data.get("correction_rounds",[])
        round_keys=[(row["subject_id"],row["dimension"]) for row in correction_rounds]
        if len(round_keys)!=len(set(round_keys)):
            issues.append(_issue("/correction_rounds","duplicate_correction_round","each applicable subject/dimension has one correction-round row"))
        for index,row in enumerate(discrepancies):
            if row.get("kind") in {"calculation_error","source_error","unsupported_inference"} and row.get("severity")!="blocking":
                issues.append(_issue(f"/discrepancies/{index}/severity","blocking_severity","calculation/source/unsupported-inference discrepancies must block"))
        for index,row in enumerate(correction_rounds):
            round_no=row.get("round")
            round2_ids=row.get("round2_trigger_discrepancy_ids",[])
            if not (set(row.get("trigger_discrepancy_ids",[]))|set(round2_ids)) <= set(by_id):
                issues.append(_issue(f"/correction_rounds/{index}/trigger_discrepancy_ids","dangling_discrepancy","correction-round trigger references an unknown discrepancy"))
            if round_no==2:
                if not round2_ids:
                    issues.append(_issue(f"/correction_rounds/{index}/round2_trigger_discrepancy_ids","round2_trigger_missing","round 2 must list the round-1-introduced discrepancies that triggered it"))
                elif any(by_id.get(i,{}).get("introduced_in_round")!=1 for i in round2_ids):
                    issues.append(_issue(f"/correction_rounds/{index}/round2_trigger_discrepancy_ids","round2_trigger_not_new","round 2 may only target discrepancies introduced by the round-1 correction"))
            elif round2_ids:
                issues.append(_issue(f"/correction_rounds/{index}/round2_trigger_discrepancy_ids","round2_trigger_without_round2","round-2 triggers require round 2"))
            blocking=[d for d in discrepancies if d.get("dimension_owner")==row.get("dimension") and d.get("severity")=="blocking"]
            final_round = round_no==2 or (round_no==1 and any(d.get("introduced_in_round")!=1 for d in blocking))
            if final_round and blocking and data.get("verdict")!="blocked":
                issues.append(_issue("/verdict","correction_round_blocked","a blocking discrepancy remains after the last allowed correction round; verdict must be blocked"))
    elif kind=="final_verdict": _final(data,issues)
    elif kind=="runtime_trace": _runtime_trace(data,issues)
    return issues


class _ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        result = {"ok": False, "kind": None, "issues": [_issue("/", "argument_error", "invalid command-line arguments")]}
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        print(f"quality_contracts: {message}", file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser=_ContractArgumentParser(description="Validate destiny-matrix JSON contracts")
    parser.add_argument("kind",choices=KINDS); parser.add_argument("json_path"); parser.add_argument("--evidence"); parser.add_argument("--json",action="store_true")
    args=parser.parse_args(argv)
    try:
        data=json.loads(Path(args.json_path).read_text(encoding="utf-8"))
        evidence=json.loads(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else None
    except (OSError,json.JSONDecodeError) as exc:
        print(json.dumps({"ok":False,"kind":args.kind,"issues":[_issue("/","file_error",f"Cannot read valid JSON input ({type(exc).__name__})")]},ensure_ascii=False))
        print(f"quality_contracts: input read failed ({type(exc).__name__})",file=sys.stderr); return 2
    issues=_validate_schema(args.kind,data) if args.kind=="chart_bundle" else check(args.kind,data,evidence=evidence,base_dir=str(Path(args.json_path).resolve().parent))
    blocking=[issue for issue in issues if issue["code"]!="usage_coverage"]
    result={"ok":not blocking,"kind":args.kind,"issues":issues}
    print(json.dumps(result,ensure_ascii=False,separators=(",",":")))
    if blocking:
        print(f"quality_contracts: {len(blocking)} contract issue(s)", file=sys.stderr)
    return 0 if not blocking else 1


if __name__=="__main__":
    raise SystemExit(main())