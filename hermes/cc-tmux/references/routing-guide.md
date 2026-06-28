# Hermes 消息路由使用指南（cc-route.sh 接线文档）

> **何时读取**：Hermes 收到用户消息、且有 CC session 活跃时。
> **核心脚本**：`cc-route.sh` + `cc-active-sessions.sh`
> **设计原则**：脚本判"能不能做"，Hermes 判"怎么做"。

---

## 一分钟速览

```
用户消息到达
    │
    ├─ 无活跃 CC ──→ 正常处理（你本来就该做的事）
    │
    └─ 有活跃 CC ──→ cc-active-sessions.sh --json
            │
            ├─ 多个 session ──→ 按 topic 匹配 / 最近活跃 / 问用户
            │
            └─ 一个 session ──→ 分类 intent → cc-route.sh → 按建议行动
```

---

## Step 1：有无 CC？

收到用户消息后，先调：

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-active-sessions.sh --json
```

返回 `[]` → 无活跃 CC，直接正常处理用户消息。

返回 `[{...}]` → 有 CC。跳到 Step 2。

## Step 2：选哪个 session？

| session 数 | 策略 |
|-----------|------|
| 0 | 正常处理 |
| 1 | 直接用 |
| ≥2 | ① 当前 conversation topic 匹配（`--topic`）→ ② 最近心跳 → ③ 问用户"有两个 CC 在跑，发给哪个？" |

选好后记下 session 名，比如 `hermes-cc-default-jz-skills-0629-0115`。

## Step 3：分类用户意图

看用户消息内容，归类为 5 种之一：

| intent | 判断标准 | 示例 |
|--------|---------|------|
| `status_query` | 问进度/状态/在干嘛 | "到哪了？""CC在干嘛？" |
| `continuation` | 当前任务的补充信息/微调 | "别忘了也改一下test""顺便把README也更新" |
| `redirect` | 改变当前任务方向 | "停，别做X了，改做Y""换方案，用Z方法" |
| `new_task` | 全新的独立任务 | "帮我看一下另一个项目的bug""明天天气怎么样" |
| `unknown` | 无法判断 | 歧义消息/闲聊/不确定 |

## Step 4：调 cc-route.sh

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-route.sh \
  --session hermes-cc-xxx \
  --intent continuation
```

输出 JSON。关键字段：`.recommendation.action` 和 `.recommendation.confirm_required`

## Step 5：按 action 行动

### `handle_directly`

CC 不在/已结束/空闲且新任务无关。**Hermes 自己处理，不碰 CC。**

告诉用户："CC 当前空闲/已完成，我直接处理。"

### `report_status`

用户只是想看状态。读输出 JSON 中的 `cc_state` / `heartbeat_age_s` / `freeze`，格式化汇报。

```markdown
📡 CC 状态：⚡ TOOL（调 Bash）· 心跳 3s 前 · 无冻结
```

### `queue`

CC 正忙（THINKING/TOOL/WAITING_AGENTS），消息不该打断它。

行动：
1. 告诉用户"CC 正在 X，消息已排队，完成后转发"
2. 调 `cc-wait-marker.sh --session <s> --after <now_epoch>` 等 turn-done
3. turn-done 出现 → 用 `tmux_type` 把用户原消息发给 CC + Enter
4. 📡 汇报"已转发"

> ⚠️ 不要在 queue 期间阻塞回复用户。先回用户的询问，再后台等 turn-done。

### `forward_now`

CC 处于可安全接收输入的状态（IDLE/TOOL/BLOCKED）。

行动：
1. 用 `tmux_type` 把用户消息发给 CC 的 ❯ 提示符
2. 按 Enter
3. 用 `cc-send-robust.sh send-to-pane` 验证已消费

```bash
# 示例（用 mcp_tmux_bridge）
tmux_type --target <session> --text "用户说：别忘了也更新 tests/test-route.sh"
tmux_keys --target <session> --keys Enter
```

### `interrupt`

CC THINKING + 冻结 + 用户要重定向。高风险。

行动：
1. **先汇报用户确认**（`confirm_required: true`）
2. 用户确认后：
   - `tmux_keys Escape` 打断当前思考
   - `tmux_type` 发送重定向指令
   - `tmux_keys Enter`
3. 汇报"已打断并转发"

> 🔴 绝不跳过确认步骤。用户可能改主意。

---

## 完整流程图

```
用户消息
  │
  ├──→ cc-active-sessions.sh --json
  │      │
  │      ├── [] ──→ 正常处理（无 CC）
  │      └── [{session, state, ...}]
  │             │
  │             ├── ≥2 sessions ──→ 匹配 topic / 问用户
  │             └── 1 session
  │                    │
  │                    ├── 分类 intent（5 种）
  │                    │
  │                    ├──→ cc-route.sh --session X --intent Y
  │                    │
  │                    └── 读 .recommendation.action：
  │                          ├── handle_directly → Hermes 处理
  │                          ├── report_status   → 📡 状态汇报
  │                          ├── queue           → 回用户 + 等 turn-done + 转发
  │                          ├── forward_now     → tmux_type + Enter
  │                          └── interrupt       → 确认 → Escape + 转发
```

---

## 边界情况

| 场景 | 处理 |
|------|------|
| cc-route.sh 返回 `error: jq_unavailable` | action 已降级为 handle_directly，Hermes 自行处理 |
| 多个 CC session 且无 topic 匹配 | 列给用户选（"route-review 还是 wrr-research？"） |
| queue 等了超过 10 分钟 | 主动抓屏确认 CC 是否冻结，汇报用户 |
| CC 状态是 GONE/ERROR/SHELL | action 必定是 handle_directly，可建议用户跑 cc-finish 收尾 |
| 用户消息是"CC 在干嘛" | intent=status_query → report_status，不碰 CC |
| forward_now 发了但 CC 没消费 | cc-send-robust.sh 会自动重试，3 次失败则汇报 |

---

## 相关文件

- `scripts/cc-route.sh` — 路由决策引擎
- `scripts/cc-active-sessions.sh` — 活跃 session 枚举
- `scripts/cc-wait-marker.sh` — turn-done 事件等待
- `scripts/cc-send-robust.sh` — send-keys 健壮封装
- `tests/test-route.sh` — 21 项路由测试
