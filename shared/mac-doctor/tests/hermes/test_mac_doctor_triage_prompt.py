import json

import mac_doctor_triage as triage


def test_build_prompt_contains_required_sections(tmp_path):
    # 真实 P1 preferences schema：interpretations / suppressions 均为 list-of-dict
    prefs = {
        "version": 1,
        "facts": {"known_short_running_tools": ["ccusage"]},
        "interpretations": [{"id": "sig-a", "text": "known flaky mcp cleanup"}],
        "suppressions": [
            {"signature": "sig-b", "first_seen": 0.0, "last_seen": 9.0e18,
             "count": 2, "ttl_hours": 3},
        ],
    }
    pref_path = tmp_path / "preferences.json"
    pref_path.write_text(json.dumps(prefs), encoding="utf-8")

    snapshot = {"host": "mac", "status": "warn"}
    facts = {"trigger": {"signature": "sig-a"}}
    trend = {"window_hours": 24, "total": 1}

    prompt = triage.build_prompt(
        snapshot=snapshot, facts=facts, trend=trend, preferences_path=pref_path)
    data = json.loads(prompt)

    assert set(data) == {
        "snapshot", "facts", "interpretations",
        "suppressions", "trend", "output_schema",
    }
    assert data["snapshot"] == snapshot
    assert data["facts"] == facts
    assert data["trend"] == trend
    assert data["interpretations"][0]["text"] == "known flaky mcp cleanup"
    assert data["suppressions"][0]["signature"] == "sig-b"
    # memory_write 按 Spec §2.3 为 object
    assert data["output_schema"]["memory_write"]["type"] == "object"
    assert set(data["output_schema"]) == {
        "verdict", "diagnosis", "recommendation",
        "memory_write", "should_push", "push_message",
    }


def test_build_prompt_missing_prefs_falls_back_to_empty(tmp_path):
    # 文件不存在 → load_preferences 返回 DEFAULT（interpretations/suppressions 空 list）
    prompt = triage.build_prompt(
        snapshot={}, facts={}, trend={},
        preferences_path=tmp_path / "absent.json")
    data = json.loads(prompt)
    assert data["interpretations"] == []
    assert data["suppressions"] == []
