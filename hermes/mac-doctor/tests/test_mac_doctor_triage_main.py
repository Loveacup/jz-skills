import json

import mac_doctor_triage as triage


def test_main_missing_stdin_is_silent_stdout(capsys):
    rc = triage.main(argv=[], stdin_text="")
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == ""
    assert "warn" in out.err.lower()


def test_main_should_push_false_stdout_empty(capsys):
    result = {
        "verdict": "transient",
        "diagnosis": "transient cpu spike",
        "recommendation": "suppress",
        "memory_write": {"key": "interpretations.add", "value": {"id": "foo"}},
        "should_push": False,
        "push_message": "do not send",
    }
    rc = triage.emit_result(json.dumps(result))
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == ""
    assert out.err == ""


def test_main_should_push_true_emits_strict_schema(capsys):
    result = {
        "verdict": "persistent",
        "diagnosis": "mcp zombie repeated",
        "recommendation": "restart service",
        "memory_write": {"key": "facts.add", "value": {"id": "mcp-zombie"}},
        "should_push": True,
        "push_message": "mac-doctor: mcp zombie repeated",
        "extra_noise": "should be stripped",  # 非契约字段须被剔除
    }
    rc = triage.emit_result(json.dumps(result))
    out = capsys.readouterr()
    data = json.loads(out.out)
    assert rc == 0
    assert set(data) == {
        "verdict", "diagnosis", "recommendation",
        "memory_write", "should_push", "push_message",
    }
    assert data["should_push"] is True
    assert data["memory_write"] == {"key": "facts.add", "value": {"id": "mcp-zombie"}}


def test_main_bad_llm_json_warns_and_stdout_empty(capsys):
    rc = triage.emit_result("{bad json")
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == ""
    assert "warn" in out.err.lower()


def test_main_delegates_to_emit_result(capsys):
    result = {
        "verdict": "transient", "diagnosis": "d", "recommendation": "r",
        "memory_write": {}, "should_push": False, "push_message": "",
    }
    rc = triage.main(argv=[], stdin_text=json.dumps(result))
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == ""  # should_push=false → 静默
