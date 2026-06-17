# CC Hook v2.1.178 实测事实表

> 2026-06-17 Phase 0 冒烟验证。**本表是运行时实测,优先级高于任何文档/调研报告。**
> 方法:隔离 tmux 内嵌套真实 `claude`(haiku 省 token,bypassPermissions 交互模式),
> 各 hook 写不同标记文件,据标记反推行为。夹具在 `/tmp/cc-phase0/`(run.sh / run2.sh / test-settings.json)。
> 验证床选型:**必须用交互式 tmux,不能用 `claude -p`**——bug #40506 下 `-p` 模式 PreToolUse 不触发,会得出假阴性。

## 环境
- CC `2.1.178` · macOS 26.5 · `defaultMode: bypassPermissions` · 模型 haiku-4-5

## CLI 事实(`claude --help` 直读)

| 参数 | 结论 | help 原文 / 备注 |
|------|:---:|------|
| `--settings <file-or-json>` | ✅ 存在 | "Path to a settings JSON file or a JSON string to **load additional settings from**" → 叠加层 |
| `--hooks-dir` | ❌ 不存在 | help 无此项。hook 只能经 settings 配置 |
| `--bare` | ⚠️ **跳过 hooks** | "Minimal mode: **skip hooks**, LSP, plugin sync…" → 部署时**绝不能**带 --bare |
| `--debug [filter]` | ✅ 可观测 | 示例 `"api,hooks"`,`claude --debug hooks` 可看 hook 触发 |
| `--add-dir/--agents/--mcp-config/--plugin-dir` | ✅ | 与 --settings 并列的注入面 |

## 五项冒烟结果

### R1 — `--settings` hooks 是累积还是覆盖 ⟦go/no-go⟧
**结论:ACCUMULATE(累积/双触发)** — 决定性。

- 方法:全局 `~/.claude/settings.json` 已有 PostToolUse(Bash) 归档 hook;`--settings` 也放一个 Bash PostToolUse。跑一次产生 >4KB 输出的 Bash。
- 证据:**两边都触发** —
  - 全局 hook → `/tmp/cc-output/phase0test/responses-1781641866.log`(11012 字节)生成
  - `--settings` hook → `R1_settings_fired` 标记 + `settings_post.log` 一行
  - 旁证:嵌套 CC 的 pane 顶部出现了全局 SessionStart hook 注入的 `[cc-tmux]...#S363...` context,而我的 `--settings` SessionStart 不 echo → 说明全局 SessionStart 也跑了。
- **推论:迁移到 `--settings` 注入时,必须先摘掉全局 `~/.claude/settings.json` 里的 cc-tmux hooks**,否则每个事件双触发(双写心跳、Stop 双 block、大输出双归档)。

### R2 — `$CC_TMUX_HOOK_DIR` 在 hook shell 触发时能否展开 ⟦go/no-go⟧
**结论:PASS** — 方案 C(`--settings` 指 skill 模板 + 环境变量自定位 hook 路径)可行,**不必降级方案 D**。

- 方法:启动行 `... CC_TMUX_HOOK_DIR=/tmp/cc-phase0/hooks claude --settings ...`;`--settings` 的 hook 命令含 `bash "$CC_TMUX_HOOK_DIR/marker.sh"`。
- 证据:`R2_hookdir_expanded` 标记生成;`r2.log` = `HOOKDIR=[/tmp/cc-phase0/hooks]` → 变量在 hook 触发时由 CC 派生 shell 正确展开(与 `CC_TMUX_SESSION` 传播同构)。

### R3 — `async:true` 心跳可靠性
**结论:PASS** — 异步追加在突发下无丢失。

- 方法:PreToolUse 设 `async:true`,强制 3×Write + 1×Bash。
- 证据:`pre.log` 4 行,精确对应 4 次调用;其中 **3 个 Write 同在 epoch 1781641969(同一秒突发)全部捕获,零丢失**。
- 推论:高频监控 hook 可放心用 `async:true`,对 CC 工具循环零延迟。

### R4 — PreToolUse 是否每个工具调用都触发(bypass 交互模式)
**结论:PASS** — 每调用必触发,且无 matcher = 匹配所有工具。

- 证据:4 次工具调用(3 Write + 1 Bash)= 4 次 PreToolUse(`PRE Write ×3` + `PRE Bash ×1`)。Write 也触发 → 省略 matcher = match-all 确认。
- 注:首轮测试看似只触发 1 次,实为 haiku 把两条命令合并成 **1 个** Bash 调用("Ran 1 shell command"),1 调用=1 触发,自洽,非漏触发。

### R5 — 事件真实性(逐个标记验证)
| 事件 | 触发 | payload 关键字段(实测) |
|------|:---:|------|
| SessionStart | ✅ | `source=startup` |
| UserPromptSubmit | ✅ | — |
| PreToolUse | ✅ | `tool_name`(Write/Bash) |
| PostToolUse | ✅ | matcher `Bash` 命中 |
| Stop | ✅ | 本轮结束即触发(~8s) |
| **SessionEnd** | ✅ | `reason=prompt_input_exit`(`/exit` 退出时) |
| SubagentStop | (未测) | 本轮未派子 agent,标记未生成(符合预期) |

## 对演进方案的直接影响

| Phase 0 闸 | 结果 | 落地动作 |
|------|------|------|
| R1 | ACCUMULATE | Phase 1/4 **必须摘全局 hooks**,改由 `--settings` 单一来源 |
| R2 | PASS | 采用**方案 C**:cc-start 加 `--settings $SKILL_ROOT/templates/settings.runtime.json` + 导出 `CC_TMUX_HOOK_DIR`;不需生成临时 settings |
| R3 | PASS | 监控 hook 用 `async:true` |
| R4 | PASS | PreToolUse 可作可靠心跳源(每调用刷新) |
| R5 | PASS | Stop→turn-done 标记、SessionEnd(reason)→区分正常退出 vs 崩溃,均可落地 |

## 仍未验证(NOT tested — 核心方案不得依赖)

claude-code-guide 调研报告里以下项**本次未实测**,使用前须单独 `--debug hooks` 复验:
- hook 类型 `http` / `mcp_tool` / `prompt` / `agent`(主动外呼/LLM 决策)——方案刻意不依赖,守"零新依赖"。
- 冷门事件 `PostToolBatch` / `MessageDisplay` / `ConfigChange` / `CwdChanged` / `FileChanged` / `TeammateIdle` / `PostCompact` 等——核心只用上表 8 个已验证事件。
- `--settings` 对**非 hooks 键**(如 model/permissions)的 override-vs-merge 语义——本次只验证了 hooks=累积。
- SessionEnd 其它 `reason` 取值(clear/resume/logout/...)——只实测了 `prompt_input_exit`。
- `CLAUDE_SESSION_ID` 仍为空(沿用旧结论,本次未重测;所有 hook 继续从 stdin 取 `session_id`)。

## 复查节奏
并入 bug-registry 的月度复查:每月复验 R1(双写,影响要不要摘全局)+ R4(漏触发)+ SessionEnd reason 取值。
