---

name: memory-hub
description: |
  Jz-Plugin v4.0 的记忆-日志回路内核：集中式单写入口 + 按 type 分片的 append-only JSONL（issue/evolution/status_event 三 shard）+
  共享 envelope schema + 纯 stdlib 校验。CC 自动归集管：CC handoff → mem_ingest → cqi_runtime → mem_merge → Obsidian CQI 持续审计。
  把技能的「问题/纠正」(issue) 与「演进/版本变更」(evolution) 沉淀为机器可审计的真相源，经 git 同步、按 issue id 关联 Obsidian CQI 文档。
  Use when: 记录技能问题/用户纠正/审计发现、登记技能演进、校验记忆日志、append CQI event、
  memory-hub write、validate logs、记忆回路、日志回路、CC 事件归集、CQI 自动 ack、合并审计文档。
  DO NOT use for: 通用长期记忆/向量检索（用 supermemory）、自主改写技能正文或评判技能质量。
type: routine
version: 0.2.1
author: Hermes + Claude Code — Phase 1.5 收尾（mem_merge + 自动触发 + cron 兜底）
license: MIT

---

# memory-hub（Phase 1.5：CC × CQI 自动化接入）

Cursor 插件生态只是参考样板；**这个回路才是 Jz-Plugin 的主体**。Phase 1 落地了单写入口 + append-only 三 shard + git 回路。Phase 1.5 接入了 CC 自动归集管道 + CQI runtime + mem_merge 自动审计 + cron 兜底。不碰 marketplace/UI/Kanban 关键路径。

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
python3 scripts/cqi_runtime.py --quiet   # cron/no_agent 模式：无事零 stdout 静默

# ④ 合并：把新 issue 按 waterline 增量合并进 Obsidian CQI 审计文档（只追加、去重、幂等）
python3 scripts/mem_merge.py             # 无 waterline=全量但仅近 30 天；文档不存在则建带 frontmatter 新档
python3 scripts/mem_merge.py --quiet     # cron/no_agent 模式：无事零 stdout 静默
```

- **自动触发链**：CC session 结束后 Hermes 异步依次跑 `mem_ingest → cqi_runtime → mem_merge`，全 fail-open。
  另设每 30 分钟 cron 兜底 `cqi_runtime --quiet && mem_merge --quiet`（捕获漏触发，两脚本幂等）。**必须加 `--quiet`**——cron `no_agent=true` 时非空 stdout = 消息投递，不加则无事也每 30 分钟推送一条噪音。

- **CC 接入协议**：见 `autonomous-ai-agents/claude-code` skill「§CQI 事件吐出」——CC 每轮结束把 issue/evolution
  以 JSONL 写到 `/tmp/cc-cqi-events-<session>.jsonl`（只吐原始事件，不写 status）。
- **状态机边界**：`new→acknowledged` 由 `cqi_runtime.py` 自动；`resolved/wontfix/duplicate` 必须裁判面，禁止自动。
- **fail-open**：ingest 单行坏不阻断其余行（计 degraded）；任一环节写失败不阻断 Hermes 主任务。

## Schema 速览

硬校验（缺失/非法即拒写）：`id` · `type`(issue|evolution|status_event) · `skill` · `source`(user|cc|agent|hook|runtime|audit) · `evidence`(存原话) · `ts`(ISO-8601 带时区)。`status_event` 额外硬校验 `payload.issue_id` + `payload.status`(new|acknowledged|in_progress|resolved|wontfix|duplicate)。
软校验（告警）：`requester` · `source_hash`(sha256:…) · `trigger` · `skill_version` · `payload`。
完整规范见 `schemas/event.schema.json`。

## ⚠️ 常见坑

- **`mem_write --type status_event` 必须同时带 `--source`**（如 `--source audit`），否则校验以 `invalid source None` 拒写。仅 `--by human` 不够——`by` 只是 payload 字段，不替代信封的 `source`。
- **`mem_write --issue-id` 指向的 issue 必须已存在**，否则 status-log 中出现孤立状态事件。手动裁决前先 `mem_read` 确认 issue_id 正确。
- **手改 jsonl = 绕过校验**。即使只是改一个字符，也可能引入不可解析的 ts 或非法 type，导致 `mem_read` 的 reduce 崩溃（已知 bug：ts 不可解析 + 合法 ts 混排会炸 TypeError，待修）。
- **cron `no_agent=true` + 脚本有 stdout = 噪音轰炸**：`no_agent=true` 模式下，非空 stdout 会作为消息投递给用户。`cqi_runtime.py` 和 `mem_merge.py` 在无事发生时默认打印 `✓ no new issues`、`→ waterline at` 等，导致每 tick 一条噪音。**解决方案：cron shell 脚本中加 `--quiet`，无事时零 stdout → 静默**。手工跑不加 `--quiet`（保留可读输出），只有 cron 模板加。
- **`sync-all.sh` 部署后必须 `diff` 验证**：修改脚本后跑 `./deploy/sync-all.sh hermes`，部署端文件可能因 `rm -rf` + `cp -r` 时序问题未实际更新（2026-06-04 真实案例：源码加了 `--quiet` flag 并 commit，`sync-all.sh` 显示 `✅ Hermes (3 profiles)`，但部署端 `cqi_runtime.py` 和 `mem_merge.py` 仍是旧版无 `--quiet`，cron 继续每 30 分钟推送噪音）。**部署后必须验证：** `diff ~/code/jz-skills/hermes/memory-hub/scripts/cqi_runtime.py ~/.hermes/skills/governance/memory-hub/scripts/cqi_runtime.py` 等关键文件两端一致。不一致时手动 `cp` 补齐。
- **Cron shell 脚本路径：profile 目录优先** 🆕：`cronjob()` 的 `script` 字段解析相对路径时走 `~/.hermes/profiles/<profile>/scripts/`，**不是** `~/.hermes/scripts/`。cron 兜底脚本必须落在 profile 目录下（如 `~/.hermes/profiles/regent/scripts/memory-hub-cqi-sweep.sh`），否则 cron scheduler 找不到脚本。多 profile 环境每个 profile 独立维护。2026-06-04 真实案例：脚本更新到 `~/.hermes/scripts/` 但 cron 实际执行 `~/.hermes/profiles/regent/scripts/` 下的旧版——cron 持续推送噪音直至发现并修复。
- **Cron 实体不存在 — 静默故障** 🆕：Jz-Plugin doc 说每 30 分钟兜底但 cron 从未创建时，CC handoff 文件在 /tmp/ 堆积无声，88-审计/ 停更。部署后必须验证 cron 存在：cronjob list | grep memory-hub。2026-06-06：16 个 event 堆了 2 天，修复后建 cf4559e475c9。

## Git 同步回路

`append（单写入口）→ validate（exit 0）→ git add references/*.jsonl → 双语 commit → push/pull → Obsidian 按 issue id 关联`。

## 深入

- **完整 Phase 1 方案 / 架构 / 研究采纳-暂缓 / 验收标准** → [references/phase-1-scheme.md](references/phase-1-scheme.md)
- **CQI 审计工作流（全管道 + Obsidian 文档映射 + 裁决命令）** → [references/cqi-audit-workflow.md](references/cqi-audit-workflow.md)
- **CQI 方法学根基** → `governance/skill-authoring`（`log-driven-cqi-mvp`、`structured-cqi-log-memory`）
- **路线图全景** → Obsidian `02-Plan&CQI/Jz-Plugin-v4.0-Cursor插件生态研究计划.md`（第 3 节 Phase 1）

## 边界（Phase 1.5 明确不做）

Kanban 关键路径 / A2A / 自主改写技能 / 自动 resolved/wontfix/duplicate；SQLite / 向量 / 知识图谱 / MCP 记忆服务——数据积累后于 P5 评估。
