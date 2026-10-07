from datetime import datetime

import mac_doctor


def test_verify_reports_unknown_when_hermes_is_absent(monkeypatch, capsys):
    monkeypatch.setattr(mac_doctor.paths, "hermes_home", lambda: None)
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "loaded", "last_exit": None, "run_interval": "600"})
    monkeypatch.setattr(mac_doctor, "_latest_snapshot", lambda: datetime.now().astimezone().isoformat())
    assert mac_doctor.main(["verify"]) == 0
    output = capsys.readouterr().out
    assert "[UNKNOWN] hermes_cron_jobs" in output
    assert "[PASS] launchagent_loaded" in output


def test_verify_marks_absent_snapshot_unknown(monkeypatch):
    monkeypatch.setattr(mac_doctor.paths, "hermes_home", lambda: None)
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "UNKNOWN", "last_exit": None, "run_interval": None})
    monkeypatch.setattr(mac_doctor, "_latest_snapshot", lambda: None)
    checks = mac_doctor._verify_observations()
    assert [item["status"] for item in checks] == ["UNKNOWN", "UNKNOWN", "UNKNOWN"]
