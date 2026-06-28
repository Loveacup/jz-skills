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

## Advisor + WATCHDOG（v3 委员会，16.2.3+）

**16.2.3 多 advisor `WATCHDOG.yml` 委员会**（已落地，推荐）：

### 启用配置（`~/.omp/agent/config.yml`）

```yaml
modelRoles:
  advisor: anthropic/claude-sonnet-4-5:medium

advisor:
  enabled: true
  subagents: false      # 防多模型 fan-out 审查风暴
  syncBacklog: 3        # 控频降本（默认 3）

retry:
  fallbackChains:
    advisor:
      - anthropic/claude-sonnet-4:medium
      - openai/gpt-5-mini:fast
```

### WATCHDOG 发现位置（优先级从高到低）

1. 用户级：`~/.omp/agent/WATCHDOG.yml`（优先）/ `WATCHDOG.md`
2. 项目级：`<dir>/WATCHDOG.yml`、`<dir>/.omp/WATCHDOG.yml`

多文件**同时加载**，近 cwd 后注入优先。

### `@` 导入语法

可把 STDD 承重墙规则 `@` 进 WATCHDOG：

```yaml
# WATCHDOG.yml 内
advisors:
  - slug: delivery-auditor
    ...
    instruction: |
      @assets/stdd-rules/P1-decidable.md
      @assets/stdd-rules/P2-acceptance-required.md
      ...
```

### 运维 slash

- `/advisor on|off` — 启停 advisor
- `/advisor status` — 查看当前状态
- `/advisor dump` — 导出最后一次审查结果
- `/advisor configure` — TUI 配置 advisor 参数
- `@path/to/file.md` — 导入外部规则

### 委员会 → STDD 承重墙映射

裁到 5 个 advisor（详见 `assets/WATCHDOG.yml`）：

| Advisor | Severity | 映射承重墙 |
|---|---|---|
| delivery-auditor | blocker | P2 验收不可省 + claimcheck |
| correctness-auditor | concern→blocker | P3 证据优先 |
| security-auditor | blocker | danger 类 |
| evidence-anchor-checker | concern | claimcheck（P3 子集） |
| style-keeper | concern | 命名/AI 腔 |

**Per-advisor 跨模型 = P4 第二维「模型/视角独立」**。Auto-fix 双授权红线。Chair 不部署。

### 回退：单 WATCHDOG.md（≤16.2.2）

`WATCHDOG.yml = 16.2.3+ 委员会；WATCHDOG.md = ≤16.2.2 单 advisor 回退`。

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
