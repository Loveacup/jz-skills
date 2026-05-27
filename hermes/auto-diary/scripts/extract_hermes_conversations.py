#!/usr/bin/env python3
"""
Extract Hermes conversation summaries for auto-diary.
Queries Hermes state.db SQLite databases (main + profiles) for sessions.
v2.0: migrated from JSON file reading to SQLite (JSON files deprecated May 2026).
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo


def _get_state_dbs() -> list[tuple[str, Path]]:
    """Return (profile_label, state_db_path) tuples for all Hermes state DBs.

    Main DB = "default". Profile DBs are named after the profile directory.
    """
    hermes_home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    hermes_home = Path(hermes_home)
    dbs: list[tuple[str, Path]] = []

    # Main state.db
    main_db = hermes_home / "state.db"
    if main_db.exists():
        dbs.append(("default", main_db))

    # Profile state.dbs — profiles live under hermes_home/profiles/ (flat),
    # not under hermes_home/profiles/<name>/.
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.exists():
        for profile_dir in sorted(profiles_dir.iterdir()):
            if not profile_dir.is_dir():
                continue
            profile_db = profile_dir / "state.db"
            if profile_db.exists():
                dbs.append((profile_dir.name, profile_db))

    return dbs


def extract_hermes_summary(date_str: str) -> list:
    """
    Extract conversation summaries from Hermes sessions for a given date.

    Args:
        date_str: Date in format 'YYYY-MM-DD'

    Returns:
        List of conversation summaries, each containing:
        - platform: source (telegram/cron/api_server) + profile label when not default
        - profile: "default" or profile name
        - session_start: HH:MM in Asia/Shanghai
        - message_count: number of messages
        - user_turns: number of user messages
        - topics: list of topic hints from first 5 user messages (raw hints)
        - summary: brief description
    """
    shanghai = ZoneInfo("Asia/Shanghai")
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    summaries = []

    skip_prefixes = (
        "[System note:",
        "[Replying to:",
        "[IMPORTANT:",
        "[CONTEXT COMPACTION",
    )

    for profile_label, db_path in _get_state_dbs():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except Exception:
            continue

        try:
            # Find sessions for the target date
            cur = conn.execute("""
                SELECT id, source, model, started_at, message_count, title
                FROM sessions
                WHERE date(started_at, 'unixepoch', 'localtime') = ?
                ORDER BY started_at ASC
            """, (date_str,))

            for row in cur:
                session_id = row["id"]
                source = row["source"] or "unknown"

                # Skip sessions with no messages
                if not row["message_count"] or row["message_count"] == 0:
                    continue

                # Extract user messages for topic hints
                msg_cur = conn.execute("""
                    SELECT role, content
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """, (session_id,))

                user_messages = []
                for msg in msg_cur:
                    role = msg["role"]
                    content = msg["content"] or ""
                    if role == "user" and isinstance(content, str):
                        skip = any(content.startswith(p) for p in skip_prefixes)
                        if not skip:
                            user_messages.append(content)

                if not user_messages:
                    continue

                # Build platform label
                platform = source
                if profile_label != "default":
                    platform = f"{source}/{profile_label}"

                # Collect topic hints (raw — agent generalizes during diary writing)
                topics = []
                for msg in user_messages[:5]:
                    topic = msg.strip().split("\n")[0][:80]
                    if topic and topic not in topics:
                        topics.append(topic)

                # Session start time in Shanghai
                start_ts = row["started_at"]
                start_dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
                start_local = start_dt.astimezone(shanghai)

                summary = {
                    "platform": platform,
                    "profile": profile_label,
                    "session_start": start_local.strftime("%H:%M"),
                    "message_count": row["message_count"],
                    "user_turns": len(user_messages),
                    "topics": topics[:3],
                    "summary": (
                        f"{len(user_messages)} 轮对话，涉及: {', '.join(topics[:2])}"
                        if topics else "日常对话"
                    ),
                }
                summaries.append(summary)

        except Exception:
            pass
        finally:
            conn.close()

    summaries.sort(key=lambda x: (x["session_start"], x.get("profile", "")))
    return summaries


def _clean_topic(topic: str) -> str:
    return " ".join((topic or "").strip().split())[:100]


def _interesting_topics(summaries: list, limit: int = 8) -> list[str]:
    skip_prefixes = (
        "[Note:",
        "[CONTEXT COMPACTION",
        "Review the conversation above",
        "work kanban task ",
        "你是 regent profile 的 Kanban 值房协调 run",
        "[Your active task list",
        "You've reached the maximum number of tool-calling",
        "slash_command:",
        "[IMPORTANT:",
    )
    topics: list[str] = []
    for summary in summaries:
        for raw_topic in summary.get("topics", []) or []:
            topic = _clean_topic(raw_topic)
            if not topic or any(topic.startswith(prefix) for prefix in skip_prefixes):
                continue
            if topic not in topics:
                topics.append(topic)
            if len(topics) >= limit:
                return topics
    return topics


def build_profile_overview(summaries: list) -> dict:
    """Aggregate raw session summaries into a compact diary overview."""
    if not summaries:
        return {
            "total_sessions": 0,
            "total_messages": 0,
            "total_user_turns": 0,
            "default": None,
            "governance": None,
        }

    default_sessions = [s for s in summaries if s.get("profile") == "default"]
    profile_sessions = [s for s in summaries if s.get("profile") != "default"]

    def pack(items: list, label: str) -> Optional[dict]:
        if not items:
            return None
        profiles = sorted({s.get("profile", "default") for s in items})
        return {
            "label": label,
            "profiles": profiles,
            "session_count": len(items),
            "message_count": sum(s.get("message_count", 0) for s in items),
            "user_turns": sum(s.get("user_turns", 0) for s in items),
            "topics": _interesting_topics(items, limit=8),
        }

    return {
        "total_sessions": len(summaries),
        "total_messages": sum(s.get("message_count", 0) for s in summaries),
        "total_user_turns": sum(s.get("user_turns", 0) for s in summaries),
        "default": pack(default_sessions, "Hermes / default"),
        "governance": pack(profile_sessions, "太子 / 三省六部工作概览"),
    }


def format_for_diary(summaries: list) -> str:
    """Format Hermes conversation summaries as a compact diary section."""
    overview = build_profile_overview(summaries)
    if overview["total_sessions"] == 0:
        return ""

    lines = ["### 🤖 AI 助手工作概览"]
    lines.append(f"- 总会话数: {overview['total_sessions']}")
    lines.append(f"- 总消息数: {overview['total_messages']}")
    lines.append(f"- 用户轮次: {overview['total_user_turns']}")

    default = overview.get("default")
    if default:
        lines.append("\n#### Hermes / default")
        lines.append(f"- 会话数: {default['session_count']}")
        if default["topics"]:
            lines.append("- 主题: " + "；".join(default["topics"][:5]))

    governance = overview.get("governance")
    if governance:
        lines.append("\n#### 太子 / 三省六部工作概览")
        lines.append(f"- 覆盖 profiles: {', '.join(governance['profiles'])}")
        lines.append(f"- 会话数: {governance['session_count']}")
        lines.append(f"- 消息数: {governance['message_count']}")
        lines.append(f"- 用户轮次: {governance['user_turns']}")
        if governance["topics"]:
            lines.append("- 重点: " + "；".join(governance["topics"][:8]))
        else:
            lines.append("- 重点: 太子治理、派工、审校、归档与三省六部 kanban 子任务执行。")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: extract_hermes_conversations.py YYYY-MM-DD")
        sys.exit(1)

    date_str = sys.argv[1]
    summaries = extract_hermes_summary(date_str)

    if summaries:
        print(format_for_diary(summaries))
    else:
        print("当日无 Hermes 对话记录")
