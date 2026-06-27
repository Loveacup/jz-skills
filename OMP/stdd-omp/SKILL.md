---
name: stdd-omp
description: |
  STDD methodology skill for Oh My Pi (OMP). Trigger on STDD, Spec-and-Test,
  可证伪验收, 验收驱动, 四步循环 Spec Accept Build Verify, 三梁, 路线图校准
  calibration, 闭环 closed-loop, 无人值守 GOAL, 独立验收 independent audit.
  Runs the full STDD micro-loop inside OMP with objective gates and independent
  auditor wiring.
type: workflow
theme: methodology
best_for:
  - 个人/小团队用 OMP 做需求-验收-实现-验证闭环
  - 需要可证伪验收契约的代码/写作/研究/产品/决策任务
  - 追求 producer≠judge 的独立审计与防漂移交付
scenarios:
  - 新功能/缺陷修复/重构前的需求澄清与验收设计
  - 多 agent 协作任务的委派、审计与收尾
  - L3 无人值守 GOAL 闭环的夜间/后台执行
---

# stdd-omp

在 OMP 内闭环运行 STDD（Spec → Accept → Build → Verify）的个人/小团队方法论。

## 强制入口：自动检测 / 安装模式

每次触发 **必须先运行** `scripts/orchestrate.mjs` 做只读检测，再看结果决定下一步。主路径是 CLI：

```bash
node scripts/orchestrate.mjs
```

在支持本地 ES module 动态导入的环境（如 Node）也可：

```js
const o = await import('file:///path/to/scripts/orchestrate.mjs');
const status = await o.run();
```

`status.actions` 可能包含：

- `install-hook`：opt-in 危险命令 hook 未安装（建议安装）
- `sync-version`：本地版本落后于 GitHub 最新 release（需配置 `STDD_OMP_GITHUB_REPO`，向后兼容 `STDD_OMP_REPO`）
- `warning`：native agent 根目录（默认 `~/.omp/agent/`，可被 `PI_CODING_AGENT_DIR` / `PI_CONFIG_DIR` 覆盖）为空，或 GitHub repo 格式无效

**两阶段纪律**：

1. **status 阶段**：只读检测，**绝不**写文件。
2. **install 阶段**：只有当 `actions` 非空且用户明确同意（`ask`/`resolve`）后，才执行：

   ```js
   await o.installHook();
   // 如需自定义 auditor，再单独调用：await o.installAuditor();
   ```

   或 CLI：

   ```bash
   # 先 dry-run 看会装什么
   node scripts/orchestrate.mjs --install --dry-run
   # 确认后再执行安装
   node scripts/orchestrate.mjs --install
   # 若要覆盖已有文件
   node scripts/orchestrate.mjs --install --force
   ```

## 顶部硬规则区（5 条承重墙）

| 编号 | 规则 | 违反后果 |
|---|---|---|
| P1 可裁决 | 每条验收项必须能判 `true/false`；模糊词必须补判据。 | 不予 Build。 |
| P2 验收不可省 | 没有 Accept 契约，不进入 Build。 | 视为 L0 草稿，不落盘或仅放 Inbox。 |
| P3 证据优先 | 验证证据链：实态 > 测试 > diff > 报告；禁止用推测放行。 | Verify FAIL，回 Build 或回 Spec。 |
| P4 角色分离 | Build 的 executor 不能当 judge；L3 无人值守必须走独立 auditor agent/session。 | 审计结果无效，任务降级为 L2 人审。 |
| P6 终止条件 | 同一任务 regen 硬顶 3、slice 硬顶 2；达到上限必须停并升级人工。沉默 = 失败。 | 自动 block，输出 `counter exceeded max`。 |

## 何时用 / 适用边界

| 档位 | 复杂度 | 特征 | OMP 载体 |
|---|---|---|---|
| L0 | 30 秒内可决定 | 一句话意图，不落地 | 当前 session 口头确认，不落盘 |
| L1 | 小改动 | 影响面 ≤1 文件/模块，改 ≤2 次可收敛 | context-files / `SYSTEM.md` / `.stdd/L1-requirements.md` |
| L2 | 中等 | 跨模块、影响评价指标、需要设计选择 | `assets/three-beams/L2-implementation.md` + plan |
| L3 | 高/无人值守 | 对外交付、夜间 GOAL、多 agent 协作 | `todo` + `plan` + `assets/three-beams/L3-control.md` |

升级触发：改超 2 次仍不过 → L1；影响评价/接口 → L2；对外/无人值守 → L3。
「刚好足够」护栏：能 L1 不 L2，能 L2 不 L3；文档重量与失败成本成正比。

## 四步微循环（OMP 接线）

### ① Spec — 一句话意图

- 只写 What/Why，不写 How。
- L0 可丢弃；长期价值 → 落盘到三梁 L1/L2/L3 文档。
- 工具：直接对话；需要结构化 → `ask` 确认 scope；复杂 L2/L3 → 生成 `plan` 等待 `resolve(apply)`。
- 委托：若可用，调用 `prd-development` / `user-story` / `problem-statement`；否则自写。

### ② Accept — 可证伪验收契约

- 逐条必须能判真假；含模糊词（如「快」「稳定」「优雅」）时补量化判据。
- 人审闸：
  - 值得 plan → `resolve(apply)` 通过 plan；
  - 轻量 → `ask` 让用户确认 checklist。
- L3 无人值守 → 先让独立 auditor 审契约可证伪性。
- 形式库与口诀见 `references/acceptance-forms.md`。

### ③ Build — 最小产出

- 委派 executor：`task` subagent，agent 选 `task` / `oracle` / 自定义角色。
- 约束：不越 scope、不提前抽象、每个产出对应一条验收项。
- 长任务：`async.enabled` + `task.isolation.mode`；完成后发 `irc` turn-done。
- 角色隔离：同任务不要让 executor 自审（P4）。

### ④ Verify — 判真假、 gates、审计、硬顶

- 客观项：用 `scripts/gates.mjs`（`eval` js 导入为主，CLI 为辅）。
- 危险项：匹配 danger patterns → block，升级人工；启用 `assets/stdd-gate.hook.ts` + `tools.approvalMode`。
- 主观项/独立审计：默认 spawn 内置 `reviewer` / `oracle`；可选自定义 `stdd-auditor`（只审不改）。
- regen 计数：`gates.mjs counter --key <task> --kind regen --max 3 --incr`；满 3 停。
- 分支：
  - 全过 → 收尾、回写经验。
  - 不达标 → 回 ③（executor 重试）。
  - 契约错 → 回 ②/①（调整 Spec/Accept）。
  - 满硬顶 → 停，升级人工。

## AI agent 执行指令（可粘贴块）

```text
1. 解析用户意图 → 写一句话 Spec（What/Why，不写 How）。
2. 将 Spec 转译成可证伪 Acceptance checklist（逐条 true/false）。
3. 人审闸：
   - L0/L1：ask 确认 checklist。
   - L2/L3：写成 Plan 工件（.stdd/plan.md 或 L3-control.md：Spec/Accept/Build slices/Verify/Escalation），调用 resolve(apply) 进入 plan 模式。
4. Build：task 委派 executor；默认 isolated=true（失败不污染 workspace），async 长任务，完成发 irc turn-done。
5. Verify：
   - 客观项：eval js 调用 gates.mjs verifyArtifact/verifyTest。
   - 危险项：gates.mjs scanDanger / stdd-gate hook block。
   - 主观项：auditor 读 agent://<id> 输出，独立 reviewer/oracle 审计。
   - 计数：gates.mjs bumpCounter，regen max=3，slice max=2。
6. 全过 → 收尾 + retain/recall 写 memory；不过 → 按分支回退；满硬顶 → 升级人工。

角色模型映射：
- Spec/Plan 用 modelRoles.plan
- Build executor 用 modelRoles.task
- Audit 模型角色用 `modelRoles.advisor`；agent 可用 `reviewer`/`oracle`
```

## 最大化 OMP 机制（推荐配置）

| STDD 步骤 | OMP 机制 | 用法 |
|---|---|---|
| Spec+Accept | Plan 工件 + `resolve(apply)` | L2/L3 写成 `.stdd/plan.md` 或 `L3-control.md`，分节：Spec/Accept/Build slices/Verify/Escalation |
| Build | `task` + `isolated: true` + `async.enabled` | L2/L3 默认隔离执行，失败不污染父 workspace |
| 完成信号 | `irc send` / `irc wait` / `send await:true` | executor turn-done；coordinator 超时未收 = 失败 |
| 审计 | `reviewer`/`oracle` + `agent://<id>` | auditor 读 executor 输出 artifact，不看自辩；模型角色用 `advisor` |
| 模型选择 | `modelRoles` | Spec=plan，Build=task，Audit=advisor |
| 经验回写 | `memory.backend: local` + `retain`/`recall` | 全过后写经验，后续任务先 recall |
| Web 验收 | `browser` | E2E 断言加入 Acceptance checklist |

推荐 `~/.omp/agent/config.yml`：

```yaml
memory:
  backend: local
modelRoles:
  plan: anthropic/claude-sonnet-4:medium
  task: openai/gpt-5.5:medium
  advisor: anthropic/claude-sonnet-4:high
tools:
  approvalMode: write
  approval:
    bash: prompt
    edit: prompt
    write: prompt
task:
  isolation:
    mode: auto
  async:
    enabled: true
```

## plan / todo / task / irc 协同接线

| 场景 | 工具组合 |
|---|---|
| Spec+Accept 人审 | Plan 工件（`.stdd/plan.md` 或 `L3-control.md`）+ `resolve(apply)`；轻量用 `ask` |
| 任务分阶段 | `todo`：父 agent 用 `init`/`start`/`done`，文本精确匹配；子代理不继承 todo |
| 委派 Build | `task` batch：agent=`task`/`oracle`；`isolated: true` 默认开；async 长任务 |
| 完成信号 | `irc` send turn-done；等待方用 `irc wait` 或 `send await:true`；超时无响应 = 失败 |
| 审计独立 | auditor 必须不含 `edit`/`write`；默认用内置 `reviewer`/`oracle`，读取 `agent://<id>`；可选 `stdd-auditor` |
| P0 单点 vs P1 批处理 | P0：单 executor → 自审/他审；P1：批量 task → 全部 turn-done → 一次性 auditor |

## 三梁项目骨架

- L1 Requirements：`assets/three-beams/L1-requirements.md` 模板，Context Pyramid 顶层。
- L2 Implementation：`assets/three-beams/L2-implementation.md` 模板，设计决策与影响面。
- L3 Control：`assets/three-beams/L3-control.md` 模板，任务切片、审计链、退出条件。
- 路线图是派生投影，不是独立梁；每次变更必须同步回三梁。
- 详细纪律见 `references/three-beams.md`。

## 委托 skill / worker

- 需求/PRD：`prd-development`
- 用户故事：`user-story`
- 问题陈述：`problem-statement`
- 调研：`web_search` + `agent-reach`
- 澄清/对赌：`ask` / `oracle`
- 若对应 skill 不可用，降级为自写，不阻塞流程。

## 经验回写

- 全过后，用 memory backend `local` 写一行经验：本次任务类型、成功关键、踩坑点。
- 可调用 `retain` / `recall` / `reflect` Hindsight tools（如启用）。

## References

- `references/acceptance-forms.md` — 跨项目类型验收形式库。
- `references/macro-calibration.md` — 宏循环五步（审查→分级→委派→审核→收尾）。
- `references/three-beams.md` — 三梁骨架与防变重护栏。
- `references/agent-roles.md` — P4 角色绑定与 auditor 配置。
- `references/omp-integration.md` — STDD 与 OMP 机制完整映射。
- `references/advanced-omp-wiring.md` — eval/TTSR/Advisor/LSP/DAP/Browser 等高价值能力接线。
- `references/goal-loop.md` — L3 无人值守 GOAL 闭环。
- `references/gates.md` — `gates.mjs` 调用、退出码、hook 安装、危险模式表。
- `assets/INSTALL.md` — OMP 安装与跨 OS 说明。

## Cross-OS note

- 门控脚本 `scripts/gates.mjs` 是单一 ES module，纯 Node/Bun `fs`/`child_process`，无 shell builtin。
- 主入口为 OMP `eval` js（Bun VM），win/mac/Linux 行为一致，不依赖 PATH。
- CLI fallback：`node scripts/gates.mjs ...` 或 `bun scripts/gates.mjs ...`。
- 路径全部使用 `~` / `skill://` / cwd-relative `.stdd/`，OMP 会按 OS 解析（Windows 下 `~` = `%USERPROFILE%`）。
