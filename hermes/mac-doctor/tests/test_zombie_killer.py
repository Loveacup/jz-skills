"""zombie_killer 单元测试: Phase 2 Raycast 配置 gap 钩子 (2026-07-02)。

覆盖:
- 总开关拦截 (gated)
- 候选 PPID 挑选 (pick_known_kill_ppids)
- 冷却 (should_skip_ppid)
- 主函数: killed / 4 个 skipped 子桶
- marker 健壮性: 坏 JSON / 坏 schema / 坏类型 → fail-soft
- 空 zombie / 空 prefs → 安全返回

设计: kill_fn / now_fn / marker_path 全部注入,不真杀任何进程。
"""
import json
import sys
import time
from pathlib import Path

import pytest

# 直接 import runtime default skill 的 zombie_killer (与 cron-worker 加载的同一份)
_RUNTIME_PATH = Path("/Users/alexcai/.hermes/skills/apple/mac-doctor/scripts/zombie_killer.py")
_spec = __import__("importlib").util.spec_from_file_location("zombie_killer", _RUNTIME_PATH)
zombie_killer = __import__("importlib").util.module_from_spec(_spec)
sys.modules["zombie_killer"] = zombie_killer
_spec.loader.exec_module(zombie_killer)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _make_prefs(auto_kill_zombies=True, known_parents=None):
    return {
        "version": 1,
        "facts": {
            "known_zombie_parents": known_parents or {},
            "user_preferences": {
                "auto_kill_zombies": auto_kill_zombies,
                "quiet_hours": {"start": 23, "end": 7},
            },
        },
        "interpretations": [],
        "suppressions": [],
    }


def _make_zombies(ppid_pairs):
    return [{"pid": pid, "ppid": ppid, "cmd": cmd} for ppid, pid, cmd in ppid_pairs]


# ---------------------------------------------------------------------------
# load_kill_marker / save_kill_marker
# ---------------------------------------------------------------------------
def test_load_kill_marker_missing_returns_empty(tmp_path):
    assert zombie_killer.load_kill_marker(tmp_path / "missing.json") == {}


def test_load_kill_marker_corrupt_json_returns_empty(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json at all")
    assert zombie_killer.load_kill_marker(p) == {}
    assert "marker 损坏" in capsys.readouterr().err


def test_load_kill_marker_non_dict_returns_empty(tmp_path, capsys):
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]))
    assert zombie_killer.load_kill_marker(p) == {}
    assert "顶层非 dict" in capsys.readouterr().err


def test_load_kill_marker_filters_bad_types(tmp_path):
    """坏类型项 (val 非 number) 静默丢,不报噪音。

    注: JSON 规范 key 必须是 string,所以 int key 123 在 JSON 层就被转成 "123" —
    我们的 dict 过滤只看 val 类型,不影响 key。
    """
    p = tmp_path / "mixed.json"
    p.write_text(json.dumps({
        "good": 1234.5,
        "bad_val": [1, 2],  # val 不是 number
        "good_zero": 0,
    }))
    marker = zombie_killer.load_kill_marker(p)
    assert marker == {"good": 1234.5, "good_zero": 0.0}


def test_save_kill_marker_roundtrip(tmp_path):
    p = tmp_path / "marker.json"
    zombie_killer.save_kill_marker({"31909": 1234.5}, p)
    assert p.exists()
    assert zombie_killer.load_kill_marker(p) == {"31909": 1234.5}


# ---------------------------------------------------------------------------
# pick_known_kill_ppids
# ---------------------------------------------------------------------------
def test_pick_known_kill_ppids_filters_by_auto_kill_true():
    prefs = _make_prefs(known_parents={
        "31909": {"auto_kill": True, "name": "Raycast"},
        "54063": {"auto_kill": False, "name": "RustDesk"},
        "97120": {"auto_kill": True, "name": "iii"},
    })
    zombies = _make_zombies([
        ("31909", "31991", "<defunct>"),
        ("54063", "54622", "<defunct>"),
        ("97120", "4000", "<defunct>"),
    ])
    picked = zombie_killer.pick_known_kill_ppids(zombies, prefs)
    assert picked == ["31909", "97120"]  # sorted, 54063 (auto_kill=False) 被滤


def test_pick_known_kill_ppids_dedup():
    prefs = _make_prefs(known_parents={"31909": {"auto_kill": True}})
    zombies = _make_zombies([
        ("31909", "1", "<defunct>"),
        ("31909", "2", "<defunct>"),
        ("31909", "3", "<defunct>"),
    ])
    assert zombie_killer.pick_known_kill_ppids(zombies, prefs) == ["31909"]


def test_pick_known_kill_ppids_empty_inputs():
    assert zombie_killer.pick_known_kill_ppids([], _make_prefs()) == []
    assert zombie_killer.pick_known_kill_ppids(_make_zombies([("x", "y", "z")]), _make_prefs(known_parents={})) == []


# ---------------------------------------------------------------------------
# should_skip_ppid
# ---------------------------------------------------------------------------
def test_should_skip_ppid_within_cooldown():
    now = 10000.0
    marker = {"31909": now - 3600}  # 1h ago, default 3h cooldown
    assert zombie_killer.should_skip_ppid("31909", marker, now) is True


def test_should_skip_ppid_outside_cooldown():
    now = 10000.0
    marker = {"31909": now - 4 * 3600}  # 4h ago
    assert zombie_killer.should_skip_ppid("31909", marker, now) is False


def test_should_skip_ppid_unknown_returns_false():
    assert zombie_killer.should_skip_ppid("99999", {}, 10000.0) is False


# ---------------------------------------------------------------------------
# kill_known_zombies: 主函数
# ---------------------------------------------------------------------------
def test_total_switch_false_blocks_kill(tmp_path):
    """总开关 auto_kill_zombies=False → gated=True, 不杀。"""
    marker = tmp_path / "m.json"
    prefs = _make_prefs(auto_kill_zombies=False, known_parents={
        "31909": {"auto_kill": True},
    })
    result = zombie_killer.kill_known_zombies(
        _make_zombies([("31909", "1", "z")]), prefs, marker_path=marker
    )
    assert result["gated"] is True
    assert "auto_kill_zombies=False" in result["reason"]
    assert result["killed"] == []
    assert result["skipped"] == {"cooldown": [], "not_found": [], "permission_denied": [], "error": []}
    assert not marker.exists()


def test_kill_known_zombies_kills_ppid(tmp_path):
    """总开关 True + 候选 PPID + 用 mock kill_fn 验证被调。"""
    marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"31909": {"auto_kill": True}})
    zombies = _make_zombies([("31909", "31991", "<defunct>")])

    killed = []
    def mock_kill(pid, sig):
        killed.append((pid, sig))

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert killed == [(31909, 9)]  # SIGKILL = 9
    assert result["killed"] == ["31909"]
    assert result["gated"] is False
    assert marker.exists()
    assert json.loads(marker.read_text())["31909"] > 0


def test_kill_known_zombies_not_found_subbucket(tmp_path):
    """ProcessLookupError → skipped.not_found + 写 marker (父进程已不在,僵尸会被 init reap)。"""
    marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"99999": {"auto_kill": True}})
    zombies = _make_zombies([("99999", "99998", "<defunct>")])

    def mock_kill(pid, sig):
        raise ProcessLookupError(f"no such pid {pid}")

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert result["killed"] == []
    assert result["skipped"]["not_found"] == ["99999"]
    assert result["skipped"]["permission_denied"] == []
    assert result["skipped"]["cooldown"] == []
    assert marker.exists(), "not_found 写 marker 避免短时间重试"


def test_kill_known_zombies_permission_denied_subbucket(tmp_path):
    """PermissionError → skipped.permission_denied, 不写 marker。"""
    marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"31909": {"auto_kill": True}})
    zombies = _make_zombies([("31909", "31991", "<defunct>")])

    def mock_kill(pid, sig):
        raise PermissionError(f"can't kill {pid}")

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert result["killed"] == []
    assert result["skipped"]["permission_denied"] == ["31909"]
    assert not marker.exists(), "permission_denied 不写 marker, 下次再试"


def test_kill_known_zombies_cooldown_skips(tmp_path):
    """marker 里 1h 前杀过 → 冷却中, 不调 kill_fn。"""
    marker = tmp_path / "m.json"
    marker.write_text(json.dumps({"31909": time.time() - 3600}))
    prefs = _make_prefs(known_parents={"31909": {"auto_kill": True}})
    zombies = _make_zombies([("31909", "31991", "<defunct>")])

    called = []
    def mock_kill(pid, sig):
        called.append(pid)

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert called == []
    assert result["skipped"]["cooldown"] == ["31909"]
    assert result["killed"] == []


def test_kill_known_zombies_value_error_subbucket(tmp_path, capsys):
    """ValueError (ppid 非数字等) → skipped.error。"""
    marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"abc": {"auto_kill": True}})
    zombies = _make_zombies([("abc", "1", "z")])

    def mock_kill(pid, sig):
        raise ValueError(f"invalid pid {pid}")

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert result["skipped"]["error"] == ["abc"]
    assert "kill abc failed" in capsys.readouterr().err


def test_kill_known_zombies_unknown_ppid_never_called(tmp_path):
    """PPID 不在 prefs → 全程不调 kill_fn。"""
    marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"12345": {"auto_kill": True}})
    zombies = _make_zombies([("99999", "99998", "<defunct>")])

    called = []
    def mock_kill(pid, sig):
        called.append(pid)

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert called == []
    assert result["killed"] == []
    assert all(result["skipped"][k] == [] for k in result["skipped"])
    assert not marker.exists()


def test_kill_known_zombies_mixed_outcomes(tmp_path):
    """多个 PPID 混合: kill / not_found / permission_denied / cooldown。

    PPID 用数字字符串,符合 prefs.known_zombie_parents 的实际 schema (key 是 str PID)。
    """
    marker = tmp_path / "m.json"
    marker.write_text(json.dumps({"4004": time.time() - 100}))  # 100s 前, 冷却中
    prefs = _make_prefs(known_parents={
        "1001": {"auto_kill": True},  # → killed
        "1002": {"auto_kill": True},  # → not_found
        "1003": {"auto_kill": True},  # → permission_denied
        "4004": {"auto_kill": True},  # → cooldown
    })
    zombies = _make_zombies([
        ("1001", "1", "z"),
        ("1002", "2", "z"),
        ("1003", "3", "z"),
        ("4004", "4", "z"),
    ])

    def mock_kill(pid, sig):
        if pid == 1001:
            return  # OK
        if pid == 1002:
            raise ProcessLookupError
        if pid == 1003:
            raise PermissionError
        raise AssertionError(f"cooldown 不应被 kill (pid={pid})")

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=marker
    )
    assert result["killed"] == ["1001"]
    assert result["skipped"]["not_found"] == ["1002"]
    assert result["skipped"]["permission_denied"] == ["1003"]
    assert result["skipped"]["cooldown"] == ["4004"]
    saved = json.loads(marker.read_text())
    assert "1001" in saved
    assert "1002" in saved
    assert "1003" not in saved  # perm 不写
    assert "4004" in saved  # cooldown 已有


def test_load_kill_marker_corrupt_json_makes_broken_backup(tmp_path):
    """坏 JSON 时备份成 .broken-{ts} 留取证,避免反复 fail-soft 风暴重杀。"""
    p_marker = tmp_path / "m.json"
    p_marker.write_text("not json at all")
    assert zombie_killer.load_kill_marker(p_marker) == {}
    # 应该有 .broken-{ts} 备份
    backups = list(tmp_path.glob("m.json.broken-*"))
    assert len(backups) == 1, f"应有 1 个 .broken 备份, 实际 {len(backups)}"


def test_load_kill_marker_non_dict_makes_broken_backup(tmp_path):
    """顶层非 dict 时也备份。"""
    p_marker = tmp_path / "m.json"
    p_marker.write_text(json.dumps([1, 2, 3]))
    assert zombie_killer.load_kill_marker(p_marker) == {}
    backups = list(tmp_path.glob("m.json.broken-*"))
    assert len(backups) == 1


def test_kill_known_zombies_permission_denied_warns_stderr(tmp_path, capsys):
    """permission_denied 走 stderr 警告(L3 triage 可观测信号),但不写 marker。"""
    p_marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"31909": {"auto_kill": True}})
    zombies = _make_zombies([("31909", "1", "z")])

    def mock_kill(pid, sig):
        raise PermissionError("nope")

    result = zombie_killer.kill_known_zombies(
        zombies, prefs, kill_fn=mock_kill, marker_path=p_marker
    )
    assert result["skipped"]["permission_denied"] == ["31909"]
    err = capsys.readouterr().err
    assert "31909" in err and "PermissionError" in err
    assert not p_marker.exists(), "permission_denied 不写 marker (避免错过权限修复)"


def test_kill_known_zombies_empty_inputs(tmp_path):
    marker = tmp_path / "m.json"
    prefs = _make_prefs(known_parents={"31909": {"auto_kill": True}})

    # 空 zombies
    r1 = zombie_killer.kill_known_zombies([], prefs, marker_path=marker)
    assert r1["killed"] == []
    assert r1["skipped"] == {"cooldown": [], "not_found": [], "permission_denied": [], "error": []}
    assert not marker.exists()

    # 空 prefs.known_zombie_parents
    r2 = zombie_killer.kill_known_zombies(
        _make_zombies([("31909", "1", "z")]),
        _make_prefs(known_parents={}),
        marker_path=marker,
    )
    assert r2["killed"] == []
