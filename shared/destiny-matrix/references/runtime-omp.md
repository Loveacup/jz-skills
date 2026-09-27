# omp 运行时映射

只映射 `team-orchestration.md` 的中立动词与能力词，不改 Stage、数据契约或质量门。判定方法见 `team-orchestration.md §10`（工具表有 `task` 子代理工具、可 `write agent://<id>` → omp）。

> 本文件是 omp 工具名在 skill 里**唯一**出现的地方。omp 升级改名时只改这里；工具名以运行时工具表为准，本表与工具表冲突时信工具表并回填本表。

## 编排动词

| 动词 | omp 实现 |
|---|---|
| `dispatch(stage, 席位[])` | 一个 Stage 一次 `task` 调用（batch 形）：`{context, tasks:[…]}`。每席位一个 item：`name: Dm<席位CamelCase>`、`agent: dm-deep｜dm-research｜dm-light`（分档见 `team-orchestration.md §11`）、`task: 席位契约全文 + 本席位输入切片 + $DM/$DM_PY/$WS/<席位> + capability_map + 委派五要素`；有 schema 的席位加 `outputSchema: <schemas/*.json 内容>`、`schemaMode: "strict"` |
| `context`（批次共享背景） | 会渲染进**同批每个**子代理的系统提示。只放本批所有席位都可见的中性材料；S4 批次严禁放任何一维 JSON 或成稿（`team-orchestration.md §1.3`） |
| `barrier(stage)` | 结果自动送达；本批全部送达前不派下游。无事可做时用 `wait`，不轮询 `proc://` |
| `collect(席位)` | 结果正文；全文 `agent://<id>`；JSON 字段 `agent://<id>/<key>`。schema 席位读 `structuredOutput.data` 与校验状态。每席位记 `resolvedModel`、`resolvedModelIsFallback` 进 `runtime_trace` |
| `message(to)` | `write agent://<id>`。**修订流不用**（`team-orchestration.md §2`） |
| `fresh_spawn(席位)` | 新的 `task` item、新 `name`（如 `DmBookWriterR1`）；task 正文按 §2 注入，不带被拒章节原文 |
| `ask_user` | Leader 用 `ask`；teammate 没有此能力，问题从 `questions_for_user` 收集后由 Leader 代问 |
| `teardown` | `read proc://` 查看仍在运行的作业；滞留者 `write proc://<id>/kill` |

## 能力词 → omp 通道

| 能力词 | omp 通道 | 备注 |
|---|---|---|
| 【读文件】 | `read`（`skill://destiny-matrix/<路径>` 或 `$DM/<路径>`） | `skill://` 只读 |
| 【跑脚本】 | `bash`：`$DM_PY $DM/scripts/<脚本>.py …` | 不用 PATH 上的 `python3` |
| 【写成书】/【写临时】 | `write` 到绝对路径（成书：交付目录；临时：`$WS/<席位>/`） | 不写 `local://`：同会话所有子代理共享其根目录 |
| 【网页检索】 | `web_search`（本机 `modelRoles.web` 已指向 Exa）；工具表里有 Exa MCP 时可用其高级检索 | MCP 工具名从工具表读，不写死 |
| 【抓网页】 | `read <URL>` | 服务端渲染源 |
| 【真实浏览器】 | `eval` 中的 `browser` 对象（首次使用前读 `xd://eval/browser`）；截屏、表单提交 | 不可用时记「降级：真实浏览器→不可用」 |
| 【问用户】 | `ask`（仅 Leader） | — |

## 模型分档

三个档位 agent 定义在 `$DM/adapters/omp/dm-{deep,research,light}.md`，软链到 `~/.omp/agent/agents/`（`doctor.py` 核验）。frontmatter 只写 omp 自带角色：

| agent | `model`（按序尝试） | `thinking-level`（角色无后缀时的后备） |
|---|---|---|
| `dm-deep` | `@slow` → `@default` | high |
| `dm-research` | `@default` → `@slow` | medium |
| `dm-light` | `@smol` → `@task` | low |

- 角色指向哪个模型由用户 `modelRoles` 决定；角色后缀（如 `:auto`）优先于 frontmatter 的 `thinking-level`。
- 只调一档：`task.agentModelOverrides: { dm-research: "@slow" }`（值写角色）。
- `prewalk: false`、`advisor: false` 已写在 frontmatter；`doctor.py` 会提示是否在 `config.yml` 的 `task.agentPrewalk` / `task.agentAdvisor` 里同样锁 off（与 sil-* 做法一致，不自动改用户配置）。
- light 档失败（脚本报错后仍无 G1 齐备 JSON）→ 同席位改用 `dm-research` 重派，trace 记录实际档位。

## 运行时差异要点

- omp 没有 `blockedBy`：依赖靠「一个 Stage 一批 + barrier」表达，等价且更不易漏。
- 子代理不继承对话历史，只继承 skill/上下文文件与共享的 `local://`——判官隔离的风险点在 `local://` 与批次 `context`，不在历史。
- 单个子代理结果超过预览上限时，正文用 `agent://<id>` 读全文，不要把截断预览当完整产出注入下游。
