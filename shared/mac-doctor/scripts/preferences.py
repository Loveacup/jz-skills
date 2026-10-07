"""mac-doctor 操作偏好持久层 (P1).

数据文件: `inspection_dir() / "preferences.json"`（默认真实账户 home 下的 `.hermes/inspection`）
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
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from macdoctor.paths import account_home, data_dir, preferences_file


def real_home():
    return str(account_home())


def inspection_dir():
    return data_dir()


PREFERENCES_FILE = preferences_file()

DEFAULT = {
    "version": 1,
    "facts": {
        "known_short_running_tools": [],
        "known_zombie_parents": {},
        "known_mcp_cleanup_targets": [],
        "user_preferences": {
            "quiet_hours": {"start": 23, "end": 7},
            "auto_kill_zombies": False,
            "auto_kill_mcp_orphans": False,
        },
    },
    "interpretations": [],
    "suppressions": [],
}


def list_broken_backups(path=PREFERENCES_FILE):
    path = Path(path)
    return sorted(path.parent.glob(f"{path.name}.broken-*"))


def prune_broken_backups(path=PREFERENCES_FILE, keep=0):
    """Explicitly prune broken backups; never invoked by normal loads."""
    backups = list_broken_backups(path)
    keep = max(0, int(keep))
    removed = []
    for backup in backups[:-keep] if keep else backups:
        backup.unlink()
        removed.append(backup)
    return removed


def _backup_broken(path, reason):
    try:
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        broken = path.with_name(f"{path.name}.broken-{digest}")
        try:
            with broken.open("xb") as backup:
                backup.write(content)
        except FileExistsError:
            pass
        print(f"{reason}: backed up to {broken}", file=sys.stderr)
    except OSError as exc:
        print(f"{reason}: could not back up preferences: {exc}", file=sys.stderr)
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
        current_format = (
            isinstance(s.get("signature"), str) and bool(s["signature"])
            and isinstance(s.get("last_seen"), (int, float))
            and isinstance(s.get("ttl_hours"), (int, float))
        )
        legacy_format = (
            all(isinstance(s.get(key), str) and bool(s[key])
                for key in ("key", "rule", "based_on", "created_at"))
            and isinstance(s.get("trigger_count_at_creation"), int)
            and not isinstance(s.get("trigger_count_at_creation"), bool)
        )
        if not (current_format or legacy_format):
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
        # Preserve old key/rule-based entries; the current signature/TTL model
        # cannot safely interpret them, so they are never applied or expired.
        if "signature" not in s:
            kept.append(s)
            continue
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
