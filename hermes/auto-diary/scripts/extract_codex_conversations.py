#!/usr/bin/env python3
"""
Extract Codex conversation summaries for auto-diary.
v2.1: rich per-session detail — message counts, user turns, automation IDs,
      full topic extraction, assistant action summaries, guardian outcomes.
v2.0: dual-source — SQLite threads table + JSONL session files.
"""

import os, pwd, sqlite3, json, glob, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def _real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def _parse_source(src_val) -> str:
    if isinstance(src_val, dict):
        return json.dumps(src_val)
    return str(src_val or "")


def _classify_source(source_str: str) -> dict:
    source_str = (source_str or "").strip()
    if "subagent" in source_str or "guardian" in source_str:
        return {"category": "guardian", "label": "🤝 Guardian/Subagent"}
    elif source_str in ("exec", "cli"):
        return {"category": "program_call", "label": "🤖 程序/CLI调用"}
    else:
        return {"category": "standalone", "label": "💻 独立对话"}


def _guess_project(title: str, cwd: str = "") -> str:
    t = (title or "").lower()
    c = (cwd or "").lower()
    if "surge" in c or "surge" in t:           return "surge"
    if "askills" in t or "askills" in c:       return "askills"
    if "agent-skills" in c or "agent skills" in t: return "agent-skills"
    if ".agents" in c:                         return "agent-skills"
    if "hermes" in t or "hermes" in c:         return "hermes"
    if "obsidian" in c or "obsidian" in t:     return "obsidian"
    if "kanban" in t:                          return "kanban"
    if "bookmark" in t:                        return "bookmark"
    if "codex" in c:                           return "codex"
    if "claude" in t or "cc" in t:             return "claude-code"
    return ""


def _clean_title(raw_title: str, max_len: int = 120) -> str:
    if not raw_title:
        return "(无主题)"
    lines = raw_title.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#") or line.startswith("```"): continue
        if line.startswith("<") and line.endswith(">"): continue
        if line.startswith("The following is the Codex agent"): continue
        if line.startswith("Reviewed Codex session"): continue
        if line.startswith("<environment_context>"): continue
        if line.startswith("<cwd>"): continue
        if line.startswith("<shell>"): continue
        if line.startswith(">>> TRANSCRIPT"): continue
        if len(line) > 5:
            return line[:max_len]
    return raw_title[:max_len]


def _is_skippable_user_msg(text: str) -> bool:
    """Check if a user message should be skipped (AGENTS.md injection, etc)."""
    if not text or not text.strip():
        return True
    if text.startswith("# AGENTS.md instructions"):
        return True
    if "AGENTS.md" in text[:200] and "<INSTRUCTIONS>" in text[:200]:
        return True
    if text.startswith("<environment_context>"):
        return True
    if text.startswith("The following is the Codex agent history"):
        return True
    return False


def _extract_rich_session_data(filepath: str, meta: dict) -> dict:
    """Extract rich per-session data from a JSONL file.

    Returns: {
        message_count, user_turns, user_topics, assistant_summary,
        automation_id, model
    }
    For guardian: also guardian_outcomes
    """
    result = {
        "message_count": 0,
        "user_turns": 0,
        "user_topics": [],
        "assistant_summary": "",
        "automation_id": "",
        "model": meta.get("model_provider", ""),
    }

    source_str = _parse_source(meta.get("source", ""))
    is_guardian = "subagent" in source_str or "guardian" in source_str
    if is_guardian:
        result["guardian_outcomes"] = []

    try:
        with open(filepath, "r") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                if d.get("type") == "response_item":
                    result["message_count"] += 1
                    payload = d.get("payload", {})
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload.replace("'", '"'))
                        except (json.JSONDecodeError, AttributeError):
                            continue

                    role = payload.get("role", "")
                    content = payload.get("content", "")
                    if isinstance(content, list):
                        text = "".join(
                            item.get("text", "")
                            for item in content
                            if isinstance(item, dict) and item.get("type") == "input_text"
                        )
                    elif isinstance(content, str):
                        text = content
                    else:
                        text = ""

                    if role == "user" and not _is_skippable_user_msg(text):
                        result["user_turns"] += 1
                        topic = _extract_topic_line(text)
                        if topic and topic not in result["user_topics"]:
                            result["user_topics"].append(topic)
                        # Detect automation ID
                        if "Automation:" in text:
                            for tline in text.split("\n"):
                                if "Automation ID:" in tline:
                                    aid = tline.split("Automation ID:")[-1].strip()
                                    result["automation_id"] = aid
                                    break

                    elif role == "assistant" and text:
                        # First assistant message as action summary (don't overwrite once set)
                        if not result["assistant_summary"]:
                            first_line = text.strip().split("\n")[0].strip()
                            if len(first_line) > 10:
                                result["assistant_summary"] = first_line[:200]

                        # Guardian approval decisions — independent of summary extraction.
                        # 🔴 B1 fix: previously this was an `elif`, so the FIRST assistant message
                        # (usually the verdict JSON itself) got consumed by assistant_summary above
                        # and execution never fell through to here — leaving guardian_outcomes
                        # permanently empty for the common single-verdict guardian session. Now an
                        # independent `if`: the same message can both seed the summary AND be parsed
                        # as a guardian outcome.
                        if is_guardian:
                            try:
                                gd = json.loads(text) if text.strip().startswith("{") else None
                                if gd:
                                    outcome = {
                                        "action": gd.get("outcome", "?"),
                                        "risk": gd.get("risk_level", "?"),
                                        "rationale": (gd.get("rationale", "") or "")[:150],
                                    }
                                    if outcome["action"] not in [o.get("action") for o in result.get("guardian_outcomes", [])]:
                                        result.setdefault("guardian_outcomes", []).append(outcome)
                            except (json.JSONDecodeError, AttributeError):
                                pass

    except Exception:
        pass

    return result


def _extract_topic_line(text: str) -> str:
    """Extract a short topic from a user message."""
    text = text.strip()
    if not text:
        return ""
    # Skip automation boilerplate
    if text.startswith("Automation:"):
        for line in text.split("\n"):
            if line.startswith("Automation:") and "Automation ID:" not in line:
                return line.strip()[:120]
        return ""
    # Take first non-empty line
    first = text.split("\n")[0].strip()
    if len(first) > 150:
        first = first[:147] + "..."
    return first


def _read_jsonl_session_meta(filepath: str) -> Optional[dict]:
    try:
        with open(filepath, "r") as f:
            first_line = f.readline().strip()
            if not first_line: return None
            d = json.loads(first_line)
            if d.get("type") != "session_meta": return None
            payload = d.get("payload", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload.replace("'", '"'))
                except (json.JSONDecodeError, AttributeError):
                    return None
            return payload
    except Exception:
        return None


def _scan_jsonl_sessions(date_str: str) -> list[dict]:
    home = _real_home()
    sessions = []
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []

    year, month, day = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")

    for source_label, source_dir in [
        ("jsonl", home / ".codex" / "sessions" / year / month / day),
        ("jsonl_archived", home / ".codex" / "archived_sessions"),
    ]:
        if not source_dir.exists():
            continue

        if source_label == "jsonl_archived":
            date_prefix = f"rollout-{date_str}"
            files = sorted(source_dir.glob(f"{date_prefix}*.jsonl"))
        else:
            files = sorted(source_dir.glob("*.jsonl"))

        for jsonl_path in files:
            meta = _read_jsonl_session_meta(str(jsonl_path))
            if not meta:
                continue

            thread_id = meta.get("id", "")
            ts_iso = meta.get("timestamp", "")
            source_raw = meta.get("source", "")
            source_str = _parse_source(source_raw)
            classification = _classify_source(source_str)
            cwd = meta.get("cwd", "")

            # Rich extraction
            rich = _extract_rich_session_data(str(jsonl_path), meta)
            if rich.get("automation_id"):
                classification = {  # Override: automations are standalone
                    "category": "standalone",
                    "label": "💻 独立对话",
                }

            # Parse time
            try:
                ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
                time_str = ts.astimezone(CST).strftime("%H:%M")
            except (ValueError, AttributeError):
                fname = jsonl_path.name
                time_match = re.search(r"T(\d{2})-(\d{2})-(\d{2})", fname)
                time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else "??:??"

            # Title from first real user message or automation ID
            if rich.get("automation_id"):
                title = rich["automation_id"]
            elif rich.get("user_topics"):
                title = rich["user_topics"][0][:120]
            else:
                bi = meta.get("base_instructions", "")
                if isinstance(bi, dict):
                    bi = bi.get("text", "")
                title = _clean_title(bi) if bi else "(无主题)"

            project = _guess_project(" ".join(rich.get("user_topics", [])), cwd)

            session = {
                "thread_id": thread_id,
                "time": time_str,
                "source": source_str,
                "category": classification["category"],
                "label": classification["label"],
                "title": title,
                "project": project,
                "cwd": cwd,
                "_origin": source_label,
                # Rich fields
                "message_count": rich["message_count"],
                "user_turns": rich["user_turns"],
                "user_topics": rich["user_topics"],
                "assistant_summary": rich["assistant_summary"],
                "automation_id": rich.get("automation_id", ""),
                "model": rich.get("model", ""),
            }
            if "guardian_outcomes" in rich:
                session["guardian_outcomes"] = rich["guardian_outcomes"]

            sessions.append(session)

    return sessions


def _scan_sqlite_sessions(date_str: str) -> list[dict]:
    home = _real_home()
    state_db = home / ".codex" / "state_5.sqlite"
    if not state_db.exists():
        return []

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_start = int(dt.replace(tzinfo=CST).timestamp())
        day_end = int((dt.replace(tzinfo=CST) + timedelta(days=1)).timestamp())
    except ValueError:
        return []

    sessions = []
    try:
        conn = sqlite3.connect(str(state_db))
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, created_at, source, title, model FROM threads "
            "WHERE created_at >= ? AND created_at < ? ORDER BY created_at",
            (day_start, day_end),
        )
        for row in cur.fetchall():
            ts = row["created_at"]
            time_str = datetime.fromtimestamp(ts, tz=CST).strftime("%H:%M")
            source_str = row["source"] or ""
            classification = _classify_source(source_str)
            title = _clean_title(row["title"] or "")
            project = _guess_project(row["title"] or "")
            sessions.append({
                "thread_id": row["id"],
                "time": time_str,
                "source": source_str,
                "category": classification["category"],
                "label": classification["label"],
                "title": title,
                "project": project,
                "cwd": "",
                "_origin": "sqlite",
                "message_count": 0,
                "user_turns": 0,
                "user_topics": [],
                "assistant_summary": "",
                "automation_id": "",
                "model": row["model"] or "",
            })
        conn.close()
    except Exception as e:
        print(f"[extract_codex] SQLite error: {e}", flush=True)
    return sessions


def extract_codex_sessions(date_str: str) -> list[dict]:
    sqlite_sessions = _scan_sqlite_sessions(date_str)
    jsonl_sessions = _scan_jsonl_sessions(date_str)

    seen_ids = set()
    merged = []
    # JSONL first (richer data: message counts, topics, actions)
    for s in jsonl_sessions:
        tid = s["thread_id"]
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            merged.append(s)
    # SQLite fallback for sessions not in JSONL
    for s in sqlite_sessions:
        tid = s["thread_id"]
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            merged.append(s)
    merged.sort(key=lambda s: s["time"])
    return merged


def get_codex_overview(date_str: str) -> dict:
    sessions = extract_codex_sessions(date_str)

    # Aggregate by project for richer grouping
    projects = {}
    for s in sessions:
        p = s.get("project", "") or "other"
        if p not in projects:
            projects[p] = {"count": 0, "standalone": 0, "guardian": 0, "program_call": 0, "sessions": []}
        projects[p]["count"] += 1
        projects[p][s["category"]] += 1
        projects[p]["sessions"].append(s)

    return {
        "total": len(sessions),
        "standalone": sum(1 for s in sessions if s["category"] == "standalone"),
        "guardian": sum(1 for s in sessions if s["category"] == "guardian"),
        "program_call": sum(1 for s in sessions if s["category"] == "program_call"),
        "sessions": sessions,
        "by_project": projects,
        # Cross-runtime hints (cwd analysis)
        "cross_runtime_hints": _detect_cross_runtime(sessions),
    }


def _detect_cross_runtime(sessions: list[dict]) -> list[str]:
    """Detect cross-runtime collaboration hints from cwd analysis."""
    hints = []
    for s in sessions:
        cwd = s.get("cwd", "")
        if "hermes" in cwd.lower():
            hints.append(f"Codex 操作了 Hermes 目录: {cwd}")
        if "obsidian" in cwd.lower():
            hints.append(f"Codex 访问了 Obsidian vault: {cwd}")
        if ".agents" in cwd.lower():
            hints.append("Codex 参与了 Agent Skills 中心化治理")
        if "surge" in cwd.lower():
            hints.append("Codex 参与了 Surge 网关配置")
    return list(set(hints))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        date_str = datetime.now(CST).strftime("%Y-%m-%d")
    else:
        date_str = sys.argv[1]
    overview = get_codex_overview(date_str)
    print(json.dumps(overview, ensure_ascii=False, indent=2))
