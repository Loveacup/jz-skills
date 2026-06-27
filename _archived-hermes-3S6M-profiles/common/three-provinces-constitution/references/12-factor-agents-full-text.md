# 12-Factor Agents — 原文全量提取
> 来源: https://github.com/humanlayer/12-factor-agents
> 提取时间: 2026-05-26

---

## Factor 1: Natural Language to Tool Calls

One of the most common patterns in agent building is to convert natural language to structured tool calls.

核心理念: LLM 把自然语言翻译成结构化 JSON（如 Stripe API 调用参数），确定性代码执行，不依赖 agent 框架的"自主循环"。

关键是分离：LLM 负责"下一步做什么"的判断，代码负责"怎么做"。

---

## Factor 2: Own your prompts

Don't outsource your prompt engineering to a framework.

核心理念: Prompt 是一等代码，不是框架的黑箱配置。自己写 prompt template，用 BAML 或任何工具，但要完全掌控发送给 LLM 的每一个 token。

五大好处: 完全控制、可测试可评估、快速迭代、透明、可利用非标 API 技巧。

---

## Factor 3: Own your context window

Everything is context engineering. LLMs are stateless functions that turn inputs into outputs.

核心理念: 不必用标准 message-based 格式。用自定义 XML 标签打包上下文（如 `<slack_message>`、`<list_git_tags_result>`、`<error>`），塞进单条 user message，token 和注意力效率远超标准格式。

关键模式: Thread → events → event_to_prompt() → 单条 user message。

上下文包含: prompt + RAG + 历史工具调用 + 跨会话记忆 + 输出格式指令。

控制要点: 信息密度、错误格式、安全过滤、token 效率。

Karpathy、Tobi 等人后来都认可了"上下文工程"这个概念。

---

## Factor 4: Tools are just structured outputs

Tools don't need to be complex. At their core, they're just structured output from your LLM that triggers deterministic code.

核心理念: LLM 输出 JSON → 代码执行对应操作 → 结果回写上下文。LLM 决定"做什么"，代码控制"怎么做"。工具调用不等于必须执行——你有权在中间插入审批、修改参数、甚至完全替换执行逻辑。

配合 Factor 8 使用效果最佳。

---

## Factor 5: Unify execution state and business state

SIMPLIFY - unify execution state (current step, waiting status, retry counts) and business state (what's happened so far) as much as possible.

核心理念: 用一条统一事件流（Thread）作为唯一真相来源。所有状态都可以从 context window 推断出来。不要单独维护"执行状态"和"业务状态"。

七大好处: 简洁、可序列化、可调试、灵活扩展、可恢复、可分叉、可观察。

Thread → serialize → 随时恢复或分叉到新上下文。

---

## Factor 6: Launch/Pause/Resume with simple APIs

Agents are just programs, and we have things we expect from how to launch, query, resume, and stop them.

核心理念: 简单 API 启动 agent；长任务时 pause 并持久化；webhook 触发 resume 从断点继续。

关键: pause 必须能在"工具选择"和"工具执行"之间发生——这是做审批的基础。

---

## Factor 7: Contact humans with tool calls

You might get better results by having the LLM *always* output JSON, and then declare its intent with tokens like `request_human_input` or `done_for_now`.

核心理念: 人类交互建模为 tool call（`RequestHumanInput`），不要硬编码在代码里。LLM 始终输出结构化 JSON，通过 intent 字段区分"调工具"和"找人类"。

在内循环（Agent→LLM）和外循环（Agent→Human→Agent）之间切换时，统一事件流自然承载。

支持多人协作、多 Agent 通信、持久化工作流。

---

## Factor 8: Own your control flow

Build your own control structures that make sense for your specific use case.

核心理念: 三种控制流模式——
- `request_clarification`: break loop，等人类回复
- `fetch_git_tags`: 同步执行，结果追加后 continue loop
- `deploy_backend`: 高风险操作，break loop 等审批

最大的框架痛点: 不能在"工具选择"和"工具执行"之间中断——导致要么 sleep 等待（脆弱），要么只做低风险操作（局限），要么 yolo（危险）。

---

## Factor 9: Compact Errors into Context Window

One of the benefits of agents is "self-healing" — LLM can read an error and figure out what to change.

核心理念: 错误捕获后格式化成紧凑形式追加到上下文窗口，设连续错误上限（如 3 次），超过阈值 → 升级给人类或重置上下文。

错误太多的根因通常是 agent 范围太大——结合 Factor 10（小而专）从根本上解决。

---

## Factor 10: Small, Focused Agents

Rather than building monolithic agents that try to do everything, build small, focused agents that do one thing well.

核心理念: 上下文窗口越长，LLM 越容易迷失。每个 agent 3-20 步，职责单一。Agent 只是更大确定性系统中的一块积木。

LLM 变强了还需要小 agent 吗？需要——更强的 LLM 能处理更长的上下文，意味着同样的小 agent 能覆盖 DAG 中更大的一块，但"小而专"的原则不变。

NotebookLM 团队: "最神奇的时刻总是发生在模型能力的边缘。"

---

## Factor 11: Trigger from anywhere, meet users where they are

Enable users to trigger agents from slack, email, sms, or whatever channel. Enable agents to respond via the same channels.

核心理念: 支持多平台触发（cron、webhook、消息）+ 多平台响应。结合 Factor 6（pause/resume）和 Factor 7（human contact），实现外循环 agent。

好处: 让用户在现有工作流中使用 AI、非人类触发（事件/cron）、高风险操作可审批。

---

## Factor 12: Make your agent a stateless reducer

This one is mostly just for fun.

核心理念: Agent 核心逻辑 = `(state, event) → new_state` 的纯函数。状态从外部传入，决策后返回新状态。thread 是 foldl 的累积器。

虽说是 "for fun"，但这让 agent 可测试、可重放、可预测。

---

## Honorable Mention: Factor 13 — Pre-fetch all the context you might need

（附录，非正式第十二条之外的第十三条）
