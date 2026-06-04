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
version: 0.1.0
author: Hermes + Claude Code — Phase 1 记忆-日志回路基础
license: MIT
---

# memory-hub（Phase 1：记忆-日志回路基础）

Cursor 插件生态只是参考样板；**这个回路才是 Jz-Plugin 的主体**。Phase 1 只做最小可验证的本地回路，不碰 marketplace/UI/Kanban/cron。

## 铁律（违反即破坏真相源）

1. **单写入口**：所有结构化记录只经 `scripts/mem_write.py`；**不手改 jsonl**（手改绕过校验与 provenance）。
2. **只追加**：writer 仅 `O_APPEND`，永不重写既有行。
3. **分片不混库**：`type` 决定 shard——`issue`→`references/issue-log.jsonl`，`evolution`→`references/evolution-log.jsonl`。
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

## Schema 速览

硬校验（缺失/非法即拒写）：`id` · `type`(issue|evolution) · `skill` · `source`(user|cc|agent|hook|runtime|audit) · `evidence`(存原话) · `ts`(ISO-8601 带时区)。
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
