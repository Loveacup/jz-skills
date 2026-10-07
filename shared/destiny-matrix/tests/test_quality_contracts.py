import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.quality_contracts import age_years, check, route_topics, task_fingerprint

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/synthetic_cases.json").read_text(encoding="utf-8"))


class QualityContractsTest(unittest.TestCase):
    def test_six_synthetic_intakes_pass_and_route(self):
        expected_routes = {
            "full-local": ["personality", "bazi", "ziwei", "astrology", "synthesis", "timing", "relationships", "practice"],
            "neris-only": ["personality", "practice"],
            "uncertain-time": ["bazi", "ziwei", "practice"],
            "synastry-year": ["relationships", "timing"],
            "wellbeing": ["wellbeing"],
            "minor-subtypes16": ["personality", "bazi", "ziwei", "astrology", "synthesis", "timing", "relationships", "practice"],
        }
        for case_id, brief in CASES.items():
            with self.subTest(case=case_id):
                self.assertEqual([], check("intake_brief", brief))
                self.assertEqual(expected_routes[case_id], route_topics(brief))

    def test_age_changes_on_birthday(self):
        self.assertEqual(17, age_years("2008-05-02", "2026-05-01"))
        self.assertEqual(18, age_years("2008-05-02", "2026-05-02"))
        minor = copy.deepcopy(CASES["minor-subtypes16"])
        minor["age_years"] = 17
        minor["minor_mode"] = False
        minor["subject"]["birth_date"] = "2008-05-02"
        minor["analysis_as_of"] = "2026-05-01"
        self.assertTrue(any(issue["code"] == "minor_mode_required" for issue in check("intake_brief", minor)))
        minor["age_years"] = 18
        minor["analysis_as_of"] = "2026-05-02"
        self.assertFalse(any(issue["code"] in {"minor_mode_required", "age_mode_mismatch"} for issue in check("intake_brief", minor)))

    def test_transcription_disagreement_blocks_without_averaging(self):
        brief = copy.deepcopy(CASES["minor-subtypes16"])
        trans = brief["personality_input"]["transcription"]
        trans["second_pass"][0]["value"] = 21
        trans["status"] = "needs_clarification"
        issues = check("intake_brief", brief)
        self.assertIn("transcription_mismatch", {issue["code"] for issue in issues})
        self.assertEqual(20, trans["first_pass"][0]["value"])
        self.assertEqual(21, trans["second_pass"][0]["value"])
        self.assertNotIn(16.5, [row["value"] for row in trans["first_pass"] + trans["second_pass"]])

    def test_task_fingerprint_reuse_and_invalidation_inputs(self):
        base = {"slice": {"birth_date": "2000-01-15"}, "upstream_hashes": ["a"], "versions": {"py": "3.13"}, "contract_hashes": {"schema": "h1"}, "role_snapshot": {"role": "deep"}}
        fp = task_fingerprint(**base)
        self.assertEqual(fp, task_fingerprint(**base))
        altered = copy.deepcopy(base); altered["slice"]["birth_date"] = "2000-01-16"
        self.assertNotEqual(fp, task_fingerprint(**altered))
        altered = copy.deepcopy(base); altered["contract_hashes"]["schema"] = "h2"
        self.assertNotEqual(fp, task_fingerprint(**altered))
        altered = copy.deepcopy(base); altered["role_snapshot"]["role"] = "research"
        self.assertNotEqual(fp, task_fingerprint(**altered))

    def test_runtime_trace_event_dedup_and_null_usage(self):
        trace = {"tasks": [{"task_id":"t1","stage":"S3","seat":"analyst","agent":"worker","requested_role":"research","configured_model":None,"resolvedModel":None,"resolvedModelIsFallback":None,"model_observation_source":None,"started_at":None,"finished_at":None,"wall_ms":None,"task_fingerprint":None,"reused_from":None,"retry_of":None,"status":"ok","input_artifact_ids":[],"output_artifact_ids":[],"usage_events":[{"event_id":"e1","request_id":None,"input_tokens":None,"output_tokens":None,"cache_read_tokens":None,"cache_write_tokens":None,"cost":None,"currency":None,"source":None,"coverage":None}]}]}
        self.assertIn("usage_coverage", {issue["code"] for issue in check("runtime_trace", trace)})
        usage = trace["tasks"][0]["usage_events"][0]
        self.assertIsNone(usage["input_tokens"])
        trace["tasks"].append(copy.deepcopy(trace["tasks"][0]))
        self.assertIn("duplicate_event_id", {issue["code"] for issue in check("runtime_trace", trace)})

    def test_transcription_difference_without_clarification_fails(self):
        brief = copy.deepcopy(CASES["minor-subtypes16"])
        trans = brief["personality_input"]["transcription"]
        trans["second_pass"][0]["value"] = 21
        trans["status"] = "verified"
        self.assertIn("transcription_mismatch", {i["code"] for i in check("intake_brief", brief)})


    def test_lunar_and_gregorian_dates_must_agree(self):
        brief = copy.deepcopy(CASES["full-local"])
        brief["subject"]["lunar_date"] = {
            "year": 2000, "month": 1, "day": 15, "is_leap_month": False
        }
        self.assertIn("lunar_date_mismatch", {issue["code"] for issue in check("intake_brief", brief)})

    def test_missing_applicable_judge_is_rejected(self):
        judge = {
            "dimension":"bazi","subject_id":"primary","input_artifact_ids":[],
            "input_payload_sha256":"a"*64,"isolation_level":"input_only",
            "independent_readings":[],"calculation_issues":[],"interpretation_limits":[]
        }
        expected = [{"subject_id":"primary","dimension":"bazi"}]
        verdicts = {"expected_judges":expected,"judges":[judge]}
        self.assertEqual([], check("judge_verdicts", verdicts))
        verdicts["judges"] = []
        self.assertIn("missing_applicable_judge", {issue["code"] for issue in check("judge_verdicts", verdicts)})
        verdicts["expected_judges"] = []
        verdicts["judges"] = [judge]
        self.assertIn("unexpected_judge", {issue["code"] for issue in check("judge_verdicts", verdicts)})

    def test_used_correction_round_with_blocker_requires_blocked_verdict(self):
        report = {
            "comparison_log": [],
            "discrepancies": [{
                "id":"D-1","dimension_owner":"bazi","claim_ids":["B-001"],
                "kind":"unsupported_inference","severity":"blocking","evidence":"supported evidence review","fix_type":"analysis"
            }],
            "correction_rounds":[{"subject_id":"primary","dimension":"bazi","round":1,"trigger_discrepancy_ids":["D-1"]}],
            "verdict":"revise","revise_targets":[],"disclosure_for_book":None
        }
        self.assertIn("correction_round_blocked", {issue["code"] for issue in check("consistency_report", report)})

    def test_second_round_only_for_errors_introduced_by_first_correction(self):
        def report(introduced, round_no, verdict):
            row = {"subject_id":"primary","dimension":"jung","round":round_no,"trigger_discrepancy_ids":["D-0"]}
            if round_no == 2:
                row["round2_trigger_discrepancy_ids"] = ["D-1"]
            return {
                "comparison_log": [],
                "discrepancies": [
                    {"id":"D-0","dimension_owner":"jung","claim_ids":["J-001"],"kind":"wording_difference","severity":"editorial","evidence":"resolved in round 1","fix_type":"prose"},
                    {"id":"D-1","dimension_owner":"jung","claim_ids":["J-002r1"],"kind":"calculation_error","severity":"blocking","evidence":"count wrong","fix_type":"calculation","introduced_in_round":introduced},
                ],
                "correction_rounds":[row],
                "verdict":verdict,"revise_targets":[],"disclosure_for_book":None
            }
        codes = lambda data: {issue["code"] for issue in check("consistency_report", data)}
        self.assertNotIn("correction_round_blocked", codes(report(1, 1, "revise")))
        self.assertIn("correction_round_blocked", codes(report(0, 1, "revise")))
        self.assertIn("round2_trigger_not_new", codes(report(0, 2, "blocked")))
        self.assertIn("correction_round_blocked", codes(report(1, 2, "revise")))
        self.assertEqual(set(), codes(report(1, 2, "blocked")))

    def test_case_evidence_correction_invalidates_dependents(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "input.json"
            artifact_path.write_text("{\"value\":1}", encoding="utf-8")
            digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            evidence = {
                "artifacts": [
                    {"artifact_id":"input","path":"input.json","sha256":digest,"depends_on_claim_ids":[],"depends_on_artifact_ids":[],"status":"current"},
                    {"artifact_id":"reading","path":"input.json","sha256":digest,"depends_on_claim_ids":["J-001"],"depends_on_artifact_ids":["input"],"status":"current"}
                ],
                "sources":[],
                "claims":[{"claim_id":"J-001","owner":"analyst","subject_id":"primary","kind":"computed_fact","statement":"fixture fact","input_refs":[{"artifact_id":"input","sha256":digest,"json_pointer":"/value"}],"source_ids":[],"parent_claim_ids":[],"counterevidence":[],"limits":[],"status":"active"}],
                "corrections":[],
                "limitations":[]
            }
            self.assertEqual([], check("case_evidence", evidence, base_dir=tmp))
            evidence["corrections"] = [{"correction_id":"C-1","invalidated_claim_ids":["J-001"],"replacement_claim_ids":[],"reason":"independent correction"}]
            codes = {issue["code"] for issue in check("case_evidence", evidence, base_dir=tmp)}
            self.assertIn("correction_not_propagated", codes)

    def test_final_verdict_requires_publishable_state(self):
        check_ids = "I1 I2 I3 A1 A2 A3 R1 R2 R3 D1 D2 D3 D4 P1 P2 P3".split()
        checks = [{"id":cid,"verdict":"pass","evidence":{"artifact":"book.html","location":"#ch-1","quote":"observed"},"reason":"verified"} for cid in check_ids]
        pre = {
            "verdict_id":"pre-1","previous_verdict":None,"review_phase":"pre_export","evidence_revision":"r0",
            "artifact_hashes":{"html":"a"*64,"pdf":None},"checklist_results":copy.deepcopy(checks),
            "validator_output":{},"visual_qa":[],"decision":"pass","revision_round":0,
            "revision_instructions":[],"blocked_items":[],"recommendations":[],"export_result":None,
            "reader_takeaways":["你在压力下先收缩再求证。","时辰前提改变第三章读法。","本周试一次先说需要再说方案。"]
        }
        self.assertIn("pre_export_pass", {issue["code"] for issue in check("final_verdict", pre)})
        post = copy.deepcopy(pre)
        post.update({"review_phase":"post_export","decision":"pass","artifact_hashes":{"html":"a"*64,"pdf":"b"*64},"visual_qa":[{"observation":"observed"}],"export_result":{"html_sha256":"c"*64,"pdf_sha256":"b"*64}})
        self.assertIn("artifact_hash_mismatch", {issue["code"] for issue in check("final_verdict", post)})

    # --- v5.2 style layering -------------------------------------------------
    @staticmethod
    def layered_evidence():
        claim = {"claim_id":"C-1","owner":"analyst","subject_id":"primary","kind":"traditional_interpretation",
                 "statement":"fixture","input_refs":[],"source_ids":["CR-1"],"parent_claim_ids":[],
                 "counterevidence":[],"limits":["审计层限制"],"status":"active"}
        lim = lambda lid, changes, placement: {"limitation_id":lid,"affected_claim_ids":["C-1"],"impact":"audit note",
                                               "changes_reading":changes,"reader_text":"如果时辰改动，这一节改读为另一种倾向。",
                                               "required_placement":placement}
        return {"artifacts":[],"claims":[claim],"corrections":[],
                "sources":[{"source_id":"CR-1","kind":"common_reading","locator":"紫微通行读法：天机主思虑","version":None,
                            "status":"verified","excerpt":None}],
                "limitations":[lim("L-OPEN",True,"opening"),lim("L-ADJ",True,"adjacent"),lim("L-AUD",False,"appendix")]}

    def test_limitation_layers_validate_and_misplacement_has_readable_codes(self):
        evidence = self.layered_evidence()
        self.assertEqual([], check("case_evidence", evidence))
        bad = copy.deepcopy(evidence); bad["limitations"][2]["required_placement"] = "adjacent"
        self.assertIn("limitation_placement", {i["code"] for i in check("case_evidence", bad)})
        bad = copy.deepcopy(evidence); bad["limitations"][1]["required_placement"] = "appendix"
        self.assertIn("reader_limitation_in_appendix", {i["code"] for i in check("case_evidence", bad)})
        bad = copy.deepcopy(evidence); del bad["limitations"][0]["reader_text"]
        self.assertIn("schema", {i["code"] for i in check("case_evidence", bad)})
        bad = copy.deepcopy(evidence); bad["limitations"][0]["reader_text"] = ""
        self.assertIn("schema", {i["code"] for i in check("case_evidence", bad)})

    def test_common_reading_source_is_paraphrase_only_and_traditional(self):
        evidence = self.layered_evidence()
        bad = copy.deepcopy(evidence); bad["sources"][0]["excerpt"] = "“天机主善”"
        self.assertIn("common_reading_excerpt", {i["code"] for i in check("case_evidence", bad)})
        bad = copy.deepcopy(evidence); bad["claims"][0]["kind"] = "psychological_hypothesis"
        self.assertIn("common_reading_claim_kind", {i["code"] for i in check("case_evidence", bad)})
        catalog = {"schema_version":1,"sources":[{"source_id":"cr","kind":"common_reading","author":"通行读法","title":"天机",
                   "edition":None,"locator":"现代教材通行表述","url":None,"verification_status":"verified","quotes":[],
                   "supports":["通行象义"],"does_not_support":["古籍原文"]}]}
        self.assertEqual([], check("sources", catalog))
        catalog["sources"][0]["quotes"] = [{"quote_id":"cr-q01","original":"天机主善","translation":None,"translation_kind":"none"}]
        self.assertIn("common_reading_quote", {i["code"] for i in check("sources", catalog)})

    def test_synthesis_child_inherits_reader_limitations(self):
        evidence = self.layered_evidence()
        child = copy.deepcopy(evidence["claims"][0])
        child.update({"claim_id":"S-1","owner":"synthesizer","parent_claim_ids":["C-1"],"source_ids":[]})
        evidence["claims"].append(child)
        codes = {i["code"] for i in check("case_evidence", evidence)}
        self.assertIn("inherited_limitation_missing", codes)
        for row in evidence["limitations"]:
            if row["changes_reading"]:
                row["affected_claim_ids"].append("S-1")
        self.assertEqual([], check("case_evidence", evidence))

    def test_active_claim_needs_verified_common_reading(self):
        evidence = self.layered_evidence()
        evidence["sources"][0]["status"] = "unverified"
        self.assertIn("common_reading_unverified", {i["code"] for i in check("case_evidence", evidence)})
        evidence["claims"][0]["status"] = "rejected"
        self.assertNotIn("common_reading_unverified", {i["code"] for i in check("case_evidence", evidence)})

    def test_chart_plan_limitations_reader_layer_single_section(self):
        evidence = self.layered_evidence()
        section = lambda sid, lids: {"section_id":sid,"title":"t","question_ids":[],"claim_ids":["C-1"] if sid == "ziwei" else [],
                                     "required_content":["x"],"limitation_ids":lids}
        plan = {"planning_rationale":"r","special_features":[],"sections":[section("ziwei",["L-ADJ"]),section("synthesis",[])],
                "chart_table":[],"total":{"planned":0}}
        self.assertEqual([], check("chart_plan", plan, evidence=evidence))
        codes = lambda p: {i["code"] for i in check("chart_plan", p, evidence=evidence)}
        bad = copy.deepcopy(plan); bad["sections"][1]["limitation_ids"] = ["L-ADJ"]
        self.assertIn("limitation_multiple_sections", codes(bad))
        self.assertIn("limitation_multiple_sections", {i["code"] for i in check("chart_plan", bad)})
        bad = copy.deepcopy(plan); bad["sections"][0]["limitation_ids"] = ["L-ADJ","L-AUD"]
        self.assertIn("section_limitation_not_reader_layer", codes(bad))
        bad = copy.deepcopy(plan); bad["sections"][0]["limitation_ids"] = ["L-ADJ","L-OPEN"]
        self.assertIn("section_limitation_not_adjacent", codes(bad))
        bad = copy.deepcopy(plan); bad["sections"][0]["limitation_ids"] = ["L-ADJ","L-GHOST"]
        self.assertIn("dangling_limitation", codes(bad))
        bad = copy.deepcopy(plan); bad["sections"][0]["limitation_ids"] = []
        self.assertIn("adjacent_limitation_unplanned", codes(bad))
        bad = copy.deepcopy(plan); bad["sections"][0]["limitation_ids"] = ["L-ADJ","L-ADJ"]
        self.assertIn("schema", codes(bad))

    def test_reader_takeaways_required_or_r1_d3_fail(self):
        check_ids = "I1 I2 I3 A1 A2 A3 R1 R2 R3 D1 D2 D3 D4 P1 P2 P3".split()
        rows = [{"id":cid,"verdict":"deferred" if cid.startswith("P") else "pass",
                 "evidence":{"artifact":"book.html","location":"#x","quote":"q"},"reason":"r"} for cid in check_ids]
        verdict = {"verdict_id":"pre-1","previous_verdict":None,"review_phase":"pre_export","evidence_revision":"r0",
                   "artifact_hashes":{"html":"a"*64,"pdf":None},"checklist_results":rows,"validator_output":{},"visual_qa":[],
                   "decision":"awaiting_export","revision_round":0,"revision_instructions":[],"blocked_items":[],
                   "reader_takeaways":["一","二","三"],"recommendations":[],"export_result":None}
        codes = lambda v: {i["code"] for i in check("final_verdict", v)}
        self.assertEqual(set(), codes(verdict))
        empty = copy.deepcopy(verdict); empty["reader_takeaways"] = []
        self.assertIn("reader_takeaways_missing", codes(empty))
        empty.update({"decision":"revise","revision_instructions":[{"check_id":"R1","fix_type":"prose","owner":"book-writer",
                      "claim_ids":[],"section_ids":["bazi"],"problem":"p","acceptance":"a"}]})
        empty["checklist_results"][check_ids.index("R1")]["verdict"] = "fail"
        self.assertIn("reader_takeaways_missing", codes(empty))  # R1 alone is not enough
        empty["checklist_results"][check_ids.index("D3")]["verdict"] = "fail"
        self.assertEqual(set(), codes(empty))
        short = copy.deepcopy(verdict); short["reader_takeaways"] = ["一","二"]
        self.assertIn("reader_takeaways_count", codes(short))
        many = copy.deepcopy(verdict); many["reader_takeaways"] = ["句"] * 6
        self.assertIn("schema", codes(many))
        missing = copy.deepcopy(verdict); del missing["reader_takeaways"]
        self.assertIn("schema", codes(missing))


if __name__ == "__main__":
    unittest.main()
