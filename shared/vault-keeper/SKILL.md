---
name: vault-keeper
description: "Obsidian 知识库生命周期治理引擎（数据面在 vault 纯 Markdown，控制面在本 skill）。执行三道闸——写入闸(隔离区禁直接写 core)、晋升闸(硬门槛+风险×置信矩阵)、变更闸(矛盾裁决+append-only 日志)，外加复合置信度、风险定级、Lint 巡检、抽样自校准。当用户要：摄入/ingest 一个源、晋升/promote 候选页、lint/巡检知识库、抽样审核、矛盾裁决、把对话回填入库、冷启动治理体系时使用。读 vault GOVERNANCE.md 配置(不硬编码)、写 PIPELINE_LOG。委托 obsidian 做文件 IO、obsidian-md-ac 做格式。不要用于：单纯写笔记(用 obsidian)、纯格式化(用 obsidian-md-ac)、与生命周期无关的检索。"
version: 0.1.0
author: AlexCai
license: MIT
platforms: [macos, windows, linux]
metadata:
  tags: [obsidian, knowledge-base, governance, lifecycle, gate, lint, sampling, multi-cli]
  orchestrates: [obsidian, obsidian-md-ac]
  stateful: true
---

# vault-keeper — 知识库生命周期治理引擎

> 控制面（git 版本化）。数据面在 vault（纯 Markdown，Obsidian Sync 畅通）。
> 完整方法论：`20-Areas/20_Obsidian方法论/Obsidian x Ai方法论_v2.0_正式版_20260614.md`。

## 🚨 Red Flags（别乱来）

| 你的冲动 | 为什么不对 |
|---|---|
| 直接把页写成 `lifecycle_state: core` | **违反写入闸**。只有 `gate.py` 通过后 `promote.py` 能置 core |
| 用 AI 自报的 0.9 当 confidence | confidence 是 `confidence.py` 的**复合信号**，AI 自评只占一票 |
| 矛盾就覆盖旧 claim | **知识污染**。矛盾走裁决卡，旧 claim 不删不覆盖 |
| 把阈值写死在脚本里 | 阈值在 vault `GOVERNANCE.md`（改=R3）。引擎用 `config.py` 读 |
| 删除/对外发布/改 GOVERNANCE 自己做 | **R3 红线**，必须人工。skill 只提议 |

## 启动必读

1. 定位 vault：环境变量 `$VAULT`（缺则问用户）。引擎目录记为 `$VK`（本 skill 的 `engine/`）。
2. 读 `$VAULT/GOVERNANCE.md`（阈值+不变量+规则）与 `$VAULT/ROUTER.md`（core 内分流+定级）。
3. 缺治理文件 → 走「冷启动」（见下）。

## 决策树：用户想干什么

```
来了一个意图
├─ 有新源(URL/PDF/粘贴/对话产出) → Ingest
├─ 候选页加工好了,要进正本       → Promote
├─ 高价值对话产出要留存           → Query 回填 → Ingest
├─ 定期/大改后体检               → Lint
├─ 每周质量抽查                   → Sampling
├─ 发现矛盾                       → Adjudicate(人裁决)
└─ 首次部署                       → 冷启动
```

## 操作 → engine 映射（AI 判断由你做，确定性由引擎做）

| 操作 | 你(agent)做的 AI 判断 | 调引擎(确定性) | 写 |
|---|---|---|---|
| **Ingest** | 评分(五级锚定)→过滤(领域)→抽取实体与摘要 | `capture.py`(落源) → `ingest.py --title.. --sources..`(建 candidate) | candidate + LOG |
| **Promote** | 选 ROUTER 目标区；判断是否权威变更/丢信息合并 | `gate.py <页> --to <区> --inlinks N` → 退出码 0 则 `promote.py --to <区> --conf --risk` | core 页 / 队列 + LOG |
| **Query 回填** | 判断是否 >500 字且有综合价值 | `wiki_save.py --title --file` → 再 Ingest | conversation 源 |
| **Lint** | 读报告，决定修哪些（🟡） | `lint.py` | 88-审计/lint-*.md |
| **Sampling** | spot-check 抽样页，记缺陷 | `sampling.py` | 88-审计/sampling-*.md |
| **Adjudicate** | 取证→**人**裁决 | （生成取证卡，见 references/matrix.md） | 88-审计/adjudication/*.md |

调用示例（`$VK` = 本 skill 的 engine 目录）：
```bash
export VAULT=~/Documents/Obsidian/AlexCai
python3 $VK/gate.py "$VAULT/01-Staging/检索增强生成(RAG).md" --to 30-Resources/10_AI知识
# 退出码 0 → 自动晋升
python3 $VK/promote.py "$VAULT/01-Staging/检索增强生成(RAG).md" --to 30-Resources/10_AI知识 --conf 0.91 --risk R2
```

## 红线（交给人，skill 不自动做）

- 🔴 **R3**：删除、对外发布、改 `GOVERNANCE.md`/`ROUTER.md`（改逻辑则改本 skill engine + git PR review）。
- 🟡 **送队列不自动翻状态**：gate 退出码 10（R2 中置信 / R3）、退出码 30（矛盾）→ 写入 88-审计 队列，等人。

## 委托（不自己实现）

- 文件移动/读写/同步 → `obsidian` skill。
- 新页格式化、双链规范、callout/mermaid → `obsidian-md-ac` skill。

## 冷启动（首次）

1. `cd ~/code/jz-skills && git pull && bash deploy/sync-all.sh`（部署本 skill 到各 CLI）。
2. 在 vault 根建 `GOVERNANCE.md`/`ROUTER.md`/`PIPELINE_LOG.md`（模板见方法论 §15.1–15.3），删旧 `SCHEMA/RESOLVER/WIKI_INDEX/WIKI_LOG`。
3. `python3 $VK/backfill_state.py`（现有 core 区批量标 `lifecycle_state: core`）。
4. `python3 $VK/capture.py --backfill`（存量源补 id+hash，按需）。
5. 跑通一次 Ingest→Promote→Lint 验证闭环；`python3 $VK/sampling.py` 开抽样环。

## 验收（健康指标）

- core 每页都有 `sources`（Dataview 查空集）；无页绕过隔离区进 core（`check_write_gate.py` 退出码 0）；
- `PIPELINE_LOG` 随操作增长；人工队列可一天清空；抽样错误率下降。
