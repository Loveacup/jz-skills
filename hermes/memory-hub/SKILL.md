---
name: memory-hub
description: |
  Jz-Plugin v4.0 的记忆-日志回路内核：集中式单写入口 + 按 type 分片的 append-only JSONL +
  共享 envelope schema + 纯 stdlib 校验。把技能的「问题/纠正」(issue) 与「演进/版本变更」(evolution)
  沉淀为机器可审计的真相源，经 git 同步、按 issue id 关联 Obsidian CQI 文档。
  Use when: 记录技能问题/用户纠正/审计发现、登记技能演进、校验记忆日志、append CQI event、
  memory-hub write、validate logs、记忆回路、日志回路。
  DO NOT use for: 通用长期记忆/向量检索（用 supermemory）、cron/Kanban 自动编排（Phase 2）、
  直接改技能正文或评判技能质量。
version: 0.2.1
author: Hermes + Claude Code — Phase 1.5 收尾（mem_merge + 自动触发 + cron 兜底）
license: MIT
---

# memory-hub（Phase 1：记忆-日志回路基础）

Cursor 插件生态只是参考样板；**这个回路才是 Jz-Plugin 的主体**。Phase 1 只做最小可验证的本地回路，不碰 marketplace/UI/Kanban/cron。

## 铁律（违反即破坏真相源）

1. **单写入口**：所有结构化记录只经 `scripts/mem_write.py`；**不手改 jsonl**（手改绕过校验与 provenance）。
2. **只追加**：writer 仅 `O_APPEND`，永不重写既有行。
3. **分片不混库**：`type` 决定 shard——`issue`→`references/issue-log.jsonl`，`evolution`→`references/evolution-log.jsonl`，`status_event`→`references/status-log.jsonl`。
4. **存储层不做业务判断**：只管格式/溯源完整性，不评判技能质量、不改技能正文。

## 快速用法

```bash
# 记录一条「用户纠正」（issue）；id/ts 缺省自动生成
python3 scripts/mem_write.py --type issue --skill <skill> --source user \
  --trigger user_correction --evidence "<原话，逐字>" --implicated-rule <rule-id>

# 登记一条「技能演进」（evolution）
python3 scripts/mem_write.py --type evolution --skill <skill> --source cc \
  --change-type rule_add --validation-score 90 --evidence "<改了什么>" \
  --changelog-ref "CHANGELOG.md#xyz"

# 也可整条 JSON 从 stdin 写入
echo '{...}' | python3 scripts/mem_write.py --stdin

# push 前必过：逐行校验（exit 0 才提交）
python3 scripts/validate_logs.py
```

校验失败 → exit 2，**零写入**；IO 失败 → exit 3（不阻断调用方主任务，降级报告）。

## Phase 1.5：CC × CQI 自动化接入

闭环：**CC 吐事件 → Hermes 归集 → CQI 自动确认 → 状态可查**。三个新脚本，零新依赖，全 fail-open。

```bash
# ① 归集：Hermes 检测 CC session 结束时调，读 handoff → 校验 → 批量写 → 删 handoff → 最终闸门
python3 scripts/mem_ingest.py            # 默认 glob /tmp/cc-cqi-events-*.jsonl

# ② 查询：按 status_event 的 ts 最新归约出每条 issue 的 current_status（无事件=new）
python3 scripts/mem_read.py --type issue --status new --skill <skill> --since 2026-06-01

# ③ CQI runtime 薄层：拉 new issue，自动追加 status_event（new→acknowledged, by=cqi-auto）
python3 scripts/cqi_runtime.py           # 不碰 resolved/wontfix/duplicate（裁判面边界）

# ④ 合并：把新 issue 按 waterline 增量合并进 Obsidian CQI 审计文档（只追加、去重、幂等）
python3 scripts/mem_merge.py             # 无 waterline=全量但仅近 30 天；文档不存在则建带 frontmatter 新档
```

- **自动触发链**：CC session 结束后 Hermes 异步依次跑 `mem_ingest → cqi_runtime → mem_merge`，全 fail-open。
  另设每 30 分钟 cron 兜底 `cqi_runtime && mem_merge`（捕获漏触发，两脚本幂等）。接入协议见 `claude-code`「§CQI 事件吐出」。

- **CC 接入协议**：见 `autonomous-ai-agents/claude-code` skill「§CQI 事件吐出」——CC 每轮结束把 issue/evolution
  以 JSONL 写到 `/tmp/cc-cqi-events-<session>.jsonl`（只吐原始事件，不写 status）。
- **状态机边界**：`new→acknowledged` 由 `cqi_runtime.py` 自动；`resolved/wontfix/duplicate` 必须裁判面，禁止自动。
- **fail-open**：ingest 单行坏不阻断其余行（计 degraded）；任一环节写失败不阻断 Hermes 主任务。

## Schema 速览

硬校验（缺失/非法即拒写）：`id` · `type`(issue|evolution|status_event) · `skill` · `source`(user|cc|agent|hook|runtime|audit) · `evidence`(存原话) · `ts`(ISO-8601 带时区)。`status_event` 额外硬校验 `payload.issue_id` + `payload.status`(new|acknowledged|in_progress|resolved|wontfix|duplicate)。
软校验（告警）：`requester` · `source_hash`(sha256:…) · `trigger` · `skill_version` · `payload`。
完整规范见 `schemas/event.schema.json`。

## Git 同步回路

`append（单写入口）→ validate（exit 0）→ git add references/*.jsonl → 双语 commit → push/pull → Obsidian 按 issue id 关联`。

## 深入

- **完整 Phase 1 方案 / 架构 / 研究采纳-暂缓 / 验收标准** → [references/phase-1-scheme.md](references/phase-1-scheme.md)
- **CQI 方法学根基** → `governance/skill-authoring`（`log-driven-cqi-mvp`、`structured-cqi-log-memory`）
- **路线图全景** → Obsidian `02-Plan&CQI/Jz-Plugin-v4.0-Cursor插件生态研究计划.md`（第 3 节 Phase 1）

## 边界（Phase 1 明确不做）

cron / Kanban / A2A / 持续巡检 / 自主改写技能；SQLite / 向量 / 知识图谱 / MCP 记忆服务——数据积累后于 P5 评估。
