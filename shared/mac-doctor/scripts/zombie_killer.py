"""zombie_killer — L2 watchdog 钩子: 杀 known_zombie_parents 里 auto_kill=true 的父进程。

设计原则 (Codex 评审采纳):
- 纯函数,无模块副作用
- kill_fn / now_fn / marker_path 可注入 → 单元测试不需要真杀进程
- 4 个 skipped 子桶: cooldown / not_found / permission_denied / error
- marker 健壮性: 坏 JSON / 坏 schema / 坏类型 → fail-soft 返回空 dict, stderr 警告

被消费方:
- cron-worker/scripts/mac-doctor-watchdog.py (动态加载)
- 默认 skill 自身的 skill CLI `mac-doctor` (后续可加 subcommand)

版本: v1.0 (2026-07-02)
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from macdoctor.paths import data_dir


DEFAULT_MARKER_PATH = data_dir() / ".known-zombie-killed.json"
DEFAULT_COOLDOWN_HOURS = 3


def _backup_broken_marker(path: Path, reason: str) -> None:
    """把损坏/非法的 marker 备份成 .broken-{ts},避免下次又被反复 fail-soft。

    与 preferences.py 的 _backup_broken 对称;防 marker 损坏后风暴重杀
    (每 30min cron 一轮,坏 marker 永不 reap → 反复触发).
    """
    try:
        broken = path.with_name(f"{path.name}.broken-{int(time.time())}")
        shutil.copy2(path, broken)
        print(f"zombie_killer: marker {reason}, 备份到 {broken}", file=sys.stderr)
    except Exception as e:
        print(f"zombie_killer: marker 备份失败 ({e})", file=sys.stderr)


def load_kill_marker(path: Path = DEFAULT_MARKER_PATH) -> dict:
    """读 kill marker,返回 {ppid_str: last_kill_ts_float}。

    健壮性: 路径不存在 / 坏 JSON / 坏 schema / 坏类型 → 返回空 dict, stderr 警告。
    """
    try:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as e:
        _backup_broken_marker(path, f"损坏/不可读 ({e})")
        return {}

    if not isinstance(data, dict):
        _backup_broken_marker(path, f"顶层非 dict (got {type(data).__name__})")
        return {}

    cleaned = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, (int, float)):
            cleaned[k] = float(v)
    return cleaned


def save_kill_marker(marker: dict, path: Path = DEFAULT_MARKER_PATH) -> bool:
    """原子写 marker (tempfile + replace)。失败返回 False, 不抛异常。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError as e:
        print(f"zombie_killer: 写 marker 失败 ({e})", file=sys.stderr)
        return False


def pick_known_kill_ppids(zombies: list, prefs: dict) -> list:
    """从 zombie 集合里挑出 PPID 在 prefs.known_zombie_parents 且 auto_kill=true 的。

    Args:
        zombies: list of {pid, ppid, cmd}
        prefs: 完整 prefs dict (load_preferences 输出)

    Returns:
        去重后的 PPID list (str)
    """
    known_parents = prefs.get("facts", {}).get("known_zombie_parents", {}) or {}
    if not zombies or not known_parents:
        return []

    picked = set()
    for z in zombies:
        if not isinstance(z, dict):
            continue
        ppid = str(z.get("ppid", "")).strip()
        cfg = known_parents.get(ppid)
        if cfg and cfg.get("auto_kill") is True:
            picked.add(ppid)
    return sorted(picked)


def should_skip_ppid(
    ppid: str, marker: dict, now: float, cooldown_hours: float = DEFAULT_COOLDOWN_HOURS
) -> bool:
    """同 PPID 在 cooldown 窗口内已杀过 → 跳过。"""
    last = marker.get(ppid)
    if not isinstance(last, (int, float)):
        return False
    return (now - last) < cooldown_hours * 3600


def _process_identity(pid: int):
    try:
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "pid=", "-o", "ppid=", "-o", "lstart=", "-o", "command="],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode:
        return None
    parts = proc.stdout.strip().split(None, 7)
    if len(parts) < 8:
        return None
    return tuple(parts[:7]) + (" ".join(parts[7:]),)
def kill_known_zombies(
    zombies: list,
    prefs: dict,
    *,
    kill_fn: Callable = os.kill,
    now_fn: Callable = time.time,
    marker_path: Optional[Path] = None,
    cooldown_hours: float = DEFAULT_COOLDOWN_HOURS,
    identity_fn: Callable = _process_identity,
    sleep_fn: Callable = time.sleep,
    grace_seconds: float = 1.0,
) -> dict:
    """Signal opted-in zombie parents gently, then re-verify identity before SIGKILL."""
    result = {"killed": [], "skipped": {"cooldown": [], "not_found": [], "permission_denied": [],
              "error": [], "identity_changed": []}, "gated": False, "reason": None}
    user_prefs = prefs.get("facts", {}).get("user_preferences", {})
    if not user_prefs.get("auto_kill_zombies", False):
        result["gated"] = True
        result["reason"] = "user_preferences.auto_kill_zombies=False"
        return result
    candidates = pick_known_kill_ppids(zombies, prefs)
    if not candidates:
        return result
    marker_path = marker_path or DEFAULT_MARKER_PATH
    marker = load_kill_marker(marker_path)
    now = now_fn()
    records = {str(item.get("ppid")): item for item in zombies if isinstance(item, dict)}
    for ppid in candidates:
        if should_skip_ppid(ppid, marker, now, cooldown_hours):
            result["skipped"]["cooldown"].append(ppid)
            continue
        try:
            pid = int(ppid)
            before = identity_fn(pid)
            supplied = records.get(ppid, {}).get("parent_identity")
            expected = tuple(supplied) if supplied is not None else before
            if before is None or expected is None or tuple(before) != expected:
                result["skipped"]["identity_changed"].append(ppid)
                continue
            kill_fn(pid, signal.SIGTERM)
            sleep_fn(max(0, grace_seconds))
            after = identity_fn(pid)
            if after is None:
                result["killed"].append(ppid)
                marker[ppid] = now
                continue
            if tuple(after) != expected:
                result["skipped"]["identity_changed"].append(ppid)
                continue
            kill_fn(pid, signal.SIGKILL)
            result["killed"].append(ppid)
            marker[ppid] = now
        except ProcessLookupError:
            result["skipped"]["not_found"].append(ppid)
            marker[ppid] = now
        except PermissionError:
            result["skipped"]["permission_denied"].append(ppid)
            print(f"zombie_killer: signal PPID {ppid} denied; will retry next run", file=sys.stderr)
        except (ValueError, OSError) as exc:
            result["skipped"]["error"].append(ppid)
            print(f"zombie_killer: process {ppid} failed: {exc}", file=sys.stderr)
    if any(marker.get(pid) == now for pid in candidates):
        save_kill_marker(marker, marker_path)
    return result
