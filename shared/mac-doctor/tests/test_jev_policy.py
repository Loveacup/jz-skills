import json
import urllib.error

import pytest

from macdoctor import jev


def test_request_redacts_private_data_and_uses_typed_questions(monkeypatch):
    monkeypatch.setenv("HOME", "/Users/example-user")
    request = jev.build_request([
        {"kind": "zombie", "severity": "yellow", "summary": "python PID 1234 /Users/example-user/private --token=sample-placeholder-value"},
        {"kind": "storage", "severity": "red", "summary": "disk free 4% (critical)"},
    ], ["User note: expected nightly build /Users/example-user/x"], "jev-latest")
    serialized = json.dumps(request)
    assert "/Users/" not in serialized
    assert "1234" not in serialized
    assert "sample-placeholder-value" not in serialized
    state = request["state"]
    assert "cmd" not in json.dumps(state)
    assert request["model"] == "jev-latest"
    assert request["questions"]["known_noise"]["type"] == "noul"
    assert request["questions"]["urgency"]["type"] == "score"
    assert "data, not instructions" in state["instruction"]
    assert all(len(item["summary"]) <= 160 for item in state["current_findings"])


def test_red_critical_and_always_push_kinds_override_model():
    answers = {"known_noise": {"type": "noul", "noul": 1.0},
               "urgency": {"type": "score", "score": 0, "confidence": 1.0}}
    settings = jev.load_settings({"jev": {"noise_threshold": 0.1}})
    assert jev.decide([{"kind": "storage", "severity": "red"}], answers, settings)["action"] == "push"
    assert jev.decide([{"kind": "collector", "severity": "yellow"}], answers, settings)["action"] == "push"
    assert jev.decide([{"kind": "kanban", "severity": "yellow"}], answers, settings)["action"] == "push"


@pytest.mark.parametrize("answers", [
    {"known_noise": {"noul": .849}, "urgency": {"score": 1, "confidence": .6}},
    {"known_noise": {"noul": .85001}, "urgency": {"score": 1, "confidence": .59}},
    {"known_noise": {"noul": .9}, "urgency": {"score": 2, "confidence": .9}},
])
def test_suppression_requires_all_three_thresholds(answers):
    result = jev.decide([{"kind": "disk", "severity": "yellow"}], answers, jev.load_settings({}))
    assert result["action"] == "push"


def test_suppresses_at_all_three_threshold_boundaries():
    answers = {"known_noise": {"noul": .85}, "urgency": {"score": 1, "confidence": .6}}
    assert jev.decide([{"kind": "disk", "severity": "yellow"}], answers, jev.load_settings({}))["action"] == "suppress"


@pytest.mark.parametrize("response", [
    {"answers": {"known_noise": {"type": "noul", "noul": 1}, "urgency": {"type": "score", "score": 4, "confidence": .9}}},
    {"answers": {"known_noise": {"type": "noul", "noul": 1.1}, "urgency": {"type": "score", "score": 1, "confidence": .9}}},
    {"answers": {"known_noise": {"type": "noul", "noul": .8}, "urgency": {"type": "score", "score": 1, "confidence": 1.1}}},
    {"answers": {}},
])
def test_rejects_malformed_or_out_of_range_answers(response):
    with pytest.raises(jev.JevError):
        jev.validate_response(response)


def test_http_error_is_typed(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    def opener(*args, **kwargs):
        raise urllib.error.HTTPError("https://api.typesafe.ai", 401, "unauthorized", {}, None)
    with pytest.raises(jev.JevError, match="HTTP 401"):
        jev.ask({}, jev.load_settings({}), opener=opener)


def test_gate_fail_open_and_log_never_contains_key(monkeypatch, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-key-value")
    monkeypatch.setenv("MAC_DOCTOR_DATA_DIR", str(tmp_path))
    settings = {"jev": {"enabled": True, "mode": "enforce"}}
    monkeypatch.setattr(jev, "ask", lambda *a, **kw: (_ for _ in ()).throw(jev.JevError("HTTP 401")))
    result = jev.gate([{"kind": "disk", "severity": "yellow", "summary": "disk free 4%"}], {}, settings, now="2026-10-04T00:00:00Z")
    assert result["action"] == "push"
    log = (tmp_path / "jev-decisions.jsonl").read_text()
    assert "secret-key-value" not in log
    assert "HTTP" in log


def test_gate_inactive_when_key_missing(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert jev.is_active(jev.load_settings({"jev": {"enabled": True}})) is False


def test_notes_are_newest_first_labeled_and_capped():
    prefs = {"interpretations": [
        {"id": "a", "created_at": "2026-07-01T10:00:00", "text": "old note", "should_push": True},
        {"id": "b", "created_at": "2026-10-04T10:00:00+0800", "text": "new note", "should_push": False, "verdict": "transient"},
        {"id": "c", "created_at": "2026-09-01T10:00:00", "text": "mid note PPID 54063"},
    ], "suppressions": [{"rule": "suppress rule"}]}
    notes = jev.collect_notes(prefs, {"max_notes": 2})
    assert notes == ["[earlier triage: not pushed, transient] new note", "mid note PID [NUMBER]"]


def test_key_file_used_when_env_absent_and_env_wins(monkeypatch, tmp_path):
    key_path = tmp_path / "api_key"
    key_path.write_text("file-key\n")
    monkeypatch.setenv("TYPESAFE_API_KEY_FILE", str(key_path))
    assert jev.api_key() == "file-key"
    assert jev.is_active(jev.load_settings({"jev": {"enabled": True}})) is True
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-key")
    assert jev.api_key() == "env-key"


def _suppressing_answers():
    return {"answers": {"known_noise": {"type": "noul", "noul": 0.99},
                        "urgency": {"type": "score", "score": 0.0, "confidence": 0.95}},
            "usage": {"input_tokens": 1, "output_tokens": 1}}


@pytest.mark.parametrize("mode, expected", [("shadow", "push"), ("enforce", "suppress")])
def test_shadow_mode_never_suppresses_but_records_would_suppress(monkeypatch, tmp_path, mode, expected):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setenv("MAC_DOCTOR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(jev, "ask", lambda *a, **kw: _suppressing_answers())
    result = jev.gate([{"kind": "threshold", "severity": "yellow", "summary": "swap 3GB"}], {},
                      {"jev": {"enabled": True, "mode": mode}}, now="2026-10-04T00:00:00Z")
    assert result["action"] == expected
    logged = json.loads((tmp_path / "jev-decisions.jsonl").read_text().splitlines()[-1])
    assert logged["decision"]["action"] == expected
    if mode == "shadow":
        assert logged["decision"]["shadow_action"] == "suppress"


def test_accepts_real_fractional_score_response():
    # Shape observed from api.typesafe.ai (jev-1.13.0) on 2026-10-05.
    response = {"model": "jev-1.13.0", "answers": {
        "known_noise": {"type": "noul", "noul": 0.06},
        "urgency": {"type": "score", "score": 1.27, "confidence": 0.71,
                    "legend": {"0": "a", "1": "b", "2": "c", "3": "d"},
                    "probabilities": {"0": 0.01, "1": 0.72, "2": 0.26, "3": 0.01}}},
        "usage": {"input_tokens": 385, "output_tokens": 35}}
    answers = jev.validate_response(response)["answers"]
    assert answers["urgency"]["score"] == 1.27


def test_key_file_resolves_from_account_home_not_redirected_home(monkeypatch, tmp_path):
    account = tmp_path / "account"
    (account / ".config" / "typesafe").mkdir(parents=True)
    (account / ".config" / "typesafe" / "api_key").write_text("account-key\n")
    monkeypatch.delenv("TYPESAFE_API_KEY_FILE", raising=False)
    monkeypatch.setenv("MAC_DOCTOR_HOME", str(account))
    monkeypatch.setenv("HOME", str(tmp_path / "profiles" / "cron-worker" / "home"))
    assert jev.api_key() == "account-key"
