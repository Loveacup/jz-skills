# oaipro + Claude Opus 4.7 — Kanban 上下文格式冲突

## 症状

Planner profile 配置 `custom:oaipro` + `claude-opus-4-7`，简单查询正常，但 Kanban worker 运行中崩殂：

```
BadRequestError [HTTP 400]
Provider: custom  Model: claude-opus-4-7
Endpoint: https://api.oaipro.com/v1
Error: HTTP 400: messages.5.content.0.text.text: Field required
```

## 诊断

- 端点可通（`curl https://api.oaipro.com/v1/models → 200`）
- API key 有效
- 简单单轮查询成功：`hermes -p planner chat -q "说一个字：好" --yolo` → 正常返回
- Kanban worker 崩溃发生在 conversation 的第 5 条消息索引处 — 工具调用后的消息历史中出现了 oaipro API 无法接受的 content block 格式

## 根因分析

`custom:oaipro` 是 OpenAI Chat Completions 兼容端点。Hermes 为 Anthropic 模型构造消息时使用 content blocks 格式（`[{"type": "text", "text": "..."}, {"type": "tool_use", ...}]`）。oaipro 端点在某些场景下对 content block 结构有更严格的校验，导致 mid-conversation 格式不匹配。

具体触发条件：工具调用返回结果后，conversation history 中的某条消息 content 格式不符合 OpenAI Chat Completions schema 的嵌套 `text.text` 要求。

## 处理流程

### 阶段 1：确认非配置之过（首次崩殂）

1. **先做隔离测试**：`hermes -p <profile> chat -q "简单查询" --yolo`。若简测通过，说明 config 正确，崩殂是 Kanban context 消息格式冲突。
2. 等待 Kanban dispatcher 自动重试（max-retries=2），有时第 2 次能成功；或手动 `unblock` + `dispatch` 重跑。

### 阶段 2：多次崩殂后奏请换模型（≥3 次）

- v0.8 planner 崩 2 次后第 3 次自愈通过；v0.9 planner 崩 3 次未愈。
- 若 ≥3 次仍不通过，**奏请 Emperor 定夺**，提供清晰选项：
  1. 改稳定 provider（如 kimi-k2.6 / deepseek-v4-pro）
  2. 继续 oaipro + 手动解阻
  3. 其他方案
- **Emperor 最终批准切换**：v0.9 中 Emperor 选择 `kimi-k2.6 (kimi-coding)`，此后 planner 再无崩殂。配置变更有 Emperor 明旨即可，非绝对禁止。

### 同步动作

模型切换后需同步更新：
- `agent-registry.md` 中 planner 模型记录
- 相关归档文档中的模型配置表

## 历史教训

- **v0.8 教训**：Regent 擅改 planner config（oaipro→kimi），Emperor 当场纠正（"Planner 就是要改成 custom:oaipro + claude-opus-4-7啊"）。此后 config 修改必须有旨意。
- **v0.9 纠偏**：Regent 过度遵守此规则——崩 3 次仍不敢奏请换模。正确做法：隔离测试通过 → 确认非 config 错误 → 若重试无效（≥3 次）→ 奏请 Emperor 定夺并提供清晰选项（含稳定备选 provider）。
- **最终决议**（v0.9 Emperor 明旨）：Planner 改用 `kimi-k2.6 (kimi-coding)`，此后所有 Kanban 任务稳定运行，零崩殂。

## 环境

- Provider: `custom:oaipro` → `https://api.oaipro.com/v1`
- Model: `claude-opus-4-7`
- 记录时间: 2026-05-18
