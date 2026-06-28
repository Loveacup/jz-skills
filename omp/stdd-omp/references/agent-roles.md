# STDD-OMP Agent 角色绑定

## 6 角色（OMP 单-CLI 映射，优先 bundled）

| 角色 | 职责 | OMP 单-CLI 载体（优先 bundled） |
|---|---|---|
| 协调者 coordinator | 面向你的唯一入口：接需求→定角色→grill→编译 GOAL→发出→收口；纯路由 | OMP 主 session（`Main`），你只跟它对话 |
| 编排者 orchestrator | 拆解、派单、汇总、再规划 | 主 agent + bundled `plan`（规划）；`task` batch fan-out / `eval` `agent()`/`pipeline()`/`parallel()` |
| 执行者 executor | 工作单元内执行、自验、上抛证据句柄 | bundled `task`/`oracle`（轻量 `quick_task`），`isolated` 返回 patch |
| 测试者 tester | 动态跑、拿运行时证据（exit code/落盘/日志） | `eval`+`gates.mjs verifyTest` / `bash` / `browser` / `debug` / `lsp diagnostics`（需子代理跑则 bundled `task`/`quick_task`） |
| 审核者 auditor | 凭证据静态复算、三态裁决、审执分离 | **同步审**：bundled `reviewer`/`oracle`（+可选自定义 `stdd-auditor`），读 `agent://<id>`/`history://<id>`；**回合级审**：v3 `WATCHDOG.yml` 多 advisor 委员会（16.2.3，per-advisor 跨模型=P4 第二维）/ 单 `WATCHDOG.md`（≤16.2.2 回退） |
| 发布者 publisher | 收口 commit/tag/push（确认≠执行） | 主 agent 手动收口，受 `stdd-gate.hook.ts` danger 门 + approval 拦截 |

## P4：Producer ≠ Judge（独立性两维）

执行 agent ≠ 评估 agent；L3/无人值守必须独立 auditor。

**独立性两维**：
1. **上下文独立**（换 session/子 agent，OMP task 子 agent 天然不继承历史）
2. **模型/视角独立**（auditor 用不同 modelRole/provider，或 WATCHDOG.yml 委员会 per-advisor 跨模型）

同模型 fresh 子 agent 只买①；碰核心状态权威/并发安全/会静默崩塌的判定须叠②或用 P3 实态兜底。

OMP 手册校准正例：爬 config get → lsp → 真跑 当 ground truth（不是模型记忆/文档声称）。

## 审核独立性三级

| 级别 | 做法 | 适用 | 判据 |
|---|---|---|---|
| 自审 | executor 完成后快速自检 | L0/L1 草稿 | 改一行过时文档自审够 |
| 净 session 审 | 新 session 只读审计 | L2 任务 | 中等复杂度 |
| 独立 auditor 审 | `task agent:reviewer` / `oracle` / 可选 `stdd-auditor` | L3 / GOAL | 核心状态权威/并发安全须独立 auditor 审 |

## 角色→bundled 子代理映射 + 临时专家 + fork-bomb 控制

**角色优先落到 bundled 子代理**：
- 调研/只读审 → `explore`
- 检索/文档 → `librarian`
- UI → `designer`
- 复核/审计（同步）→ `reviewer`/`oracle`
- 执行 → `task`/`oracle`/`quick_task`
- 规划 → `plan`

**临时专家**（bundled 无覆盖才起）：
- 自定义 ad-hoc agent 放 `~/.omp/agent/agents/<name>.md`
- 同 `stdd-auditor` 机制
- Frontmatter `tools`/`spawns` = 能力声明即契约，声明不出 = 不起

**Fork-bomb 红线**（OMP既有键 enforce）：
- `task.maxConcurrency` — 并发上限
- `task.maxRecursionDepth` — 递归 depth 硬顶
- `task.maxRuntimeMs` — 超时 kill
- Spawn 策略：`spawns` / `task.disabledAgents` / `PI_BLOCKED_AGENT`
- 用完即弃：`task.agentIdleTtlMs` idle-park

## 动态发现 + 自定义覆盖

OMP 按名称动态发现 agent。默认 auditor 是内置 `reviewer`/`oracle`。

可选增强：若把 `assets/stdd-auditor.agent.md` 复制到 `~/.omp/agent/agents/stdd-auditor.md`，
可用 `task agent:stdd-auditor` 替代 reviewer/oracle，获得更聚焦的审计角色。

如果 auditor 缺失：
- L1/L2：用 `oracle` 或 `reviewer`。
- L3：必须有独立 auditor（reviewer/oracle 或 stdd-auditor）；缺失则任务不能进入无人值守。

## 隔离防冲突

- 同任务不要让 executor 在完成后立即自审。
- 多 executor 并行时启用 `task.isolation.mode`。
- auditor 应在干净上下文或独立 session 中运行。

## Advisor 委员会（v3，审核者回合级载体，16.2.3 已部署）

`WATCHDOG.yml` 双 advisor 架构（详见 `assets/WATCHDOG.yml`）：

| Advisor | Slug | 模型 | 镜头 | STDD 承重墙覆盖 |
|---|---|---|---|---|
| Reviewer | `reviewer` | Codex auto-review:medium | 宽镜头：14 条规则全科审查 | P1–P6 全覆盖（scope shrinkage/P3 fake verification/MUST-NEVER/tool audit/delivery） |
| Claim Verify | `claim-verify` | DeepSeek V4 Flash | 窄镜头：声称核实（交付类+事实类） | P3 claimcheck（声称 vs 证据独立核对，≤2 条/轮 concern only） |

**Per-advisor 跨模型（Codex + DeepSeek，不同家族）= P4 第二维「模型/视角独立」**。Refute-or-Promote 实证跨模型交叉验证多发现 ~3% 同族遗漏。Reviewer: blocker/concern/nit；Claim Verify: concern only，与 reviewer 去重。

`advisor.enabled: true`、`advisor.subagents: false`、`advisor.syncBacklog` 默认 3。`retry.fallbackChains.advisor` 降级链。Chair 不部署（advisor 间不通信）。

单 `WATCHDOG.md` = ≤16.2.2 回退。

## 三级门控

| 级别 | 配置 | 效果 |
|---|---|---|
| 只读 | `tools.approvalMode: always-ask` | 每个 tool_call 都问 |
| 写入 | `tools.approvalMode: write` + `tools.approval.bash: ask` | 写入/危险工具需确认 |
| 危险 | hook + approval 双重拦截 | 危险命令 block |

```yaml
tools:
  approvalMode: write
  approval:
    bash: ask
    edit: ask
    write: ask
```

## modelRoles 映射

| STDD 角色 | OMP modelRole | 用途 |
|---|---|---|
| Spec / Plan / Accept | `plan` | 结构化规划、长程思考、生成 Plan 工件 |
| Build executor | `task` | 执行导向、代码/写作产出 |
| 审计 / 顾问 | `advisor` | 审慎判断、少改动、独立评估；agent 可用 `reviewer`/`oracle` |
| 快速检查 | `smol` | 轻量、低成本、短延迟 |
| 轻量任务 | `tiny`（16.2.2+） | 更轻量、更低成本 |
| 深度难题 | `slow` / `plan:high` | 复杂设计、需要深度推理 |

示例 `~/.omp/agent/config.yml`：

```yaml
memory:
  backend: local
autolearn:
  enabled: true

modelRoles:
  plan: anthropic/claude-sonnet-4:medium
  task: openai/gpt-5.5:medium
  advisor: anthropic/claude-sonnet-4:high
```

## Profile / modelRoles 隔离

- `omp --profile stdd` 只迁移 native lane；agents lane `~/.agents/skills/` 不动。
- 可为 auditor 使用 `advisor` 模型角色（即 `modelRoles.advisor`），避免与 executor 同模型/同 session。

## 启动对齐清单（协调者 grill 8 维）

协调者起手跑此清单，逐维钉死再进四步循环。

| # | 维度 | 检查项 |
|---|---|---|
| 1 | 需求&验收 (P1/P2) | 意图是否可证伪？验收契约是否逐条 true/false？ |
| 2 | 角色 (P4) | 需要哪些角色？是否独立 auditor？独立性一维或两维？ |
| 3 | 档位&自动度 (L0–L3/full-auto) | 任务强度 L 档？交互 or full-auto？升级触发条件？ |
| 4 | 技术文档目录/三梁落点 | 梁1/梁2/梁3 落哪个文件？路线图如何派生？ |
| 5 | 溯源 | 核心数据/API/schema 在哪个权威源？版本号？ |
| 6 | skill 嵌入 | 需要调用哪些 skill？（prd-development / agent-reach / omp-ops …） |
| 7 | 边界&门 (P4/P6) | regen/slice 硬顶、danger 清单、不可逆操作红线 |
| 8 | 样板登记 | 是否存在可复用的历史 GOAL/验收模板？ |

纪律：能查代码库/已有文档自答的不问你，只把真分叉抛你（交互档）或自核留痕（full-auto）。
