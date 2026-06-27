# memory-hub · Phase 1 方案：记忆-日志回路基础

> Jz-Plugin v4.0 的**内核**。本文件是 Phase 1 的可执行方案（交付物 C）。
> 定位：Cursor 插件生态只是参考样板；本回路才是主体。Phase 1 不做 marketplace/UI/Kanban。

---

## 1. 架构 · 单写入口 + 分片 append-only

```
                         ┌─────────────────────────────┐
  read / modify / event  │        memory-hub           │
  ───────────────────▶   │   mem_write.py（唯一写入口） │
                         │   1) 组装 envelope          │
                         │   2) validate_record()      │  ← 校验失败即拒写
                         │   3) flock + O_APPEND 追加   │
                         └───────────────┬─────────────┘
                                         │ 按 type 分片
                        ┌────────────────┴────────────────┐
                        ▼                                  ▼
            references/issue-log.jsonl        references/evolution-log.jsonl
            （问题/纠正/审计发现）              （技能演进/版本/规则变更）
```

**铁律**
- **单写入口**：所有结构化记录只经 `mem_write.py`，不手改 jsonl。手改绕过校验与 provenance。
- **只追加（append-only）**：writer 仅 `O_APPEND`，永不重写既有行；jsonl 是机器真相源。
- **分片不混库**：`type` 决定落哪个 shard；不做巨型无类型 dump。
- **存储层只管格式/溯源完整性，不做业务判断**（不评判技能质量、不改技能正文）。

**记忆分层**（三层各司其职，对应 EverOS「Markdown=真相 / SQLite=索引」哲学的轻量版）：
| 层 | 载体 | 角色 |
|----|------|------|
| 机器真相 | git + `*.jsonl`（本组件） | append-only、可审计、可重放 |
| 人类 CQI | Obsidian `02-Plan&CQI/*.md` | 问题图谱、闸门、可读性，按 issue id 关联 |
| 运行时记忆 | Jz-Plugin 运行态 | 派生索引，可重建，非权威 |

---

## 2. Schema · envelope + type enum

单一信封 `schemas/event.schema.json`（draft-07 为规范；`validate_logs.py` 用纯 stdlib 镜像等价子集，**不引 jsonschema 依赖**）。

**硬校验（缺失/非法即拒写，exit 2）**
| 字段 | 规则 |
|------|------|
| `id` | 非空字符串。约定 `ISSUE-<skill>-NNN` / `EVO-<skill>-NNN`；亦为 CQI join key。缺省自动生成、序号递增。 |
| `type` | enum：`issue` \| `evolution`（分片选择器）。 |
| `skill` | 非空字符串，目标技能名。 |
| `source` | enum：`user`\|`cc`\|`agent`\|`hook`\|`runtime`\|`audit`（信号来源）。 |
| `evidence` | 非空字符串。纠正类事件须存**原文**，不可只存摘要。 |
| `ts` | ISO-8601 **带时区偏移**（如 `+08:00`）；必须能被 `datetime.fromisoformat` 解析，naive 时间拒收。缺省取当前本地时间。 |

**软校验（接受但告警）**：`requester`（user\|cc\|agent\|cron\|kanban）、`source_hash`（`sha256:<64hex>`，技能文件实现时附）、`trigger`（manual_review\|runtime_failure\|scheduled_audit\|user_correction）、`skill_version`、`session_id`、`payload`。

**payload 按 type**
- `issue`：`implicated_rule`、可选 `change_type`。
- `evolution`：`change_type`（rule_add/rule_edit/rule_remove/refactor/version_bump/doc）、`validation_score`(0–100)、`changelog_ref`。

**重复 id**：`validate_logs.py` 全文件扫描，重复 id 告警（不阻断）。

---

## 3. 三频钩子 · 仅本地（Phase 1）

借鉴 `log-driven-cqi-mvp` 的三频，**只记录、只提醒，不自动改技能**。Phase 1 钩子皆为本地、手动/CC 介导，**不接 cron/kanban/A2A**（那是 Phase 2）。

| 频率 | 触发 | 动作 | 落点 |
|------|------|------|------|
| **read** | 技能加载/读取 | 只读检查：changelog 摘要、provenance(repo/ref/SHA/pin)、stale 状态、未决 issue。可提示，不改写。 | 提示，不落库 |
| **modify** | 技能被改 | 追加 `CHANGELOG.md` 人读条目 + 一条 `evolution` 记录 + 质量闸结论。MVP 软闸（warn）。 | `evolution-log.jsonl` |
| **event** | 用户纠正 / 显式规则指令（"以后不要这样"/"顺序错了"/"记住这个流程"）/ 运行时错误 / 审计发现 / 反复执行缺漏 | 追加一条 `issue` 记录，**保存原话** + 来源指针 + 受影响技能。 | `issue-log.jsonl` |

> cadence 节流（采自 Cursor continual-learning）：轮次≥N + 距上次≥M 分钟 + transcript mtime 前进，三重闸 + JSON 状态文件。**Phase 1 仅作为钩子参数预留，不做自动触发。**

---

## 4. Git 同步回路

```bash
# 1) append（经单写入口）
python3 scripts/mem_write.py --type issue --skill <s> --source user \
  --trigger user_correction --evidence "<原话>" --implicated-rule <rule>

# 2) validate（push 前必过）
python3 scripts/validate_logs.py            # exit 0 才继续

# 3) git append-only 提交（双语，符合仓库规范）
git add hermes/memory-hub/references/*.jsonl
git commit -m "chore(memory-hub): append issue/evolution events / 追加记忆事件"

# 4) push / pull（多机/多 profile 收敛）
git push && git pull --rebase

# 5) Obsidian 链接：在 02-Plan&CQI 的 CQI 文档里用 issue id 关联（ISSUE-<skill>-NNN）
```

退化策略：写失败**不阻断**调用方主任务，转为 stderr 报告 + 降级记录；validate 失败则拦在 commit 前。

---

## 5. 研究采纳 / 暂缓（已核验，2026-06-04）

> 研究用来**约束 MVP**，不是扩范围。三仓库经后台 agent 抓取核验。

| 来源 | 已确认 | 采纳进 Phase 1 | 暂缓（→P5） |
|------|--------|----------------|-------------|
| **Cursor continual-learning** | stop hook + skill + agents-memory-updater；`followup_message` 提示；状态文件 `.cursor/hooks/state/continual-learning*.json`；cadence=10 轮/120 分钟/mtime 前进；trial=3 轮/15 分钟/24h；更新就地、去重、每段 ≤12 bullet。**修正**：仅 `completed` 且 `loop_count===0` 的轮次计数；trial 为 env 开关、非默认。 | ① cadence 三重闸 + JSON 状态文件（作钩子参数）；② "就地更新、无元数据、上限 bullet" 的克制纪律。 | 子 agent 委派模型；Bun/TS 钩子运行时；AGENTS.md 自动改写。 |
| **Muninn** | 三类记忆 episodic/semantic/procedural；SQLite+向量(nomic-embed-text 768d)；知识图谱；procedure evolution；TS MCP server。**修正**：工具名带 `memory_` 前缀、共 12 个（非 9）。 | episodic/semantic/procedural 作为**记录标签约定**（未来 payload tag）。 | 整套 SQLite+向量+知识图谱+MCP server。 |
| **EverOS** | 转对话/轨迹/文件为结构化可检索演进记忆；存储轻量：Markdown=真相 + SQLite=状态 + LanceDB=向量/BM25，**刻意拒绝** Mongo/ES/Milvus/Redis/Kafka。**修正**：不是"评估基础设施"，是完整记忆运行时；记录是 markdown 式（Episodes/Cases/Profiles/Skills），无可直接抄的 typed schema。 | "Markdown/JSONL=真相、派生索引可重建" 的分层哲学（印证本方案，引为旁证）；四类记忆面名可作未来 type 候选。 | LanceDB+SQLite+markdown 全管线、DDD 分层架构。 |

**缺口**：Cursor 的 `.cursor-plugin` manifest 全 schema 未抄；Muninn 12 工具全名未逐一枚举；EverOS 无 Python dataclass/Pydantic 记录模型可直接复用。→ 均非 Phase 1 阻塞项。

---

## 6. 验收标准（Phase 1 完成定义）

- [x] `mem_write.py` 追加合法记录 → exit 0，行数 +1，文件仍通过 validate。
- [x] 自动 id 序号递增（`ISSUE-<skill>-001` → `-002`）。
- [x] 拒写非法记录：空 `skill` / 非法 `ts`（含 naive 无时区）/ 非法 `type` → exit 2，**零写入**。
- [x] `validate_logs.py` 在种子日志上 exit 0；遇损坏行 exit 1 并报**行号**。
- [x] append-only：writer 仅 `O_APPEND`，从不重写既有行（代码审查 + 行数验证）。
- [x] 零外部依赖：python3 stdlib 即可跑（无 jsonschema / 无 venv）。
- [x] （部署）`deploy/sync-all.sh` / `sync-back.sh` 已加入 `governance/memory-hub` 映射（仅全局，不进 per-profile 循环），二者 `bash -n` 通过；**只加映射，未实际 sync**——`./deploy/sync-all.sh hermes` 由用户在就绪时执行。

> 前 6 项由本次实施的冒烟测试 T1–T11 验证；末项（部署）由 `bash -n` 双脚本验证、未实际 sync。

---

## 7. 边界（明确不做 / 留 Phase 2+）

- ❌ cron / Kanban 编排 / A2A profile 群 / 持续巡检 / 自主改写技能。
- ❌ SQLite / 向量 / 知识图谱 / MCP 记忆服务（数据积累后于 P5 再评估）。
- ❌ 让记忆层做质量判断或改技能正文。
- Kanban（若引入）只能是控制面、引用 log id，**绝不**成为真相源。
