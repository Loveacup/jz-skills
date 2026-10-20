#!/usr/bin/env python3
"""Extract privacy-bounded, date-scoped summaries from native OMP sessions."""
from __future__ import annotations

import json
import os
import pwd
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Shanghai")
MAX_USER_TOPICS = 12
MAX_ASSISTANT_SUMMARIES = 8
MAX_USER_CHARS = 500
MAX_ASSISTANT_CHARS = 1200


def _home_dir() -> Path:
    try:
        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, ImportError, OSError):
        return Path.home()


def default_sessions_dir() -> Path:
    explicit = os.environ.get("OMP_SESSIONS_DIR")
    if explicit:
        return Path(explicit).expanduser()
    agent_dir = os.environ.get("PI_CODING_AGENT_DIR")
    if agent_dir:
        root = Path(agent_dir).expanduser()
        if not root.is_absolute():
            root = _home_dir() / root
        return root / "sessions"
    if os.environ.get("OMP_PROFILE"):
        return Path("/__omp_named_profile_requires_explicit_sessions_dir__")
    return _home_dir() / ".omp" / "agent" / "sessions"


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(LOCAL_TZ)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ)
    except (ValueError, OverflowError):
        return None


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return " ".join(content.split())
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return " ".join(" ".join(parts).split())


def _short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _record_excerpt(item: dict[str, Any], field: str, omitted_field: str, text: str, limit: int, max_chars: int, preserve_first: int) -> None:
    excerpts = item[field]
    excerpt = _short(text, max_chars)
    if len(excerpts) < limit:
        excerpts.append(excerpt)
        return
    del excerpts[preserve_first]
    excerpts.append(excerpt)
    item[omitted_field] += 1


def extract_omp_conversations(date_str: str, sessions_dir: str | Path | None = None, full_scan: bool | None = None) -> dict[str, Any]:
    """Read OMP JSONL sessions touched since the target local day and extract visible turns.

    Message timestamps, not file dates, decide which turns belong to the diary day.
    The mtime gate avoids scanning the entire OMP history for normal daily runs.
    """
    target_day = date.fromisoformat(date_str)
    if full_scan is None:
        full_scan = os.environ.get("OMP_FULL_SCAN") == "1"
    root = Path(sessions_dir).expanduser() if sessions_dir is not None else default_sessions_dir()
    result: dict[str, Any] = {
        "date": target_day.isoformat(),
        "source": "omp",
        "status": "unavailable",
        "full_scan": full_scan,
        "session_count": 0,
        "root_session_count": 0,
        "branch_session_count": 0,
        "user_turns": 0,
        "assistant_responses": 0,
        "files_considered": 0,
        "files_scanned": 0,
        "bytes_scanned": 0,
        "malformed_lines": 0,
        "discovery_errors": 0,
        "file_errors": 0,
        "files_changed_during_scan": 0,
        "sessions": [],
    }
    if not root.is_dir():
        result["reason"] = "OMP sessions directory not found or profile path is ambiguous"
        return result

    floor = datetime.combine(target_day, time.min, tzinfo=LOCAL_TZ).timestamp()
    candidates = []
    for path in root.rglob("*.jsonl"):
        try:
            if full_scan or path.stat().st_mtime >= floor:
                candidates.append(path)
        except OSError:
            result["discovery_errors"] += 1
    result["files_considered"] = len(candidates)
    by_id: dict[str, dict[str, Any]] = {}

    for path in candidates:
        try:
            before = path.stat()
            result["files_scanned"] += 1
            result["bytes_scanned"] += before.st_size
            file_session_id = path.stem
            file_title = ""
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        result["malformed_lines"] += 1
                        continue
                    if not isinstance(record, dict):
                        continue
                    kind = record.get("type")
                    if kind in ("title", "title_change"):
                        if isinstance(record.get("title"), str):
                            file_title = _short(record["title"], 160)
                            item = by_id.get(file_session_id)
                            if item is not None:
                                item["title"] = file_title
                        continue
                    if kind == "session":
                        session_id = str(record.get("id") or file_session_id)
                        file_session_id = session_id
                        item = by_id.setdefault(session_id, {
                            "session_id": session_id,
                            "parent_session_id": record.get("parentSession"),
                            "title": _short(str(record.get("title") or file_title), 160),
                            "project": Path(str(record.get("cwd") or "")).name or None,
                            "first_event": None,
                            "last_event": None,
                            "user_topics": [],
                            "user_topics_omitted": 0,
                            "assistant_summaries": [],
                            "assistant_summaries_omitted": 0,
                            "user_turns": 0,
                            "assistant_responses": 0,
                        })
                        if record.get("parentSession"):
                            item["parent_session_id"] = str(record["parentSession"])
                        continue
                    if kind != "message" or not isinstance(record.get("message"), dict):
                        continue
                    message = record["message"]
                    role = message.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    if role == "assistant" and message.get("stopReason") not in (None, "stop"):
                        continue
                    timestamp = _parse_timestamp(record.get("timestamp") or message.get("timestamp"))
                    if timestamp is None or timestamp.date() != target_day:
                        continue
                    text = _message_text(message.get("content"))
                    if not text:
                        continue
                    session_id = str(record.get("sessionId") or file_session_id)
                    item = by_id.setdefault(session_id, {
                        "session_id": session_id,
                        "parent_session_id": None,
                        "title": "",
                        "project": path.parent.name,
                        "first_event": None,
                        "last_event": None,
                        "user_topics": [],
                        "user_topics_omitted": 0,
                        "assistant_summaries": [],
                        "assistant_summaries_omitted": 0,
                        "user_turns": 0,
                        "assistant_responses": 0,
                    })
                    stamp = timestamp.isoformat(timespec="minutes")
                    if item["first_event"] is None or stamp < item["first_event"]:
                        item["first_event"] = stamp
                    if item["last_event"] is None or stamp > item["last_event"]:
                        item["last_event"] = stamp
                    if role == "user":
                        item["user_turns"] += 1
                        _record_excerpt(item, "user_topics", "user_topics_omitted", text, MAX_USER_TOPICS, MAX_USER_CHARS, preserve_first=3)
                    else:
                        item["assistant_responses"] += 1
                        _record_excerpt(item, "assistant_summaries", "assistant_summaries_omitted", text, MAX_ASSISTANT_SUMMARIES, MAX_ASSISTANT_CHARS, preserve_first=2)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                result["files_changed_during_scan"] += 1
        except OSError:
            result["file_errors"] += 1

    sessions = [item for item in by_id.values() if item["user_turns"] or item["assistant_responses"]]
    sessions.sort(key=lambda item: (item["first_event"] or "", item["session_id"]))
    result["sessions"] = sessions
    result["session_count"] = len(sessions)
    result["branch_session_count"] = sum(bool(item.get("parent_session_id")) for item in sessions)
    result["root_session_count"] = result["session_count"] - result["branch_session_count"]
    result["user_turns"] = sum(item["user_turns"] for item in sessions)
    result["assistant_responses"] = sum(item["assistant_responses"] for item in sessions)
    if result["malformed_lines"] or result["discovery_errors"] or result["file_errors"] or result["files_changed_during_scan"]:
        result["status"] = "partial"
    else:
        result["status"] = "ok" if sessions else "empty"
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date", help="Diary date in YYYY-MM-DD")
    parser.add_argument("--sessions-dir", type=Path, default=None)
    parser.add_argument("--full-scan", action="store_true", help="Include files older than the target date; potentially scans the entire OMP history")
    args = parser.parse_args()
    print(json.dumps(extract_omp_conversations(args.date, args.sessions_dir, full_scan=True if args.full_scan else None), ensure_ascii=False, indent=2))
