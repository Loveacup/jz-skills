# -*- coding: utf-8 -*-
"""P0 回归: fetch_all.process_step() 的结构化结果，失败绝不塌缩为 None/null。

锁定行为:
  - 子步骤失败 → {'status':'failed','returncode':N,'error':...}，永不 None
  - 成功但无 RESULT_JSON → {'status':'ok','parsed':False}
  - 成功且有 RESULT_JSON → 原始数据 + {'status':'ok','parsed':True}
  - parse_result_json 对成功/失败的底层解析行为
  - 全程 monkeypatch run_script，无真实子进程/网络
"""

import fetch_all


def test_process_step_failure_is_structured_not_none(monkeypatch):
    # 模拟子脚本非零退出
    monkeypatch.setattr(
        fetch_all, "run_script",
        lambda script, *args: (2, "", "boom"),
    )
    res = fetch_all.process_step("字幕", "fetch_subtitle_auto.py", "BVx")
    assert res is not None
    assert res["status"] == "failed"
    assert res["returncode"] == 2
    assert "boom" in res["error"]


def test_process_step_success_without_result_json(monkeypatch):
    # returncode 0 但 stdout 无 RESULT_JSON 包裹
    monkeypatch.setattr(
        fetch_all, "run_script",
        lambda script, *args: (0, "some logs but no result block", ""),
    )
    res = fetch_all.process_step("字幕", "fetch_subtitle_auto.py", "BVx")
    assert res is not None
    assert res == {"status": "ok", "parsed": False}


def test_process_step_success_with_result_json(monkeypatch):
    stdout = (
        "log line\n"
        "RESULT_JSON_START\n"
        '{"title": "x", "method": "official"}\n'
        "RESULT_JSON_END\n"
    )
    monkeypatch.setattr(
        fetch_all, "run_script",
        lambda script, *args: (0, stdout, ""),
    )
    res = fetch_all.process_step("字幕", "fetch_subtitle_auto.py", "BVx")
    assert res is not None
    assert res["status"] == "ok"
    assert res["parsed"] is True
    assert res["title"] == "x"
    assert res["method"] == "official"


def test_is_failed_helper():
    assert fetch_all.is_failed({"status": "failed", "returncode": 1}) is True
    assert fetch_all.is_failed({"status": "ok", "parsed": True}) is False
    assert fetch_all.is_failed(None) is False


def test_parse_result_json_valid():
    out = 'x\nRESULT_JSON_START\n{"a": 1}\nRESULT_JSON_END\ny'
    assert fetch_all.parse_result_json(out) == {"a": 1}


def test_parse_result_json_malformed_returns_none():
    out = "RESULT_JSON_START\nnot json{\nRESULT_JSON_END"
    assert fetch_all.parse_result_json(out) is None


def test_parse_result_json_absent_returns_none():
    assert fetch_all.parse_result_json("no markers here") is None
