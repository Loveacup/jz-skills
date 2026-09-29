# omp 运行时映射

本文只把 [`team-orchestration.md`](team-orchestration.md) 的中立阶段、角色档位与能力映射到 omp；DAG、输入隔离、输出形状、裁决、复用和发布状态由该文件唯一规定。

## 编排动词

| 动词 | omp 实现 |
|---|---|
| `dispatch(stage, roles)` | 每席位一个 `task` item，使用本文件下方规定的 adapter；共享 `context` 只放同批均可见的中性说明，席位专属原始输入仅放该 task 的内容。 |
| `barrier(stage)` | 等待 DAG 中本批所需任务结果全部送达后再派遣下游，不轮询后台任务。 |
| `collect(role)` | 读取完整 task 结果；schema 任务核验结构化输出。Leader 是 runtime_trace 唯一写入者，登记实际可观察模型、用量、状态和输入/输出产物 ID。 |
| `message(to)` | `write agent://<id>` 传递必要依赖、纠错或产物 ID；不得用共享文件路径替代判官输入隔离。 |
| `fresh_spawn(role)` | 新 `task` item、新名称和独立上下文。fresh writer 仅接收修订包及获准保留的资产，不接触被拒正文。 |
| `ask_user` | 由 Leader 使用可用询问通道；teammate 仅返回 `questions_for_user`。 |
| `teardown` | 按当前工具表检查运行中任务并清理残留。 |

## 能力映射

| 能力 | omp 通道 | 边界 |
|---|---|---|
| 【读文件】 | `read` | `skill://` 只读。 |
| 【跑脚本】 | `bash`：`$DM_PY $DM/scripts/<脚本>.py …` | 不用 PATH 上的解释器。 |
| 【写成书】/【写临时】 | `write` 到授权的工作区路径 | 不将 `local://` 当作隔离区；按流程单一写盘权限执行。 |
| 【网页检索】/【抓网页】 | 使用运行时工具表提供的 `web_search`、URL `read` 或 MCP | 具体工具以当前工具表为准；外传本案资料前检查逐项授权。 |
| 【真实浏览器】 | `eval` 中 `browser`（先读 `xd://eval/browser`） | 工具不可用则报告无法核验，不推测结果。 |
| 【问用户】 | Leader 的询问通道 | 仅 Leader 可问。 |

## 档位与 adapter

adapter 是 `agents` 的运行模板，不改变角色职责：

| 档位 | 角色 | adapter | frontmatter `model` 顺序 |
|---|---|---|---|
| deep | 四位 judge、chief-judge、synthesizer、book-writer、book-finalizer | `dm-deep` | `["@slow", "@default"]` |
| research | external-verifier、四位 analyst、love-specialist、growth-specialist、chart-director | `dm-research` | `["@default", "@slow"]` |
| light | intake-refiner、caster、确定的机械式布局补丁 | `dm-light` | `["@smol", "@task"]` |

- model role 解析由用户当前 `/model` roles 决定；skill 不写具体模型 ID。允许并尊重 `task.agentModelOverrides`，例如 `{"dm-research":"@slow"}` 或 `{"dm-deep":"@default:high"}`；不修改全局 roles。
- thinking 后缀优先于 adapter 的 `thinking-level`；无后缀时才使用 frontmatter 值。`:auto` 保留为自动模式，不统一改成 high/xhigh。
- 只有 light 能力不足且任务仍适合相邻档时，最多升级到 research 一次；输入、文件、参数或依赖错误先修原因，不能原样重跑。不得将 deep 的分析、judge 或 finalizer 任务降为 light。
- 若模型角色之间实际上解析为相同模型，只报告无分层收益；不能据档位名称推断费用或能力。

## Trace 采集

Leader 按 `team-orchestration.md` 登记每项 task：`requested_role`、`configured_model`、`resolvedModel`、`resolvedModelIsFallback`、`model_observation_source`、时间、耗时、指纹、复用关系、状态、输入/输出产物及原生用量事件。未由运行时明确提供的模型/费用/token 字段为 `null`；不按字数、时间或角色档位估算。

同案复用只由 `team-orchestration.md` 的 fingerprint 规则决定。判官结果在原始输入、计算方法、版本及角色配置不变时可复用；仅分析稿改写时 fresh chief 重比，不重派判官。
