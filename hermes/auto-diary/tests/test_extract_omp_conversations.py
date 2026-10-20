import json
import os
import sys
import types
from datetime import datetime

import scripts.collect_data as collect_data
from scripts.extract_omp_conversations import extract_omp_conversations


def _write_session(path, events, target_date="2026-10-02"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")
    stamp = datetime.fromisoformat(target_date + "T00:00:00+08:00").timestamp()
    os.utime(path, (stamp, stamp))


def test_extracts_local_day_user_and_final_assistant_without_internal_content(tmp_path):
    sessions = tmp_path / "sessions"
    path = sessions / "project" / "session-1.jsonl"
    _write_session(path, [
        {"type": "session", "id": "session-1", "timestamp": "2026-10-01T16:00:00Z", "cwd": "/work/project", "title": "OMP sample", "parentSession": "root-1"},
        {"type": "message", "timestamp": "2026-10-01T16:30:00Z", "message": {"role": "user", "content": [{"type": "text", "text": "Review the daily data pipeline."}]}},
        {"type": "message", "timestamp": "2026-10-01T16:31:00Z", "message": {"role": "assistant", "stopReason": "toolUse", "content": [{"type": "thinking", "thinking": "private reasoning"}, {"type": "toolCall", "name": "read", "arguments": {}}]}},
        {"type": "message", "timestamp": "2026-10-01T16:32:00Z", "message": {"role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": "Pipeline contract checked; missing OMP source identified."}]}},
        {"type": "message", "timestamp": "2026-10-01T15:59:00Z", "message": {"role": "user", "content": [{"type": "text", "text": "Previous local date; exclude."}]}},
    ])

    result = extract_omp_conversations("2026-10-02", sessions_dir=sessions)

    assert result["status"] == "ok"
    assert result["session_count"] == 1
    assert result["branch_session_count"] == 1
    item = result["sessions"][0]
    assert item["session_id"] == "session-1"
    assert item["user_turns"] == 1
    assert item["assistant_responses"] == 1
    assert item["user_topics"] == ["Review the daily data pipeline."]
    assert item["assistant_summaries"] == ["Pipeline contract checked; missing OMP source identified."]
    serialized = json.dumps(result)
    assert "private reasoning" not in serialized
    assert "Previous local date" not in serialized


def test_missing_session_directory_is_reported_not_misreported_as_zero(tmp_path):
    result = extract_omp_conversations("2026-10-02", sessions_dir=tmp_path / "missing")
    assert result["status"] == "unavailable"
    assert result["session_count"] == 0
    assert result["sessions"] == []


def test_collect_data_exposes_omp_source(monkeypatch):
    hermes_module = types.ModuleType("extract_hermes_conversations")
    setattr(hermes_module, "build_profile_overview", lambda _data: {})
    setattr(hermes_module, "extract_hermes_summary", lambda _date: [])
    setattr(hermes_module, "format_for_diary", lambda _data: "")
    omp_data = {"date": "2026-10-02", "source": "omp", "status": "empty", "session_count": 0, "sessions": []}
    omp_module = types.ModuleType("extract_omp_conversations")
    setattr(omp_module, "extract_omp_conversations", lambda _date: omp_data)
    monkeypatch.setitem(sys.modules, "extract_hermes_conversations", hermes_module)
    monkeypatch.setitem(sys.modules, "extract_omp_conversations", omp_module)
    monkeypatch.setattr(collect_data, "extract_cc_summary", lambda _date: [])
    monkeypatch.setattr(collect_data, "build_cc_overview", lambda _data: None)
    monkeypatch.setattr(collect_data, "format_cc_for_diary", lambda _data: "")

    result = collect_data.get_ai_logs("2026-10-02")

    assert result["omp"] is omp_data
    assert result["omp"]["status"] == "empty"


def test_exposes_counts_when_prompt_excerpts_are_capped(tmp_path):
    events: list[dict[str, object]] = [{"type": "session", "id": "session-cap", "timestamp": "2026-10-01T16:00:00Z"}]
    for index in range(13):
        events.append({"type": "message", "timestamp": f"2026-10-01T16:{index:02d}:00Z", "message": {"role": "user", "content": [{"type": "text", "text": f"Prompt {index}"}]}})
    for index in range(9):
        events.append({"type": "message", "timestamp": f"2026-10-01T17:{index:02d}:00Z", "message": {"role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": f"Answer {index}"}]}})
    _write_session(tmp_path / "sessions" / "session-cap.jsonl", events)

    result = extract_omp_conversations("2026-10-02", sessions_dir=tmp_path / "sessions")

    item = result["sessions"][0]
    assert len(item["user_topics"]) == 12
    assert item["user_topics"][0] == "Prompt 0"
    assert item["user_topics"][-1] == "Prompt 12"
    assert item["user_topics_omitted"] == 1
    assert len(item["assistant_summaries"]) == 8
    assert item["assistant_summaries"][-1] == "Answer 8"
    assert item["assistant_summaries_omitted"] == 1


def test_full_scan_finds_session_files_with_preserved_old_mtime(tmp_path):
    sessions = tmp_path / "sessions"
    path = sessions / "session-old-mtime.jsonl"
    _write_session(path, [
        {"type": "session", "id": "session-old-mtime", "timestamp": "2026-10-01T16:00:00Z"},
        {"type": "message", "timestamp": "2026-10-01T16:30:00Z", "message": {"role": "user", "content": [{"type": "text", "text": "A historical OMP session."}]}},
    ])
    old_stamp = datetime.fromisoformat("2026-10-01T00:00:00+08:00").timestamp()
    os.utime(path, (old_stamp, old_stamp))

    normal = extract_omp_conversations("2026-10-02", sessions_dir=sessions)
    full = extract_omp_conversations("2026-10-02", sessions_dir=sessions, full_scan=True)

    assert normal["status"] == "empty"
    assert full["status"] == "ok"
    assert full["session_count"] == 1
