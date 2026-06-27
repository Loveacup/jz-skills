# Kanban 五种工作模式总览

> 2026-06-04 整理。Kanban 不只是 swarm——它是一个完整的任务编排系统。

## 模式一览

### 1. 单任务模式（最基础）

```
hermes kanban create --assignee <profile> "标题"
hermes kanban dispatch
```

一个任务分配给一个 profile，dispatcher 捡起来跑。**不需要 swarm，不需要多 profile。**

机制：dispatcher 嵌在 gateway 里 → 捡 `ready` 状态任务 → 启动 worker agent 进程 → `kanban_complete` 或 `kanban_block`

> 适合：早新闻这种「一个 agent 跑全套」的场景

### 2. Swarm 模式（并行 fan-out）

```
hermes kanban swarm \
  --worker lane-zh:"中文搜索:web-research-router" \
  --worker lane-en:"英文搜索:web-research-router" \
  --verifier auditor \
  --synthesizer publisher \
  "目标描述"
```

N worker 并行 → verifier 校验 → synthesizer 合成。每个 worker profile 需要独立 gateway（含独立端口）。

> ⚠️ 代价：需要为每个 worker profile 启动 gateway。详见 `references/kanban-swarm-setup.md`

> 适合：需要并行加速的大规模搜索+合成 pipeline

### 3. 编排模式（Orchestrator）

一个 profile 当 orchestrator，手写 `kanban_create` + `parents=[...]` 构建灵活依赖图：

```python
t1 = kanban_create(title="成本对比", assignee="researcher")
t2 = kanban_create(title="性能对比", assignee="researcher")
t3 = kanban_create(title="综合推荐", assignee="analyst", parents=[t1, t2])
t4 = kanban_create(title="决策备忘录", assignee="writer", parents=[t3])
```

> 适合：复杂多步骤任务，依赖关系非固定线性链

### 4. Triage 模式（自动分解）

```
hermes kanban specify <task_id>     # 模糊想法 → 具体 spec
hermes kanban decompose <task_id>   # spec → 自动分解成子任务图
```

扔一个模糊想法进 triage column，LLM 自动分解并路由。

> 适合：想法还不清晰，让系统帮忙拆解

### 5. Goal 模式（持久化 worker）

```python
kanban_create(..., goal_mode=True, goal_max_turns=15)
```

Worker 每轮跑完后 judge 对照验收标准评估。不满足 → 同 session 继续（上下文不断）。预算耗尽 → 自动 block。

> 适合：「翻译整个文档站」这种多轮才能完成的大任务

## 模式选择决策树

```
任务量小、依赖简单？
  ├─ 是 → 单任务模式
  └─ 否 → 需要并行加速？
          ├─ 是 → 线性 pipeline（并行+验证+合成）？
          │       ├─ 是 → Swarm 模式
          │       └─ 否 → 编排模式
          └─ 否 → 任务边界不清晰？
                  ├─ 是 → Triage 模式
                  └─ 否 → 多轮才能完成？
                          ├─ 是 → Goal 模式
                          └─ 否 → 单任务模式
```

## 关键 CLI

```bash
hermes kanban --help                    # 全子命令
hermes kanban create --assignee P "T"   # 创建单任务
hermes kanban swarm --worker ...        # Swarm 创建
hermes kanban dispatch --max N          # 分发
hermes kanban stats                     # 状态总览
hermes kanban show <id>                 # 任务详情
hermes kanban reclaim <id>              # 回收卡住任务
```
