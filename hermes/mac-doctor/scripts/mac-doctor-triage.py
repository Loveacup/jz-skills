#!/usr/bin/env python3
"""mac-doctor triage — L3 诊断 LLM agent 入口（被 cron 调用，不直接调 LLM API）。

职责（Spec §2.3）：
- 读 .triage-trigger（watchdog 落的触发文件）
- 读 history.db 近 24h 趋势（snapshots 表）
- 读 preferences.json + 组装结构化 JSON prompt 交给 Hermes agent loop
- 消费 agent loop 回填的 LLM 结果：should_push=true 才输出严格 §2.3 JSON，否则静默
- 失败兜底：stdin 缺 / JSON 错 / IO 错 → stderr warn + stdout 空 + rc 0（不阻塞其他 cron）
"""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

PREFERENCES_MODULE = Path(
    "/Users/alexcai/.hermes/skills/apple/mac-doctor/scripts/preferences.py")
HISTORY_DB = Path.home() / ".hermes" / "inspection" / "history.db"

# Spec §2.3 输出契约：交给 LLM 的 output_schema 与最终 stdout 严格键集
OUTPUT_SCHEMA = {
    "verdict": "string (transient|persistent|critical)",
    "diagnosis": "string (单行根因)",
    "recommendation": "string (建议行动 1-3 条)",
    "memory_write": {
        "type": "object",
        "description": "{key: 'facts.add|interpretations.add', value: ...}",
    },
    "should_push": "boolean",
    "push_message": "string (若 should_push=true 的推送内容)",
}
RESULT_KEYS = (
    "verdict", "diagnosis", "recommendation",
    "memory_write", "should_push", "push_message",
)


def _trigger_path():
    """惰性解析触发文件路径（在调用时读 HOME，便于测试 monkeypatch）。"""
    return Path.home() / ".hermes" / "inspection" / ".triage-trigger"


def read_trigger(path=None):
    """读 watchdog 落的 .triage-trigger。

    - 文件不存在 → None（静默，无 stdout/stderr）
    - 合法 JSON object → dict
    - JSON 损坏或非 object（list/标量）→ ValueError（留给 main 边界兜底）
    """
    path = _trigger_path() if path is None else Path(path)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)  # JSONDecodeError 是 ValueError 子类
    if not isinstance(data, dict):
        raise ValueError(f"trigger 必须是 JSON object，实得 {type(data).__name__}")
    return data


def _classify(row):
    """单行快照 → status 集合（cpu>70 abnormal / mem critical / disk<15 low_disk）。"""
    tags = []
    cpu = row.get("cpu_percent")
    if cpu is not None and cpu > 70:
        tags.append("abnormal")
    if row.get("memory_pressure") == "critical":
        tags.append("critical")
    disk = row.get("disk_free_gb")
    if disk is not None and disk < 15:
        tags.append("low_disk")
    return tags or ["normal"]


def read_trend(db_path, now=None):
    """读 history.db snapshots 表近 24h 趋势，返回结构化 dict。

    now=None → 用 SQLite datetime('now')；否则以 now 为参考点算 -24h 窗口（便于测试）。
    db 不存在/表为空时返回零值骨架（defensive，不抛）。
    """
    db_path = Path(db_path)
    trend = {"window_hours": 24, "columns": [], "total": 0,
             "by_status": {}, "top_cpu_processes": [], "latest_snapshot": {}}
    if not db_path.exists():
        return trend
    con = sqlite3.connect(str(db_path))
    try:
        con.row_factory = sqlite3.Row
        cols = [r[1] for r in con.execute("PRAGMA table_info(snapshots)")]
        trend["columns"] = cols
        if not cols:
            return trend
        if now is None:
            sql = ("SELECT * FROM snapshots WHERE timestamp >= "
                   "datetime('now','-24 hours') ORDER BY timestamp ASC")
            rows = [dict(r) for r in con.execute(sql)]
        else:
            sql = ("SELECT * FROM snapshots WHERE timestamp >= "
                   "datetime(?, '-24 hours') ORDER BY timestamp ASC")
            rows = [dict(r) for r in con.execute(sql, (now,))]
    finally:
        con.close()
    trend["total"] = len(rows)
    by_status, cpu_counter = {}, {}
    for row in rows:
        for tag in _classify(row):
            by_status[tag] = by_status.get(tag, 0) + 1
        proc = row.get("top_cpu_process")
        if proc:
            cpu_counter[proc] = cpu_counter.get(proc, 0) + 1
    trend["by_status"] = by_status
    top = sorted(cpu_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    trend["top_cpu_processes"] = [{"process": p, "count": c} for p, c in top]
    if rows:
        trend["latest_snapshot"] = rows[-1]  # ASC 排序，末行为最新
    return trend


def _load_preferences(path):
    """复用 P1 preferences.load_preferences（cron-worker profile 下用 importlib 加载）。"""
    spec = importlib.util.spec_from_file_location(
        "mac_doctor_preferences", PREFERENCES_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_preferences(path)


def build_prompt(snapshot, facts, trend, preferences_path):
    """组装交给 Hermes agent loop 的结构化 JSON prompt（不调 LLM API）。

    interpretations / suppressions 由 P1 load_preferences 提供（list；缺失兜底空 list）。
    """
    prefs = _load_preferences(preferences_path)
    payload = {
        "snapshot": snapshot,
        "facts": facts,
        "interpretations": prefs.get("interpretations", []),
        "suppressions": prefs.get("suppressions", []),
        "trend": trend,
        "output_schema": OUTPUT_SCHEMA,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def emit_result(stdin_text):
    """消费 Hermes agent loop 回填的 LLM 结果 JSON，决定是否推送。

    - JSON 解析失败 / 非 object → stderr warn + stdout 空 + rc 0
    - should_push=false → stdout 空（静默），rc 0
    - should_push=true → 仅输出严格 §2.3 六键 JSON（剔除多余字段），rc 0
    """
    try:
        result = json.loads(stdin_text)
        if not isinstance(result, dict):
            raise ValueError("triage 结果须为 JSON object")
    except (ValueError, TypeError) as e:
        print(f"warn: bad triage result json: {e}", file=sys.stderr)
        return 0
    if not result.get("should_push"):
        return 0  # 静默
    strict = {k: result.get(k) for k in RESULT_KEYS}
    print(json.dumps(strict, ensure_ascii=False, separators=(",", ":")))
    return 0


def main(argv=None, stdin_text=None):
    """cron 入口边界：兜住一切异常，绝不阻塞其他 cron（rc 恒 0）。"""
    try:
        if not stdin_text or not stdin_text.strip():
            print("warn: missing triage stdin", file=sys.stderr)
            return 0
        return emit_result(stdin_text)
    except Exception as e:  # 文件 IO / sqlite / preference 等边界异常
        print(f"warn: triage failed: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main(argv=sys.argv[1:], stdin_text=sys.stdin.read()))
