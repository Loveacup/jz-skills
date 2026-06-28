# STDD 宏循环校准

## 五步宏循环

```text
审查 → 分级 → 委派 → 审核 → 收尾
```

| 步骤 | 问题 | OMP 机制 |
|---|---|---|
| 审查 | 当前状态 vs 目标差多少？ | `explore` 只读调研 + `read`/`grep` |
| 分级 | 这是 L0/L1/L2/L3 哪一档？ | 对照 SKILL.md 分档表 |
| 委派 | 谁做 Build？谁审？ | `task` batch；executor + auditor 分离 |
| 审核 | 验收项全过吗？ | `gates.mjs` + `reviewer`/`oracle`/`stdd-auditor` |
| 收尾 | 经验回写 + 状态清理 | `memory://root` 读经验 + `autolearn` 自动沉淀 + `todo done` + counter reset |

## 偏差三形态 + 统一判据

| 偏差 | 现象 | 判据 |
|---|---|---|
| convention-only 缺口 | 文档写了但代码/配置未生效 | 用 lsp/真跑验证，不以文档声称作证据 |
| 降级实现 | 验收项被悄悄放宽或掉落 | diff 文件与 checklist 逐项对应；每条验收仍能判 true/false |
| 自相矛盾 | 两处行为不一致 | 两边都验证，以实测为准 |

**统一判据**：凡把「能不能做」交给 LLM 自觉就是偏差。

## 第三条外循环：上游真相校准

尺子在仓库之外（上游 schema/CHANGELOG/registry/Issues）。

铁律：**源码/schema 说什么算什么，README 只是线索且常滞后。**

新偏差类「陈旧失真」：文档与 schema 现状相反。

**审查第一动作** = 拉官方源并锁尺子版本（commit SHA/npm 版本/schema 快照）。

适用边界：
- 不适用「PRD 过期」禁用
- 必须能访问权威官方源
- 尺子未锁版本时禁用
- 未发布特性标前瞻不算偏差

**Worked example**（OMP 手册 §22 即此外循环的活样板）：

权威源阶梯：`settings-schema.ts > CHANGELOG > npm registry > Issues > README > omp://`

五步校准流程：
1. 锁定当前知道的最新稳定版（本地 OMP 版本号）
2. 拉 settings-schema.ts → 默认、新增 key、废弃 key
3. 对 CHANGELOG：新增/变更/废弃 → 查根因
4. 对 npm：release date 确认版本在 registry 存在
5. 对 Issues：限「文档与 schema 不一致」的 issue，区分「bug」与「未来需求」

易错高发区清单：
- 版本号可能写在三处（CHANGELOG 标题 / npm registry 字段 / 代码内 version 常量）
- 默认值逐条对 schema，不凭记忆/README/教程
- 工具增删改名（OMP 16.2.0: `search`→`grep`、`find`→`glob`）
- 新 modelRole（如 16.2.2 的 `tiny`）
- Issues caveat：未来需求 ≠ 文档失真

## 量化档（校准/L3 限定，不下放 L0–L2）

**逐条落地率**：

$$\text{落地率} = \frac{\text{满足} + 0.5 \times \text{部分满足}}{N}$$

- Standard ≥ 0.9
- Deep = 1.0
- 未达回炉

**sid 追溯台账**：
- 每验收项一 sid
- ①Spec → ④Verify 全程跟踪
- 终稿附 point-by-point 对照

**门裁切矩阵**（L 档 ↔ 启用哪些门 + 阈值）：

| 门 | L0 | L1 | L2 | L3/full-auto |
|---|---|---|---|---|
| claimcheck（反幻觉） | off | off | opt-in | on（>40%重跑） |
| counter（regen/slice） | off | on | on | on（硬顶 3/2） |
| 量化档 | off | off | off | on（≥0.9） |
| 上游真相 | off | off | opt-in | on |

**altitude 守则**：只在校准/L3 启用量化档；L0–L2 走布尔。

## 五条原则

1. 先审状态，再分级；不越级派任务。
2. L3 必须拆分 slice；每个 slice 对应一个 micro-loop。
3. auditor 独立：与 executor 不同 agent / 不同 session。
4. 计数器满硬顶必须升级人工，不得自动再试。
5. 全过才收尾；未过先回退到对应步骤。

## 适用边界

### 该用

- 任务失败成本高。
- 需要多人/多 agent 协作。
- 需要对外交付或夜间运行。

### 禁用

- 临时探索、一次性查询（L0）。
- 用户明确说「随便试试」。

## 反模式

| 反模式 | 后果 | 修正 |
|---|---|---|
| 跳过 Accept 直接 Build | 反复返工 | 没有 checklist 不 Build |
| executor 自审 | 偏见放行 | 强制 auditor 角色分离 |
| 硬顶后继续 regen | 浪费 token、引入风险 | 计数器到顶 → 升级人工 |
| 路线图独立维护 | 三梁与代码不同步 | 路线图是派生投影，变更回写三梁 |

## 收尾步：自文档化校准

被校准的长期文档末尾留「如何更新本文档」节：

1. 权威尺子在哪（URL / 文件路径）
2. 上次对齐上游版本号（commit SHA / npm version / schema 快照）
3. 重跑最小动作清单（具体命令）

残留留账分两类：
- **需求残留**：验收项未满足但决定接受（需理由 + 日期 + 批准人）
- **证据残留**：夹逼放行项（需标注夹逼两端 + 为什么不能直接观察）

## 渐进采纳级别

**校准级别 0–2 与任务强度 L0–L3 是两把正交尺子**：

- **级别 0**（只审不修）：只在关键任务写 Acceptance checklist，发现偏差记日志。
- **级别 1**（审+修 P0）：所有 L1+ 任务跑 gates.mjs verify，L2+ 强制独立 auditor，发现 P0 偏差必须修正。
- **级别 2**（全量五步）：L3 全闭环 GOAL + 上游真相校准 + 量化档 + sid 追溯 + 自文档化校准，含计数器与异步 task。
