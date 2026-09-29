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
            "revision_instructions":[],"blocked_items":[],"recommendations":[],"export_result":None
        }
        self.assertIn("pre_export_pass", {issue["code"] for issue in check("final_verdict", pre)})
        post = copy.deepcopy(pre)
        post.update({"review_phase":"post_export","decision":"pass","artifact_hashes":{"html":"a"*64,"pdf":"b"*64},"visual_qa":[{"observation":"observed"}],"export_result":{"html_sha256":"c"*64,"pdf_sha256":"b"*64}})
        self.assertIn("artifact_hash_mismatch", {issue["code"] for issue in check("final_verdict", post)})

if __name__ == "__main__":
    unittest.main()
