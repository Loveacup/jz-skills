"""mac-doctor watchdog 集成测试 (P2).

watchdog.py 位于 cron-worker profile，PYTHONPATH 下无法直接 import，
统一用 importlib.util.spec_from_file_location 动态加载（每个 test 拿到全新模块，
模块级 _seen_counts 因此天然隔离）。

5 个 TDD slice × 2 test = 10 case，集中本文件，函数式写法。
"""
import importlib.util
import json
from pathlib import Path

WATCHDOG = Path("/Users/alexcai/.hermes/profiles/cron-worker/scripts/mac-doctor-watchdog.py")


def load_watchdog():
    spec = importlib.util.spec_from_file_location("mac_doctor_watchdog", WATCHDOG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# S1 — preferences 动态加载 + cron 入口不变
# ---------------------------------------------------------------------------
def test_load_preferences_uses_tmp_path(monkeypatch, tmp_path):
    mod = load_watchdog()
    prefs_file = tmp_path / "preferences.json"
    prefs_file.write_text(json.dumps({
        "version": 1,
        "facts": {
            "known_short_running_tools": ["ccusage"],
            "known_zombie_parents": {},
            "known_mcp_cleanup_targets": [],
            "user_preferences": {
                "quiet_hours": {"start": 23, "end": 7},
                "auto_kill_zombies": False,
                "auto_kill_mcp_orphans": True
            }
        },
        "interpretations": [],
        "suppressions": []
    }), encoding="utf-8")
    monkeypatch.setattr(mod, "PREFERENCES_FILE", prefs_file)
    assert mod.load_prefs()["facts"]["known_short_running_tools"] == ["ccusage"]


def test_main_signature_still_no_args():
    mod = load_watchdog()
    assert callable(mod.main)
    assert mod.main.__code__.co_argcount == 0


# ---------------------------------------------------------------------------
# S2 — known_short_running_tools 白名单过滤 CPU 100% 告警
# ---------------------------------------------------------------------------
def test_known_short_running_tool_suppresses_cpu_alert(monkeypatch):
    mod = load_watchdog()
    prefs = {
        "facts": {
            "known_short_running_tools": ["ccusage"],
            "known_zombie_parents": {},
            "known_mcp_cleanup_targets": [],
            "user_preferences": {}
        },
        "interpretations": [],
        "suppressions": []
    }
    alert = {"text": "Process ccusage sustained CPU 100%", "is_anomaly": False}
    assert mod.is_known_short_running_tool("ccusage", prefs) is True
    assert mod.filter_known_short_running_alerts([alert], prefs) == []


def test_unknown_cpu_alert_survives_filter():
    mod = load_watchdog()
    prefs = {"facts": {"known_short_running_tools": ["ccusage"]}}
    alert = {"text": "Process python sustained CPU 100%", "is_anomaly": False}
    assert mod.filter_known_short_running_alerts([alert], prefs) == [alert]


# ---------------------------------------------------------------------------
# S3 — 连续同 signature 写 suppression，TTL 内静默
# ---------------------------------------------------------------------------
def test_same_signature_second_seen_writes_suppression(monkeypatch, tmp_path):
    mod = load_watchdog()
    prefs_file = tmp_path / "preferences.json"
    monkeypatch.setattr(mod, "PREFERENCES_FILE", prefs_file)
    prefs = mod.load_prefs()
    sig = "collector:Disk low"
    assert mod.record_signature_seen(sig, prefs, now=1000) is False
    assert mod.record_signature_seen(sig, prefs, now=1010) is True
    saved = json.loads(prefs_file.read_text(encoding="utf-8"))
    suppressions = saved["suppressions"]
    assert suppressions[0]["signature"] == sig
    assert suppressions[0]["count"] == 2
    assert suppressions[0]["ttl_hours"] == 3


def test_active_suppression_silences_signature(monkeypatch, tmp_path):
    mod = load_watchdog()
    prefs_file = tmp_path / "preferences.json"
    monkeypatch.setattr(mod, "PREFERENCES_FILE", prefs_file)
    prefs = mod.load_prefs()
    sig = "zombie:1,2,3"
    mod.add_suppression(sig, prefs, now=1000)
    assert mod.is_signature_suppressed(sig, mod.load_prefs(), now=1001) is True


# ---------------------------------------------------------------------------
# S4 — trigger_triage 写 .triage-trigger，写失败 fail-soft
# ---------------------------------------------------------------------------
def test_trigger_triage_writes_reason(monkeypatch, tmp_path):
    mod = load_watchdog()
    trigger = tmp_path / ".triage-trigger"
    monkeypatch.setattr(mod, "TRIAGE_TRIGGER_FILE", trigger)
    mod.trigger_triage("collector:Disk low")
    payload = json.loads(trigger.read_text(encoding="utf-8"))
    assert payload["reason"] == "collector:Disk low"
    assert "created_at" in payload


def test_trigger_triage_failure_does_not_raise(monkeypatch, tmp_path):
    mod = load_watchdog()
    monkeypatch.setattr(mod, "TRIAGE_TRIGGER_FILE", tmp_path / "missing" / ".triage-trigger")
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    mod.trigger_triage("x")


# ---------------------------------------------------------------------------
# S5 — save_report_state 封装 zombie_sig/mcp_cleaned_msg 写回 + 行数 < 450
# ---------------------------------------------------------------------------
def test_save_report_state_keeps_zombie_sig_and_mcp_msg(monkeypatch, tmp_path):
    mod = load_watchdog()
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(mod, "STATE_FILE", state_file)
    mod.save_report_state(
        diagnosis="Disk low",
        snap={"disk_free_gb": 9.5},
        issues=[
            ("zombie", [{"pid": "2", "cmd": "z"}, {"pid": "1", "cmd": "z"}]),
            ("mcp", "清理了 2 个孤儿 MCP 进程"),
        ],
    )
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["zombie_sig"] == "1,2"
    assert state["mcp_cleaned_msg"] == "清理了 2 个孤儿 MCP 进程"


def test_watchdog_line_count_stays_under_450():
    path = Path("/Users/alexcai/.hermes/profiles/cron-worker/scripts/mac-doctor-watchdog.py")
    assert len(path.read_text(encoding="utf-8").splitlines()) < 450
