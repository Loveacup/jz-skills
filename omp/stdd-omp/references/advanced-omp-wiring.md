# STDD-OMP 高级 OMP 能力接线

把 OMP 的 `eval` workflow、TTSR、Advisor+WATCHDOG、LSP/DAP/Browser 等高价值能力，映射到 STDD 的四步微循环与承重墙。

## eval 工作流 → Verify / Build 编排

OMP `eval` 是持久化代码内核，适合把多步客观校验写成可复现脚本。

| STDD 步骤 | eval 用法 | 收益 |
|---|---|---|
| Verify（客观项） | `eval js` import `scripts/gates.mjs` | 跨 OS、无 PATH 依赖、结果可判定 |
| Verify（多维度并行） | 并行跑多个 `gates.mjs` 校验 | 缩短验证时间 |
| Build（多阶段流水线） | 在 `eval` 中用代码编排多阶段（读取→处理→校验） | 数据→处理→产物 可追踪 |
| full-auto 编排 | `eval` `agent()` / `parallel()` / `pipeline()` / `completion()` | verdict 路由、多 slice 并发 |

**最小兼容路径**：

```js
const g = await import('file:///path/to/scripts/gates.mjs');
const artifact = g.verifyArtifact('dist/app.js');
const test = g.verifyTest('node -e "process.exit(0)"');
const danger = g.scanDanger('git push');
```

`agent()` / `parallel()` / `pipeline()` / `completion()` 是 OMP `eval` 内置助手（手册 §5）。

## TTSR / Rules → 动态规则墙

OMP 支持规则文件（`~/.omp/agent/rules/*.md` 或 `.omp/rules/`），通过 YAML frontmatter 控制生效。

**已验证的 TTSR schema**（OMP 手册 §15）：

```yaml
---
name: stdd-evidence-guard
condition: "(应该过了|大概没问题|probably (fine|passes)|seems to pass)"
repeatMode: after-gap
---
证据缺失 = 不通过。请补 file:line / exit code / agent://<id> 证据锚。
```

规则 frontmatter 键：
- `name` — 规则名
- `condition` — 正则（stream token 触发）
- `astCondition` — ast-grep 模式（元变量同名须一致）
- `repeatMode: once|after-gap` — 触发策略
- 全局：`ttsr.enabled` / `ttsr.builtinRules` / `ttsr.disabledRules` / `ttsr.contextMode: keep|discard`

**STDD token 级 TTSR 规则示例**：

① P3 推测放行词：
```yaml
---
name: stdd-P3-guess-guard
condition: "(应该过了|大概没问题|probably (fine|passes)|seems to pass)"
repeatMode: after-gap
---
证据缺失 = 不通过。用 gates.mjs verify / lsp / debug / browser 补证据锚。
```

② P2/缩范围：
```yaml
---
name: stdd-P2-scope-creep
condition: "(scaffold|MVP|v1|占位|stub).{0,12}(完成|done|交付)"
repeatMode: after-gap
---
不缩范围/不虚报完成。未达验收项判失败。
```

③ danger 文本兜底（与 `stdd-gate.hook.ts` 互补）：
```yaml
---
name: stdd-danger-text
condition: "(git push.{0,10}force|rm -rf|DROP TABLE)"
repeatMode: after-gap
---
危险操作！需 hook/approval 确认。
```

**规则生效需要 `ttsr.enabled: true`（默认 off）**。`alwaysApply` 规则为常驻基线（`assets/stdd-rules/*.md`），TTSR 为零税补充，并存不互替。

## Advisor + WATCHDOG（v3 双 advisor，16.2.3+ 已部署）

**v3 架构**：1 全科主审 + 1 声称核实 checker。详见 `assets/WATCHDOG.yml`（与 `~/.omp/agent/WATCHDOG.yml` 同步）。

### 启用配置（`~/.omp/agent/config.yml`）

```yaml
# advisor 角色能力方向：批判性分析、客观判断、细节审查；建议选用具备强批判推理能力的模型
modelRoles:
  advisor: <批判审查>  # 填入具备批判性分析与细节审查能力的模型标识

advisor:
  enabled: true
  subagents: false
  syncBacklog: 3
```

### 双 advisor → STDD 承重墙映射

| Advisor | Slug | 模型能力方向 | 镜头 | STDD 覆盖 |
|---|---|---|---|---|
| Reviewer | `reviewer` | 批判性分析、客观判断、细节审查 | 宽镜头：scope/delivery/tool audit/fake verification（14条规则） | P1–P6 全覆盖 |
| Claim Verify | `claim-verify` | 事实核实、证据对照、低延迟扫描 | 窄镜头：声称核实（交付类+事实类，≤2条/轮 concern only） | P3 claimcheck（声称 vs 证据） |

**Per-advisor 跨能力方向（批判审查 + 声称核实，不同专长）= P4 第二维「模型/视角独立」**。Refute-or-Promote 实证跨模型交叉验证多发现 ~3% 同族遗漏。Chair 不部署（独立运行，无通信）。

### WATCHDOG 发现位置

1. 用户级：`~/.omp/agent/WATCHDOG.yml`（优先）/ `WATCHDOG.md`
2. 项目级：`<dir>/WATCHDOG.yml`、`<dir>/.omp/WATCHDOG.yml`

### 运维 slash

- `/advisor on|off` — 启停 advisor
- `/advisor status` — 查看当前状态
- `/advisor dump` — 导出最后一次审查结果
- `/advisor configure` — TUI 配置 advisor 参数

### 回退：单 WATCHDOG.md（≤16.2.2）

`WATCHDOG.yml = 16.2.3+ 双 advisor；WATCHDOG.md = ≤16.2.2 单 advisor 回退`。

## LSP / DAP / Browser → Verify 的多种证据

| 验收类型 | OMP 工具 | 示例 |
|---|---|---|
| 类型正确、重构无遗漏 | `lsp` references/rename | 重命名后 `grep` 确认旧符号归零 |
| 运行行为正确 | `debug` launch + evaluate | 断点处检查变量值 |
| Web 前端可交互 | `browser` goto + observe | 元素可见、页面无 console error |
| 外部依赖/协议 | `web_search` + `read` | 查官方文档确认 API 用法 |

建议把 `lsp diagnostics` 作为代码型 Build 的硬性验收项之一。

## 推荐组合

- L0/L1：`ask` + `gates.mjs` verifyArtifact
- L2：`resolve(plan)` + `task` isolated + `eval` parallel verify + `lsp diagnostics`
- L3：`resolve(plan)` + `async task` + `reviewer`/`oracle` auditor + `browser`/DAP + `gates.mjs` counter + `irc` turn-done + Advisor 委员会（WATCHDOG.yml）

## 与 hook 的关系

- `stdd-gate.hook.ts`：在 `tool_call` 层拦截危险命令（通用、跨 OS、零规则路径依赖）。
- TTSR：在模型生成 token 层拦截违规表述（零上下文税、动态提醒）。
- Advisor/WATCHDOG：回合级审查，适合捕获策略性偏差。
- `gates.mjs`：客观结果判定，可验证、可计数。

四层共同构成 STDD 的 P3/P4/P6 护栏。
