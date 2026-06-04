# Changelog — memory-hub

All notable changes to this skill are documented here. Append-only intent;
machine-readable mirror lives in `references/evolution-log.jsonl`.

## [0.1.0] — 2026-06-04

Phase 1：记忆-日志回路基础（Memory/Log Loop Foundation）首版。

### Added
- `schemas/event.schema.json` — 共享 event envelope（draft-07 规范，`type` ∈ {issue, evolution}）。
- `scripts/mem_write.py` — 唯一写入口；按 `type` 路由到分片，`flock` + `O_APPEND` 只追加；
  硬校验 6 核心字段，缺省自动生成递增 id 与带时区 ts；exit 0/2/3。
- `scripts/validate_logs.py` — 逐行校验，行号级报错，重复 id 告警；校验逻辑为单一真相源
  （被 `mem_write.py` import，writer 与 validator 不会漂移）。
- `references/issue-log.jsonl` / `references/evolution-log.jsonl` — 各 1 条种子记录（兼作冒烟样本）。
- `references/phase-1-scheme.md` — Phase 1 完整方案：架构 / schema 规则 / 三频钩子 / git 同步回路 /
  研究采纳-暂缓表（Cursor continual-learning · Muninn · EverOS，已核验）/ 验收标准。

### Verified
- 冒烟测试 T1–T11 全过：合法追加 / 自动 id 递增 / append-only / 四类拒写（空 skill·非法 ts·
  非法 type·naive 无时区）/ 损坏行行号检测 / 种子日志不被污染。
- 零外部依赖：python3 stdlib（无 jsonschema、无 venv）。

### Deferred (Phase 2+)
- cron / Kanban / A2A / 持续巡检 / 自主改写技能。
- SQLite / 向量 / 知识图谱 / MCP 记忆服务（P5 评估）。
