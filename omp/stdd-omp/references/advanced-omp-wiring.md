# STDD-OMP 高级 OMP 能力接线

把 OMP 的 `eval` workflow、TTSR、Advisor+WATCHDOG、LSP/DAP/Browser 等高价值能力，映射到 STDD 的四步微循环与承重墙。

## eval 工作流 → Verify / Build 编排

OMP `eval` 是持久化代码内核，适合把多步客观校验写成可复现脚本。

| STDD 步骤 | eval 用法 | 收益 |
|---|---|---|
| Verify（客观项） | `eval js` import `scripts/gates.mjs` | 跨 OS、无 PATH 依赖、结果可判定 |
| Verify（多维度并行） | 若 runtime 支持并发工具，可并行跑多个 `gates.mjs` 校验 | 缩短验证时间 |
| Build（多阶段流水线） | 在 `eval` 中用代码编排多阶段（读取→处理→校验） | 数据→处理→产物 可追踪 |
| 子代理代码化 | 若 runtime 支持，可在 `eval` 中动态 spawn 子代理 | 更灵活的编排 |

**最小兼容路径（任何 OMP 版本都可用）**：

```js
const g = await import('file:///path/to/scripts/gates.mjs');
const artifact = g.verifyArtifact('dist/app.js');
const test = g.verifyTest('node -e "process.exit(0)"');
const danger = g.scanDanger('git push');
```

> 注：`parallel(...)` / `pipeline(...)` / `agent(...)` 等是 `OMP_使用手册.md` 中描述的 `eval` 可选辅助能力；不同版本/配置支持度可能不同。生产使用前先在本机 `eval js` 单元格中测试。

## TTSR / Rules → 动态规则墙

OMP 支持规则文件（`~/.omp/agent/rules/*.md` 已在本机验证），通过 YAML frontmatter 控制是否生效。规则体随会话上下文注入，可作为 STDD 承重墙的动态提醒。

**已验证的最小兼容格式**（本机 `~/.omp/agent/rules/omp-identity.md`）：

```yaml
---
alwaysApply: true
---
P1 可裁决：所有结论必须对应一条可证伪的验收项...
```

> 可加 `name`、`enabled` 等键便于管理，但最小兼容只需 `alwaysApply: true` 验证通过。

STDD 规则映射（用 `alwaysApply` 方式）：

| STDD 承重墙 | 规则文件名 | 规则体要点 |
|---|---|---|
| P1 可裁决 | `stdd-rules/P1-decidable.md` | 结论必须可证伪；禁止模糊表述 |
| P2 验收不可省 | `stdd-rules/P2-acceptance-required.md` | 无 Acceptance 不 Build |
| P3 证据优先 | `stdd-rules/P3-evidence-first.md` | 实态 > 测试 > diff > 报告 |
| P4 角色分离 | `stdd-rules/P4-role-separation.md` | producer ≠ judge |
| P6 终止条件 | `stdd-rules/P6-hard-limit.md` | regen max=3，slice max=2 |
| 危险发布 | `stdd-rules/danger-push.md` | 发布/推送需确认 |

> `OMP_使用手册.md` 提到 **TTSR（stream 正则触发）** 能力，但 `event`/`pattern`/`action` schema 尚未在本机 `~/.omp/agent/rules/` 验证。**请先复制一条 `event/pattern/action` 规则到本地规则目录测试生效后，再切换；生产环境建议先用本技能提供的 `alwaysApply` 模板。**

## Advisor + WATCHDOG.md → P4 独立审计增强

Advisor 是 OMP 内置的“第二只眼”，在每个回合结束后审查主代理工作。

启用条件（`~/.omp/agent/config.yml`）：

```yaml
modelRoles:
  advisor: anthropic/claude-sonnet-4-5:medium

advisor:
  enabled: true
  syncBacklog: 1
  subagents: true   # 子代理也启用 advisor
```

WATCHDOG.md 只注入 Advisor 系统提示，不污染主代理。STDD 项目可放项目根或 `.omp/WATCHDOG.md`。

WATCHDOG 审查重点：
- 验收契约是否被跳过或弱化
- 是否出现“推测放行”措辞
- 是否 producer 与 judge 同 session
- 是否超出 regen/slice 上限仍继续
- 危险命令是否被 hook/approval 拦截

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
- L3：`resolve(plan)` + `async task` + `reviewer`/`oracle` auditor + `browser`/DAP + `gates.mjs` counter + `irc` turn-done + Advisor + WATCHDOG

## 与 hook 的关系

- `stdd-gate.hook.ts`：在 `tool_call` 层拦截危险命令（通用、跨 OS、零规则路径依赖）。
- TTSR：在模型生成 token 层拦截违规表述（零上下文税、动态提醒）。
- Advisor/WATCHDOG：回合级审查，适合捕获策略性偏差。
- `gates.mjs`：客观结果判定，可验证、可计数。

四层共同构成 STDD 的 P3/P4/P6 护栏。
