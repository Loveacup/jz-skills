#!/usr/bin/env python3
"""
Extract Codex conversation summaries for auto-diary.
Queries Codex state_5.sqlite → threads table for sessions on a target date.
v1.0: initial Codex session extraction, integrated with diary pipeline.
"""

import os, pwd, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def _real_home() -> Path:
    """Return the real user home directory from passwd DB, bypassing env vars."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def _classify_source(source_str: str) -> dict:
    """Classify a Codex thread source into diary category."""
    source_str = (source_str or "").strip()

    if "subagent" in source_str:
        return {
            "category": "guardian",
            "label": "🤝 Guardian/Subagent",
        }
    elif source_str in ("exec", "cli"):
        return {
            "category": "program_call",
            "label": "🤖 程序/CLI调用",
        }
    else:
        # vscode or any other source → standalone
        return {
            "category": "standalone",
            "label": "💻 独立对话",
        }


def _guess_project(title: str, rollout_path: str) -> str:
    """Guess a project name from session title or path."""
    path_str = (rollout_path or "").lower()
    title_str = (title or "").lower()

    # Path-based clues
    if "hermes" in path_str or "hermes" in title_str:
        return "hermes"
    if "askills" in title_str:
        return "askills"
    if "agent skills" in title_str or "agent-skills" in path_str:
        return "agent-skills"
    if "kanban" in title_str:
        return "kanban"
    if "supermemory" in title_str:
        return "supermemory"
    if "skill" in title_str or "skill" in path_str:
        return "skills"
    if "bookmark" in title_str:
        return "bookmark"
    if "claude" in title_str or "cc" in title_str:
        return "claude-code"
    if "automation" in title_str or "automation" in path_str:
        return "automation"

    return ""


def _clean_title(raw_title: str, max_len: int = 120) -> str:
    """Extract a meaningful short topic from the raw title field.

    The title contains the first user message, often very long with markdown.
    Take the first meaningful line, strip markdown cruft.
    """
    if not raw_title:
        return "(无主题)"

    # Split by lines, take the first non-empty, non-markdown-header line
    lines = raw_title.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip markdown headers and code fences
        if line.startswith("#") or line.startswith("```"):
            continue
        # Skip permission/framework prefixes
        if line.startswith("<") and line.endswith(">"):
            continue
        if line.startswith("The following is the Codex agent"):
            continue
        if line.startswith("Reviewed Codex session"):
            continue
        if len(line) > 5:
            return line[:max_len]

    # Fallback: just truncate the whole thing
    return raw_title[:max_len]


def extract_codex_sessions(date_str: str) -> list[dict]:
    """Extract Codex thread summaries for a given date.

    Args:
        date_str: 'YYYY-MM-DD' in Asia/Shanghai timezone.

    Returns:
        List of thread dicts: {thread_id, time, category, label, title, project}
    """
    state_db = _real_home() / ".codex" / "state_5.sqlite"
    if not state_db.exists():
        return []

    # Convert date string to Unix timestamp range in CST
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_start = int(dt.replace(tzinfo=CST).timestamp())
        day_end = int((dt.replace(tzinfo=CST) + timedelta(days=1) - timedelta(seconds=1)).timestamp())
    except ValueError:
        return []

    sessions = []
    try:
        conn = sqlite3.connect(str(state_db))
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, created_at, source, title, rollout_path "
            "FROM threads "
            "WHERE created_at BETWEEN ? AND ? "
            "ORDER BY created_at",
            (day_start, day_end),
        )
        for row in cur.fetchall():
            ts = row["created_at"]
            time_str = datetime.fromtimestamp(ts, tz=CST).strftime("%H:%M")
            source_str = row["source"] or ""
            classification = _classify_source(source_str)
            title = _clean_title(row["title"] or "")
            project = _guess_project(row["title"] or "", row["rollout_path"] or "")

            sessions.append(
                {
                    "thread_id": row["id"],
                    "time": time_str,
                    "source": source_str,
                    "category": classification["category"],
                    "label": classification["label"],
                    "title": title,
                    "project": project,
                }
            )
        conn.close()
    except Exception as e:
        print(f"[extract_codex] Error: {e}", flush=True)
        return []

    return sessions


def get_codex_overview(date_str: str) -> dict:
    """Return aggregated Codex session overview for diary.

    Returns:
        {
            "total": N,
            "standalone": N,
            "guardian": N,
            "program_call": N,
            "sessions": [...],
        }
    """
    sessions = extract_codex_sessions(date_str)
    return {
        "total": len(sessions),
        "standalone": sum(1 for s in sessions if s["category"] == "standalone"),
        "guardian": sum(1 for s in sessions if s["category"] == "guardian"),
        "program_call": sum(1 for s in sessions if s["category"] == "program_call"),
        "sessions": sessions,
    }


if __name__ == "__main__":
    import json, sys

    if len(sys.argv) < 2:
        date_str = datetime.now(CST).strftime("%Y-%m-%d")
    else:
        date_str = sys.argv[1]

    overview = get_codex_overview(date_str)
    print(json.dumps(overview, ensure_ascii=False, indent=2))
