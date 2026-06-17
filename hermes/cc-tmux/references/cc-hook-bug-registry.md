# CC Hook Bug Registry

> 2026-06-15 调研发现。这些是 Claude Code PreToolUse hook 的已知开放 bug，是 cc-tmux 不依赖 hook 做硬门、改用外部脚本（mkdir 原子目录锁 + 祝福路径）的关键论据。

## 开放 Bug 清单

| Issue | 严重度 | 症状 | 影响 |
|-------|:------:|------|------|
| [#43407](https://github.com/anthropics/claude-code/issues/43407) | 🔴 CRITICAL | PreToolUse hook 返回 exit 2 + `permissionDecision:"deny"` — 工具调用**不被阻断**，静默忽略 deny 决定 | 依赖 hook 做安全 guard 的用户实际无保护 |
| [#18312](https://github.com/anthropics/claude-code/issues/18312) | 🔴 CRITICAL | Bash 在 allow list 时，PreToolUse 的 permissionDecision **完全被忽略**（包括 deny） | allow list + hook 组合 = hook 形同虚设 |
| [#52822](https://github.com/anthropics/claude-code/issues/52822) | 🟡 MEDIUM | `permissionDecision:"allow"` 不抑制原生权限弹窗，用户仍需手动确认 | hook 的"自动放行"承诺落空 |
| [#40506](https://github.com/anthropics/claude-code/issues/40506) | 🟡 MEDIUM | `claude -p` 非交互模式下 PreToolUse hook **完全不触发** | headless 模式 hook 零作用（tmux 交互模式不受影响） |
| N/A (cc-tmux pitfall) | 🟡 MEDIUM | `CLAUDE_SESSION_ID` 环境变量在 hook 执行时为空（CC v2.1.178 实测）。Fallback `:-unknown` 导致产物全归 `unknown/`，Stop 软门 counter key 塌缩跨 session 污染 | 修复：所有 hook 从 stdin JSON 取 `session_id`。`in=$(cat)` 先保存 stdin，再 `jq -r '.session_id'`——stdin 只能读一次。cc-start v1.4+ 注入 `CC_TMUX_SESSION` 环境变量作为优先键 |

## 设计影响

**一级影响**：PreToolUse hook 不可当硬门。`exit 2 + deny JSON` 被静默忽略意味着：任何依赖 hook 做"阻断式安全防护"的设计都是脆弱的。

**二级影响**：即使 hook 正常工作，allow list 会覆盖 hook 决定。这意味着 hook 和 permission 系统之间存在未解决的优先级冲突。

**三级影响**：hook 的 `allow` 语义无法替代原生权限系统的 `allow`。

**四级影响（2026-06-17 Phase 0 实测）**：`--settings <file>` 注入的 hooks 与全局 `~/.claude/settings.json` 的 hooks **累积触发（双写）**，不是覆盖。这意味着迁移到 `--settings` 注入时**必须先摘掉全局 hooks**，否则心跳双写、Stop 双 block。详见 `cc-hook-facts-v2.1.178-20260617.md` §R1。

## 对 cc-tmux 的设计推论

cc-tmux 做了以下架构选择来规避这些问题：

1. **占用检测** → `mkdir` 原子目录锁（OS 级原子操作，不依赖 CC hook）
2. **敏感操作拦截** → 不在本 skill 范围；子 CC 安全由 CC 原生 permission deny-rule（非 hook）覆盖
3. **汇报/复核** → 祝福脚本路径（让合规=最省事），不赌 hook 强制
4. **CC hook** → 明确降级为 belt-and-suspenders（补充层），不作为主硬门

## 监控用法是 hook 的"安全车道"（Phase 2/3，2026-06-17）

事件驱动监控（Phase 2/3）把 hook 用在它**可靠**的事情上，刻意避开它**不可靠**的事情——所以上面全部 deny 类 bug **都不影响监控**：

| hook | 监控用途 | 是否碰 deny 类 bug |
|------|---------|:--:|
| PreToolUse(async) / PostToolUse | `touch` 心跳（freshness） | ❌ 只 exit 0，从不 deny |
| UserPromptSubmit / SessionEnd | 写 state log 生命周期事件 | ❌ |
| Notification | 写心跳 + idle 状态 | ❌ |
| Stop | 写 `cc-turn-done` 标记（cc-stop-check 软门用 `decision:block`，非 deny） | ❌（block≠deny，且有 gate-counter 有界） |

**核心论点**：#43407 / #18312 / #52822 全是 PreToolUse **deny 决定**被忽略的 bug。监控**从不做 deny 决定**——它只让 hook 触发并写文件（这是 hook 100% 可靠的部分，Phase 0 R3/R4 实测）。所以监控是 hook 的**安全用法**，与 bug-registry 的核心推论（"hook 永不作唯一硬门，只作 belt-and-suspenders"）完全一致：监控不是硬门，是状态总线。

**唯一相关 bug 是 #40506**（`-p` 模式 PreToolUse 不触发）：cc-tmux 用交互式 tmux **不受影响**；若有人用 `claude -p` 跑被驱动 CC，hook 心跳失效 → watcher 的 tmux capture-pane 探针成为唯一信号（可接受降级，非静默失败）。

## 监测

这些 bug 的状态应定期复查（建议每月）。若上游修复，cc-tmux 可以考虑将 hook 升级为 belt-and-suspenders 层——但**永远不作为唯一硬门**。

### 复查状态 — 2026-06-17（Phase 0-3 验证）

| 项 | 状态 | 对监控的影响 |
|----|------|------|
| #43407 / #18312 / #52822（deny 类） | 仍开放（未复测上游） | **无影响**：监控不做 deny（见上节安全车道） |
| #40506（`-p` PreToolUse 不触发） | 仍开放 | 交互模式不受影响；`-p` 模式降级到 watcher 探针 |
| CLAUDE_SESSION_ID 为空 | 仍为空（v2.1.178） | 已解决：全部 hook 走 stdin `session_id` + `CC_TMUX_SESSION` 键 |
| R1（`--settings` hooks 累积/双写） | **实测确认累积** | 已摘全局 hooks；保持摘除 |
| R2（`$CC_TMUX_HOOK_DIR` 展开） | **实测 PASS** | 方案 C 落地，脚本自定位 |
| R3（async 突发可靠） / R4（每调用触发） | **实测 PASS** | 心跳总线可靠，无丢失 |
| R5（事件真实性）/ SessionEnd reason | **实测 PASS**（reason=`prompt_input_exit`） | turn-done/lifecycle 信号成立 |

下次月度复查清单（2026-07 起）：
- 4 个开放 bug 状态（#43407 / #18312 / #52822 / #40506）是否上游修复
- R1 双写行为是否改变（影响要不要继续摘全局 hooks）
- R4 PreToolUse 漏触发是否出现
- SessionEnd `reason` 取值是否新增
- 实测事实表见 `cc-hook-facts-v2.1.178-20260617.md`
