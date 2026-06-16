# cc-tmux 测试结果 — 2026-06-17（文件名沿用历史 33of33）

> ⚠️ **2026-06-17 更新**：原「33/33 全绿」在审计中实跑只复现 30–31/33（test-hooks 套件
> 停留在 Pitfall #15 修复前的 env 约定，验证了不会被部署的旧模板）。经 D-4 键统一修复 +
> 测试重对齐后，**当前实跑 48/48 全绿**（每次提交前实跑核实，不再凭历史快照）。
> 含 2026-06-17 晚的冻结检测修复（THINK_TIME 计时器 + spinner 行锚定 + 心跳第 7 字段）。

## 测试套件汇总（实跑 2026-06-17）

| 套件 | 文件 | 用例 | 结果 | 覆盖范围 |
|------|------|:--:|:--:|------|
| §3.1 | `tests/test-monitor.sh` | 6/6 | ✅ | TOOL>IDLE / THINKING>IDLE / Pure IDLE / ✢✳✶ 字检测 |
| §3.1 freeze | `tests/test-monitor-freeze.sh` | 6/6 | ✅ | THINK_TIME 递增→重置(不误报) / 双停→不重置(真冻结) / token 变化→重置 / **sub-minute 37s** / **分钟制 49m·(Pitfall#14)** / 分钟制冻结 |
| §3.2 | `tests/test-send.sh` | 9/9 | ✅ | 基础发送 / --dry-run / --expect / 残留重试 / 队列 Esc |
| §3.8+D-4 | `tests/test-start.sh` | 5/5 | ✅ | #7 自检 / #3 exit3 / **CC_TMUX_SESSION 注入接线** |
| §3.7+D-4 | `tests/test-finish.sh` | 6/6 | ✅ | **清理契约**：heartbeat/state/expect/counter/cc-output 全清 + 杀 session + 释放锁 |
| §3.3-3.7 | `tests/test-hooks.sh` | 16/16 | ✅ | 归档(tmux 键) / Bash tool_response / Notification 总线 / SessionStart 读总线 / Stop 软门 / **D-4 键优先级 + UUID 降级** |
| **合计** | | **48/48** | ✅ | |

## D-4 键统一修复（本次核心）

| 改动 | 文件 |
|------|------|
| cc-start 注入 `CC_TMUX_SESSION=<tmux名>` 到 claude 启动环境 | `scripts/cc-start.sh` |
| hook 规范键 `${CC_TMUX_SESSION:-<stdin session_id>}` | `hooks/cc-posttool.sh` · `hooks/cc-stop-check.sh` · `templates/settings.template.json`（3 内联） |
| cc-finish 补清理 counter + cc-output（键已统一，cc-finish 知道 tmux 名） | `scripts/cc-finish.sh` |
| SessionStart banner 多字节边界 bug（`$k。` → `${k}。`）顺手修复 | `templates/settings.template.json` |
| 删除分叉旧模板（env 版）→ 单一事实源 | 删 `hooks/settings.template.json` |
| test-hooks 重对齐（喂 stdin session_id / 读 templates/ / 清 unknown 键） | `tests/test-hooks.sh` |

**连带激活**：§3.7 Stop 软门端到端命中（读到 cc-send 写的 `cc-expect-<tmux名>`）；§3.4 Notification
与 cc-monitor 写同一 `cc-state-<tmux名>.log`；§3.5 SessionStart「最近状态」不再恒空。

## 部署 smoke 清单（上线前必须通过）

- [ ] **`CC_TMUX_SESSION` 传播到 hook 环境**：cc-tmux 驱动的 CC 里写 >8KB 文件 → 归档落
      `/tmp/cc-output/<tmux名>/`（非 UUID、非 `unknown/`）。**这是单测无法覆盖的唯一假设。**
- [ ] PostToolUse 在交互模式触发（非 `claude -p`）
- [ ] Notification matcher 名 `idle_prompt|permission_prompt` 当前 CC 版本有效
- [ ] SessionStart 不阻断会话启动，banner 与最近状态正确渲染
- [ ] Stop hook 配 `cc-send --expect` 时 block 语义往返正常

## 部署状态（2026-06-17）

- **已部署到全局** `~/.claude/hooks/`（cc-posttool.sh + cc-stop-check.sh）与
  `~/.claude/settings.json`（4 事件内联，stdin-jq + D-4 键统一版）。
- 注：全局部署使 hook 对所有 CC 会话生效（非 cc-tmux 驱动的降级回 UUID 键）。session 级
  `--settings` 注入（plan §9）是更干净的长期模型，尚未接线。
