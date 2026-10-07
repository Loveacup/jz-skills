import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "scripts" / "preferences.py"
spec = importlib.util.spec_from_file_location("preferences_paths", MODULE)
preferences = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preferences)


def test_inspection_dir_uses_explicit_override(monkeypatch, tmp_path):
    target = tmp_path / "chosen"
    monkeypatch.setenv("MAC_DOCTOR_INSPECTION_DIR", str(target))
    assert preferences.inspection_dir() == target


def test_all_layers_use_same_override_when_profile_home_is_redirected(monkeypatch, tmp_path):
    import importlib.util

    inspection = tmp_path / "shared-inspection"
    monkeypatch.setenv("HOME", "/tmp/profile-home")
    monkeypatch.setenv("MAC_DOCTOR_INSPECTION_DIR", str(inspection))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    skill = Path(__file__).parents[1]
    adapters = skill / "adapters" / "hermes"
    collector = load("collector_path_test", skill / "scripts" / "collector-daemon.py")
    zombie = load("zombie_path_test", skill / "scripts" / "zombie_killer.py")
    triage = load("triage_path_test", adapters / "triage.py")
    watchdog = load("watchdog_path_test", adapters / "watchdog.py")
    assert collector.DB_FILE == inspection / "history.db"
    assert zombie.DEFAULT_MARKER_PATH == inspection / ".known-zombie-killed.json"
    assert triage.HISTORY_DB == inspection / "history.db"
    assert triage._trigger_path() == inspection / ".triage-trigger"
    assert watchdog.PREFERENCES_FILE == inspection / "preferences.json"
    assert watchdog.TRIAGE_TRIGGER_FILE == inspection / ".triage-trigger"
    assert "/tmp/profile-home" not in str(collector.DB_FILE)
