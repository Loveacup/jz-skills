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


def test_watchdog_gated_message_does_not_crash_on_unknown_ppid(monkeypatch, tmp_path, capsys):
    """⏸️ 拦截判定对 PPID 不在 known_zombie_parents 的 zombie 不崩 (回归 2026-07-03 01:40 cron 挂)。

    之前: known_parents.get(ppid) 返回 None, None.get("auto_kill") 抛 AttributeError → exit 1
    修正: (known_parents.get(ppid) or {}).get("auto_kill") — 找不到 PPID 时当 {} 处理, 跳过。
    """
    mod = load_watchdog()
    # 9 个 zombie 全部 PPID 不在 known_parents (sshd-session / iii 都不是 auto_kill=true)
    monkeypatch.setattr(mod, "check_zombies", lambda: (
        "warn", [{"pid": str(i), "ppid": "99999", "cmd": "<defunct>"} for i in range(1, 10)]
    ))
    monkeypatch.setattr(mod, "check_kanban", lambda: ("ok", None))
    monkeypatch.setattr(mod, "check_mcp_cleanup", lambda: ("ok", None))
    monkeypatch.setattr(mod, "load_state", lambda: {})
    monkeypatch.setattr(mod, "load_prefs", lambda: {
        "facts": {
            "known_zombie_parents": {"31909": {"auto_kill": True}},  # 99999 不在里面
            "user_preferences": {"auto_kill_zombies": False},  # gated=True
        }
    })
    # 不应抛异常
    mod.main()
    out = capsys.readouterr().out
    assert "⏸️" not in out, "99999 不在 prefs, 不应报拦截"


def test_watchdog_gated_message_only_prints_when_actual_intersection(monkeypatch, tmp_path, capsys):
    """⏸️ 拦截信息只对 zombie 集里 PPID auto_kill=true 的 PPID 显示 (回归 2026-07-02)。

    旧逻辑 any(z.ppid in known_parents) 会把 auto_kill=false (如 iii PPID 97120) 也算上, 误导。
    修正后, gated=True 但 zombie 集无交集 → 不打印 ⏸️ 行。
    """
    mod = load_watchdog()
    # monkeypatch check_zombies 返回 zombie 集: 5 个 iii 僵尸 (auto_kill=false) + 0 个 Raycast
    monkeypatch.setattr(mod, "check_zombies", lambda: (
        "warn", [
            {"pid": "4000", "ppid": "97120", "cmd": "<defunct>"},
            {"pid": "4006", "ppid": "97120", "cmd": "<defunct>"},
        ]
    ))
    prefs_with_iii = {
        "facts": {
            "known_zombie_parents": {
                "97120": {"auto_kill": False, "name": "iii"},
                "31909": {"auto_kill": True, "name": "Raycast"},  # 不在 zombie 集
            },
            "user_preferences": {"auto_kill_zombies": False},
        }
    }
    monkeypatch.setattr(mod, "load_prefs", lambda: prefs_with_iii)
    # 让 main 不真跑 ps / 不静默
    monkeypatch.setattr(mod, "check_kanban", lambda: ("ok", None))
    monkeypatch.setattr(mod, "check_mcp_cleanup", lambda: ("ok", None))
    monkeypatch.setattr(mod, "load_state", lambda: {})
    # 触发 main
    mod.main()
    out = capsys.readouterr().out
    assert "⏸️" not in out, "gated=True 但 zombie 集无 auto_kill=true PPID, 不应显示拦截信息"
    assert "已消费" not in out


def test_watchdog_gated_message_prints_for_actual_match(monkeypatch, tmp_path, capsys):
    """⏸️ 拦截信息打印时, 列出实际被拦截的 PPID (修正: 精确到 PPID 而不只是"gated" 状态)。"""
    mod = load_watchdog()
    monkeypatch.setattr(mod, "check_zombies", lambda: (
        "warn", [{"pid": "31991", "ppid": "31909", "cmd": "<defunct>"}]
    ))
    monkeypatch.setattr(mod, "check_kanban", lambda: ("ok", None))
    monkeypatch.setattr(mod, "check_mcp_cleanup", lambda: ("ok", None))
    monkeypatch.setattr(mod, "load_state", lambda: {})
    monkeypatch.setattr(mod, "load_prefs", lambda: {
        "facts": {
            "known_zombie_parents": {"31909": {"auto_kill": True, "name": "Raycast"}},
            "user_preferences": {"auto_kill_zombies": False},
        }
    })
    mod.main()
    out = capsys.readouterr().out
    assert "⏸️" in out and "31909" in out, "实际有 31909 在 zombie 集 + auto_kill=true + 总开关 False, 应显示具体 PPID"


def test_watchdog_integrates_zombie_killer_hook(monkeypatch, tmp_path):
    """watchdog 集成 zombie_killer 钩子: main() 在 zombie=warn 时调用 kill_known_zombies。

    Phase 2 (2026-07-02): 杀 known_zombie_parents 抽到独立模块, watchdog 通过
    importlib 动态加载。本测试验证 loader 返回的模块确实暴露 kill_known_zombies API。
    """
    mod = load_watchdog()
    zk = mod._load_zombie_killer_module()
    assert callable(zk.kill_known_zombies)
    # 4 个 skipped 子桶的 schema 契约
    sentinel = zk.kill_known_zombies(
        [], {"facts": {"user_preferences": {"auto_kill_zombies": False},
                       "known_zombie_parents": {}}},
    )
    expected_keys = {"cooldown", "not_found", "permission_denied", "error"}
    assert set(sentinel["skipped"].keys()) == expected_keys


def test_watchdog_line_count_stays_under_460():
    """watchdog 行数硬约束 (<460)。

    历史: v2.4.2 设 450。Phase 2 (2026-07-02) 加 L2 kill_known_zombies 钩子后,代码
    抽到独立 zombie_killer 模块,watchdog 净增 ~3 行, 上限放宽到 460。仍为软约束,
    用于早预警膨胀;新功能应优先考虑拆模块而不是改这个数字。
    """
    path = Path("/Users/alexcai/.hermes/profiles/cron-worker/scripts/mac-doctor-watchdog.py")
    assert len(path.read_text(encoding="utf-8").splitlines()) < 460
