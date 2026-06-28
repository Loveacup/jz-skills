"""mac-doctor 操作偏好持久层 (P1).

数据文件: ~/.hermes/inspection/preferences.json
- 原子写: tempfile.mkstemp(同目录) + os.replace
- 损坏/非法兜底: 返回 DEFAULT 深拷贝 + stderr 警告 + .broken-{ts} 备份
- schema 以 Spec §2.1 为准: version + facts + interpretations + suppressions(list)

suppressions 采用 list 模型:
    [{signature, first_seen, last_seen, count, ttl_hours}, ...]
活跃判定: last_seen + ttl_hours * 3600 > now。

P1 仅实现 6 个 TDD slice 所需函数;
add_fact / add_suppression / is_signature_suppressed / get_active_suppressions 留到 P2。
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

PREFERENCES_FILE = Path.home() / ".hermes" / "inspection" / "preferences.json"

DEFAULT = {
    "version": 1,
    "facts": {
        "known_short_running_tools": [],
        "known_zombie_parents": {},
        "known_mcp_cleanup_targets": [],
        "user_preferences": {
            "quiet_hours": {"start": 23, "end": 7},
            "auto_kill_zombies": False,
            "auto_kill_mcp_orphans": True,
        },
    },
    "interpretations": [],
    "suppressions": [],
}


def _backup_broken(path, reason):
    """把损坏/非法文件备份到 .broken-{ts} 并写 stderr 警告。"""
    broken = path.with_name(f"{path.name}.broken-{int(time.time())}")
    shutil.copy2(path, broken)
    print(f"{reason}: backed up to {broken}", file=sys.stderr)


def _valid_preferences(prefs):
    """多字段结构校验: interpretations / suppressions 类型与必填项。"""
    if not isinstance(prefs, dict):
        return False
    if not isinstance(prefs.get("interpretations"), list):
        return False
    if not isinstance(prefs.get("suppressions"), list):
        return False
    for item in prefs["interpretations"]:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("id"), str) or not item["id"]:
            return False
        if "text" in item and not isinstance(item["text"], str):
            return False
    for s in prefs["suppressions"]:
        if not isinstance(s, dict):
            return False
        if not isinstance(s.get("signature"), str) or not s["signature"]:
            return False
        if not isinstance(s.get("last_seen"), (int, float)):
            return False
        if not isinstance(s.get("ttl_hours"), (int, float)):
            return False
    return True


def load_preferences(path=PREFERENCES_FILE):
    """加载偏好。

    - 文件不存在 → DEFAULT 深拷贝
    - JSON 解析失败或 schema 非法 → 备份 .broken-{ts} + stderr 警告 + DEFAULT 深拷贝
    """
    path = Path(path)
    if not path.exists():
        return copy.deepcopy(DEFAULT)
    try:
        with path.open("r", encoding="utf-8") as f:
            prefs = json.load(f)
    except json.JSONDecodeError:
        _backup_broken(path, "corrupt preferences")
        return copy.deepcopy(DEFAULT)
    if not _valid_preferences(prefs):
        _backup_broken(path, "invalid preferences")
        return copy.deepcopy(DEFAULT)
    return prefs


def save_preferences(path, prefs):
    """原子写: 同目录 mkstemp 临时文件 → os.replace;父目录不存在时自动创建。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def save_current(prefs):
    """便捷封装：把 prefs 原子写回默认 PREFERENCES_FILE。"""
    save_preferences(PREFERENCES_FILE, prefs)


def add_interpretation(path, item):
    """按 id 去重追加 interpretation。

    新增返回 True;id 已存在则不改文件并返回 False。
    """
    prefs = load_preferences(path)
    existing = {
        entry.get("id")
        for entry in prefs.get("interpretations", [])
        if isinstance(entry, dict)
    }
    if item.get("id") in existing:
        return False
    prefs.setdefault("interpretations", []).append(dict(item))
    save_preferences(path, prefs)
    return True


def is_suppressed(path, signature, now):
    """signature 是否处于活跃抑制中。

    顺带清理过期项(last_seen + ttl_hours * 3600 <= now,或字段缺失/非法);
    若有清理则原子写回。
    """
    prefs = load_preferences(path)
    kept = []
    active = False
    changed = False
    for s in prefs.get("suppressions", []):
        ttl = s.get("ttl_hours")
        last_seen = s.get("last_seen")
        if (not isinstance(ttl, (int, float))
                or not isinstance(last_seen, (int, float))
                or last_seen + ttl * 3600 <= now):
            changed = True
            continue
        kept.append(s)
        if s.get("signature") == signature:
            active = True
    if changed:
        prefs["suppressions"] = kept
        save_preferences(path, prefs)
    return active
