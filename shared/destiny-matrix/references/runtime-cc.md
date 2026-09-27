# Claude Code 运行时映射

只映射 `team-orchestration.md` 的中立动词与能力词，不改 Stage、数据契约或质量门。判定方法见 `team-orchestration.md §10`（工具表有 `Agent` → cc）。

> 本文件是 cc 工具名在 skill 里**唯一**出现的地方。团队原语（`TaskCreate` / `SendMessage` / 旧版 `TeamCreate` 等）以实际出现在工具表里的为准；不在工具表里就走「逐 Stage 调 `Agent`、结果回主会话」，Stage 语义不变。

## 编排动词

| 动词 | cc 实现 |
|---|---|
| `dispatch(stage, 席位[])` | 同一条消息里对本 Stage 每席位调一次 `Agent`（`subagent_type: "general-purpose"`，`name: <席位>`），prompt = 席位契约全文 + 输入切片 + `$DM/$DM_PY/$WS/<席位>` + capability_map + 委派五要素；团队可用时用 `TaskCreate` 并以 `blockedBy` 声明上游 |
| `barrier(stage)` | 本批 `Agent` 全部返回（团队模式：`TaskList` 扫描本批 completed） |
| `collect(席位)` | `Agent` 返回正文（团队模式：`TaskGet`）；schema 席位让 teammate 只输出符合 `schemas/*.json` 的 JSON，Leader 解析失败即重派 |
| `message(to)` | `SendMessage`（团队模式）。**修订流不用** |
| `fresh_spawn(席位)` | 新 `Agent` 调用、新 name |
| `ask_user` | `AskUserQuestion`（Leader） |
| `teardown` | 团队模式下按工具表提供的团队清理原语收尾；否则无需 |

**已知坑**（memory/known-issues.md「TaskCreate 失败 + Agent 启动成功」）：同一消息里 `TaskCreate × N + Agent × N` 时，TaskCreate 失败不代表 Agent 没启动——先核实，再决定是否重发，否则会重复派遣、双倍写盘。

## 能力词 → cc 通道

| 能力词 | cc 通道 |
|---|---|
| 【读文件】 | `Read`（`$DM/<路径>`） |
| 【跑脚本】 | `Bash`：`$DM_PY $DM/scripts/<脚本>.py …` |
| 【写成书】/【写临时】 | `Write` 到绝对路径（临时：`$WS/<席位>/`，不用会话 scratchpad——harness 会把 scratchpad 文件推给其他席位，见 known-issues） |
| 【网页检索】 | `WebSearch` |
| 【抓网页】 | `WebFetch` |
| 【真实浏览器】 | 工具表里的浏览器/Playwright MCP 工具 |
| 【问用户】 | `AskUserQuestion`（仅 Leader） |

## 模型分档

deep / research 档用 `inherit`（跟随主会话 `/model`）；light 档派遣时给 `Agent` 传家族别名（如 `sonnet`），不写具体模型 ID。全局设置 `CLAUDE_CODE_SUBAGENT_MODEL` 会让所有 teammate 降级——`doctor.py` 检查并报告。
