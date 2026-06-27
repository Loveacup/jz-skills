# STDD-OMP 与 OMP 机制映射

本页把 STDD 的每一步落在 OMP 的具体机制上，便于在编写/调试时直接对应。

## 当前已利用的 OMP 能力

| STDD 概念 | OMP 机制 | 当前用法 |
|---|---|---|
| Spec+Accept 人审 | `resolve` + `ask` | L2/L3 用 plan 文件 + `resolve(apply)`；轻量用 `ask` |
| Build 执行 | `task` subagent | `agent: task` / `oracle`，batch/`async`/`isolation` |
| 阶段追踪 | `todo` | 父 agent 维护 phase/task，子代理不继承 |
| 多 agent 协作 | `irc` | executor turn-done，coordinator `irc wait` |
| 独立审计 | `reviewer` / `oracle` | 默认 auditor，P4 角色分离 |
| 客观验证 | `eval` js + `gates.mjs` | 跨 OS 门控 |
| 危险拦截 | hook (`tool_call`) | `stdd-gate.ts` 预拦截 |
| 版本/安装自检 | `bash`/`node` CLI | `orchestrate.mjs` |
| 经验回写 | `memory.backend: local` | 推荐配置，全过后写经验 |

## 仍可深挖的高价值能力

### 1. Plan 模式 / Plan 工件（Spec+Accept 的正式载体）

OMP 的 plan 模式会在存在待审批 plan 文件时切换提示词，强制按章节修订。

- L2/L3 的 Spec+Accept 不应只停留在对话，应写成 **plan 工件**（如 `.stdd/plan.md` 或 `L3-control.md`）。
- 用 `resolve(apply)` 让人审通过；通过后进入 plan 模式执行。
- plan 文件建议分节：`Spec` / `Accept` / `Build slices` / `Verify gates` / `Escalation`。

### 2. Task 隔离（Build 的沙箱化）

`task.isolation.mode` 支持 `auto/apfs/btrfs/overlayfs/projfs/...`，让 executor 在 copy-on-write workspace 里跑。

- L2/L3 Build 推荐启用 `isolated: true`。
- 隔离后 executor 的改动以 patch/branch 形式返回；**Verify 全过再合并**，失败则丢弃 patch。
- 这与 STDD 的“证据优先、失败回退”天然匹配。

### 3. modelRoles / thinkingLevel（为不同角色选模型）

OMP 内置 model roles：`default`、`smol`、`slow`、`vision`、`plan`、`designer`、`commit`、`title`、`task`、`advisor`。

| STDD 角色 | 推荐 modelRole | 说明 |
|---|---|---|
| Spec / Plan | `plan` | 长程规划、结构化输出 |
| Build executor | `task` | 执行导向 |
| 审计 | `advisor` | 审慎、少改动；审计 agent 可用 `reviewer`/`oracle` |
| 快速验证/计数 | `smol` | 便宜、低延迟 |
| 复杂设计 | `slow` 或 `plan:high` | 深度推理 |

可在 `config.yml` 配置：

```yaml
modelRoles:
  plan: anthropic/claude-sonnet-4:medium
  task: openai/gpt-5.5:medium
  advisor: anthropic/claude-sonnet-4:high
```

### 4. `agent://<id>` / `history://<id>`（审计链可追溯）

- executor 完成后，输出写入 `agent://<TaskId>`；auditor 直接读取该 artifact 做审计。
- coordinator 可用 `history://<TaskId>` 查看 executor 完整轨迹，而不必重新询问。
- 这比让 executor 自报结果更可靠（P3 证据优先）。

### 5. `irc` 的 `await: true` 与 `inbox`

- executor 完成时发 `irc send`；coordinator 用 `irc wait` 或 `send ... await: true` 阻塞等信号。
- 多 executor 并行时，用 `irc inbox`  drain 所有完成消息再统一 audit。
- 超时按 `irc.timeoutMs`（默认 120s），超时应视为失败（沉默即失败）。

### 6. Memory / Hindsight（经验闭环）

- 启用 `memory.backend: local` 后，每次全过的任务可用 `retain` 写一条经验。
- 后续同类任务开头用 `recall` / `reflect` 读取历史经验，作为 Spec 输入。
- memory 自动生成的 skill playbook 也可被当前 skill 引用。

### 7. Browser E2E（验收形式扩展）

对 Web 项目，验收项可加入 browser 工具：

- `tab.goto(url)` → 页面可访问
- `tab.waitForSelector(...)` → 元素出现
- `tab.evaluate(...)` → 前端状态断言

### 8. eval 工作流 / TTSR / Advisor / LSP / DAP / Browser（高级验证）

详见 `references/advanced-omp-wiring.md`。要点：

- **eval**：把 `gates.mjs` 校验串成可复现脚本；复杂任务可尝试并行/流水线（先测试再使用）。
- **TTSR / Rules**：把 STDD 承重墙写成 `~/.omp/agent/rules/*.md` 系统规则；`alwaysApply` 已在本机验证，stream 触发 schema 需先测试。
- **Advisor + WATCHDOG.md**：启用 `advisor` modelRole，复制 `assets/WATCHDOG.md` 到 `~/.omp/agent/WATCHDOG.md`，让 Advisor 每回合审查 P1-P6。
- **LSP / DAP / Browser**：把类型检查、调试器状态、浏览器 E2E 作为验收证据，扩展 P3 客观验证面。

### 9. Hook 的 `tool_result` 后处理（可选增强）

当前 hook 只拦截 `tool_call`。可扩展为：

- `tool_result` 阶段自动把 `gates.mjs` 的 verify 结果写入 `.stdd/gate-log.jsonl`。
- `session_start` 时打印 STDD 状态摘要。
- 这些属于进阶，保持可选。

## 推荐的最小强化配置

在 `~/.omp/agent/config.yml`：

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

> **OMP 配置写法/密钥/provider/profile 细节** 见 **`/skill:omp-ops`**。本页只列出 STDD 流程所需的最小键。

## 与 SKILL.md 的对应

- `SKILL.md` 的“四步微循环”已按上表接线；
- 本节作为底层机制参考，供调试和扩展时查阅。
