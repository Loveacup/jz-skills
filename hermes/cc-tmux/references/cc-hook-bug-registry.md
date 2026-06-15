# CC Hook Bug Registry

> 2026-06-15 调研发现。这些是 Claude Code PreToolUse hook 的已知开放 bug，是 cc-tmux 不依赖 hook 做硬门、改用外部脚本（flock + 祝福路径）的关键论据。

## 开放 Bug 清单

| Issue | 严重度 | 症状 | 影响 |
|-------|:------:|------|------|
| [#43407](https://github.com/anthropics/claude-code/issues/43407) | 🔴 CRITICAL | PreToolUse hook 返回 exit 2 + `permissionDecision:"deny"` — 工具调用**不被阻断**，静默忽略 deny 决定 | 依赖 hook 做安全 guard 的用户实际无保护 |
| [#18312](https://github.com/anthropics/claude-code/issues/18312) | 🔴 CRITICAL | Bash 在 allow list 时，PreToolUse 的 permissionDecision **完全被忽略**（包括 deny） | allow list + hook 组合 = hook 形同虚设 |
| [#52822](https://github.com/anthropics/claude-code/issues/52822) | 🟡 MEDIUM | `permissionDecision:"allow"` 不抑制原生权限弹窗，用户仍需手动确认 | hook 的"自动放行"承诺落空 |
| [#40506](https://github.com/anthropics/claude-code/issues/40506) | 🟡 MEDIUM | `claude -p` 非交互模式下 PreToolUse hook **完全不触发** | headless 模式 hook 零作用（tmux 交互模式不受影响） |

## 设计影响

**一级影响**：PreToolUse hook 不可当硬门。`exit 2 + deny JSON` 被静默忽略意味着：任何依赖 hook 做"阻断式安全防护"的设计都是脆弱的。

**二级影响**：即使 hook 正常工作，allow list 会覆盖 hook 决定。这意味着 hook 和 permission 系统之间存在未解决的优先级冲突。

**三级影响**：hook 的 `allow` 语义无法替代原生权限系统的 `allow`。

## 对 cc-tmux 的设计推论

cc-tmux 做了以下架构选择来规避这些问题：

1. **占用检测** → `mkdir` 原子目录锁（OS 级原子操作，不依赖 CC hook）
2. **敏感操作拦截** → 不在本 skill 范围；子 CC 安全由 CC 原生 permission deny-rule（非 hook）覆盖
3. **汇报/复核** → 祝福脚本路径（让合规=最省事），不赌 hook 强制
4. **CC hook** → 明确降级为 belt-and-suspenders（补充层），不作为主硬门

## 监测

这些 bug 的状态应定期复查（建议每月）。若上游修复，cc-tmux 可以考虑将 hook 升级为 belt-and-suspenders 层——但**永远不作为唯一硬门**。
