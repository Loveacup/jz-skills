---
name: stdd-omp
description: |
  STDD methodology skill for Oh My Pi (OMP). Trigger on STDD, Spec-and-Test,
  可证伪验收, 验收驱动, 四步循环 Spec Accept Build Verify, 三梁, 路线图校准
  calibration, 闭环 closed-loop, 无人值守 GOAL, 独立验收 independent audit,
  角色编排, 协调者, 测试者, full-auto, 人只输入需求, 临时专家, 证据阶梯,
  夹逼放行, claimcheck, 反幻觉, 上游真相校准, 量化档, advisor 委员会.
  Runs the full STDD micro-loop inside OMP with objective gates and independent
  auditor wiring.
type: workflow
theme: methodology
best_for:
  - 个人/小团队用 OMP 做需求-验收-实现-验证闭环
  - 需要可证伪验收契约的代码/写作/研究/产品/决策任务
  - 追求 producer≠judge 的独立审计与防漂移交付
  - full-auto 人只输入需求、夜间无人值守自动闭环
scenarios:
  - 新功能/缺陷修复/重构前的需求澄清与验收设计
  - 多 agent 协作任务的委派、审计与收尾
  - L3 无人值守 GOAL 闭环的夜间/后台执行
  - 6 角色编排、full-auto 自动编译 GOAL+发出+监督
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
- `sync-version`：本地版本落后于 GitHub 最新 release（默认读取 `Loveacup/jz-skills`，可用 `STDD_OMP_GITHUB_REPO` 覆盖，向后兼容 `STDD_OMP_REPO`）
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
| P4 角色分离 | 执行 agent ≠ 评估 agent；L3/无人值守必须独立 auditor。独立性两维：①上下文独立（换 session/子 agent）②模型/视角独立（换 modelRole/模型）；同模型 fresh 子 agent 只买①，碰核心状态权威/并发安全/会静默崩塌的判定须叠②或用 P3 实态兜底。 | 审计结果无效，任务降级为人审。 |
| P6 终止条件 | 同一任务 regen 硬顶 3、slice 硬顶 2；达到上限必须停并升级人工。沉默 = 失败。 | 自动 block，输出 `counter exceeded max`。 |

## 何时用 / 适用边界

| 档位 | 复杂度 | 特征 | OMP 载体 |
|---|---|---|---|
| L0 | 30 秒内可决定 | 一句话意图，不落地 | 当前 session 口头确认，不落盘 |
| L1 | 小改动 | 影响面 ≤1 文件/模块，改 ≤2 次可收敛 | context-files / `SYSTEM.md` |
| L2 | 中等 | 跨模块、影响评价指标、需要设计选择 | plan + 梁2 中枢 |
| L3 | 高/无人值守 | 对外交付、夜间 GOAL、多 agent 协作 | `todo` + `plan` + 梁3 控制面 |
升级触发：改超 2 次仍不过 → L1；影响评价/接口 → L2；对外/无人值守 → L3。
「刚好足够」护栏：能 L1 不 L2，能 L2 不 L3；文档重量与失败成本成正比。


## 角色编排（6 内建 + 临时专家，OMP 单-CLI 映射）

| 角色 | 职责 | OMP 单-CLI 载体（优先 bundled） |
|---|---|---|
| 协调者 coordinator | 面向你的唯一入口：接需求→定角色→grill→编译 GOAL→发出→收口；纯路由 | OMP 主 session（`Main`），你只跟它对话 |
| 编排者 orchestrator | 拆解、派单、汇总、再规划 | 主 agent + bundled `plan`（规划）；`task` batch fan-out / `eval` `agent()`/`pipeline()`/`parallel()` |
| 执行者 executor | 工作单元内执行、自验、上抛证据句柄 | bundled `task`/`oracle`（轻量 `quick_task`），`isolated` 返回 patch |
| 测试者 tester | 动态跑、拿运行时证据（exit code/落盘/日志） | `eval`+`gates.mjs verifyTest` / `bash` / `browser` / `debug` / `lsp diagnostics`（需子代理跑则 bundled `task`/`quick_task`） |
| 审核者 auditor | 凭证据静态复算、三态裁决、审执分离 | **同步审**：bundled `reviewer`/`oracle`（+可选自定义 `stdd-auditor`），读 `agent://<id>`/`history://<id>`；**回合级审**：v3 `WATCHDOG.yml` 多 advisor 委员会（16.2.3，per-advisor 跨模型=P4 第二维）/ 单 `WATCHDOG.md`（≤16.2.2 回退） |
| 发布者 publisher | 收口 commit/tag/push（确认≠执行） | 主 agent 手动收口，受 `stdd-gate.hook.ts` danger 门 + approval 拦截 |

**第一动作：要不要起角色**——判据：
- L0/L1 或 ≤2 步/单文件/可逆 → 不起角色，执行者身份切换自审。
- L2+/≥3 步/改≥3 文件/需独立审/需并行/不可逆 → 起最小角色组 协调者+执行者+审核者。

**角色优先复用 bundled 子代理**：调研/只读审 → `explore`、检索/文档 → `librarian`、UI → `designer`、复核 → `reviewer`/`oracle`、执行 → `task`/`oracle`/`quick_task`、规划 → `plan`。**Bundled 无一覆盖才起临时专家**（自定义 ad-hoc agent 放 `~/.omp/agent/agents/<name>.md`，同 stdd-auditor 机制，frontmatter `tools`/`spawns`=能力声明即契约，声明不出=不起）。Fork-bomb 红线用 OMP 既有键 enforce：`task.maxConcurrency`（并发上限）+ `task.maxRecursionDepth`（递归 depth 硬顶）+ `task.maxRuntimeMs`（超时 kill）+ spawn 策略（`spawns`/`task.disabledAgents`/`PI_BLOCKED_AGENT`）；用完即弃 = `task.agentIdleTtlMs` idle-park。

协调者起手跑启动对齐清单（见 `references/agent-roles.md`），逐维钉死再进四步循环。

## 四步微循环（OMP 接线）
### ① Spec — 一句话意图

- 只写 What/Why，不写 How。
- L0 可丢弃；长期价值 → 落盘到 梁1/梁2/梁3 文档。
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

- **客观项**：用 `scripts/gates.mjs`（`eval` js 导入为主，CLI 为辅）。
- **危险项**：匹配 danger patterns → block，升级人工；启用 `assets/stdd-gate.hook.ts` + `tools.approvalMode`。
- **主观项/独立审计**：默认 spawn 内置 `reviewer` / `oracle`；可选自定义 `stdd-auditor`（只审不改）。
- **证据阶梯**：parse（`lsp diagnostics` 0 error）→ resolve（`lsp references`/`grep` 旧符号归零）→ live（`eval`/`bash`/`browser`/`debug` 真跑）；档越高→越往上爬。详见 `references/verify-evidence.md`。
- **夹逼放行第三态**：终态不可观测时沿阶梯爬到可行上限，两端夹逼（配置端+运行端）+ 缺口留账 + 论断降格；缺一退回沉默即失败。
- **claimcheck 反幻觉门**：verdict 必带可定位证据锚（file:line/exit code/agent://<id>）；不可锚率 >40% 整轮重跑；无人值守强制开。
- **软/硬失败两态**：硬失败 regen 达 3 → 停升级；软失败 → 降级放行 + 低置信度 + 不阻塞下游；沉默即失败 + 心跳（`irc` 进度，`2×心跳间隔` 无更新=卡死→重派）。
- regen 计数：`gates.mjs counter --key <task> --kind regen --max 3 --incr`；满 3 停。
- 分支：
  - 全过 → 收尾、回写经验。
  - 不达标 → 回 ③（executor 重试）。
  - 契约错 → 回 ②/①（调整 Spec/Accept）。
  - 满硬顶 → 停，升级人工。


## full-auto 档（人只输入需求）+ GOAL 落地

**人闸退为 escalation-only**：②Accept 人闸只在命中升级四条（同一单元打回 2 次 / 架构偏移 / 不可逆操作 / 验收写不出）时才回到你。
三重补偿：
1. 独立性两维（P4）
2. 证据阶梯爬高（P3）
3. 终止硬顶 + 沉默即失败（P6）

**GOAL 落地**：
- 谁发：协调者（主 session）。
- 哪一步：②Accept 定稿后、③Build 前。
- 编译「意图+验收契约」成 GOAL（criterion/verifier/threshold 三元组 + 角色绑定 + deny list + 升级四条）。
- OMP 无 `/goal` → `async task` + `todo` + `gates.mjs` + `irc` 自收敛（详见 `references/goal-loop.md`）。
- 手动 vs 自动：交互档 = 编好你点确认再发，full-auto = 自动编译+发出+监督。


> **🔧 Harness 视角提醒**：agent 犯同类错 → 改 harness（加验收项/收紧承重墙/调低再生硬顶/收紧人审 gate），不责备模型。核心承重墙不依赖 OMP 原语表的具体名称，后者过期更新即可。

## AI agent 执行指令（可粘贴块）

```text
1. 解析用户意图 → 写一句话 Spec（What/Why，不写 How）。
2. 将 Spec 转译成可证伪 Acceptance checklist（逐条 true/false）。
3. 人审闸：
   - L0/L1：ask 确认 checklist。
   - L2/L3：写成 Plan 工件（`.stdd/plan.md` 或 `beam3-control.md`：Spec/Accept/Build slices/Verify/Escalation），调用 resolve(apply) 进入 plan 模式。
4. Build：task 委派 executor；默认 isolated=true（失败不污染 workspace），async 长任务，完成发 irc turn-done。
5. Verify：
   - 客观项：eval js 调用 gates.mjs verifyArtifact/verifyTest。
   - 危险项：gates.mjs scanDanger / stdd-gate hook block。
   - 主观项：auditor 读 agent://<id> 输出，独立 reviewer/oracle 审计。
   - 计数：gates.mjs bumpCounter，regen max=3，slice max=2。
6. 全过 → 收尾 + memory 回写（`autolearn` 自动沉淀，读 `memory://root`）；不过 → 按分支回退；满硬顶 → 升级人工。

角色模型映射：
- Spec/Plan 用 modelRoles.plan
- Build executor 用 modelRoles.task
- Audit 模型角色用 `modelRoles.advisor`；agent 可用 `reviewer`/`oracle`
```

## 最大化 OMP 机制（推荐配置）

| STDD 步骤 | OMP 机制 | 用法 |
|---|---|---|
| Spec+Accept | Plan 工件 + `resolve(apply)` | L2/L3 写成 `.stdd/plan.md` 或 `beam3-control.md`，分节：Spec/Accept/Build slices/Verify/Escalation |
| Build | `task` + `task.isolation.mode` + `task.async.enabled` | L2/L3 默认隔离执行，失败不污染父 workspace |
| 完成信号 | `irc send` / `irc wait` / `send await:true` | executor turn-done；coordinator 超时未收 = 失败 |
| 审计 | `reviewer`/`oracle` + `agent://<id>` | auditor 读 executor 输出 artifact，不看自辩；模型角色用 `advisor` |
| 模型选择 | `modelRoles` | Spec=plan，Build=task，Audit=advisor |
| 经验回写 | `memory.backend: local` + `autolearn.enabled: true` | 自动沉淀，读 `memory://root`（`retain`/`recall` 需 `hindsight`/`mnemopi`） |
| Web 验收 | `browser` | E2E 断言加入 Acceptance checklist |

> **OMP 配置细节**（modelRoles、providers、API keys、search、profiles、`config.yml` 层级等）见 **`/skill:omp-ops`**。stdd-omp 给出推荐值，具体写法/密钥管理让 omp-ops 处理。

推荐 `~/.omp/agent/config.yml`：

```yaml
memory:
  backend: local
autolearn:
  enabled: true
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
| Spec+Accept 人审 | Plan 工件（`.stdd/plan.md` 或 `beam3-control.md`）+ `resolve(apply)`；轻量用 `ask` |
| 任务分阶段 | `todo`：父 agent 用 `init`/`start`/`done`，文本精确匹配；子代理不继承 todo |
| 委派 Build | `task` batch：agent=`task`/`oracle`；`task.isolation.mode` 默认开；async 长任务 |
| 完成信号 | `irc` send turn-done；等待方用 `irc wait` 或 `send await:true`；超时无响应 = 失败 |
| 审计独立 | auditor 必须不含 `edit`/`write`；默认用内置 `reviewer`/`oracle`，读取 `agent://<id>`；可选 `stdd-auditor` |
| P0 单点 vs P1 批处理 | P0：单 executor → 自审/他审；P1：批量 task → 全部 turn-done → 一次性 auditor |

## 三梁项目骨架

- 梁1 Requirements：`assets/three-beams/beam1-requirements.md` 模板，Context Pyramid 顶层。
- 梁2 Implementation：`assets/three-beams/beam2-implementation.md` 模板，设计决策与影响面。
- 梁3 Control：`assets/three-beams/beam3-control.md` 模板，任务切片、审计链、退出条件。
- 路线图是派生投影，不是独立梁；每次变更必须同步回三梁。
- 详细纪律见 `references/three-beams.md`。

## 委托 skill / worker

- 需求/PRD：`prd-development`
- 用户故事：`user-story`
- 问题陈述：`problem-statement`
- 调研：`web_search` + `agent-reach`
- 澄清/对赌：`ask` / `oracle`
- **OMP 配置/密钥/模型/搜索 provider / profile：调用 `/skill:omp-ops`**
- 若对应 skill 不可用，降级为自写，不阻塞流程。

## 经验回写

默认路径：`memory.backend: local` + `autolearn.enabled: true`。
- 后台自动抽取 → 停止时沉淀，启用 `manage_skill`/`learn` 工具，落 `~/.omp/agent/managed-skills`。
- 读经验：`read memory://root`（或 `/memory view`）。
- 可选路径：`memory.backend: hindsight`|`mnemopi` → 可用 `retain`/`recall`/`reflect`（`local` 后端不支持）。

## References
- `references/verify-evidence.md` — 证据阶梯/夹逼放行/claimcheck/软硬失败。

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
