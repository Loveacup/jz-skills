"""P5-S?: register_cron_jobs 输出 4 行 cron spec JSON 到 stdout。

cronjob 是 Hermes agent 工具（非 CLI），CLI 只产出 spec，由 Hermes 主循环解析后调
cronjob(action="create")。本测试只验证 stdout 的 4 行 JSON 结构，不真调 cronjob（零副作用）。
"""
import json

import mac_doctor


def test_register_cron_jobs_emits_four_specs(capsys):
    mac_doctor.register_cron_jobs()
    lines = [ln for ln in capsys.readouterr().out.strip().split("\n") if ln]
    specs = [json.loads(ln) for ln in lines]

    # 4 行、4 个 job，严格按 Spec §3 注册表
    assert len(specs) == 4
    assert [s["name"] for s in specs] == [
        "mac-doctor-quick", "mac-doctor-triage", "mac-doctor-deep", "mac-doctor-weekly",
    ]
    assert [s["schedule"] for s in specs] == [
        "every 30m", "every 12h", "0 3 * * *", "0 9 * * 1",
    ]

    # 公共字段齐全
    for s in specs:
        assert s["action"] == "create"
        assert s["deliver"] == "origin"
        assert "model" not in s          # 省略 → 用 Hermes 主模型

    quick, *llm_jobs = specs
    # quick: no_agent + script（watchdog 模式），无 skills/prompt
    assert quick["no_agent"] is True
    assert quick["script"] == "mac-doctor-watchdog.py"

    # 其余 3 个: LLM agent + skills + 自包含 prompt
    for s in llm_jobs:
        assert s["no_agent"] is False
        assert s["skills"] == ["mac-doctor"]
        assert s["prompt"].strip()
        assert s["enabled_toolsets"] == ["terminal", "file"]
