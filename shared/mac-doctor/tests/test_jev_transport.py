import json
import socket
import urllib.error

import pytest

from macdoctor import jev


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def valid_response():
    return {"answers": {
        "known_noise": {"type": "noul", "noul": 0.91},
        "urgency": {"type": "score", "score": 1, "confidence": 0.88},
    }, "usage": {"input_tokens": 17, "output_tokens": 4}}


def test_ask_posts_key_and_timeout_and_returns_validated_answers(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-secret-token")
    observed = {}

    def opener(request, timeout):
        observed["request"] = request
        observed["timeout"] = timeout
        return Reply(json.dumps(valid_response()).encode())

    result = jev.ask({"model": "jev-latest"}, jev.load_settings({"jev": {"timeout_s": 3}}), opener)
    assert observed["timeout"] == 3
    assert observed["request"].get_header("Authorization") == "Bearer test-secret-token"
    assert result["answers"]["urgency"]["score"] == 1
@pytest.mark.parametrize("failure", [
    lambda: socket.timeout("late"),
    lambda: urllib.error.HTTPError("https://example.invalid", 401, "unauthorized", {}, None),
    lambda: Reply(b"not json"),
])
def test_gate_fails_open_and_logs_transport_errors(monkeypatch, tmp_path, failure):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-do-not-log")
    monkeypatch.setenv("MAC_DOCTOR_DATA_DIR", str(tmp_path))

    real_ask = jev.ask
    def opener(*args, **kwargs):
        outcome = failure()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(jev, "ask", lambda request, settings: real_ask(request, settings, opener=opener))
    decision = jev.gate([{"kind": "threshold", "severity": "yellow", "summary": "disk free 4%"}],
                        {}, {"jev": {"enabled": True}}, now="2026-10-04T00:00:00Z")
    assert decision["action"] == "push"
    record = json.loads((tmp_path / "jev-decisions.jsonl").read_text().strip())
    assert record["error"]
    assert "secret-do-not-log" not in json.dumps(record)
