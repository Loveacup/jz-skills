import mac_doctor


def test_install_checks_launchagent_verification(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mac_doctor, "COLLECTOR", tmp_path / "collector-daemon.py")
    mac_doctor.COLLECTOR.write_text("collector")
    monkeypatch.setattr(mac_doctor.subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0})())
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "loaded"})
    assert mac_doctor.main(["install"]) == 0
    output = capsys.readouterr().out
    assert "registration was NOT performed" in output
    assert '"mac-doctor-quick"' in output

def test_install_fails_when_launchagent_not_loaded(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mac_doctor, "COLLECTOR", tmp_path / "collector-daemon.py")
    mac_doctor.COLLECTOR.write_text("collector")
    monkeypatch.setattr(mac_doctor.subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0})())
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "not loaded"})
    assert mac_doctor.main(["install"]) == 1
    assert "verification failed" in capsys.readouterr().err
