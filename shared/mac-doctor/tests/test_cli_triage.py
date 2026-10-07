import mac_doctor


def test_triage_explains_missing_hermes(monkeypatch, capsys):
    monkeypatch.setattr(mac_doctor.paths, "hermes_home", lambda: None)
    assert mac_doctor.main(["triage"]) == 1
    assert "Hermes is not installed" in capsys.readouterr().err
