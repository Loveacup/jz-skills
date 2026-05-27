# Regent 3S6M v0.5 session lessons

Session-derived durable lessons for 三省六部 / Kanban governance.

## Health check pattern

A reusable profile health check should validate three layers per profile:

1. `config.yaml` parses and includes `model.default`, `model.provider`, `agent.system_prompt`, and non-empty `toolsets`.
2. The provider credential is discoverable from the same source Hermes will use (profile/root config and `.env`), not just the current shell environment.
3. A smoke test actually starts the profile and asks for a minimal response, e.g. `hermes -p <profile> chat --yolo -q "只回复 OK"`.

Use a timeout per profile and classify failures separately: config invalid, missing key, invalid key (401/403), rate limit (429), provider down (5xx/timeout), unknown.

## Avoid false credential conclusions

Do not conclude a provider is broken solely because `DEEPSEEK_API_KEY` or another env var is absent in the current agent shell. Hermes may read credentials from config/auth pools/.env. Verify with the same CLI path the worker uses: `hermes -p <profile> chat ...` or `hermes auth list <provider>`.

## Reviewer blocks are gates, not always failures

If a reviewer task blocks with `review-required: verdict=reject` and lists concrete blockers, this is a successful 门下省 gate decision. Do not blindly `unblock` and rerun. Instead create a new revision task that quotes the blockers, then a new review task depending on the revision.

## Main-channel knowledge base coordination

When the user says the main channel is optimizing Obsidian/knowledge-base docs, do not overwrite those docs from a side workflow. Have the archivist prepare a pending archive package in its workspace or a clearly marked staging note, then merge once the main channel version is ready.

## 监国太子必须实时知悉 Kanban 进度

派工后监国太子不知节点推进是三省六部运营的核心盲区——用户多次纠正（"每次都要我点进度""有节点推进要向我通报""你是怎么掌控进度的？每次都不知道啊"）。解法：

1. **每轮开始先验板**：不做任何事之前，先跑 `hermes kanban list --json` 看有无状态变更
2. **部署 kanban-watchdog**：纯脚本 cron job，自发现全部活跃任务，变更推送。见 `references/kanban-watchdog-pattern.md`
3. **有 blocked 立刻疏通**，有 done 立刻衔接下一步，不用等父皇催
4. **推送要有仪式感**：输出用三省六部格式（`【尚书省 · Kanban 奏报】`），部门名中文映射

## A2A spec review pitfalls

A2A governance specs should avoid these blockers:

- Contradicting star topology by allowing informal direct lateral messages. Legal lateral work should be either Kanban parent/child handoff or a bounded regent-authorized request with `task_id`, timeout, budget, and permissions.
- Leaving `correlation_id`, `permissions`, or `evidence` vague. Define allowed shape, required fields, and minimal examples.
- Overloading `review`. Separate `gate_review` (门下省准驳), `code_review` (implementation review), and `comment` (ordinary note).
