#!/usr/bin/env python3
"""Deterministic checks for the S5 synthesizer output against the case evidence ledger.

A synthesis claim only counts as synthesis when its parents come from at least two
systems; `convergent` and `tension` rows must cite at least two systems; the core
propositions together must cover three systems (or every available one when the case
has fewer). Which system a claim belongs to is read from the ledger's `owner`; when the
owner does not name a system, the matrix column that cites the claim decides.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from quality_contracts import _issue, _validate_schema
except ImportError:  # imported as scripts.synthesis_contract
    from scripts.quality_contracts import _issue, _validate_schema

SYSTEMS = ("personality", "bazi", "ziwei", "astro")
COLUMNS = {system: f"{system}_claim_ids" for system in SYSTEMS}
# owner 为席位名（如 bazi-analyst、jung）；按其中的体系词归属，synthesizer 与专题席位不属于任何单一体系
OWNER_TOKENS = (("personality", ("jung", "personality", "mbti")), ("bazi", ("bazi",)),
                ("ziwei", ("ziwei",)), ("astro", ("astro",)))
CROSS_OWNERS = ("synthesizer", "specialist")
CROSS_RELATIONSHIPS = ("convergent", "tension")
REQUIRED_COVERAGE = 3
ESCALATIONS = ("三重印证", "四重印证", "相互印证", "互相印证", "彼此印证", "相互验证", "互相验证", "三重验证",
               "可信度提高", "严丝合缝", "命运密码", "终极课题", "科学证明", "科学验证")
# 未成年人兜底词表：只能拦住常见说法，不能代替 I3 终审
MINOR_ROMANCE = re.compile(
    "婚姻|婚恋|结婚|恋爱|恋情|早恋|暗恋|配偶|伴侣|择偶|另一半|姻缘|正缘|约会|相亲|生育|男朋友|女朋友|男女朋友"
    "|夫星|妻星|夫妻宫|子女宫|桃花(?!源)|(?:找|谈|处|搞|交|有了?)对象")
MINOR_CAREER = re.compile("适合(?:当|做|从事|担任)|(?:将来|以后|长大后?)(?:会|要|能|可以)?(?:当|成为|从事)|职业(?:方向|选择|判定|规划)")
MINOR_ABILITY = re.compile(
    "智力(?:偏低|低下|不足|一般)|智商|能力(?:不足|缺陷|偏低|较差|差|弱)|(?:学习|阅读|社交|情绪)障碍|注意力(?:缺陷|不足)"
    "|多动症|天赋(?:不足|平平)|反应(?:迟钝|慢)|不是(?:读书|学习)的料|笨")
TYPE_NAME = re.compile(r"(?<![A-Za-z])[EI][SN][TF][JP](?![A-Za-z])")
NEGATION = re.compile("(?:不谈|不写|不读|不讲|不涉及|不讨论|不作|不出现|略去|省去|避开)[^。；;！？!?\n]{0,12}$")
TRADITIONAL = str.maketrans("結戀愛對緣約會親侶擇婦宮業職適當從事將來長後為學習閱讀礙證驗訓終極運學歷緒態題",
                            "结恋爱对缘约会亲侣择妇宫业职适当从事将来长后为学习阅读碍证验训终极运学历绪态题")
SPACES = re.compile(r"[\s\u3000\u200b\u200c\u200d\ufeff]+")


def normalize(text: str) -> str:
    """繁体常用字转简体并去掉全部空白，供词表匹配。"""
    return SPACES.sub("", text).translate(TRADITIONAL)


def owner_system(owner: Any) -> str | None:
    text = str(owner or "").lower()
    found = [system for system, tokens in OWNER_TOKENS if any(token in text for token in tokens)]
    return found[0] if len(found) == 1 else None


class _Ledger:
    """Active claims of the evidence ledger plus the synthesis claims under review."""

    def __init__(self, evidence: dict, synthesis: dict):
        self.evidence = {c.get("claim_id"): c for c in evidence.get("claims", [])}
        self.local = {c.get("claim_id"): c for c in synthesis.get("synthesis_claims", [])}
        self.column = {}
        for row in synthesis.get("matrix", []):
            for system, key in COLUMNS.items():
                for claim_id in row.get(key, []):
                    self.column.setdefault(claim_id, set()).add(system)

    def get(self, claim_id: str) -> dict | None:
        return self.local.get(claim_id) or self.evidence.get(claim_id)

    def usable(self, claim_id: str) -> bool:
        # 本次返回的综合主张尚未登记，没有 status；账本里的主张必须明确为 active
        if claim_id in self.local:
            return self.local[claim_id].get("status", "active") == "active"
        return self.evidence.get(claim_id, {}).get("status") == "active"

    def own_system(self, claim_id: str) -> str | None:
        if claim_id in self.local:
            return None
        claim = self.evidence.get(claim_id)
        if claim is None:
            return None
        owner = str(claim.get("owner") or "").lower()
        system = owner_system(owner)
        if system is None and not any(word in owner for word in CROSS_OWNERS) and len(self.column.get(claim_id, ())) == 1:
            system = next(iter(self.column[claim_id]))
        return system

    def parents(self, claim_id: str) -> list[str]:
        return [p for p in (self.get(claim_id) or {}).get("parent_claim_ids", []) if self.get(p) is not None]

    def reaches(self, start: str, target: str) -> bool:
        stack, seen = [start], set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node not in seen:
                seen.add(node)
                stack.extend(self.parents(node))
        return False

    def cyclic_parents(self, claim_id: str) -> list[str]:
        """Parents that lead back to the claim itself."""
        return [p for p in self.parents(claim_id) if self.reaches(p, claim_id)]

    def systems(self, claim_id: str, _seen: frozenset = frozenset()) -> set[str]:
        """Systems a claim rests on: its own, or those of its ancestors for cross-system claims.

        Edges that lie on a dependency cycle are not followed, so a claim cannot borrow a system through a loop.
        """
        if claim_id in _seen:
            return set()
        own = self.own_system(claim_id)
        if own:
            return {own}
        found = set()
        blocked = set(self.cyclic_parents(claim_id))
        for parent in self.parents(claim_id):
            if parent not in blocked and self.usable(parent):
                found |= self.systems(parent, _seen | {claim_id})
        return found

    def grounded(self, claim_id: str, _seen: frozenset = frozenset()) -> bool:
        """True when the claim, or one of its ancestors, points into a registered artifact."""
        if claim_id in _seen:
            return False
        claim = self.get(claim_id) or {}
        if claim.get("input_refs"):
            return True
        return any(self.grounded(p, _seen | {claim_id}) for p in claim.get("parent_claim_ids", []))

    def available(self) -> set[str]:
        return {self.own_system(cid) for cid in self.evidence if self.usable(cid) and self.own_system(cid)}


def _refs(ledger: _Ledger, claim_ids: list, path: str, issues: list, *, local_ok: bool) -> list[str]:
    """Report unknown or inactive references; return the usable ones."""
    good = []
    for claim_id in claim_ids:
        if claim_id in ledger.local and not local_ok:
            issues.append(_issue(path, "synthesis_claim_in_matrix", f"{claim_id} is a synthesis claim; matrix columns cite each system's own claims"))
        elif ledger.get(claim_id) is None:
            issues.append(_issue(path, "dangling_claim", f"{claim_id} is not registered in case_evidence or returned in synthesis_claims"))
        elif not ledger.usable(claim_id):
            issues.append(_issue(path, "inactive_claim", f"{claim_id} is {ledger.get(claim_id).get('status')}; cite active claims only"))
        else:
            good.append(claim_id)
    return good


def _matrix(data: dict, ledger: _Ledger, issues: list) -> None:
    themes = [row.get("theme", "").strip() for row in data.get("matrix", [])]
    if len(themes) != len(set(themes)):
        issues.append(_issue("/matrix", "duplicate_theme", "each theme has one matrix row"))
    claim_parents = [set(c.get("parent_claim_ids", [])) for c in data.get("synthesis_claims", [])]
    for index, row in enumerate(data.get("matrix", [])):
        cited = {}
        for system, key in COLUMNS.items():
            path = f"/matrix/{index}/{key}"
            good = _refs(ledger, row.get(key, []), path, issues, local_ok=False)
            for claim_id in good:
                own = owner_system(ledger.evidence[claim_id].get("owner"))
                if own and own != system:
                    issues.append(_issue(path, "matrix_column_mismatch", f"{claim_id} belongs to {own} but is cited in the {system} column"))
            kept = [c for c in good if owner_system(ledger.evidence[c].get("owner")) in (None, system)]
            if kept:
                cited[system] = kept
        relationship = row.get("relationship")
        if not cited:
            issues.append(_issue(f"/matrix/{index}", "matrix_row_empty", "a matrix row cites at least one usable claim"))
            continue
        if relationship not in CROSS_RELATIONSHIPS:
            continue
        if len(cited) < 2:
            issues.append(_issue(f"/matrix/{index}/relationship", "relationship_needs_two_systems",
                                 f"{relationship} requires claims from at least two systems; this row cites {len(cited)}"))
            continue
        if relationship == "convergent":
            bare = [s for s, ids in cited.items() if not any(ledger.grounded(c) for c in ids)]
            if bare:
                issues.append(_issue(f"/matrix/{index}/relationship", "convergent_without_chart_basis",
                                     "convergent requires every cited system to rest on chart or score evidence (input_refs); missing: " + ",".join(bare)))
        row_sets = [set(ids) for ids in cited.values()]
        if not any(sum(1 for ids in row_sets if ids & parents) >= 2 for parents in claim_parents):
            issues.append(_issue(f"/matrix/{index}", "matrix_row_without_claim",
                                 f"a {relationship} row needs a synthesis claim whose parents include this row's claims from at least two systems"))


def _claims(data: dict, ledger: _Ledger, issues: list) -> None:
    ids = [c.get("claim_id") for c in data.get("synthesis_claims", [])]
    if len(ids) != len(set(ids)):
        issues.append(_issue("/synthesis_claims", "duplicate_id", "synthesis claim IDs must be unique"))
    for index, claim in enumerate(data.get("synthesis_claims", [])):
        claim_id = claim.get("claim_id")
        registered = ledger.evidence.get(claim_id)
        if registered is not None and registered.get("owner") != "synthesizer":
            issues.append(_issue(f"/synthesis_claims/{index}/claim_id", "claim_id_collision", f"{claim_id} is already registered to {registered.get('owner')}"))
        path = f"/synthesis_claims/{index}/parent_claim_ids"
        parents = claim.get("parent_claim_ids", [])
        loop = ledger.cyclic_parents(claim_id)
        if loop:
            issues.append(_issue(path, "dependency_cycle", "parent chain leads back to this claim through: " + ",".join(loop)))
        _refs(ledger, [p for p in parents if p != claim_id], path, issues, local_ok=True)
        systems = ledger.systems(claim_id)
        if len(systems) < 2:
            issues.append(_issue(path, "single_system_synthesis",
                                 "a synthesis claim rests on active parent claims from at least two systems; found: " + (",".join(sorted(systems)) or "none")))
        subjects = {ledger.get(p).get("subject_id") for p in parents if ledger.get(p)} - {"joint", None}
        if len(subjects) > 1 and claim.get("subject_id") != "joint":
            issues.append(_issue(f"/synthesis_claims/{index}/subject_id", "subject_crossing", "cross-person evidence must be marked joint"))
        if claim.get("kind") == "psychological_hypothesis" and not any(
                (ledger.get(p) or {}).get("kind") in ("reported_observation", "psychological_hypothesis") for p in parents):
            issues.append(_issue(f"/synthesis_claims/{index}/kind", "hypothesis_without_observation",
                                 "a psychological_hypothesis needs a parent that is a reported observation or a personality hypothesis; pure cultural synthesis is traditional_interpretation"))


def _propositions(data: dict, ledger: _Ledger, issues: list) -> dict:
    rows = data.get("core_propositions", [])
    ids = [row.get("proposition_id") for row in rows]
    if len(ids) != len(set(ids)):
        issues.append(_issue("/core_propositions", "duplicate_id", "proposition IDs must be unique"))
    statements = [re.sub(r"\s+", "", row.get("statement", "")) for row in rows]
    if len(statements) != len(set(statements)):
        issues.append(_issue("/core_propositions", "duplicate_statement", "each proposition states a different judgment"))
    covered = set()
    for index, row in enumerate(rows):
        good = _refs(ledger, row.get("claim_ids", []), f"/core_propositions/{index}/claim_ids", issues, local_ok=True)
        for claim_id in good:
            covered |= ledger.systems(claim_id)
        for field in ("image", "statement"):
            _escalation(row.get(field), f"/core_propositions/{index}/{field}", "proposition_escalation", issues)
    available = ledger.available()
    required = min(REQUIRED_COVERAGE, len(available)) if available else REQUIRED_COVERAGE
    if len(covered) < required:
        issues.append(_issue("/core_propositions", "proposition_coverage",
                             f"core propositions together must cover {required} systems; covered: " + (",".join(sorted(covered)) or "none")))
    return {"available_systems": sorted(available), "required_systems": required, "covered_systems": sorted(covered)}


def _escalation(value: Any, path: str, code: str, issues: list) -> None:
    text = normalize(value) if isinstance(value, str) else ""
    hit = [word for word in ESCALATIONS if word in text]
    if hit:
        issues.append(_issue(path, code, "states convergence as proof or destiny formula: " + "、".join(hit)))


def _strings(path: str, value: Any, skip: tuple = ()):
    """Yield (path, text) for every string below value, leaving out the audit-only keys in skip."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _strings(f"{path}/{i}", item, skip)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in skip:
                yield from _strings(f"{path}/{key}", item, skip)


READER_KEYS = ("matrix", "synthesis_claims", "core_propositions", "outline", "action_options", "limitation_increments")
AUDIT_KEYS = ("limits", "counterevidence", "impact", "input_refs", "source_ids", "parent_claim_ids", "claim_ids",
              "claim_id", "affected_claim_ids", "personality_claim_ids", "bazi_claim_ids", "ziwei_claim_ids",
              "astro_claim_ids", "question_ids", "limitation_ids", "proposition_id", "section_id", "kind",
              "subject_id", "relationship", "required_placement", "owner", "status")


def _wording(data: dict, issues: list) -> None:
    for key in ("synthesis_claims", "outline", "action_options", "limitation_increments"):
        for path, text in _strings(f"/{key}", data.get(key), AUDIT_KEYS):
            _escalation(text, path, "escalation_wording", issues)


def _outline(data: dict, ledger: _Ledger, issues: list) -> None:
    sections = data.get("outline", {}).get("sections", [])
    section_ids = [s.get("section_id") for s in sections]
    if len(section_ids) != len(set(section_ids)):
        issues.append(_issue("/outline/sections", "duplicate_id", "each section_id appears once"))
    text = ""
    for index, section in enumerate(sections):
        _refs(ledger, section.get("claim_ids", []), f"/outline/sections/{index}/claim_ids", issues, local_ok=True)
        text += "\n".join(section.get("required_content", [])) + "\n"
        if section.get("section_id") == "synthesis" and not set(section.get("claim_ids", [])) & set(ledger.local):
            issues.append(_issue(f"/outline/sections/{index}/claim_ids", "synthesis_section_without_claims",
                                 "the synthesis section cites the synthesis claims it must explain"))
    for index, row in enumerate(data.get("core_propositions", [])):
        if row.get("proposition_id") and row["proposition_id"] not in text:
            issues.append(_issue(f"/core_propositions/{index}/proposition_id", "proposition_unplaced",
                                 f"no section's required_content names {row['proposition_id']}; every proposition is echoed by a section"))
    for index, option in enumerate(data.get("action_options", [])):
        _refs(ledger, option.get("claim_ids", []), f"/action_options/{index}/claim_ids", issues, local_ok=True)


def _minor(data: dict, intake: dict, issues: list, warnings: list) -> None:
    guardian = intake.get("audience") in ("guardian", "both")
    for key in READER_KEYS:
        for path, raw in _strings(f"/{key}", data.get(key), AUDIT_KEYS):
            text = normalize(raw)
            for match in MINOR_ROMANCE.finditer(text):
                if NEGATION.search(text[:match.start()]):
                    warnings.append(_issue(path, "minor_theme_negated", f"“{match.group()}” appears in a negated context; confirm the sentence excludes the theme"))
                else:
                    issues.append(_issue(path, "minor_theme", "minor_mode replaces romance and marriage themes with family, peers, teachers and boundaries: " + match.group()))
            for pattern, code, message in (
                    (MINOR_CAREER, "minor_career_verdict", "for minors, career becomes learning and interests; no occupation verdicts: "),
                    (MINOR_ABILITY, "minor_ability_label", "no ability-deficit labels for minors: ")):
                for match in pattern.finditer(text):
                    issues.append(_issue(path, code, message + match.group()))
            names = sorted(set(TYPE_NAME.findall(raw)))
            if names:
                row = _issue(path, "minor_type_name", "reader text for minors describes what the dominant and auxiliary functions do; "
                             "type names belong to the guardian section or appendix: " + ",".join(names))
                (warnings if guardian else issues).append(row)


def check(data: dict, evidence: dict, *, intake: dict | None = None) -> tuple[list[dict], dict]:
    """Return (issues, report); an empty issue list means the synthesis passed.

    report carries the system coverage, `minor_check` (applied, not_applicable or skipped) and non-blocking `warnings`.
    """
    issues = _validate_schema("synthesis", data)
    if issues:
        return issues, {}
    if not isinstance(evidence, dict) or not isinstance(evidence.get("claims"), list):
        return [_issue("/", "evidence_invalid", "case_evidence must be an object with a claims array")], {}
    warnings = []
    ledger = _Ledger(evidence, data)
    _matrix(data, ledger, issues)
    _claims(data, ledger, issues)
    coverage = _propositions(data, ledger, issues)
    _outline(data, ledger, issues)
    _wording(data, issues)
    if intake is None:
        minor_check = "skipped"
        warnings.append(_issue("/", "minor_check_skipped", "no intake_brief was supplied; the minor_mode checks did not run"))
    elif intake.get("minor_mode") is False:
        minor_check = "not_applicable"
    else:
        minor_check = "applied"
        _minor(data, intake, issues, warnings)
    return issues, {**coverage, "minor_check": minor_check, "warnings": warnings}


class _ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"ok": False, "kind": "synthesis", "issues": [_issue("/", "argument_error", "invalid command-line arguments")]},
                         ensure_ascii=False, separators=(",", ":")))
        print(f"synthesis_contract: {message}", file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = _ContractArgumentParser(description="Validate the destiny-matrix S5 synthesis output")
    parser.add_argument("--synthesis", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--intake", help="intake_brief.json; without it the minor_mode checks are skipped and reported as skipped")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        data, evidence, intake = (json.loads(Path(p).read_text(encoding="utf-8")) if p else None
                                  for p in (args.synthesis, args.evidence, args.intake))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "kind": "synthesis", "issues": [_issue("/", "file_error", f"Cannot read valid JSON input ({type(exc).__name__})")]}, ensure_ascii=False))
        print(f"synthesis_contract: input read failed ({type(exc).__name__})", file=sys.stderr)
        return 2
    issues, report = check(data, evidence, intake=intake)
    warnings = report.pop("warnings", [])
    minor_check = report.pop("minor_check", None)
    print(json.dumps({"ok": not issues, "kind": "synthesis", "issues": issues, "warnings": warnings,
                      "minor_check": minor_check, "coverage": report}, ensure_ascii=False, separators=(",", ":")))
    if issues:
        print(f"synthesis_contract: {len(issues)} contract issue(s)", file=sys.stderr)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
