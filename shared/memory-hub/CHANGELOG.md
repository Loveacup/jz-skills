# Changelog — memory-hub

All notable changes to this skill are documented here. Append-only intent;
machine-readable mirror lives in `references/evolution-log.jsonl`.

## [0.2.1] — 2026-06-04

Phase 1.5 收尾：CQI 文档自动合并 + 全链自动触发 + cron 兜底（CC → ingest → ack → merge → Obsidian）。

### Added
- `scripts/mem_merge.py` — 把 issue 按 waterline 增量合并进 Obsidian CQI 审计文档
  `02-Plan&CQI/memory-hub CQI 持续审计.md`。复用 `mem_read` 的状态归约标注 `current_status`；
  每次追加一个 `## 批次 YYYY-MM-DD HH:MM` 段落，逐条列出状态 + evidence/location/fix 简要。
  **只追加、不覆盖、不删除**；按 issue_id 去重（已在文档中则跳过），无新条目不追加空批次（幂等）。
  waterline 存 `.merge_waterline`（上次合并最大 ts）；缺失→全量但仅近 30 天。fail-open（IO 失败 exit 3）。
- 自动触发链：`claude-code`「§CQI 事件吐出」改为三步链 `mem_ingest → cqi_runtime → mem_merge`，
  全异步 + fail-open（任一步失败不阻断后续与 Hermes 主任务）。
- cron 兜底：`~/.hermes/scripts/memory-hub-cqi-sweep.sh`（every 30m，no-agent）跑
  `cqi_runtime && mem_merge`，捕获 session 钩子漏触发。`&&` 顺序确保 merge 看到最新 ack 状态，
  避免 issue 以 new 状态被写入文档后被去重永久冻结。

### Verified
- mem_merge dry-run：6 条真实 issue 正确归约状态（resolved/wontfix/acknowledged），格式正常。
- 幂等：二次跑去重跳过、不追加空批次；waterline 增量推进。
- 零外部依赖：python3 stdlib。append-only 铁律未破（merge 仅 `O_APPEND` 到 Obsidian 文档）。

## [0.2.0] — 2026-06-04

Phase 1.5：CC × CQI 自动化接入（CC handoff → ingest → CQI runtime → 状态可查）。

### Added
- 第三分片 `status_event` → `references/status-log.jsonl`；schema/validator 同步扩展，
  硬校验 `payload.issue_id` + `payload.status`(new|acknowledged|in_progress|resolved|wontfix|duplicate)。
- `scripts/mem_ingest.py` — 批量归集 CC handoff（`/tmp/cc-cqi-events-*.jsonl`）：逐行校验→填默认→
  append→删 handoff→`validate_logs.py` 最终闸门。fail-open：坏行计 degraded 不阻断其余行。
- `scripts/mem_read.py` — 跨 shard 查询；按 `payload.issue_id` 将 status_event 按 ts 最新归约成
  `current_status`（无事件默认 new）；`--skill/--type/--status/--since` 过滤。
- `scripts/cqi_runtime.py` — CQI 薄层：拉 new issue 自动追加 status_event（new→acknowledged, by=cqi-auto）；
  幂等；**不**自动 resolved/wontfix/duplicate（裁判面边界）。
- `mem_write.py` 新增 `--status/--issue-id/--by` 与 `STATUS-<skill>-NNN` id 前缀。
- CC 侧协议写入 `autonomous-ai-agents/claude-code`「§CQI 事件吐出」节（A 决定，正文 ≤20 行）。

### Verified
- status_event：合法 dry-run exit 0；缺 issue_id / 非法 status 均 exit 2 零写入。
- mem_ingest：混合 handoff（2 合法 + 1 坏 JSON + 1 缺字段）→ 2 写入、2 degraded、handoff 删除、exit 0。
- mem_read：ack→in_progress 双事件正确归约 in_progress；`--status new` 过滤正确。
- 端到端：mem_write→validate→mem_read(new)→cqi_runtime→mem_read(acknowledged)→再 cqi_runtime(幂等无操作)；
  真实 references 上 `ISSUE-skill-authoring-001` 已自动 acknowledged，生成首条真实 `status-log.jsonl`。
- 零外部依赖：python3 stdlib。append-only 铁律未破。

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
