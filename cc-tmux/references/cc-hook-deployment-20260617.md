# CC Hook 部署验证 — 2026-06-17

> ⚠️ **部署模型已迁移（v1.9.0 / Phase 1，2026-06-17）。** 本文档**顶部的"部署步骤"（全局 cp + jq merge + 重启）已废弃**——R1 实测证明 `--settings` 注入的 hooks 与全局 hooks **累积双触发**，故全局 cc-tmux hooks 已摘除（`jq '.hooks' ~/.claude/settings.json` 现为 null）。
> **现行部署**：cc-start.sh 启动 CC 时自动 `--settings "$SKILL_ROOT/templates/settings.runtime.json"` + 导出 `CC_TMUX_HOOK_DIR`，skill 即唯一真源，零 cp / 零 jq / 零重启。详见 `hooks/README.md` §3 与 `references/cc-hook-facts-v2.1.178-20260617.md`。
> 下方的 **CLAUDE_SESSION_ID 为空根因 + stdin 消费陷阱 + 验证点教训仍然有效**（与部署方式无关），保留作历史记录。

## 部署步骤（⚠️ 已废弃，见上方横幅——仅作历史记录）

1. ~~创建 `~/.claude/hooks/` 目录，拷贝 `cc-posttool.sh` + `cc-stop-check.sh`~~ → 现由 `$CC_TMUX_HOOK_DIR` 自定位到 skill 目录，不再拷贝
2. ~~合并 hook 配置到 `~/.claude/settings.json`~~ → 现由 `--settings` 会话级注入，不再 merge（R1 累积会双写）
3. ~~**CC 必须重启才能载入新 hook 配置**~~ → 每任务全新 CC，启动即读最新，**天然无重启问题**

## 验证方法（教训：验证点必须对应实际落盘路径）

### ❌ 错误验证
- 检查 `/tmp/cc-hook-debug.log` — **没有任何 hook 写这个文件**，永远为空
- 按 tmux session 名查找 `/tmp/cc-state-<session>.log` — hook 用 CC 内部 session_id（UUID）命名

### ✅ 正确验证
| Hook 事件 | 验证点 | 判断标准 |
|-----------|--------|---------|
| SessionStart | CC pane 顶部 context | grep `[cc-tmux] 你是被 cc-tmux 驱动的 CC` |
| Notification | `/tmp/cc-state-<UUID>.log` | grep `"event":"notification"` |
| PostToolUse(Bash) | `/tmp/cc-output/<UUID>/responses-*.log` | >4096 字节输出 → 文件存在 |
| PostToolUse(Write/Edit) | `/tmp/cc-output/<UUID>/` + 格式化效果 | 调用 `cc-posttool.sh` 归档 |

## 根因：CLAUDE_SESSION_ID 为空

**实测**: `CLAUDE_SESSION_ID=[]`（空值）在 hook 执行环境中。CC v2.1.178 不导出此变量。

**后果**: 所有 `"${CLAUDE_SESSION_ID:-unknown}"` 兜底 → 产物全归 `unknown/`：
- `/tmp/cc-output/unknown/responses-*.log`
- `/tmp/cc-state-unknown.log`
- `/tmp/cc-heartbeat-unknown`

按 session 名找产物 → 找不到 → 误判"hook 不触发"。

## 修复：stdin JSON 取 session_id

CC 通过 stdin 向 hook 传入 JSON，包含 `session_id` 字段。所有 hook 改为从 stdin 提取：

```bash
# ✅ 正确：stdin 先存，再取 sid
in=$(cat)
sid=$(printf '%s' "$in" | jq -r '.session_id // "unknown"')
```

### stdin 消费陷阱

**`jq` 消费 stdin → `cat` 读不到内容。** 修复前：

```bash
# ❌ jq 先读 stdin → cat 拿不到 tool_response
sid=$(jq -r '.session_id // "unknown"')    # stdin 已消费！
in=$(cat)                                    # 空！

# ✅ 先存再取
in=$(cat)                                    # 全量保存
sid=$(printf '%s' "$in" | jq -r '.session_id')
resp=$(printf '%s' "$in" | jq -r '.tool_response // empty')
```

## 修复清单

| 文件 | 修复 | 状态 |
|------|------|:--:|
| `~/.claude/settings.json` → PostToolUse Bash 内联 | `in=$(cat)` 先存，再取 sid + tool_response | ✅ |
| `~/.claude/settings.json` → Notification 内联 | `sid=$(jq)` 从 stdin 取 | ✅ |
| `~/.claude/settings.json` → SessionStart 内联 | `sid=$(jq)` 从 stdin 取 | ✅ |
| `~/.claude/hooks/cc-posttool.sh` | `SESS=$(printf "$IN" \| jq -r '.session_id')` | ✅ |
| `~/.claude/hooks/cc-stop-check.sh` | `IN=$(cat); S=$(printf "$IN" \| jq -r '.session_id')` | ✅ |

## 排除项

- **bypassPermissions** 模式不影响 hook 触发（实测确认）
- **matcher** 语法正确（`Bash`, `Write|Edit|MultiEdit`, `idle_prompt|permission_prompt` 均命中）
- **JSON 格式**无语法错误（CC 成功加载即证明）
- **Notification 的 permission_prompt** 在 bypassPermissions 下不触发（符合预期）

## 待验证

- **Stop hook**：需在实际任务中配合 `--expect` flag 才能触发 block 语义
- **Write/Edit hook**：需 CC 使用 Write 工具（非 Bash 写文件）时触发 `cc-posttool.sh` 的 format+归档逻辑
