# STDD-OMP Agent 角色绑定

## P4：Producer ≠ Judge

| 角色 | 内置 agent | 职责 | 工具限制 |
|---|---|---|---|
| 审查/调研 | `explore` | 只读审查、找代码、找风险 | 无 edit/write |
| 执行 | `task` / `oracle` | Build 最小产出 | 按任务需要 |
| 审计 | `reviewer` / `oracle`（默认） | 判真假、只审不改 | 无 edit/write |
| 可选审计 | `stdd-auditor`（自定义） | 与 reviewer/oracle 同职责，更严格的只审约束 | 无 edit/write |

## 动态发现 + 自定义覆盖

OMP 按名称动态发现 agent。默认 auditor 是内置 `reviewer`/`oracle`。

可选增强：若把 `assets/stdd-auditor.agent.md` 复制到 `~/.omp/agent/agents/stdd-auditor.md`，
可用 `task agent:stdd-auditor` 替代 reviewer/oracle，获得更聚焦的审计角色。

如果 auditor 缺失：

- L1/L2：用 `oracle` 或 `reviewer`。
- L3：必须有独立 auditor（reviewer/oracle 或 stdd-auditor）；缺失则任务不能进入无人值守。

## 隔离防冲突

- 同任务不要让 executor 在完成后立即自审。
- 多 executor 并行时启用 `task.isolation.mode`。
- auditor 应在干净上下文或独立 session 中运行。

## 审核独立性三级

| 级别 | 做法 | 适用 |
|---|---|---|
| L1 自审 | executor 完成后快速自检 | L0/L1 草稿 |
| L2 干净 session | 新 session 只读审计 | L2 任务 |
| L3 独立 auditor | `task agent:reviewer` / `oracle` / 可选 `stdd-auditor` | L3 / GOAL |

## 三级门控

| 级别 | 配置 | 效果 |
|---|---|---|
| 只读 | `tools.approvalMode: always-ask` | 每个 tool_call 都问 |
| 写入 | `tools.approvalMode: write` + `tools.approval.bash: ask` | 写入/危险工具需确认 |
| 危险 | hook + approval 双重拦截 | 危险命令 block |

```yaml
tools:
  approvalMode: write
  approval:
    bash: ask
    edit: ask
    write: ask
```

## modelRoles 映射

| STDD 角色 | OMP modelRole | 用途 |
|---|---|---|
| Spec / Plan / Accept | `plan` | 结构化规划、长程思考、生成 Plan 工件 |
| Build executor | `task` | 执行导向、代码/写作产出 |
| 审计 / 顾问 | `advisor` | 审慎判断、少改动、独立评估；agent 可用 `reviewer`/`oracle` |
| 快速检查 | `smol` | 轻量、低成本、短延迟 |
| 深度难题 | `slow` / `plan:high` | 复杂设计、需要深度推理 |

示例 `~/.omp/agent/config.yml`：

```yaml
modelRoles:
  plan: anthropic/claude-sonnet-4:medium
  task: openai/gpt-5.5:medium
  advisor: anthropic/claude-sonnet-4:high
```

为不同角色分配不同模型/思考级别，可避免“执行模型太激进、审计模型太弱”的冲突。

## Profile / modelRoles 隔离

- `omp --profile stdd` 只迁移 native lane；agents lane `~/.agents/skills/` 不动。
- 可为 auditor 使用 `advisor` 模型角色（即 `modelRoles.advisor`），避免与 executor 同模型/同 session。
