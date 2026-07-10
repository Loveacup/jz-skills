# -*- coding: utf-8 -*-
"""P6-R corpus manifest runner tests.

The corpus runner is an explicit, side-effect-free frame for a pre-release real
sample corpus. Without ``--execute`` it must only load/validate/select samples
and emit a JSON summary — it may not call ``report_markdown``, read input files,
download, or invoke an LLM. Only ``--execute`` is allowed to run the existing
single-sample ``run_quality_gate`` on samples whose local input actually exists;
it must never auto-download to backfill a missing cache.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import run_quality_gate


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "references" / "p6r-corpus-manifest.json"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "p2e_fetch_all.json"

EXPECTED_BVIDS = {
    "BV14fTc6TEi5",
    "BV1xpT26bEgG",
    "BV17cTW6LEcE",
    "BV1hyTk6ZEfn",
    "BV1p2DyB4Ee3",
    "BV1XAjs6NExC",
    "BV1sxT56TE39",
    "BV12W7Z69EXX",
    "BV1anMP69ED5",
    "BV1SnLf6oEZq",
}


def _write_manifest(tmp_path, samples, **top):
    manifest = {
        "schema_version": 1,
        "name": "p6r-test",
        "created_at": "2026-07-10",
        "execution_policy": {
            "default_execute": False,
            "requires_execute_flag": True,
            "auto_download_allowed": False,
            "auto_llm_allowed": False,
        },
        "samples": samples,
    }
    manifest.update(top)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def _sample(sid, bvid, status="candidate", *, input_path="", cache_status="missing",
            reviewed_by=None, reviewed_at=None, verdict_source=None,
            summary_json_path=None):
    return {
        "id": sid,
        "bvid": bvid,
        "category": "测试",
        "source_note": {"type": "obsidian_formal_note", "path": "", "title": "",
                        "evidence_status": "candidate_extracted_from_existing_notes"},
        "input": {
            "fetch_all_json_path": input_path,
            "cache_status": cache_status,
            "collected_at": None,
            "collector_command": None,
        },
        "run": {
            "last_run_at": None,
            "writer_provider": None,
            "output_path": None,
            "summary_json_path": summary_json_path,
            "publishable_passed": None,
            "failed_codes": [],
        },
        "rubric": {
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "verdict_source": verdict_source,
            "notes": "",
        },
    }


# --- manifest shape ---------------------------------------------------------

def test_manifest_is_ten_real_candidates():
    manifest = run_quality_gate.load_corpus_manifest(str(MANIFEST))
    assert manifest["schema_version"] == 1
    samples = manifest["samples"]
    assert len(samples) == 10
    assert {s["bvid"] for s in samples} == EXPECTED_BVIDS
    for s in samples:
        # No sample may masquerade as gold or as already-run.
        assert s["rubric"]["status"] == "candidate"
        assert s["input"]["cache_status"] == "missing"
        assert s["source_note"]["path"].endswith(".md")
        assert s["source_note"]["title"]
        assert s["rubric"]["reviewed_by"] is None
        assert s["run"]["last_run_at"] is None
    assert run_quality_gate.validate_corpus_manifest(manifest) == []


# --- dry run: no side effects ----------------------------------------------

def test_dry_run_does_not_call_report_markdown(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("report_markdown must not be called without --execute")

    monkeypatch.setattr(run_quality_gate.generate_report, "report_markdown", boom)

    summary = run_quality_gate.run_corpus_manifest(
        str(MANIFEST), lane="candidates", execute=False
    )
    assert summary["execute"] is False
    assert summary["valid"] is True
    assert summary["lane"] == "candidates"
    assert summary["total_samples"] == 10
    assert summary["selected_count"] == 10
    assert summary["status_distribution"]["candidate"] == 10
    assert summary["executed"] is False
    assert summary["results"] == []


def test_cli_dry_run_needs_no_input_and_emits_json():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_quality_gate.py",
            "--corpus-manifest",
            str(MANIFEST),
            "--lane",
            "candidates",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    body = result.stdout.split("RESULT_JSON_START", 1)[1].split("RESULT_JSON_END", 1)[0]
    payload = json.loads(body)
    assert payload["mode"] == "corpus-manifest"
    assert payload["execute"] is False
    assert payload["selected_count"] == 10


# --- fake gold rejected -----------------------------------------------------

def test_invalid_fake_gold_rejected(tmp_path):
    bad = _sample("fake-gold", "BV1fakegold00", status="accepted_gold")  # no reviewer fields
    manifest = json.loads(_write_manifest(tmp_path, [bad]).read_text(encoding="utf-8"))
    errors = run_quality_gate.validate_corpus_manifest(manifest)
    assert errors, "accepted_gold missing reviewer fields must be rejected"
    assert any("fake-gold" in e for e in errors)


def test_dry_run_reports_invalid_manifest(tmp_path):
    bad = _sample("fake-gold", "BV1fakegold00", status="accepted_gold")
    path = _write_manifest(tmp_path, [bad])
    summary = run_quality_gate.run_corpus_manifest(str(path), lane="blocking", execute=False)
    assert summary["valid"] is False
    assert summary["validation_errors"]
    assert summary["selected_count"] == 0


# --- blocking lane ----------------------------------------------------------

def test_blocking_lane_selects_only_complete_accepted_gold(tmp_path):
    summary_file = tmp_path / "gold_summary.json"
    summary_file.write_text("{}", encoding="utf-8")

    gold = _sample(
        "complete-gold",
        "BV1goldgood00",
        status="accepted_gold",
        input_path=str(FIXTURE),
        cache_status="present",
        reviewed_by="anyis",
        reviewed_at="2026-07-10",
        verdict_source="manual_review",
        summary_json_path=str(summary_file),
    )
    passed_but_not_gold = _sample(
        "machine-only",
        "BV1qapassed00",
        status="qa_passed",
        input_path=str(FIXTURE),
        cache_status="present",
    )
    path = _write_manifest(tmp_path, [gold, passed_but_not_gold])

    summary = run_quality_gate.run_corpus_manifest(str(path), lane="blocking", execute=False)
    assert summary["valid"] is True
    selected_ids = {s["id"] for s in summary["selected"]}
    assert selected_ids == {"complete-gold"}
    # qa_passed must never be promoted into the blocking release lane.
    assert "machine-only" not in selected_ids


def test_blocking_lane_excludes_gold_missing_run_artifacts(tmp_path):
    # accepted_gold with reviewer fields but no summary_json_path / no input file.
    incomplete = _sample(
        "gold-no-artifacts",
        "BV1goldbare00",
        status="accepted_gold",
        input_path="/tmp/does-not-exist-p6r.json",
        cache_status="missing",
        reviewed_by="anyis",
        reviewed_at="2026-07-10",
        verdict_source="manual_review",
        summary_json_path=None,
    )
    path = _write_manifest(tmp_path, [incomplete])
    summary = run_quality_gate.run_corpus_manifest(str(path), lane="blocking", execute=False)
    # Schema is valid (reviewer fields present) but it is not blocking-complete.
    assert summary["valid"] is True
    assert summary["selected_count"] == 0


# --- execute ----------------------------------------------------------------

def test_execute_runs_runner_on_fixture_manifest(tmp_path):
    ready = _sample(
        "ready-fixture",
        "BV1readyfix00",
        status="input_ready",
        input_path=str(FIXTURE),
        cache_status="present",
    )
    path = _write_manifest(tmp_path, [ready])

    summary = run_quality_gate.run_corpus_manifest(
        str(path),
        lane="ready",
        execute=True,
        writer_provider="fixture",
        output_dir=str(tmp_path / "out"),
    )
    assert summary["executed"] is True
    assert summary["selected_count"] == 1
    assert len(summary["results"]) == 1
    res = summary["results"][0]
    assert res["id"] == "ready-fixture"
    assert res["executed"] is True
    assert res["passed"] is True
    assert res["error"] is None


def test_execute_missing_input_fails_clean_without_download(tmp_path, monkeypatch):
    ready = _sample(
        "ready-missing",
        "BV1missing000",
        status="input_ready",
        input_path=str(tmp_path / "nope_fetch_all.json"),
        cache_status="missing",
    )
    path = _write_manifest(tmp_path, [ready])

    # Guard: even in execute mode a missing input must not trigger generation.
    def boom(*a, **k):
        raise AssertionError("must not generate a report for a missing input")

    monkeypatch.setattr(run_quality_gate.generate_report, "report_markdown", boom)

    summary = run_quality_gate.run_corpus_manifest(
        str(path),
        lane="ready",
        execute=True,
        writer_provider="fixture",
        output_dir=str(tmp_path / "out"),
    )
    assert summary["executed"] is True
    res = summary["results"][0]
    assert res["executed"] is False
    assert res["passed"] is False
    assert res["error"] is not None
    assert "input" in res["error"].lower()


def test_execute_dry_when_flag_absent(tmp_path):
    ready = _sample(
        "ready-fixture",
        "BV1readyfix00",
        status="input_ready",
        input_path=str(FIXTURE),
        cache_status="present",
    )
    path = _write_manifest(tmp_path, [ready])
    summary = run_quality_gate.run_corpus_manifest(str(path), lane="ready", execute=False)
    assert summary["executed"] is False
    assert summary["results"] == []
    assert summary["selected_count"] == 1


def test_execute_propagates_quality_options_to_single_sample_gate(tmp_path, monkeypatch):
    ready = _sample(
        "ready-options", "BV1readyopts0", status="input_ready",
        input_path=str(FIXTURE), cache_status="present",
    )
    path = _write_manifest(tmp_path, [ready])
    captured = {}

    def fake_single_sample(*_args, **kwargs):
        captured.update(kwargs)
        return True, {"passed": True}

    monkeypatch.setattr(run_quality_gate, "run_quality_gate", fake_single_sample)
    summary = run_quality_gate.run_corpus_manifest(
        str(path), lane="ready", execute=True, writer_provider="fixture",
        run_fact_check=True, publishable_gate=True, fail_on_fallback_warning=True,
        section_qa_gate=True, depth_profile="claim-first-full", claim_qa_gate=True,
        output_dir=str(tmp_path / "out"),
    )

    assert summary["all_passed"] is True
    assert captured == {
        "writer_provider": "fixture",
        "mode": "full",
        "run_fact_check": True,
        "publishable_gate": True,
        "fail_on_fallback_warning": True,
        "section_qa_gate": True,
        "depth_profile": "claim-first-full",
        "claim_qa_gate": True,
    }


def test_corpus_execution_defaults_to_claim_first_profile(tmp_path, monkeypatch):
    ready = _sample(
        "ready-default-profile", "BV1readyprof0", status="input_ready",
        input_path=str(FIXTURE), cache_status="present",
    )
    path = _write_manifest(tmp_path, [ready])
    captured = {}

    def fake_single_sample(*_args, **kwargs):
        captured.update(kwargs)
        return True, {"passed": True}

    monkeypatch.setattr(run_quality_gate, "run_quality_gate", fake_single_sample)
    summary = run_quality_gate.run_corpus_manifest(
        str(path), lane="ready", execute=True, writer_provider="fixture",
        output_dir=str(tmp_path / "out"),
    )

    assert summary["depth_profile"] == "claim-first-full"
    assert captured["depth_profile"] == "claim-first-full"
