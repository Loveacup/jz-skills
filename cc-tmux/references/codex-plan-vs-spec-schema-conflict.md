# Codex Plan vs Spec Schema 冲突 — 案例 + 防御（2026-06-28 实发）

## 案例 1：mac-doctor v3.0 P1 `preferences.py`

**项目**：mac-doctor v3.0（OB `20-Areas/20_技术项目/mac-doctor/`）
**任务**：P1 实现操作偏好记忆模块 `preferences.py`（6 个 TDD slice）
**冲突点**：`suppressions` 字段的 schema

| 来源 | Schema | 注释 |
|------|--------|------|
| **Spec §6（source of truth）** | `suppressions: list[{signature, first_seen, last_seen, count, ttl_hours}]` | 含 5 个字段，复杂结构 |
| Codex `add_interpretation_dedup` slice 输出 | `suppressions: dict[signature: expires_at]` | 简单 kv 结构，训练先验推测 |

**为什么 Codex 推测错了**：

1. **Spec 上下文被截断** — R2.1 委派包 ALLOWED FILES 列出 `mac-doctor-Spec.md` 但**没指定章节号**。Codex 在 sandbox read-only 下看到的是 7KB 完整 Spec，但 `suppressions` schema 在 §6 preferences schema 段落，需要 Codex 主动读完整个文件才能找到。
2. **Codex 训练先验** — 大多数 preference/state 系统（macOS plist、user-prefs 类）都用 dict kv 结构存「过期时间」类信息。Codex 默认走「最常见模式」而不是「项目 specific schema」。
3. **Plan 自洽幻觉** — Codex 生成的 6 slice 内部完全自洽（RED test 优雅、impl 简洁、verify_cmd 真实），单看 plan 找不出矛盾——只有和 Spec §6 并排比较才能发现 schema 不一致。
4. **Hermes 审计盲区** — Hermes 收到 plan 后按「6 slice 是否合理 + 是否 RED-first + 行数预算」三个维度审，**漏掉「schema 是否对齐 Spec §6」**这一检查项。

**捕获点**：幸好走 R2.1 澄清协议，CC 第一轮读 Spec 后主动问「Q4: suppressions 是 dict (Codex) 还是 list (Spec)？」——**这是 CC 抓矛盾**，不是 Codex 抓矛盾，也不是 Hermes 抓矛盾。

**结果**：

- Hermes 拍板：选 Spec-list（重写 S5/S6 RED test）
- CC 一次到位实现完整 Spec §6 schema
- 节省一轮 R2.1 讨论 + 一次 CC 实现失败

如果没走 R2.1 / CC 没读 Spec / Hermes 没审 schema 对齐 → **CC 会按 Codex plan 完整复刻 dict 版本实现 preferences.py → 通过 6 个 RED test → Hermes 验收时才发现 DEFAULT.suppressions 和 Spec §6 不符 → 返工**。

---

## 案例 2：mac-doctor v3.0 P3 `triage.py` — 同一次 plan 两次 schema 冲突

**任务**：P3 实现 L3 诊断 LLM agent 入口 `mac-doctor-triage.py`（4 个 TDD slice）

**冲突点（2 处）**：

| 来源 | Schema | 注释 |
|------|--------|------|
| **Spec §2.3（source of truth）** | `memory_write: object {key: 'facts.add\|interpretations.add', value: ...}` | 嵌套对象 |
| **history.db 真实 schema** | `snapshots(id, timestamp, cpu_percent, memory_pressure, swap_used_mb, swap_total_mb, disk_free_gb, disk_total_gb, battery_health, battery_cycles, thermal_throttled, load_avg_1min, load_avg_5min, load_avg_15min, top_cpu_process, top_mem_process)` | 16 列采集快照表 |
| Codex `read_trend` slice 输出 | 表名 `inspections(ts, tool, status, signature, message)` | 假设的「事件表」 |
| Codex `output_schema` slice 输出 | `memory_write: string` | 把 Spec 写的 object 简化成 string |

**为什么 Codex 又错了**：

1. **history.db 表名 + 字段名** — Codex 默认假设一个「事件日志表」（inspections）符合 use case，但实际上 collector 存的是「系统快照表」（snapshots）。Hermes **没亲自验证** history.db 真实 schema（委派包写了路径但没跑 `sqlite3 .schema`），靠 Codex sandbox read-only 自己查 → Codex 偷懒用训练先验。
2. **memory_write 类型** — Codex 按训练先验把 Spec §2.3 的 object 嵌套简化成 string（大多数 LLM 输出规范都是 `field: "string"`）。

**捕获点**：仍然是 CC 在 R2.1 澄清阶段主动识别——

> Q2 by_status 定义：自定义 status 阈值化（cpu>70=abnormal）
> ① S3 build_prompt：选 A（走 load_preferences + 兜底）
> ② memory_write：按 Spec §2.3 用 **object**（不是 Codex 推断的 string）

**结果**：

- Hermes 拍板 S2 用真实 `snapshots` 表 + S3 memory_write 用 object
- CC 在 P3 委派包里读到 Hermes 修正 → 一次到位实现完整 Spec §2.3 schema

### 与 P1 的对比

| 维度 | P1 suppressions | P3 history.db + memory_write |
|------|----------------|------------------------------|
| Codex 错几次 | 1 次 | **2 次**（同一次 plan）|
| Hermes 提前纠正 | ✅ 派 Codex 前已发现 + 写进 CC 委派包 | ❌ 派 Codex 前**未检查 history.db 真实 schema**，靠 CC 澄清补救 |
| 拦截点 | Hermes pre-Codex audit | CC R2.1 澄清 |
| 修复成本 | 0（一次到位）| 中（CC 读修正后委派包） |

**教训**：Hermes pre-Codex audit 必须**逐个 ALLOWED FILES 文件 PRAGMA/head/cat 验证真实 schema**，**不只是信任文件存在**。即使是「用 sandbox read-only 让 Codex 自己查」，也可能在 planning-only 模式下 Codex 偷懒用训练先验。

---

## 案例 3：mac-doctor v3.0 P4 `mac-doctor` CLI — Codex 自标 spec_drift

**任务**：P4 实现 `mac-doctor` 可执行入口（6 subcommand）

**Codex 自报**：
> `spec_drift: "Spec §2.4 只声明 verify 跑 PRD §2.3 七项 checklist，未在 §2.4 列出七项名称；测试应从 PRD §2.3 固定 checklist 名称后再落地。"`

**含义**：Codex 意识到自己**没有** Spec §2.3 的具体内容（PRD §2.3 不在 ALLOWED FILES），所以默认编了 7 个名字（`collector/launchagent/cron_quick/cron_triage/cron_deep/cron_weekly/preferences`）。

**正确做法**（Hermes 已在 prompt 里强调，但应更早）：
- ALLOWED FILES 必须**包含所有相关 source of truth 文件**——Spec / Plan / PRD / DB schema 全部
- Prompt 必显式声明 "READ Spec §X.Y + §Z.A FIRST"（所有相关章节号）
- 不仅是 `Spec.md`（文件整体），必须**精确到章节号**

---

## 通用防御规则（四步）

### ① Plan 审计必查 schema 对齐（Hermes 责任）

Hermes 拿到 Codex plan 后，**逐字段对比** Codex 规划的 DEFAULT/数据结构 vs Spec 章节，**列出所有差异表**：

```markdown
## Codex Plan vs Spec Schema 对齐表

| 字段 | Codex plan | Spec §Y | 一致? |
|------|-----------|---------|:-----:|
| DEFAULT.version | 缺失 | 1 | ❌ 缺 |
| DEFAULT.facts | 缺失 | {known_short_running_tools: [...], ...} | ❌ 缺 |
| DEFAULT.interpretations | list | list | ✅ |
| DEFAULT.suppressions | dict[signature: expires_at] | list[{signature, first_seen, ...}] | ❌ schema 不一致 |
```

**不允许「看起来差不多」「应该对得上」**——任何不一致都列出来。

### ② Hermes 必须亲自验证 source-of-truth 文件 schema

**不只是 ALLOWED FILES 列表里写文件路径**——Hermes 必须**自己跑验证命令**确认真实 schema：

```bash
# 数据库
sqlite3 path/to/db ".schema"   # 或 PRAGMA table_info(table_name)
# JSON/YAML
cat path/to/file | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2)[:500])"
# Markdown
head -50 path/to/spec.md  # 找 schema 相关章节
```

**mac-doctor P3 教训**：Hermes 没验证 history.db 真实 schema，直接靠 Codex sandbox read-only 自己查 → Codex 偷懒用训练先验。

### ③ R2.1 委派包引用 Spec 时必带章节号

ALLOWED FILES 包含 Spec 时，**显式指定章节**：

```markdown
ALLOWED FILES（仅读）:
- ~/Documents/Obsidian/AlexCai/20-Areas/20_技术项目/<proj>/Spec/<proj>-Spec.md
  → **必读 §2.1 模块接口契约 / §6 preferences.json schema**

HARD RULES:
- 以 Spec 为准。Codex 推断若与 Spec 冲突以 Spec 拍板。
- 不许「训练先验」猜 schema——必须以 Spec 实际写法为准。
- 输出 YAML schema 字段若与 Spec 不一致，**必须**用 `spec_drift:` 字段标注（不要静默吞掉）。
```

**这迫使 Codex 在 planning 阶段就把 schema 章节当作 source of truth**，而不是用先验。

### ④ CC 澄清阶段第一问 = schema 对齐确认

CC 接 R2.1 任务后第一轮**必须**输出 schema 对齐清单：

```markdown
## Schema 对齐确认

| 字段 | Codex plan 写法 | Spec §Y 写法 | 一致? |
|------|---------------|------------|:-----:|
| ... | ... | ... | ... |

不一致的字段:
- `suppressions`: Codex=dict[expires_at], Spec=list[{...}] → 选 Spec，理由：____
```

**Hermes 在澄清阶段就拍板 schema**，不要留到实现阶段发现。

---

## Codex plan 模式信号（提前发现 schema 冲突）

如果看到以下模式，**99% 是 schema 推断问题**，需 Schema 对齐：

- [ ] Codex plan 用了「最常见」的 schema（dict kv / flat list / simple struct）
- [ ] Spec 章节里有复杂嵌套 schema（list of dict / 多字段 struct）
- [ ] Spec §X 标题里有「schema」「interface」「contract」「shape」字样
- [ ] Codex plan 的字段名与 Spec 不一致（如 plan 写 `expires_at`，Spec 写 `ttl_hours`）
- [ ] Codex 没在 plan 里显式写「参考 Spec §X」
- [ ] Codex plan 默认假设表名/字段名而不是从文件验证

---

## 配套 Pitfall

cc-tmux SKILL.md **Pitfall #37**：Codex 规划与 Spec 真实契约 schema 不一致，CC 默认按 Codex plan 走导致产出无法验收。

**R2.1 强化要求**（基于 P3 实战）：CC 在实现类 R2.1 任务中，**澄清阶段第一问必须是 schema 对齐确认**（schema 对齐清单 + 不一致字段决策），不要等 Hermes 自己审 plan 时才发现。

---

## 适用场景

- Codex planning-only 模式（任何项目）
- R2.1 澄清式交接流程
- Spec/Plan/PRD 三件套驱动的 STDD 项目
- 任何 schema 复杂（list of dict、nested struct、多字段 contract）的 API/存储层实现

**不适用**：

- 纯 one-shot 简单脚本（无 schema）
- 重构类任务（schema 已有，只动结构）
- 一次性 POC（schema 可由 Codex 自由设计）