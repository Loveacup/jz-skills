import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.synthesis_contract import check, owner_system

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/synthesis_contract.py"
SHA = "a" * 64


def claim(claim_id, owner, kind="traditional_interpretation", parents=(), status="active", refs=True, subject="primary"):
    return {"claim_id": claim_id, "owner": owner, "subject_id": subject, "kind": kind,
            "statement": f"合成主张 {claim_id}",
            "input_refs": [{"artifact_id": "chart", "sha256": SHA, "json_pointer": "/data"}] if refs else [],
            "source_ids": [], "parent_claim_ids": list(parents), "counterevidence": [], "limits": [], "status": status}


def evidence():
    return {"artifacts": [], "sources": [], "corrections": [], "limitations": [], "claims": [
        claim("J-01", "jung-analyst", "psychological_hypothesis"),
        claim("J-02", "jung-analyst", "reported_observation"),
        claim("B-01", "bazi-analyst"), claim("B-02", "bazi-analyst"),
        claim("Z-01", "ziwei-analyst"), claim("A-01", "astro-analyst"),
        claim("A-09", "astro-analyst", status="superseded"),
    ]}


def synthesis_claim(claim_id, parents, kind="traditional_interpretation"):
    row = claim(claim_id, "synthesizer", kind, parents, refs=False)
    del row["owner"], row["status"]
    return row


def section(section_id, claim_ids, content):
    return {"section_id": section_id, "title": "合成标题", "question_ids": [], "claim_ids": claim_ids,
            "required_content": content, "limitation_ids": []}


def synthesis():
    return {
        "matrix": [
            {"theme": "思维与学习", "personality_claim_ids": ["J-01"], "bazi_claim_ids": ["B-01"],
             "ziwei_claim_ids": [], "astro_claim_ids": ["A-01"], "relationship": "convergent", "limits": []},
            {"theme": "事业与社会角色", "personality_claim_ids": [], "bazi_claim_ids": ["B-02"],
             "ziwei_claim_ids": ["Z-01"], "astro_claim_ids": [], "relationship": "tension", "limits": []},
            {"theme": "人生节奏", "personality_claim_ids": [], "bazi_claim_ids": ["B-02"],
             "ziwei_claim_ids": [], "astro_claim_ids": [], "relationship": "parallel", "limits": ["仅八字有时间资料"]},
        ],
        "synthesis_claims": [
            synthesis_claim("S-01", ["J-01", "B-01", "A-01"]),
            synthesis_claim("S-02", ["B-02", "Z-01"]),
            synthesis_claim("S-03", ["S-01", "S-02"]),
        ],
        "core_propositions": [
            {"proposition_id": "CP-01", "image": "先拆后装", "statement": "遇到新科目时，你先把它拆成零件再装回去。", "claim_ids": ["S-01"]},
            {"proposition_id": "CP-02", "image": None, "statement": "在需要署名负责的场合，你倾向把标准定得比岗位要求高。", "claim_ids": ["S-02"]},
            {"proposition_id": "CP-03", "image": None, "statement": "三十岁前后的这步大运里，拆装的习惯第一次要对外负责。", "claim_ids": ["S-03", "B-02"]},
        ],
        "outline": {"sections": [
            section("synthesis", ["S-01", "S-02", "S-03"], ["解释 S-01 的汇聚落在思维方式一层，回扣 CP-01 与 CP-02", "CP-03 的时间条件"]),
        ]},
        "action_options": [
            {"goal": "因为 S-01", "claim_ids": ["S-01"], "small_action": "用二十分钟画一张拆解图", "frequency_or_trigger": "下次接到新课题时",
             "review_question": "拆到第几层就够用了？", "adapt_or_stop": "连续两次觉得多余就停"},
        ],
    }


def codes(data, ev=None, **kwargs):
    issues, _ = check(data, ev or evidence(), **kwargs)
    return {issue["code"] for issue in issues}


class SynthesisContractTest(unittest.TestCase):
    def test_valid_synthesis_passes_and_reports_coverage(self):
        issues, coverage = check(synthesis(), evidence())
        self.assertEqual([], issues)
        self.assertEqual(["astro", "bazi", "personality", "ziwei"], coverage["covered_systems"])
        self.assertEqual(3, coverage["required_systems"])

    def test_owner_names_map_to_systems(self):
        self.assertEqual("personality", owner_system("jung"))
        self.assertEqual("bazi", owner_system("bazi-analyst"))
        self.assertEqual("astro", owner_system("astro-analyst"))
        self.assertIsNone(owner_system("synthesizer"))
        self.assertIsNone(owner_system("analyst"))

    def test_relationship_enum(self):
        data = synthesis(); data["matrix"][0]["relationship"] = "validated"
        self.assertIn("relationship_enum", codes(data))

    def test_convergent_and_tension_need_two_systems(self):
        for relationship in ("convergent", "tension"):
            with self.subTest(relationship=relationship):
                data = synthesis(); data["matrix"][2]["relationship"] = relationship
                self.assertIn("relationship_needs_two_systems", codes(data))

    def test_two_claims_of_one_system_do_not_make_a_cross_row(self):
        data = synthesis()
        data["matrix"][1].update({"bazi_claim_ids": ["B-01", "B-02"], "ziwei_claim_ids": []})
        self.assertIn("relationship_needs_two_systems", codes(data))

    def test_matrix_column_must_match_owner(self):
        data = synthesis(); data["matrix"][1]["ziwei_claim_ids"] = ["A-01"]
        found = codes(data)
        self.assertIn("matrix_column_mismatch", found)
        self.assertIn("relationship_needs_two_systems", found)

    def test_matrix_rejects_unknown_inactive_and_synthesis_claims(self):
        data = synthesis(); data["matrix"][0]["astro_claim_ids"] = ["A-404"]
        self.assertIn("dangling_claim", codes(data))
        data = synthesis(); data["matrix"][0]["astro_claim_ids"] = ["A-09"]
        self.assertIn("inactive_claim", codes(data))
        data = synthesis(); data["matrix"][0]["astro_claim_ids"] = ["S-02"]
        self.assertIn("synthesis_claim_in_matrix", codes(data))

    def test_empty_row_and_duplicate_theme(self):
        data = synthesis(); data["matrix"][2]["bazi_claim_ids"] = []
        self.assertIn("matrix_row_empty", codes(data))
        data = synthesis(); data["matrix"][2]["theme"] = "思维与学习"
        self.assertIn("duplicate_theme", codes(data))

    def test_convergent_requires_chart_basis_in_every_system(self):
        ev = evidence(); ev["claims"][2]["input_refs"] = []
        self.assertIn("convergent_without_chart_basis", codes(synthesis(), ev))

    def test_cross_row_needs_matching_synthesis_claim(self):
        data = synthesis(); data["synthesis_claims"][1]["parent_claim_ids"] = ["B-01", "Z-01"]
        self.assertIn("matrix_row_without_claim", codes(data))

    def test_single_system_parents_are_not_synthesis(self):
        data = synthesis(); data["synthesis_claims"][1]["parent_claim_ids"] = ["B-01", "B-02"]
        self.assertIn("single_system_synthesis", codes(data))
        data = synthesis(); data["synthesis_claims"][1]["parent_claim_ids"] = []
        self.assertIn("single_system_synthesis", codes(data))

    def test_inactive_parent_does_not_count_as_a_system(self):
        data = synthesis(); data["synthesis_claims"][1]["parent_claim_ids"] = ["B-02", "A-09"]
        found = codes(data)
        self.assertIn("inactive_claim", found)
        self.assertIn("single_system_synthesis", found)

    def test_unknown_parent(self):
        data = synthesis(); data["synthesis_claims"][0]["parent_claim_ids"].append("X-1")
        self.assertIn("dangling_claim", codes(data))

    def test_duplicate_and_colliding_claim_ids(self):
        data = synthesis(); data["synthesis_claims"][1]["claim_id"] = "S-01"
        self.assertIn("duplicate_id", codes(data))
        data = synthesis(); data["synthesis_claims"][0]["claim_id"] = "B-01"
        self.assertIn("claim_id_collision", codes(data))

    def test_registered_synthesis_claim_may_be_resubmitted(self):
        ev = evidence(); ev["claims"].append(claim("S-01", "synthesizer", parents=["J-01", "B-01", "A-01"], refs=False))
        self.assertEqual(set(), codes(synthesis(), ev))

    def test_owner_without_system_falls_back_to_matrix_column(self):
        ev = evidence()
        for row in ev["claims"]:
            row["owner"] = "analyst"
        self.assertEqual(set(), codes(synthesis(), ev))

    def test_hypothesis_needs_observation_parent(self):
        data = synthesis(); data["synthesis_claims"][1]["kind"] = "psychological_hypothesis"
        self.assertIn("hypothesis_without_observation", codes(data))
        data = synthesis(); data["synthesis_claims"][0]["kind"] = "psychological_hypothesis"
        self.assertEqual(set(), codes(data))

    def test_synthesis_claim_kind_is_limited(self):
        data = synthesis(); data["synthesis_claims"][0]["kind"] = "computed_fact"
        self.assertIn("synthesis_claim_kind", codes(data))

    def test_cross_person_parents_require_joint(self):
        ev = evidence(); ev["claims"][4]["subject_id"] = "partner"
        self.assertIn("subject_crossing", codes(synthesis(), ev))

    def test_proposition_count(self):
        data = synthesis(); data["core_propositions"].pop()
        self.assertIn("proposition_count", codes(data))
        data = synthesis()
        data["core_propositions"] += [dict(data["core_propositions"][0], proposition_id=f"CP-0{i}") for i in (4, 5, 6)]
        self.assertIn("proposition_count", codes(data))

    def test_proposition_statement_and_claims_required(self):
        data = synthesis(); data["core_propositions"][0]["statement"] = "  "
        self.assertIn("proposition_statement_empty", codes(data))
        data = synthesis(); data["core_propositions"][0]["claim_ids"] = []
        self.assertIn("proposition_claims_empty", codes(data))
        data = synthesis(); data["core_propositions"][0]["claim_ids"] = ["S-404"]
        self.assertIn("dangling_claim", codes(data))

    def test_propositions_must_cover_three_systems(self):
        data = synthesis()
        for row in data["core_propositions"]:
            row["claim_ids"] = ["S-02"]
        self.assertIn("proposition_coverage", codes(data))

    def test_coverage_requirement_follows_available_systems(self):
        ev = evidence(); ev["claims"] = [c for c in ev["claims"] if c["claim_id"] in ("B-01", "B-02", "Z-01")]
        data = synthesis()
        data["matrix"] = [data["matrix"][1]]
        data["synthesis_claims"] = [data["synthesis_claims"][1]]
        for row in data["core_propositions"]:
            row["claim_ids"] = ["S-02"]
        data["outline"]["sections"][0]["claim_ids"] = ["S-02"]
        data["action_options"] = []
        issues, coverage = check(data, ev)
        self.assertEqual([], issues)
        self.assertEqual(2, coverage["required_systems"])

    def test_proposition_duplicates_and_escalation(self):
        data = synthesis(); data["core_propositions"][1]["statement"] = data["core_propositions"][0]["statement"]
        self.assertIn("duplicate_statement", codes(data))
        data = synthesis(); data["core_propositions"][1]["proposition_id"] = "CP-01"
        self.assertIn("duplicate_id", codes(data))
        data = synthesis(); data["core_propositions"][0]["image"] = "三重印证"
        self.assertIn("proposition_escalation", codes(data))

    def test_every_proposition_is_placed_in_a_section(self):
        data = synthesis(); data["outline"]["sections"][0]["required_content"] = ["只回扣 CP-01 与 CP-02"]
        self.assertIn("proposition_unplaced", codes(data))

    def test_required_content_must_not_be_empty(self):
        data = synthesis(); data["outline"]["sections"][0]["required_content"] = []
        self.assertIn("required_content_empty", codes(data))
        data = synthesis(); data["outline"]["sections"][0]["required_content"] = [" "]
        self.assertIn("required_content_empty", codes(data))

    def test_synthesis_section_cites_synthesis_claims(self):
        data = synthesis(); data["outline"]["sections"][0]["claim_ids"] = ["B-01"]
        self.assertIn("synthesis_section_without_claims", codes(data))

    def test_outline_and_action_references(self):
        data = synthesis(); data["outline"]["sections"][0]["claim_ids"].append("A-09")
        self.assertIn("inactive_claim", codes(data))
        data = synthesis(); data["action_options"][0]["claim_ids"] = ["Q-1"]
        self.assertIn("dangling_claim", codes(data))

    def test_minor_mode_theme_check(self):
        data = synthesis(); data["matrix"][1]["theme"] = "婚恋与伴侣"
        self.assertEqual(set(), codes(data))
        self.assertEqual(set(), codes(data, intake={"minor_mode": False}))
        self.assertIn("minor_theme", codes(data, intake={"minor_mode": True}))
        self.assertIn("minor_theme", codes(data, intake={"minor_mode": None}))
        self.assertEqual(set(), codes(synthesis(), intake={"minor_mode": True}))

    def minor(self, text, field="statement", audience="subject"):
        data = synthesis()
        if field == "statement":
            data["synthesis_claims"][0]["statement"] = text
        elif field == "reader_text":
            data["limitation_increments"] = [{"affected_claim_ids": ["S-01"], "impact": "审计说明", "changes_reading": True,
                                              "reader_text": text, "required_placement": "adjacent"}]
        issues, report = check(data, evidence(), intake={"minor_mode": True, "audience": audience})
        return {i["code"] for i in issues}, {w["code"] for w in report["warnings"]}

    def test_minor_terms_previously_missed(self):
        for text in ("早恋", "她在暗恋同桌", "男朋友", "女朋友", "找对象", "另一半", "姻缘", "正缘", "约会", "相亲",
                     "夫星", "妻星", "夫妻宫有天府", "子女宫", "結婚", "配 偶", "配\u3000偶", "戀愛"):
            with self.subTest(text=text):
                self.assertIn("minor_theme", self.minor(text)[0])

    def test_minor_false_positives(self):
        found, warned = self.minor("桃花源记是她喜欢的课文")
        self.assertEqual(set(), found)
        self.assertEqual(set(), warned)
        found, warned = self.minor("这类判断带对象或条件，研究对象是学习方式")
        self.assertEqual(set(), found)
        found, warned = self.minor("本书不谈婚恋，只谈同伴关系")
        self.assertEqual(set(), found)
        self.assertEqual({"minor_theme_negated"}, warned)
        self.assertIn("minor_theme", self.minor("桃花旺")[0])

    def test_minor_career_and_ability(self):
        for text in ("适合当会计", "将来会成为医生", "长大后当老师", "職業方向已定"):
            with self.subTest(text=text):
                self.assertIn("minor_career_verdict", self.minor(text)[0])
        for text in ("智力偏低", "能力不足", "有学习障碍", "反应迟钝"):
            with self.subTest(text=text):
                self.assertIn("minor_ability_label", self.minor(text)[0])
        self.assertEqual(set(), self.minor("你拿到新东西，先拆开看")[0])

    def test_minor_type_name(self):
        self.assertIn("minor_type_name", self.minor("分数最贴合 INTP")[0])
        found, warned = self.minor("分数最贴合 INTP", audience="both")
        self.assertNotIn("minor_type_name", found)
        self.assertIn("minor_type_name", warned)
        self.assertEqual(set(), self.minor("Ti 主导，Ne 辅助")[0])

    def test_minor_scans_limitation_reader_text(self):
        self.assertIn("minor_theme", self.minor("如果出生时刻有误，婚姻一节改读", field="reader_text")[0])

    def test_minor_check_status_is_reported(self):
        _, report = check(synthesis(), evidence())
        self.assertEqual("skipped", report["minor_check"])
        self.assertEqual({"minor_check_skipped"}, {w["code"] for w in report["warnings"]})
        _, report = check(synthesis(), evidence(), intake={"minor_mode": False})
        self.assertEqual("not_applicable", report["minor_check"])
        self.assertEqual([], report["warnings"])
        _, report = check(synthesis(), evidence(), intake={"minor_mode": None})
        self.assertEqual("applied", report["minor_check"])

    def test_escalation_is_scanned_beyond_propositions(self):
        for word in ("互相验证", "相互验证", "彼此印证", "三重验证", "可信度提高", "科学证明", "科學證明"):
            with self.subTest(word=word):
                data = synthesis(); data["synthesis_claims"][0]["statement"] = f"三种读法{word}"
                self.assertIn("escalation_wording", codes(data))
        data = synthesis(); data["outline"]["sections"][0]["required_content"].append("说明三体系相互印证")
        self.assertIn("escalation_wording", codes(data))
        data = synthesis(); data["outline"]["sections"][0]["title"] = "命运密码"
        self.assertIn("escalation_wording", codes(data))
        data = synthesis(); data["action_options"][0]["goal"] = "因为三重印证"
        self.assertIn("escalation_wording", codes(data))
        data = synthesis(); data["synthesis_claims"][0]["limits"] = ["不得写成相互印证"]
        self.assertEqual(set(), codes(data))

    def test_three_node_cycle_is_detected(self):
        data = synthesis()
        data["synthesis_claims"] = [synthesis_claim("S-01", ["S-02", "J-01", "B-01", "A-01"]),
                                    synthesis_claim("S-02", ["S-03", "B-02", "Z-01"]),
                                    synthesis_claim("S-03", ["S-01"])]
        issues, _ = check(data, evidence())
        cyc = [i["path"] for i in issues if i["code"] == "dependency_cycle"]
        self.assertEqual(["/synthesis_claims/0/parent_claim_ids", "/synthesis_claims/1/parent_claim_ids",
                          "/synthesis_claims/2/parent_claim_ids"], cyc)
        self.assertIn("/synthesis_claims/2/parent_claim_ids", [i["path"] for i in issues if i["code"] == "single_system_synthesis"])

    def test_cycle_cannot_lend_a_system(self):
        data = synthesis()
        data["matrix"] = [data["matrix"][2]]
        data["synthesis_claims"] = [synthesis_claim("S-01", ["S-02", "J-01"]), synthesis_claim("S-02", ["S-01", "B-01"])]
        for row in data["core_propositions"]:
            row["claim_ids"] = ["S-01", "S-02", "A-01"]
        data["outline"]["sections"][0]["claim_ids"] = ["S-01", "S-02"]
        issues, _ = check(data, evidence())
        by_code = {}
        for i in issues:
            by_code.setdefault(i["code"], []).append(i["path"])
        self.assertEqual(2, len(by_code["dependency_cycle"]))
        self.assertEqual(2, len(by_code["single_system_synthesis"]))

    def test_self_reference_is_a_cycle(self):
        data = synthesis(); data["synthesis_claims"][0]["parent_claim_ids"].append("S-01")
        self.assertIn("dependency_cycle", codes(data))

    def test_empty_matrix_is_rejected(self):
        data = synthesis(); data["matrix"] = []
        self.assertIn("matrix_empty", codes(data))

    def test_evidence_claim_without_status_is_not_usable(self):
        ev = evidence(); del ev["claims"][5]["status"]
        issues, report = check(synthesis(), ev)
        self.assertIn("inactive_claim", {i["code"] for i in issues})
        self.assertNotIn("astro", report["available_systems"])

    def test_invalid_evidence(self):
        self.assertEqual({"evidence_invalid"}, codes(synthesis(), {"claims": None}))

    def test_documented_codes_match_script(self):
        import re
        script = (ROOT / "scripts/synthesis_contract.py").read_text(encoding="utf-8")
        schema = (ROOT / "schemas/synthesis.json").read_text(encoding="utf-8")
        used = set(re.findall(r'_issue\([^,]+,\s*"([a-z0-9_]+)"', script)) | set(re.findall(r'"x-issue-code": "([a-z0-9_]+)"', schema))
        used |= set(re.findall(r'"(minor_[a-z_]+|proposition_escalation|escalation_wording)"', script)) - {"minor_mode", "minor_check"}
        doc = (ROOT / "references/cross-analysis-patterns.md").read_text(encoding="utf-8")
        section = doc[doc.index("## 产出校验"):]
        documented = set(re.findall(r"`([a-z0-9_]+)`", section)) - {"schema", "minor_check", "applied", "not_applicable", "skipped", "convergent", "tension", "relationship", "matrix", "kind", "joint", "claims", "issues", "warnings", "case_evidence"}
        self.assertEqual(set(), used - documented)
        self.assertEqual(set(), documented - used)


class SynthesisContractCliTest(unittest.TestCase):
    def run_cli(self, data, ev, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            s, e = Path(tmp) / "synthesis.json", Path(tmp) / "case_evidence.json"
            s.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
            e.write_text(json.dumps(ev, ensure_ascii=False), encoding="utf-8")
            return subprocess.run([sys.executable, str(SCRIPT), "--synthesis", str(s), "--evidence", str(e), "--json", *extra],
                                  capture_output=True, text=True)

    def test_exit_codes(self):
        ok = self.run_cli(synthesis(), evidence())
        self.assertEqual(0, ok.returncode, ok.stderr)
        self.assertTrue(json.loads(ok.stdout)["ok"])
        bad = synthesis(); bad["matrix"][2]["relationship"] = "convergent"
        failed = self.run_cli(bad, evidence())
        self.assertEqual(1, failed.returncode)
        result = json.loads(failed.stdout)
        self.assertFalse(result["ok"])
        self.assertEqual("synthesis", result["kind"])
        self.assertIn("relationship_needs_two_systems", {i["code"] for i in result["issues"]})
        self.assertEqual("skipped", result["minor_check"])
        self.assertEqual("minor_check_skipped", json.loads(ok.stdout)["warnings"][0]["code"])
        broken = self.run_cli("{not json", evidence())
        self.assertEqual(2, broken.returncode)
        self.assertEqual("file_error", json.loads(broken.stdout)["issues"][0]["code"])

    def test_argument_error_exits_two(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True)
        self.assertEqual(2, done.returncode)
        self.assertEqual("argument_error", json.loads(done.stdout)["issues"][0]["code"])


if __name__ == "__main__":
    unittest.main()
