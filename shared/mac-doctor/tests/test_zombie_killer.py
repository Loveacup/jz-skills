import signal

from scripts import zombie_killer


def _prefs():
    return {"facts": {"user_preferences": {"auto_kill_zombies": True},
                      "known_zombie_parents": {"321": {"auto_kill": True}}}}


def test_identity_mismatch_before_signal_sends_no_signal(tmp_path):
    expected = ("321", "1", "Mon Jan 1 00:00:00 2024", "parent command")
    seen = ("321", "1", "Mon Jan 1 00:00:00 2024", "different command")
    signals = []
    result = zombie_killer.kill_known_zombies(
        [{"pid": "654", "ppid": "321", "parent_identity": expected}], _prefs(),
        kill_fn=lambda pid, sig: signals.append((pid, sig)), identity_fn=lambda pid: seen,
        marker_path=tmp_path / "marker.json", sleep_fn=lambda _: None,
    )
    assert signals == []
    assert result["skipped"]["identity_changed"] == ["321"]


def test_parent_gets_term_then_kill_only_after_same_identity_survives_grace(tmp_path):
    identity = ("321", "1", "Mon Jan 1 00:00:00 2024", "parent command")
    signals, sleeps = [], []
    result = zombie_killer.kill_known_zombies(
        [{"pid": "654", "ppid": "321", "parent_identity": identity}], _prefs(),
        kill_fn=lambda pid, sig: signals.append((pid, sig)), identity_fn=lambda pid: identity,
        marker_path=tmp_path / "marker.json", sleep_fn=sleeps.append, grace_seconds=0.5,
    )
    assert signals == [(321, signal.SIGTERM), (321, signal.SIGKILL)]
    assert sleeps == [0.5]
    assert result["killed"] == ["321"]
