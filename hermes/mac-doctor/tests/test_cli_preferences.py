"""P4-S5: preferences show / edit / <key>。"""
import mac_doctor


def test_preferences_show_edit_and_key(monkeypatch, capsys):
    prefs = {"facts": {"user_preferences": {"auto_kill_zombies": False}}, "interpretations": [], "suppressions": []}
    monkeypatch.setattr(mac_doctor.preferences, "load", lambda: prefs)

    assert mac_doctor.main(["preferences", "show"]) == 0
    assert '"facts"' in capsys.readouterr().out

    assert mac_doctor.main(["preferences", "facts.user_preferences.auto_kill_zombies"]) == 0
    assert capsys.readouterr().out.strip() == "False"

    opened = []
    monkeypatch.setenv("EDITOR", "true")
    monkeypatch.setattr(mac_doctor, "open_preferences_in_editor", lambda: opened.append(True) or 0)
    assert mac_doctor.main(["preferences", "edit"]) == 0
    assert opened == [True]
