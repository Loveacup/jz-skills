#!/usr/bin/env python3
"""
Auto-Diary Data Collector - 修复版
关键修复：使用超时机制避免文件系统调用卡住
"""

import ast
import json
import os
import sys
import subprocess
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Weekday mapping in Chinese
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


def get_weekday(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return WEEKDAY_CN[dt.weekday()]
    except ValueError:
        return "未知"


def get_weather(date_str: str = None) -> str:
    """Get weather using Open-Meteo API (free, no API key needed).
    
    Args:
        date_str: Date in format 'YYYY-MM-DD'. If None, gets current weather.
    """
    # Weather code mapping (WMO Weather interpretation codes)
    weather_codes = {
        0: "☀️ 晴",
        1: "🌤 多云", 2: "🌤 多云", 3: "☁️ 阴",
        45: "🌫 雾", 48: "🌫 雾凇",
        51: "🌦 毛毛雨", 53: "🌦 小雨", 55: "🌧 中雨",
        61: "🌧 小雨", 63: "🌧 中雨", 65: "🌧 大雨",
        71: "🌨 小雪", 73: "🌨 中雪", 75: "🌨 大雪",
        80: "🌦 阵雨", 81: "🌦 阵雨", 82: "🌧 暴雨",
        95: "⛈ 雷雨", 96: "⛈ 雷暴伴冰雹", 99: "⛈ 雷暴伴冰雹",
    }
    
    try:
        if date_str:
            # Historical weather query
            url = f"https://archive-api.open-meteo.com/v1/archive?latitude=30.27&longitude=120.16&start_date={date_str}&end_date={date_str}&daily=temperature_2m_mean,weathercode&timezone=Asia/Shanghai"
            result = subprocess.run(
                ["curl", "-s", "-m", "10", url],
                capture_output=True,
                text=True,
                timeout=15,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                daily = data.get("daily", {})
                temps = daily.get("temperature_2m_mean", [])
                codes = daily.get("weathercode", [])
                
                if temps and codes:
                    temp = temps[0]
                    code = codes[0]
                    weather_desc = weather_codes.get(code, "🌡")
                    return f"杭州: {weather_desc} {temp}°C"
        else:
            # Current weather query
            result = subprocess.run(
                ["curl", "-s", "-m", "10", 
                 "https://api.open-meteo.com/v1/forecast?latitude=30.27&longitude=120.16&current_weather=true"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                temp = data.get("current_weather", {}).get("temperature", "?")
                code = data.get("current_weather", {}).get("weathercode", -1)
                weather_desc = weather_codes.get(code, "🌡")
                return f"杭州: {weather_desc} {temp}°C"
    except Exception:
        pass
    
    # Fallback: try wttr.in
    for attempt in range(2):
        try:
            result = subprocess.run(
                ["curl", "-s", "-m", "8", "wttr.in/Hangzhou?format=杭州:+%c+%t+%h"],
                capture_output=True,
                text=True,
                timeout=12,
            )
            if result.returncode == 0 and result.stdout.strip() and "Unknown" not in result.stdout:
                return result.stdout.strip()
        except Exception:
            pass
    
    return "天气获取失败"


def get_calendar_events(date_str: str) -> list:
    """Get calendar events with full details using icalBuddy."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Use icalBuddy with specific date range for the exact day only
        # Use ISO format with time to ensure we only get events for that specific day
        # Calendars: 个人1/工作1/Naomi1/Zelda1 (迁移自 iCloud <email redacted>，
        # 旧的无 "1" 后缀日历已停用，不要再查)
        cmd = [
            "icalBuddy",
            "-ic", "个人1,工作1,Naomi1,Zelda1",
            "-li",  # Include location
            "-ea",  # Exclude all-day events (they don't have times)
            "-nrd",  # No relative dates - show absolute dates
            f"eventsFrom:{dt.strftime('%Y-%m-%d')}T00:00:00",
            f"to:{dt.strftime('%Y-%m-%d')}T23:59:59"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,  # Reduced timeout to fail faster
        )
        
        if result.returncode != 0:
            return []
        
        # Parse icalBuddy multi-line output
        events = []
        lines = result.stdout.strip().split('\n')
        current_event = None
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # Event line starts with "• "
            if line.startswith('• '):
                # Save previous event if exists
                if current_event:
                    events.append(current_event)
                
                # Parse event line: "• Event Name (Calendar)"
                content = line[2:]
                if '(' in content and content.endswith(')'):
                    last_paren = content.rfind('(')
                    summary = content[:last_paren].strip()
                    calendar = content[last_paren+1:-1].strip()
                else:
                    summary = content
                    calendar = "未知"
                
                current_event = {
                    "calendar": calendar,
                    "summary": summary,
                    "time": "",
                    "location": "",
                    "notes": "",
                }
            
            # Time line: "    2026年2月12日 at 14:00 - 15:30" or "    at 14:00 - 15:30"
            elif line.startswith('    ') and ('at' in line):
                if current_event:
                    time_str = line.strip()
                    # Clean up absolute dates (Chinese format)
                    if 'at' in time_str:
                        # Extract just the time part: "14:00 - 15:30"
                        if ' at ' in time_str:
                            time_str = time_str.split(' at ')[-1]
                        # Remove any year/month/day prefixes
                        time_str = time_str.replace('today at ', '').replace('tomorrow at ', '').replace('yesterday at ', '')
                        time_str = time_str.replace('day before yesterday at ', '')
                    current_event["time"] = time_str
            
            # Location line
            elif line.startswith('    location:'):
                if current_event:
                    current_event["location"] = line.replace('    location:', '').strip()
            
            # Notes line (and subsequent indented lines)
            elif line.startswith('    notes:'):
                if current_event:
                    current_event["notes"] = line.replace('    notes:', '').strip()
            elif line.startswith('           ') and current_event and current_event.get("notes"):
                # Continuation of notes
                current_event["notes"] += " " + line.strip()
        
        # Don't forget the last event
        if current_event:
            events.append(current_event)
        
        return events
    except subprocess.TimeoutExpired:
        # icalBuddy timed out - likely permission issue
        print(f"Calendar timeout (permission issue)", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Calendar error: {e}", file=sys.stderr)
        return []


def _parse_cc_message(msg_raw) -> dict:
    """Parse CC message field which can be dict or Python repr string."""
    if isinstance(msg_raw, dict):
        return msg_raw
    if isinstance(msg_raw, str):
        try:
            return ast.literal_eval(msg_raw)
        except (ValueError, SyntaxError):
            return {}
    return {}


def _extract_cc_text(content) -> str:
    """Extract text from CC message content (list of items or plain string)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return " ".join(parts)
    return str(content)


def extract_cc_summary(date_str: str) -> list:
    """Extract Claude Code session summaries for a given date.

    Scans ~/.claude/projects/<project>/<uuid>.jsonl files.
    Uses find -newermt for fast date pre-filtering, then validates
    via in-file timestamp.

    Returns list of dicts: {project, session_start, model, message_count,
                            user_turns, topics, summary}
    """
    shanghai = ZoneInfo("Asia/Shanghai")
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    cc_projects = Path.home() / ".claude" / "projects"
    summaries = []

    if not cc_projects.exists():
        return summaries

    # Fast pre-filter: find JSONL files modified on target date
    try:
        result = subprocess.run(
            ["find", str(cc_projects), "-name", "*.jsonl",
             "-newermt", f"{date_str} 00:00",
             "!", "-newermt", f"{date_str} 23:59",
             "-type", "f"],
            capture_output=True, text=True, timeout=10,
        )
        candidate_files = [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return summaries

    if not candidate_files:
        return summaries

    skip_prefixes = (
        "[System note:", "[Replying to:", "[IMPORTANT:",
        "[CONTEXT COMPACTION", "Your task is to",
        # CC internal / wrapper messages
        "<local-command-caveat>", "<command-name>", "<command-message>",
        "<observed_from_primary_session>", "<local-command-stdout>",
        # Observer / agent system prompts
        "You are a Claude-Mem", "You are an AI assistant",
        "You are a specialized",
        # CC mode-switch / interrupt banners
        "--- MODE SWITCH:", "[Request interrupted",
    )

    for filepath in candidate_files:
        try:
            user_texts = []
            assistant_count = 0
            model = "unknown"
            cwd = ""
            session_start_utc = None

            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    entry_type = entry.get("type", "")
                    ts = entry.get("timestamp", "")

                    if entry_type == "user":
                        msg = _parse_cc_message(entry.get("message", ""))
                        if not msg:
                            continue
                        text = _extract_cc_text(msg.get("content", ""))
                        if not text or any(text.startswith(p) for p in skip_prefixes):
                            continue
                        if session_start_utc is None and ts:
                            try:
                                session_start_utc = datetime.fromisoformat(
                                    ts.replace("Z", "+00:00")
                                )
                            except ValueError:
                                pass
                        topic = text.strip().split("\n")[0][:80]
                        user_texts.append(topic)
                        if not cwd:
                            cwd = entry.get("cwd", "")

                    elif entry_type == "assistant":
                        assistant_count += 1
                        if model == "unknown":
                            msg = _parse_cc_message(entry.get("message", ""))
                            if msg:
                                model = msg.get("model", "unknown")

            if not user_texts or session_start_utc is None:
                continue

            # Validate date matches target
            session_local = session_start_utc.astimezone(shanghai)
            if session_local.date() != target_date:
                continue

            project_label = Path(cwd).name if cwd else Path(filepath).parent.name

            summaries.append({
                "project": project_label,
                "session_start": session_local.strftime("%H:%M"),
                "model": model,
                "message_count": len(user_texts) + assistant_count,
                "user_turns": len(user_texts),
                "topics": [t for t in user_texts[:3] if t],
                "summary": (
                    f"{len(user_texts)} 轮对话，模型 {model}"
                    + (f"，涉及: {', '.join(user_texts[:2])}" if user_texts else "")
                ),
            })
        except Exception:
            continue

    summaries.sort(key=lambda x: x["session_start"])
    return summaries


def build_cc_overview(summaries: list) -> Optional[dict]:
    """Aggregate CC session summaries into a compact diary overview."""
    if not summaries:
        return None

    projects = sorted(set(s["project"] for s in summaries))
    all_topics = []
    for s in summaries:
        all_topics.extend(s["topics"])

    return {
        "label": "Claude Code",
        "projects": projects,
        "session_count": len(summaries),
        "message_count": sum(s["message_count"] for s in summaries),
        "user_turns": sum(s["user_turns"] for s in summaries),
        "topics": list(dict.fromkeys(all_topics))[:8],
    }


def format_cc_for_diary(summaries: list) -> str:
    """Format CC session summaries as a compact diary section."""
    overview = build_cc_overview(summaries)
    if not overview:
        return ""

    lines = ["### 💻 Claude Code 工作概览"]
    lines.append(f"- 会话数: {overview['session_count']}")
    lines.append(f"- 消息数: {overview['message_count']}")
    lines.append(f"- 用户轮次: {overview['user_turns']}")
    lines.append(f"- 覆盖项目: {', '.join(overview['projects'][:5])}")
    if overview["topics"]:
        lines.append("- 主题: " + "；".join(overview["topics"][:8]))

    return "\n".join(lines)


def get_ai_logs(date_str: str) -> dict:
    """Extract AI conversation summaries from Hermes + Claude Code sessions."""
    ai_logs = {"hermes": [], "claude": []}

    # Extract Hermes conversations
    scripts_path = Path(__file__).parent
    sys.path.insert(0, str(scripts_path))

    try:
        from extract_hermes_conversations import (
            build_profile_overview,
            extract_hermes_summary,
            format_for_diary,
        )
        hermes_data = extract_hermes_summary(date_str)
        ai_logs["hermes"] = hermes_data
        ai_logs["hermes_overview"] = build_profile_overview(hermes_data)
        ai_logs["hermes_formatted"] = format_for_diary(hermes_data)
    except Exception as e:
        print(f"Hermes extraction error: {e}", file=sys.stderr)

    # Extract Claude Code sessions
    try:
        cc_data = extract_cc_summary(date_str)
        ai_logs["claude"] = cc_data
        ai_logs["claude_overview"] = build_cc_overview(cc_data)
        ai_logs["claude_formatted"] = format_cc_for_diary(cc_data)
    except Exception as e:
        print(f"CC extraction error: {e}", file=sys.stderr)

    return ai_logs


def read_file_safe(path: Path, timeout_secs: int = 3) -> Optional[str]:
    """Read file with timeout to avoid hanging on slow filesystems."""
    try:
        # Use os.path.exists instead of Path.exists() to avoid potential hangs
        if not os.path.exists(str(path)):
            return None
        
        # Use alarm for timeout (Unix only)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_secs)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            signal.alarm(0)
            return content
        except TimeoutError:
            return None
        finally:
            signal.alarm(0)
    except Exception:
        pass
    return None


def scan_vault_changes(vault_root: Path, date_str: str) -> list:
    """Scan Obsidian vault for files modified on specific date using find command."""
    try:
        # Use find command to get files modified on the specific date
        # This is faster and more reliable than Python's os.walk for large vaults
        cmd = [
            "find", str(vault_root),
            "-name", "*.md",
            "-newermt", f"{date_str} 00:00",
            "!", "-newermt", f"{date_str} 23:59",
            "-type", "f"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            return []
        
        changes = []
        for filepath in result.stdout.strip().split('\n'):
            if not filepath:
                continue
            
            # Skip diary files, system directories, event bridge
            skip_dirs = ("/01_日记/", "/000_日记/", "/88_event-bridge/", "/99-System/")
            if any(d in filepath for d in skip_dirs):
                continue

            # Cap total changes to avoid flooding diary
            if len(changes) >= 100:
                break
            
            # Get relative path
            try:
                rel_path = str(Path(filepath).relative_to(vault_root))
            except ValueError:
                continue
            
            # Get file title from first line
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# '):
                        title = first_line[2:]
                    else:
                        title = Path(filepath).stem
            except Exception:
                title = Path(filepath).stem
            
            changes.append({
                "path": rel_path,
                "type": "新建/修改",
                "title": title,
            })
        
        return changes
    except Exception:
        return []


def sync_obsidian():
    """Trigger Obsidian sync by launching the app if not running."""
    scripts_path = Path(__file__).parent
    sys.path.insert(0, str(scripts_path))
    
    try:
        from obsidian_sync import sync_and_wait
        return sync_and_wait()
    except Exception as e:
        return {"status": "error", "message": f"Obsidian 同步失败: {e}"}


def collect_diary_data(date_str: str) -> dict:
    """Collect all data for a single day."""
    diary_path = Path.home() / "Documents/Obsidian/AlexCai/50-Self/01_日记" / f"{date_str}.md"
    vault_root = Path.home() / "Documents/Obsidian/AlexCai"
    
    return {
        "date": date_str,
        "weekday": get_weekday(date_str),
        "weather": get_weather(date_str),
        "ai_logs": get_ai_logs(date_str),
        "calendar_events": get_calendar_events(date_str),
        "existing_content": read_file_safe(diary_path),
        "vault_changes": scan_vault_changes(vault_root, date_str),
        "obsidian_sync": sync_obsidian(),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: collect_data.py diary YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "diary":
        date_str = sys.argv[2]
        result = collect_diary_data(date_str)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif command == "weekly":
        # Simplified weekly collection
        print(json.dumps({"error": "Weekly not implemented in fix"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
