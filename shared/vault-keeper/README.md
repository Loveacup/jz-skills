# vault-keeper

知识库生命周期治理引擎 —— **Obsidian x AI 方法论 v2.0** 的控制面。

数据面（vault，纯 Markdown，Obsidian Sync 畅通）/ 控制面（本 skill，git 版本化，多 CLI 加载）分离。

## 它做什么

执行知识库内容的**生命周期状态机**与**三道闸**：

```
源(raw,00-Inbox永久) →🟢抽取建页→ 候选(candidate,01-Staging沙盘)
   →🟡晋升闸(硬门槛+风险×置信矩阵)→ 正本(core,种子→常青) →🔴发布/删除(人工)
```

- **写入闸**：禁任何工具直接写 `lifecycle_state: core`。
- **晋升闸**：硬门槛（溯源/双链/合规/去重）+ 风险×置信矩阵 → 自动/人工/退回/裁决。
- **变更闸**：矛盾走裁决卡（旧 claim 不删），所有操作写 append-only `PIPELINE_LOG`。
- **复合置信度**（非 AI 自评）+ **风险定级 R1/R2/R3** + **Lint** + **自适应抽样自校准**。

## 结构

```
vault-keeper/
├── SKILL.md            # 多 CLI 编排契约（agent 入口）
├── engine/             # 确定性引擎（$VK）
│   ├── common.py       # vault 定位 / frontmatter 读写 / 工具
│   ├── config.py       # 解析 vault GOVERNANCE.md 阈值（不硬编码）
│   ├── log.py          # PIPELINE_LOG 唯一写入口
│   ├── confidence.py   # 复合置信度
│   ├── risk.py         # R1/R2 风险定级
│   ├── gate.py         # 晋升闸：硬门槛 + 矩阵路由
│   ├── lint.py         # 孤立/断链/缺源/陈旧/合规
│   ├── sampling.py     # 抽样 + 自校准
│   ├── capture.py      # 源落 00-Inbox（id+hash）
│   ├── ingest.py       # 建/更新 candidate（确定性归档）
│   ├── promote.py      # 移入 core + 翻状态 + 日志
│   ├── wiki_save.py    # Query 回填（对话→源）
│   ├── check_write_gate.py  # 写入闸违规检测（vault pre-commit）
│   └── backfill_state.py    # 冷启动批量标 core
└── references/matrix.md     # 矩阵/R 级/阈值/取证卡速查
```

## 安装

```bash
cd ~/code/jz-skills && git pull
bash deploy/sync-all.sh        # 同步到 ~/.claude/skills · ~/.hermes/skills · pi
export VAULT=~/Documents/Obsidian/AlexCai
```

## 用法

由 agent（CC/Codex/Hermes/Pi）经 `SKILL.md` 驱动；底层可直接跑：

```bash
VK=~/.claude/skills/vault-keeper/engine
python3 $VK/config.py                          # 看当前阈值
python3 $VK/gate.py "$VAULT/01-Staging/某页.md" --to 30-Resources/10_AI知识
python3 $VK/lint.py                            # → 88-审计/lint-*.md
python3 $VK/sampling.py --days 7
```

## 约束

- 依赖：Python 3.9+ 与 `pyyaml`（轻量）。不引入 Node/Louvain 等重依赖。
- 改阈值 = 编辑 vault `GOVERNANCE.md`（R3）；改逻辑 = 改本 engine + **git PR review（人工 gate）**。
- 委托 `obsidian`（文件 IO）/ `obsidian-md-ac`（格式），不自行实现。

完整设计见 vault 内 `20-Areas/20_Obsidian方法论/Obsidian x Ai方法论_v2.0_正式版_20260614.md`。
