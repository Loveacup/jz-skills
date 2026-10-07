# Claude Code 运行时映射

本文只把 [`team-orchestration.md`](team-orchestration.md) 的中立阶段、任务和数据合同映射到 Claude Code；阶段依赖、数据隔离、质量门和修订状态均以该文件为唯一规范。

## 编排动词

| 动词 | Claude Code 实现 |
|---|---|
| `dispatch(stage, roles)` | 每个席位一次 `Agent` 调用，`name` 含席位、subject 及修订轮次。判官用 `subagent_type:"dm-judge-<dimension>"`，prompt 为 `judge_payload.py --layout split` 的个案载荷全文（未安装分维度席位时用 `"dm-judge"` 配 `--layout inline`）；其他席位用 `general-purpose`，prompt 首步读取 `agents/<seat>.md` 全文与其中列明的合同，再接收该席位专属输入切片。`model` 按下方档位表；同批席位在同一条消息里并行发出。 |
| `barrier(stage)` | 交互会话中子代理默认后台运行，每个完成时自动送达完成通知；本批必要席位的通知全部到齐即 barrier，不轮询、不 sleep。只派遣 DAG 中已满足依赖的后续阶段。当前工具表有团队任务工具（`TaskCreate` 等）时可用任务依赖表达 DAG；没有时由 Leader 按 barrier 顺序派遣。 |
| `collect(role)` | 从完成通知取结构化结果及实际可观察的模型/遥测字段；由 Leader 按唯一 runtime_trace 合同登记。 |
| `message(to)` | `SendMessage`（`to` 为该子代理 `name`）续用同一上下文，只传递依赖或已登记的产物 ID。不向判官续发任何材料；修订任务使用干净的新 writer 上下文，不把被拒稿交给 writer。 |
| `fresh_spawn(role)` | 新的 `Agent` 调用和新 `name`；依 `team-orchestration.md` 修订包合同提供素材。 |
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

| 档位 | 席位 | `subagent_type` | `model` |
|---|---|---|---|
| deep（隔离） | 四位 judge | `dm-judge-jung`、`dm-judge-bazi`、`dm-judge-ziwei`、`dm-judge-astro` | 省略；定义内 `inherit` |
| deep | chief-judge、synthesizer、book-writer、reader-editor（S8.5）、book-finalizer | `general-purpose` | 省略（继承主会话） |
| research | external-verifier、analysts、专题角色、chart-director | `general-purpose` | 省略（继承主会话） |
| light | intake-refiner、caster、受限布局补丁 | `general-purpose` | `"haiku"` |

- deep/research 跟随用户当前主会话选择。只有确定的轻量抽取、计算执行、资产装配或版式补丁使用 light；需要解释、内容裁决或终审时用对应 deep/research 档。用户要求全程不降档时，light 席位同样省略 `model`。
- 模型解析顺序为：派遣时的 `model` 参数 → agent 定义的 `model` → `CLAUDE_CODE_SUBAGENT_MODEL` → 主会话模型。查阅当前覆盖设置并记录可观察的解析结果；不修改用户全局配置，不将配置值说成已实际解析的模型。
- Claude Code 的继承是运行时策略，不套用 OMP 的角色后缀或 `task.agentModelOverrides` 规则。
- 模型选择与实际模型缺失时，runtime_trace 对应字段置 `null` 并标明观测来源；不按调用时长推测。

## 判官隔离 adapter（dm-judge）

安装（只加软链，不改用户设置）：

```bash
mkdir -p ~/.claude/agents
"$DM_PY" "$DM/scripts/build_judge_adapters.py"
for f in dm-judge dm-judge-jung dm-judge-bazi dm-judge-ziwei dm-judge-astro; do
  ln -sf "$DM/adapters/cc/$f.md" ~/.claude/agents/$f.md
done
```

四个分维度席位由 `build_judge_adapters.py` 生成，正文里已有该维的判官合同、framework、知识卡与来源索引，Leader 只需发出十几 KB 的个案载荷。合同或知识卡改动后重新运行该脚本；`doctor.py` 的 `judge.adapters.fresh` 会核对。Claude Code 在会话开始时载入 agent 定义，新装或重新生成后要开新会话才生效。通用的 `dm-judge` 留作未安装分维度席位时的退路。

`doctor.py --json` 的 `cc.agent.dm-judge` 与 `cc.agent.dm-judge.tools` 检查链接和 frontmatter。定义要点：

- `tools: ToolSearch`。Claude Code 拒绝派生工具列表解析为空的子代理（报 “would be spawned with zero tools”），`TodoWrite` 与任务工具在当前模型上默认不提供，列它们同样被拒。`ToolSearch` 只检索子代理自身工具池里的延迟工具，而该池没有文件、Shell、网络或派遣工具，因此读不到工作区。冒烟中子代理实际只见到运行时注入的 `SubagentHandback`，未见 `Read`/`Bash`。
- `disallowedTools: mcp__*` 去掉全部 MCP 工具；`omitClaudeMd: true` 不加载用户、项目和本地 CLAUDE.md；不设 `skills`、`memory`、`mcpServers`。`maxTurns: 4` 限制轮次。
- 判官只看到定义正文、Leader 的派遣 prompt 和运行时环境段。要标 `input_only`，prompt 必须与 `judge_payload.py` 输出的载荷逐字一致，split 时席位定义还须与现行合同一致（§3）。

不为 light/research/deep 另建 Claude Code 定义：`general-purpose` 已继承主会话模型和完整工具，light 只需在派遣时传 `model:"haiku"`，席位纪律已在 `agents/<seat>.md`。另建定义只会复制 omp adapter 的纪律文本，还要多装三条软链，没有额外的隔离或模型收益。

运行阶段和 task_fingerprint、runtime_trace、同案复用及预算暂停机制见 [`team-orchestration.md`](team-orchestration.md)。
