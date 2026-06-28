import json

import mac_doctor_triage as triage


def test_read_trigger_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert triage.read_trigger() is None


def test_read_trigger_parses_json_dict(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = tmp_path / ".hermes" / "inspection" / ".triage-trigger"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"source": "watchdog", "signature": "abc"}),
                 encoding="utf-8")

    assert triage.read_trigger() == {"source": "watchdog", "signature": "abc"}


def test_read_trigger_malformed_raises_valueerror(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = tmp_path / ".hermes" / "inspection" / ".triage-trigger"
    p.parent.mkdir(parents=True)
    p.write_text("not json at all", encoding="utf-8")

    try:
        triage.read_trigger()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_read_trigger_non_object_raises_valueerror(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = tmp_path / ".hermes" / "inspection" / ".triage-trigger"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    try:
        triage.read_trigger()
        assert False, "expected ValueError"
    except ValueError:
        pass
