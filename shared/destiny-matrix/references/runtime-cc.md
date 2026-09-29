# Claude Code 运行时映射

本文只把 [`team-orchestration.md`](team-orchestration.md) 的中立阶段、任务和数据合同映射到 Claude Code；阶段依赖、数据隔离、质量门和修订状态均以该文件为唯一规范。

## 编排动词

| 动词 | Claude Code 实现 |
|---|---|
| `dispatch(stage, roles)` | 每个角色使用独立 `Agent` 子任务，名称含席位及修订轮次；prompt 首步读取 `agents/<seat>.md` 全文与其中列明的合同，再接收该席位专属输入切片。团队工具可用时以任务依赖表达 DAG；否则由 Leader 按 barrier 顺序派遣。 |
| `barrier(stage)` | 等待本批所有必要角色完成；只派遣 DAG 中已满足依赖的后续阶段。 |
| `collect(role)` | 收集结构化结果及实际可观察的模型/遥测字段；由 Leader 按唯一 runtime_trace 合同登记。 |
| `message(to)` | 只用于传递依赖或已登记的产物 ID；修订任务使用干净的新 writer 上下文，不把被拒稿交给 writer。 |
| `fresh_spawn(role)` | 新建 Agent 子任务和名称；依 `team-orchestration.md` 修订包合同提供素材。 |
| `ask_user` | 只有 Leader 询问；席位把缺口和必要问题写回 Leader。 |
| `teardown` | 有团队/后台任务时按当前工具表清理；未提供清理工具时确认必要任务已结束。 |

## 能力映射

| 能力 | Claude Code 通道 |
|---|---|
| 【读文件】 | `Read` |
| 【跑脚本】 | `$DM_PY $DM/scripts/<脚本>.py …` |
| 【写成书】/【写临时】 | 仅按 `team-orchestration.md` 的写盘权限写工作区；writer 写 HTML，Leader 按合同执行 PDF 导出。 |
| 【网页检索】/【抓网页】 | 使用当前工具表中的检索/抓取工具；先检查本次是否有外传个案资料的授权。 |
| 【真实浏览器】 | 使用本次会话已提供的浏览器工具；未提供时如实记能力不可用。 |
| 【问用户】 | 仅 Leader。 |

## 模型档位

| 档位 | 席位 | Claude Code `model` 设置 |
|---|---|---|
| deep | judges、chief-judge、synthesizer、book-writer、book-finalizer | `inherit` |
| research | external-verifier、analysts、专题角色、chart-director | `inherit` |
| light | intake-refiner、caster、受限布局补丁 | 按现有模型家族别名配置；不写具体模型 ID。 |

- deep/research 跟随用户当前主会话选择。只有确定的轻量抽取、计算执行、资产装配或版式补丁使用 light；需要解释、内容裁决或终审时用对应 deep/research 档。
- 查阅当前 `CLAUDE_CODE_SUBAGENT_MODEL` 等覆盖设置并记录可观察的解析结果；不修改用户全局配置，不将配置值说成已实际解析的模型。
- Claude Code 的 `inherit` 是运行时策略，不套用 OMP 的角色后缀或 `task.agentModelOverrides` 规则。
- 模型选择与实际模型缺失时，runtime_trace 对应字段置 `null` 并标明观测来源；不按调用时长推测。

运行阶段和 task_fingerprint、runtime_trace、同案复用及预算暂停机制见 [`team-orchestration.md`](team-orchestration.md)。
