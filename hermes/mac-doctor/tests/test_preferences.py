"""mac-doctor preferences.py 契约测试 (P1, 6 TDD slice).

运行: cd ~/.hermes/skills/apple/mac-doctor && python3 -m pytest tests/test_preferences.py -v
依赖: pytest tmp_path / capsys fixture, 不建 conftest.py。
suppressions 采用 Spec §2.1 list 模型: [{signature, first_seen, last_seen, count, ttl_hours}]。
"""


# --- S1: load_default --------------------------------------------------------
def test_load_missing_returns_default_copy(tmp_path):
    from scripts.preferences import DEFAULT, load_preferences

    path = tmp_path / "preferences.json"
    prefs = load_preferences(path)

    assert prefs == DEFAULT
    assert prefs is not DEFAULT
    # 必含 Spec schema 关键段
    assert prefs["version"] == 1
    assert "facts" in prefs
    assert prefs["suppressions"] == []
    # 深拷贝: 改返回值不污染 DEFAULT
    prefs["interpretations"].append({"id": "x"})
    assert DEFAULT["interpretations"] == []


# --- S2: save_atomic ---------------------------------------------------------
def test_save_preferences_atomic_roundtrip(tmp_path):
    import json
    from scripts.preferences import load_preferences, save_preferences

    path = tmp_path / "preferences.json"
    prefs = {
        "version": 1,
        "facts": {"known_short_running_tools": ["ripgrep"]},
        "interpretations": [{"id": "disk_full", "text": "free space"}],
        "suppressions": [],
    }

    save_preferences(path, prefs)

    assert load_preferences(path) == prefs
    assert json.loads(path.read_text(encoding="utf-8")) == prefs
    assert not list(tmp_path.glob("*.tmp"))

    # 父目录不存在时自动创建
    nested = tmp_path / "a" / "b" / "preferences.json"
    save_preferences(nested, prefs)
    assert load_preferences(nested) == prefs


# --- S3: backup_on_corruption ------------------------------------------------
def test_load_corrupt_preferences_backs_up_and_returns_default(tmp_path, capsys):
    from scripts.preferences import DEFAULT, load_preferences

    path = tmp_path / "preferences.json"
    path.write_text("{bad json", encoding="utf-8")

    prefs = load_preferences(path)
    err = capsys.readouterr().err

    assert prefs == DEFAULT
    assert "corrupt preferences" in err
    broken = list(tmp_path.glob("preferences.json.broken-*"))
    assert len(broken) == 1
    assert broken[0].read_text(encoding="utf-8") == "{bad json"


# --- S4: add_interpretation_dedup --------------------------------------------
def test_add_interpretation_deduplicates_by_id(tmp_path):
    from scripts.preferences import add_interpretation, load_preferences

    path = tmp_path / "preferences.json"
    item = {"id": "battery_health", "text": "Ignore known battery warning"}

    assert add_interpretation(path, item) is True
    assert add_interpretation(path, dict(item)) is False

    prefs = load_preferences(path)
    assert prefs["interpretations"] == [item]


# --- S5: suppression_ttl (list 模型) -----------------------------------------
def test_suppression_ttl_active_and_expired_cleanup(tmp_path):
    from scripts.preferences import is_suppressed, load_preferences, save_preferences

    path = tmp_path / "preferences.json"
    save_preferences(path, {
        "version": 1,
        "facts": {},
        "interpretations": [],
        "suppressions": [
            {"signature": "active",  "first_seen": 0, "last_seen": 5000, "count": 2, "ttl_hours": 1},
            {"signature": "expired", "first_seen": 0, "last_seen": 1000, "count": 1, "ttl_hours": 1},
        ],
    })

    # active: 5000 + 3600 = 8600 > 6000 → 活跃; expired: 1000 + 3600 = 4600 <= 6000 → 过期
    assert is_suppressed(path, "active", now=6000) is True
    assert is_suppressed(path, "expired", now=6000) is False

    prefs = load_preferences(path)
    sigs = {s["signature"] for s in prefs["suppressions"]}
    assert "active" in sigs
    assert "expired" not in sigs


# --- S6: multi_field_validation (list 模型) ----------------------------------
def test_multi_field_validation_rejects_invalid_preferences(tmp_path, capsys):
    from scripts.preferences import DEFAULT, load_preferences

    path = tmp_path / "preferences.json"
    # interpretations 应为 list, suppressions 应为 list — 此处类型全错
    path.write_text(
        '{"version": 1, "facts": {}, "interpretations": "bad", "suppressions": {}}',
        encoding="utf-8",
    )

    prefs = load_preferences(path)
    err = capsys.readouterr().err

    assert prefs == DEFAULT
    assert "invalid preferences" in err
    assert len(list(tmp_path.glob("preferences.json.broken-*"))) == 1
