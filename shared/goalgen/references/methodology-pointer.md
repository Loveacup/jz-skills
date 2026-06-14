# goalgen 方法论指针

goalgen 是「多 agent 协作 goal 方法论」的可执行落地。**承重墙逐条、capability-match、gate_mode、跨-CLI 驱动 skill、四类拓扑** 等详尽机制，权威源在 Obsidian：

`Documents/Obsidian/<VAULT>/20-Areas/20_技术项目/多Agent协作 goal 方法论/`

| 文档 | 内容 |
|---|---|
| `00_总览与导航` | 问题域 + 4 边界 + 9 承重墙总表 + 术语 + 证据约定 |
| `01_方法论主文-承重墙与goal生命周期` | P1–P9 逐条规范 + goal 生命周期状态机 + **§1.13 确认门模式（human/auto）** |
| `02_CLI能力清单-自描述接入schema附录` | 15 字段 schema + 种子卡（§G 实测值）+ `cross_cli_drivers` + `execution_options` |
| `03_协作协议模板-四类拓扑与goal模板` | 星型/流水线/对等评审/嵌套 协议 + 终止/升级/审计门矩阵（含 gate_mode 列） |
| `04_goal生成器skill需求规格-生命周期与红线` | 本 skill 的字段级 SPEC：输入/输出契约/19字段/capability-match/25检查点 |
| `05_goalgen 构建方案` | 架构 + 跨 CLI 移植 + roadmap + 构建治理 + dogfood goal |

> 证据态约定：`[C]` 已确认（official-doc / local-runtime-truth §G）/ `[I]` 设计推断。三省六部/监国/regent-3s6m/御史台/A2A 均为**已退役方案**（2026-06-04 退役封存），不作 live 锚定。
