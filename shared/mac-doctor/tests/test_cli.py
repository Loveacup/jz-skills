import mac_doctor


def test_root_parser_registers_runtime_and_owned_commands():
    parser = mac_doctor.build_parser()
    assert parser.parse_args(["status", "--json"]).json is True
    assert parser.parse_args(["history", "--hours", "24", "--json"]).hours == 24
    assert parser.parse_args(["check", "--json"]).command == "check"
    assert parser.parse_args(["storage"]).command == "storage"
    assert parser.parse_args(["clean", "plan"]).command == "clean"


def test_install_and_uninstall_flags(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(mac_doctor.paths, "launchagent_plist", lambda: tmp_path / "agent.plist")
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "not loaded"})
    monkeypatch.setattr(mac_doctor.subprocess, "run", lambda *a, **kw: calls.append(a[0]) or type("R", (), {"returncode": 0})())
    assert mac_doctor.main(["uninstall"]) == 0
    assert calls == []
    assert "dry-run" in capsys.readouterr().out
    assert mac_doctor.main(["uninstall", "--force"]) == 0
    assert calls[0][0] == "launchctl"
