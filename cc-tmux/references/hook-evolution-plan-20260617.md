# Hook 演进方案：部署自动化 + 事件驱动监控

> 调研日期 2026-06-17 · CC v2.1.178 · cc-tmux v1.8.1
> 源：CC xhigh 深度调研，产出 `/tmp/cc-hook-evolution-plan.md`（25KB/360行）
> 本文件为 condensed 参考版，完整版在 `/tmp/cc-hook-evolution-plan.md`

## 0. 一句话结论

两个问题（部署自动化 + 监控替代轮询）是**同一个架构杠杆的两面**：

1. **部署**：cc-start.sh 每个任务全新拉起 `claude` → 用 `--settings` 在启动瞬间注入 hook，skill = 唯一真源
2. **监控**：hook 事件推 + watcher 守护进程兜底 → Hermes 转被动读，**把节律义务从 LLM 彻底搬走**

## 1. 部署自动化：`--settings` 注入

### 经验事实（v2.1.178 `claude --help` 验证）

| 能力 | 结论 |
|------|------|
| `--settings <file-or-json>` | ✅ 存在，"load **additional** settings from"（叠加层） |
| `--hooks-dir` | ❌ 不存在 |
| `--bare` | ⚠️ 会跳过 hooks，部署时绝不能带 |
| `--debug hooks` | ✅ 冒烟测试工具 |

### 方案：启动时注入

```bash
# cc-start.sh 改为：
HOOKDIR="$SKILL_ROOT/hooks"
tmux send-keys -t "$SESSION" \
  "HOME=\"$USER_HOME\" CC_TMUX_SESSION=\"$SESSION\" CC_TMUX_HOOK_DIR=\"$HOOKDIR\" \
   claude --model ${MODEL} --effort ${EFFORT} \
          --settings \"$SKILL_ROOT/templates/settings.runtime.json\"" Enter
```

模板里 hook 自定位：`"command": "bash \"$CC_TMUX_HOOK_DIR/cc-stop-check.sh\""`

### 未验证风险（Phase 0 必须测）

- **R1**：`--settings` hooks 与全局 hooks 是累积还是覆盖？双写？
- **R2**：`$CC_TMUX_HOOK_DIR` 在 hook shell 里能否展开？
- Fallback：方案 D——cc-start 生成 `/tmp/cc-settings-<s>.json`（绝对路径烤进去）

## 2. 事件驱动监控：混合架构

### 核心洞察

监控三个问题：CC 在不在干活？有没有卡死？本轮干完了没？

三候选对比：
- **LLM 定时轮询（现状）**：不擅长定时，根因病灶 ✗
- **CC hook 事件推**：100% 可靠但只在有事件时触发，看不到纯思考 △
- **确定性 shell 循环（watcher）**：100% 守时，能读 TUI spinner ✓

→ **三者各司其职的混合架构**

```
        ┌─── PUSH（事件，零节律义务）───┐
CC hooks: PreToolUse/PostToolUse → 刷心跳
          Stop → 写 turn-done 标记
          Notification → IDLE
          SessionStart/End → 生命周期
                    │ 写
                    ▼
        统一状态总线（/tmp 下，按 CC_TMUX_SESSION 键）
        heartbeat / state-log / turn-done / freeze
                    ▲ 写（仅心跳陈旧时补探针）
                    │
        ┌── TIMER（确定性 shell，唯一 poller）──┐
cc-watcher 守护进程: 每 N 秒检查心跳
  仅心跳陈旧(无 tool 事件) → capture-pane 读 THINK_TIME
  → 区分深思(计时器在走) vs 冻结(计时器也停)
                    │
                    ▼ READ（被动，按需）
                 Hermes(LLM)
  想知道状态：读 state / heartbeat
  该看结果了：读 turn-done 标记
  有没有出事：读 freeze 告警
```

### hook 不能替代的：纯思考期冻结判定

纯思考期 CC 不调任何工具 → **没有任何 hook 触发** → 心跳陈旧。
此时唯一信号是 TUI spinner 计时器（THINK_TIME），**无 hook 能读**。
→ cc-monitor.sh v1.8.1 的 THINK_TIME/SPINNER_LINE 逻辑必须保留，只是换调用方。

### 新增事件

| 事件 | 语义 | 写什么 |
|------|------|--------|
| **PreToolUse** | WORKING（高频） | `async:true` 刷心跳 |
| **UserPromptSubmit** | RECEIVED | 心跳 + 清 turn-done |
| **Stop** | TURN_DONE | 新增写 `cc-turn-done-<s>` |
| **SessionEnd** | GONE | state=GONE（区分崩溃） |

### 新增状态文件

```
/tmp/cc-turn-done-<s>     Stop hook 写：{"ts":"...","seq":N}
                          Hermes 读它 → 本轮完成，该看结果了
/tmp/cc-freeze-<s>        watcher 确认冻结时写
                          Hermes 被动检查 → 告警
```

## 3. 与现有体系整合

| 组件 | 变化 |
|------|------|
| **cc-monitor.sh** | 不改删。改为「hook 心跳够新→纯读文件快路径；心跳陈旧→探针」。Hermes 仍可随时手动跑 |
| **cc-finish.sh** | 先认 `cc-turn-done` 为完成权威；心跳新鲜度退为辅助；清理多删 turn-done/freeze |
| **cc-watcher.sh** | 扶正为常驻守护进程。cc-start 后台拉起 + 记 PID，cc-finish 时 kill |
| **Hermes** | 删除「每 30-60s 轮询」节律义务；改「读 turn-done + 按需读状态 + 被动查 freeze」 |

## 4. 实施路线图

| 阶段 | 内容 | 优先级 |
|------|------|:--:|
| **P0 验证** | 冒烟 R1-R5（--settings 双写、路径展开、async、PreToolUse 触发、SessionEnd） | **闸门** |
| **P1 部署** | 新增 `settings.runtime.json` + cc-start 改启动行 + 摘全局 hooks | 高 |
| **P2 监控** | PreToolUse/SessionEnd hook + watcher 改造 + cc-monitor 快路径 | 高 |
| **P3 Hermes 被动** | SKILL.md/SOUL.md 删轮询义务 + cc-finish 认 turn-done | **根治** |
| P4 清理 | 去全局 hooks + 文档更新 + 测试扩到新 hook + v1.9.0 | 中 |

## 5. 风险底线

- 所有新 hook 走**非 deny 安全车道**（exit 0、best-effort、静默降级），完美避开 bug-registry 全部 deny 类 bug（#43407/#18312/#52822 都不影响监控用法）
- 两个 go/no-go 硬闸：R1（双写）、R2（路径展开）
- 不引入 http/mcp_tool 外呼（文件标记已够，守住零新依赖约束）
