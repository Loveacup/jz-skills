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
| 收尾 | 经验回写 + 状态清理 | `memory.local` + `todo done` + counter reset |

## 偏差三形态 + 统一判据

| 偏差 | 现象 | 判据 |
|---|---|---|
| 范围漂移 | Build 产出超出 Spec | diff 文件与 checklist 逐项对应 |
| 验收软化 | 模糊词未量化 | 每条验收项能判 true/false |
| 审计失焦 | executor 自审或 auditor 改代码 | auditor 工具列表无 edit/write |

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

## 渐进采纳级别

- **Level 0**：只在关键任务写 Acceptance checklist。
- **Level 1**：所有 L1+ 任务跑 gates.mjs verify。
- **Level 2**：L2+ 强制独立 auditor。
- **Level 3**：L3 全闭环 GOAL，含计数器与异步 task。
