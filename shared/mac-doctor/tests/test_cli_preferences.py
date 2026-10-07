import mac_doctor


def test_preferences_show_and_dotted_key(monkeypatch, capsys):
    prefs = {"facts": {"user_preferences": {"auto_kill_zombies": False}}, "interpretations": [], "suppressions": []}
    monkeypatch.setattr(mac_doctor.preferences, "load_preferences", lambda: prefs)
    assert mac_doctor.main(["preferences", "show"]) == 0
    assert '"facts"' in capsys.readouterr().out
    assert mac_doctor.main(["preferences", "facts.user_preferences.auto_kill_zombies"]) == 0
    assert capsys.readouterr().out.strip() == "False"


def test_preferences_edit_uses_configured_editor(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setenv("EDITOR", "editor-test")
    monkeypatch.setattr(mac_doctor.paths, "preferences_file", lambda: tmp_path / "prefs.json")
    monkeypatch.setattr(mac_doctor.subprocess, "run", lambda args: seen.append(args) or type("R", (), {"returncode": 0})())
    assert mac_doctor.main(["preferences", "edit"]) == 0
    assert seen[0][0] == "editor-test"
