import mac_doctor


def test_uninstall_defaults_to_dry_run_and_force_checks_return(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(mac_doctor.paths, "launchagent_plist", lambda: tmp_path / "agent.plist")
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "not loaded"})
    monkeypatch.setattr(mac_doctor.subprocess, "run", lambda args, **kwargs: calls.append(args) or type("R", (), {"returncode": 0})())
    assert mac_doctor.main(["uninstall"]) == 0
    assert calls == []
    assert "dry-run" in capsys.readouterr().out
    assert mac_doctor.main(["uninstall", "--force"]) == 0
    assert calls[0][0] == "launchctl"


def test_uninstall_propagates_bootout_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(mac_doctor.paths, "launchagent_plist", lambda: tmp_path / "agent.plist")
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "not loaded"})
    monkeypatch.setattr(mac_doctor.subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 5})())
    assert mac_doctor.main(["uninstall", "--force"]) == 5
