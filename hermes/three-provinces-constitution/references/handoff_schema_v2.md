# 三省六部交接协议（Handoff Schema）v2

本文档定义三省六部各阶段之间**形式化交接**的数据格式与校验规则。所有跨阶段产出必须遵从此 Schema，御史稽核以此为准。

**版本说明**：v2 是 v1 的严格超集。所有 v1 字段名、位置、语义保持不变；新增字段独立放置于 `state` 块内及顶层，不影响已有解析路径。

---

## 一、通用 Handoff 格式

每个阶段产出必须包含以下字段（YAML 或 JSON 均可）：

```yaml
task_id: string              # 必填，全局唯一任务标识
stage: 中书 | 门下 | 尚书 | 六部 | 御史 | 史馆   # 必填，本次交接所处阶段
parent_task_id: string | null   # fan-in / gate / synthesis 时必填
artifacts:                   # 必填，本阶段产出物清单（≥1 条）
  - path: string             # 绝对路径或 kanban workspace 相对路径
    type: prd | code | data | report | index | other
    summary: string          # 一句话摘要，≤80 字
blocked_by: [task_id]        # 阻塞依赖，无则为 []
integrity_signals:           # 完整性信号，御史据此判定
  sources_count: integer     # 引用来源数（研撰类）或文件数（工程类）
  verification_status: pending | passed | failed | skipped
  cross_check_done: boolean  # 是否做了交叉核验
boundary_violation: boolean  # 是否检出越界，默认 false
concession_log:              # 反骑墙日志（分析/研判类必填）
  total_challenges: integer  # 受质疑次数
  total_concessions: integer # 让步次数
  consecutive_concessions: integer  # 当前连续让步计数，必须 ≤1
state:                       # 必填，子 agent 作为 Reducer 的状态记录
  status: pending | running | blocked | done | failed
  last_event: string         # 触发此次状态变更的事件
  previous_status: string    # 变更前状态
  checkpoint_data: any       # >5min 或 budget>high 任务必填，子 agent 自定义恢复数据
  resume_from: task_id | null  # 恢复任务时指向原 task_id
  # ── v2 新增字段（state 块内）──
  recovery_count: integer    # 本任务累计恢复/重试次数，默认 0
  last_recovery_reason: string | null  # 上次恢复原因，≤80 字；无则为 null
error_report:                # 仅出错时必填，全文 ≤500 字
  error_type: string         # timeout / api_error / parse_error / boundary_violation / other
  root_cause: string         # 1-2 句，≤80 字
  suggested_fix: string      # 1 句，≤60 字
next_stage: string           # 下一阶段名（最终归档则为 "完成"）
notes: string                # 自由文本，可空
# ── v2 新增字段（顶层）──
delivery_required: boolean   # 本 handoff 是否必须送达下游；默认 true
```

### 通用校验规则
- `task_id` 缺失 → 御史封驳，退回起始阶段重发
- `artifacts` 为空 → 视为空奏，退回本阶段重做
- `boundary_violation = true` → 自动退回上一阶段
- `consecutive_concessions > 1` → 触发反骑墙预警，退回重述判断
- `state.status` 与 Kanban 卡片状态不一致 → 御史标记异常，退回同步状态
- `state.checkpoint_data` 在 timeout >5min 或 budget >high 任务中缺失 → 退回补充
- `error_report` 任一字段超长（root_cause >80 字 / suggested_fix >60 字 / 全文 >500 字）→ 退回重报，禁止 dump stack trace
- **v2 新增**：`state.recovery_count` 缺失 → 视为 0，不封驳（兼容 v1 产物）
- **v2 新增**：`delivery_required = false` 时，御史跳过送达校验，但仍执行内容稽核

---

## 二、各阶段特定字段与校验

### 2.1 中书省（拟制阶段）
**特定字段**：
```yaml
plan:
  decomposition: [string]    # 任务拆解步骤，≥1
  sources_planned: [string]  # 计划使用的来源/方向清单
  routes: [{step, owner, deliverable}]   # 路径设计
  budget: low | mid | high
  timeout: string            # e.g. "5m", "30m"
```
**校验规则**：
- `decomposition` 空 → 退回中书
- 若 `routes` 中出现中书自身执行 `web_search / file_write` → 标记 `boundary_violation`

### 2.2 门下省（封驳阶段）
**特定字段**：
```yaml
review:
  duplicates_removed: integer
  urls_verified: {checked: integer, broken: integer}
  low_quality_excluded: [{source, reason}]
  verdict: pass | partial_pass | reject
  reject_reasons: [string]   # verdict != pass 时必填
```
**校验规则**：
- 若 `review` 中新增了原中书未规划的来源 → `boundary_violation`（门下不得自行补源）
- `verdict = reject` 时必须有 `reject_reasons` ≥1

### 2.3 尚书省（派工阶段）
**特定字段**：
```yaml
dispatch:
  kanban_tasks: [{task_id, owner, parent_task_id, deps}]
  fan_out_count: integer
  fan_in_strategy: gate | review | synthesis | none
  blocked_unblocked: [{task_id, action, ts}]   # ts 用 ISO 8601
```
**校验规则**：
- 任一 `kanban_tasks[*]` 缺 `parent_task_id` 且策略非 none → 违反"创建时绑定"规矩
- 若尚书 artifacts 含具体研撰产出（非调度日志） → `boundary_violation`

### 2.4 六部 / 将作监（施行阶段）
**特定字段**：
```yaml
execution:
  owner: 工部 | 礼部 | 户部 | 兵部 | 刑部 | 吏部 | 将作监
  changed_files: [{path, action: created|modified|deleted}]   # 工程类
  evidence_chain: [{source, url, quote}]                      # 研撰类
  test_log: string                                             # 工程类，路径
  return_path: 尚书省                                           # 必须经尚书回禀
```
**校验规则**：
- `return_path != 尚书省` → `boundary_violation`（不得越级直奏太子）
- 工程类无 `changed_files` 或 `test_log` → 退回重做
- 研撰类无 `evidence_chain` 或 `sources_count < 2` → 退回重做

### 2.5 御史台（稽核阶段）
**特定字段**：
```yaml
audit:
  target_task_id: string
  checks:
    boundary_check: pass | fail
    evidence_check: pass | fail
    concession_rate: float   # 0.0–1.0
    cross_check: pass | fail
  findings: [{severity: low|mid|high|critical, item, evidence}]
  verdict: clean | warn | reject
  recommendation: string
```
**校验规则**：
- 若 `audit.artifacts` 含对被稽核产出的**修改**（非批注） → `boundary_violation`（御史不得代笔）
- `concession_rate > 0.30` → 必须出 warn 以上 finding
- `verdict = reject` → 自动退回 owner 的上一阶段

### 2.6 史馆（归档阶段）
**特定字段**：
```yaml
archive:
  obsidian_path: string
  qmd_index_updated: boolean
  original_hash: string      # 归档前原稿哈希
  archived_hash: string      # 归档后哈希，应等于 original_hash
  retention: permanent | transient
```
**校验规则**：
- `original_hash != archived_hash` → `boundary_violation`（史馆篡改原稿）
- `retention = transient` 的内容不得入 long-term memory

---

## 三、流转图

```text
中书 ──handoff──▶ 门下 ──handoff──▶ 尚书 ──fan-out──▶ 六部/将作监
                                                       │
                              ◀──── handoff (fan-in) ──┘
                                       │
                                       ▼
                                     御史 ──verdict──▶ 史馆
                                       │
                                  reject 时退回
```

每条 handoff 都是一份满足"通用 Handoff 格式"+ 对应阶段"特定字段"的产物，由发起方写入 kanban workspace，下一阶段读取后再追加自己的部分。

---

## 四、与反骑墙协议的衔接

- 分析、评估、研判类 artifact（包括 morning-news-briefing 的「分析」与「总结」）必须填 `concession_log`
- 御史 `audit.checks.concession_rate` 由 `concession_log` 推导：`total_concessions / max(total_challenges, 1)`
- `consecutive_concessions > 1` 在任何阶段被发现 → 自动 `boundary_violation` 并退回

---

## 五、v1 → v2 迁移说明

| 变更项 | v1 | v2 |
|--------|----|----|
| `state.recovery_count` | 无 | 新增，默认 0 |
| `state.last_recovery_reason` | 无 | 新增，默认 null |
| `delivery_required` | 无 | 新增顶层字段，默认 true |
| 其余全部字段 | 保留 | 保留（名/位置/语义不变） |

**兼容性承诺**：v1 产物无需改写即可被 v2 解析器接受；缺失的新增字段按默认值处理。v2 产物向下兼容时，v1 解析器会忽略未知字段（YAML/JSON 标准行为）。

---

*奉天承运，三省六部章程，交接有据，越界必查。*
