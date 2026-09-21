# STDD 宏循环校准

## 五步宏循环

```text
审查 → 分级 → 执行 → 审核 → 收尾
```

| 步骤 | 问题 | 做法 |
|---|---|---|
| 审查 | 当前状态 vs 目标差多少？ | 使用当前 runtime 提供的只读工具；不假定固定 agent 名。 |
| 分级 | 这是 L0/L1/L2/L3 哪一档？ | 对照 SKILL.md 分档表。 |
| 执行 | 是否需要委派？ | L1 内联；L2/L3 仅在能力/独立性需要时按 roster 委派。 |
| 审核 | 验收项全过吗？ | L1 内联证据；L2 fresh-context evaluator；L3 independent auditor。 |
| 收尾 | 依赖项是否都有 PASS？ | BLOCKED 不放行；清理状态并保存证据。 |

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
2. L1 内联，L2 独立上下文，L3 独立 auditor；agent 名按 runtime capability 选择。
3. L3 的 slice 必须有不重叠所有权与 single-writer 记录。
4. regen max=3、slice max=2；到顶停止并升级人工。
5. 全部依赖验收 PASS 才收尾；FAIL 回退，BLOCKED 停止依赖链。

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
| L1 一律委派/独立审 | 增加无意义开销 | L1 当前 agent 内联验证 |
| L2/L3 使用固定 agent 名 | runtime 不存在或能力不符 | 查询 roster，按 capability 选择 |
| 软失败低置信度放行 | 依赖结论无证据 | 相关项 BLOCKED；只让无依赖工作继续 |
| timeout 后自动重派 | 形成双 writer | 先取得 stop proof |
| 硬顶后继续 regen | 无限循环 | 到顶停止并升级人工 |
| full-auto 执行发布/安装/认证 | 越权 | 对具体高风险动作另取授权 |

## 收尾步：自文档化校准

被校准的长期文档末尾留「如何更新本文档」节：

1. 权威尺子在哪（URL / 文件路径）
2. 上次对齐上游版本号（commit SHA / npm version / schema 快照）
3. 重跑最小动作清单（具体命令）

残留留账分两类：
- **需求残留**：验收项未满足但由有权用户明确接受变更后的契约（理由 + 日期 + 批准人）
- **证据残留**：记录已有证据、缺口和 blocks；相关验收保持 BLOCKED，直到直接证据满足

## 渐进采纳级别

**校准级别 0–2 与任务强度 L0–L3 是两把正交尺子**：

- **级别 0**（只审不修）：仅记录关键 Acceptance 与偏差。
- **级别 1**（局部采用）：L1 内联 Verify；L2 使用独立上下文 evaluator。
- **级别 2**（完整采用）：L3 使用独立 auditor、GOAL、上游真相校准、量化档、sid、regen/slice 硬顶。

STDD 的采用必须来自用户明确选择或项目治理文件，不由泛化关键词自动升级。
