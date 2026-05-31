# Agent Pipeline 执行流详解

> 本文件是 SKILL.md 主入口下沉的执行细节。Leader 在派单时应回到 SKILL.md 主表，遇到任何具体调度疑问再查此文件。
>
> **没有模式分支**——v5.0 删除了 Deep/Standard/Quick 三模式。所有 16 个 agent 一律全开，所有质检门一律全跑。

---

## 执行流总览（ASCII 拓扑）

```
Pre -1: question-refiner  ──┐
                              │
Pre  0: memory_reader.py  ──┤  Leader Bash + 串行
                              │
Stage 0:   topic-preprocessor ─────────┐
Stage 0.5: knowledge-enricher ─────────┤  串行
Stage 1:   framework-builder ──────────┤  （引入 analysis_type 路由）
Stage 1.5: got-controller ─────────────┘
                       │
              ┌────────┼─────────┐
              │        │         │
   Stage 2a 并行 (blocked_by = [framework, got])
   ├─ spatial-researcher
   ├─ temporal-researcher
   └─ domain-researcher
              │
              ▼
   Stage 2b 并行 (blocked_by = [t_spatial, t_temporal, t_domain])
   ├─ stakeholder-analyst
   └─ causal-analyst
              │
              ▼
   Stage 3:  source-manager (CoV 三层 + verdict)
              │
   Stage 4:  insight-synthesizer (横纵交汇 5 问 + 三剧本)
              │
   Stage 5:  longform-writer  ◄──── L2 内置自检 ──┐
              │                                    │
   Stage 6:  output-finalizer ────────────────────┘ 修订循环（SendMessage）
                ├─ L1 硬性规则
                ├─ L3 内容终审
                └─ L4 活人感 (调用 Skill("de-slop"))
              │
   Stage 6.5: Skill("obsidian-md-ac") 美化  ← Leader 直接调用
              │
              ▼
   Stage 7 并行（非阻塞）
   ├─ memory-curator
   └─ pattern-crystallizer
              │
              ▼
   复制到 ~/Obsidian/AlexCai/00-Inbox/
              │
            TeamDelete
```

---

## Stage-by-Stage CC 调用伪代码

> 注意：以下 Python 风格仅为可读性示意。Leader 实际执行时一律使用 CC 原生 tool：`TeamCreate / TaskCreate / Task / TaskGet / TaskUpdate / Monitor / TaskStop / SendMessage / Bash / Skill`。
>
> **关键约定**：Leader 必须先 `Read(agents/core/<name>.md)` 把 agent prompt 全文塞入 `Task(prompt=...)`，因为 16 个 worker 全部以 `subagent_type="general-purpose"` 启动，没有内置 role-prompt。

### 0. 团队创建 + 记忆读取

```python
TeamCreate(team_name=f"sil-{topic_short}",
           description=f"战略洞察: {user_input[:50]}")

# 记忆读取（Leader Bash 直接执行，不走 Task）
Bash(f'python3 "${{SKILL_DIR}}/scripts/memory_reader.py" '
     f'"{user_input}" '
     f'"${{WORKSPACE}}/memory-context.json"')
```

### 1. 创建所有任务节点（声明依赖）

```python
# Pre -1
t_pre   = TaskCreate("问题澄清",     description="question-refiner")

# Stage 0 / 0.5 / 1 / 1.5
t0      = TaskCreate("主题预处理",   description="topic-preprocessor",   blocked_by=[t_pre])
t05     = TaskCreate("知识增强",     description="knowledge-enricher",   blocked_by=[t0])
t1      = TaskCreate("框架构建",     description="framework-builder",    blocked_by=[t05])
t15     = TaskCreate("GoT 路径评估", description="got-controller",       blocked_by=[t1])

# Stage 2a 并行（blocked_by = [t15]）
t_spatial  = TaskCreate("空间维度研究", description="spatial-researcher",  blocked_by=[t15])
t_temporal = TaskCreate("时间维度研究", description="temporal-researcher", blocked_by=[t15])
t_domain   = TaskCreate("领域维度研究", description="domain-researcher",   blocked_by=[t15])

# Stage 2b 并行（blocked_by = [2a 三个]）
researchers_2a = [t_spatial, t_temporal, t_domain]
t_stake   = TaskCreate("利益相关者分析", description="stakeholder-analyst", blocked_by=researchers_2a)
t_causal  = TaskCreate("因果链分析",     description="causal-analyst",      blocked_by=researchers_2a)

# Stage 3 / 4 / 5 / 6
t3 = TaskCreate("来源验证+CoV",  description="source-manager",
                blocked_by=researchers_2a + [t_stake, t_causal])
t4 = TaskCreate("洞察提炼",      description="insight-synthesizer", blocked_by=[t3])
t5 = TaskCreate("长文撰写",      description="longform-writer",     blocked_by=[t4])
t6 = TaskCreate("输出整理",      description="output-finalizer",    blocked_by=[t5])

# Stage 7 并行（非阻塞，memory + pattern）
t7a = TaskCreate("记忆整理",     description="memory-curator",        blocked_by=[t6])
t7b = TaskCreate("模式结晶",     description="pattern-crystallizer",  blocked_by=[t6])
```

### 2. 启动 worker（串行段落 = 单 Task；并行段落 = 单 turn 多 Task）

#### 串行启动（每次先 Read agent prompt）

```python
prompt_pre = Read("agents/core/question-refiner.md")
Task(prompt=prompt_pre, subagent_type="general-purpose",
     team_name=team_name, name="question-refiner", task_id=t_pre)
# Leader 用 TaskGet/Monitor 等待 t_pre 完成后再启动 t0

prompt_t0 = Read("agents/core/topic-preprocessor.md")
Task(prompt=prompt_t0, ..., task_id=t0)
# 依此类推: t05 → t1 → t15
```

#### Stage 2a 并行（同一条 assistant message 里发 3 个 Task）

```python
# Leader 在同一个 turn 内发出 3 个 Task 调用 = CC 并行语义
Task(prompt=Read("agents/core/spatial-researcher.md"),  ..., task_id=t_spatial)
Task(prompt=Read("agents/core/temporal-researcher.md"), ..., task_id=t_temporal)
Task(prompt=Read("agents/core/domain-researcher.md"),   ..., task_id=t_domain)
```

#### Stage 2b 并行（必须等 2a 全部 completed）

```python
# Leader 通过 Monitor 等待 t_spatial / t_temporal / t_domain 全部 completed
Task(prompt=Read("agents/optional/stakeholder-analyst.md"), ..., task_id=t_stake)
Task(prompt=Read("agents/optional/causal-analyst.md"),      ..., task_id=t_causal)
```

#### Stage 3-6 串行

```python
Task(prompt=Read("agents/optional/source-manager.md"),      ..., task_id=t3)
Task(prompt=Read("agents/core/insight-synthesizer.md"),     ..., task_id=t4)
Task(prompt=Read("agents/core/longform-writer.md"),         ..., task_id=t5)
Task(prompt=Read("agents/core/output-finalizer.md"),        ..., task_id=t6)
# output-finalizer 内部可能触发修订循环 → 通过 SendMessage 与 longform-writer 协作
```

#### Stage 6.5 Leader 直接调用 Skill（不是第 17 个 agent）

```python
final_file = Bash("ls -t ${WORKSPACE}/战略洞察-*.md | head -1").strip()

Skill(
  skill="obsidian-md-ac",
  args=f"美化文件 {final_file}：emoji 标题、==高亮==、Mermaid、callouts、YAML 合规、wikilinks 关系分析"
)
```

#### Stage 7 并行（非阻塞）

```python
Task(prompt=Read("agents/optional/memory-curator.md"),       ..., task_id=t7a)
Task(prompt=Read("agents/optional/pattern-crystallizer.md"), ..., task_id=t7b)
# 不等待，直接进入收尾
```

#### 收尾

```python
Bash(f"cp {final_file} ~/Obsidian/AlexCai/00-Inbox/")
TeamDelete(team_name)
```

---

## 关键模式说明

### CC 并行语义

> **并行 = 同一 assistant message 里发多个 Task 调用**

CC 没有 `await wait_all(...)` 这种 verb。Leader 表达"并行"的唯一方式就是在一个 assistant turn 里连续发出多个 `Task(...)` 调用。等待则靠 `TaskGet`、`Monitor` 流式查看，或下游 `TaskCreate(blocked_by=[...])` 的依赖声明。

### Read agent prompt → 注入 Task

16 个 worker 全部以 `subagent_type="general-purpose"` 启动，没有内置 role-prompt。Leader 必须：

```python
prompt = Read("agents/core/<agent-name>.md")
Task(prompt=prompt, subagent_type="general-purpose", team_name=..., name=..., task_id=...)
```

如果省略 `Read` 直接传简短描述，worker 会失去全部 role / methodology / output 规范，输出质量塌方。

### 删除的自造 verb 对照表

| ❌ 自造 verb（v4.x） | ✅ CC 原生 |
|---|---|
| `dispatch_teammate(agent, task)` | `Read(agent.md)` + `Task(prompt=..., name=agent, task_id=task)` |
| `await wait_task(t)` | `TaskGet(t)` 或 `Monitor` 等到 status=completed |
| `await wait_all([t1, t2])` | 同 turn 发出 + 各自 TaskGet / 下游 blocked_by |
| `run_script("foo.py", ...)` | `Bash("python3 ${SKILL_DIR}/scripts/foo.py ...")` |
| `broadcast_shutdown()` | `TeamDelete(team_name)` |

---

## Stage 2 依赖修复（关键修正）

**v4.x 错误**：stakeholder + causal 被放在 Stage 2 与 spatial/temporal/domain 同级并行，但其 prompt 实际依赖 3 个 researcher 的输出 → Leader 严格执行会拿到空输入。

**v5.0 修复**：拆为 2a 与 2b 两层。

| Stage | Agents | blocked_by |
|---|---|---|
| 2a | spatial / temporal / domain | [t1 框架] 或 [t15 GoT] |
| 2b | stakeholder + causal | [t_spatial, t_temporal, t_domain] |

---

## TaskUpdate 心跳协议

所有 worker 必须在以下时刻调 `TaskUpdate`：

| 时机 | 内容 |
|---|---|
| 阶段切换 | `TaskUpdate(task_id, status="in_progress", progress_pct=NN, message="开始 XXX 阶段")` |
| 每 90 秒 | 即使无新进展也要心跳一次（防 Leader 判死） |
| 完成时 | `TaskUpdate(task_id, status="completed", progress_pct=100, message="输出文件: xxx.md")` |
| 失败时 | `TaskUpdate(task_id, status="failed", message="错误原因: ...")` |

Leader 端：
- `TaskGet(task_id)` 拉单次状态
- `Monitor(task_ids=[...])` 流式监听
- 超过 心跳间隔 × 2（180 秒）未更新 → 视为卡死，触发降级

---

## SendMessage 协作场景

| 场景 | 用法 |
|---|---|
| 修订循环 | `output-finalizer` 检测到 L1/L3/L4 fail → `SendMessage(longform-writer 的 task_id, "修订指令: 段落 X 触发 L1 黑名单, 请改写")` |
| 数据缺口 | `insight-synthesizer` 发现 spatial 数据缺 → `SendMessage(spatial-researcher 的 task_id, "请补充: 上海一线门店数据缺失")` |
| Leader 广播 | 关键阶段切换可对 team 广播（可选） |

**接收方语义**：
- worker 在 `in_progress` 状态可接收 SendMessage，处理后再用 TaskUpdate 报新进度
- worker 已 `completed`：必须由 Leader 新建 `TaskCreate + Task` 唤起新一轮 worker，不能给死单发消息

---

## 失败恢复与超时治理

### 默认超时（写进 `config.json` 的 `task_timeouts` 节）

| Agent 类型 | 默认超时 |
|---|---|
| 普通 agent（topic-pre / framework / synth / writer / finalizer） | 600 s |
| researcher（spatial / temporal / domain，含 Exa 3 轮） | 900 s |
| source-manager（含 CoV crawl） | 1200 s |

### 重试策略

| Agent | 失败处理 |
|---|---|
| spatial / temporal / domain / stakeholder / causal | fail → 重试 1 次（temperature +0.1）→ 仍 fail 写空 placeholder + 低置信度标记，**不阻塞下游** |
| longform-writer / output-finalizer | fail → 重试 1 次 → 仍 fail 则 `TaskStop` 整个 team，保留中间产物 |
| memory-curator / pattern-crystallizer / got-controller | 失败永久 skip（非关键路径） |

### 降级路径

| 触发条件 | 降级动作 |
|---|---|
| got-controller > 5 分钟未完成 | `TaskStop(t15)`，下游 blocked_by 改为 [t1] |
| source-manager > 8 分钟未完成 | `TaskStop(t3)`，直接喂 raw research 给 insight-synthesizer |
| 任何 L1-L4 闸门累计回炉到上限 | 标记低置信度放行 + 最终评分 -0.5 + 报告告警 |

### Partial 处理

- Stage 2a：3 个 researcher 只要 **2/3** 成功，Stage 2b 即可启动；synthesizer 在文章中标注「X 维度缺失」
- Stage 2b：stakeholder / causal 全失败 → synthesizer 仍可启动，但 L3 论点-证据-结论链覆盖率会扣分

---

## memory_reader.py 路径修正

**v4.x 错误**：硬编码 v3.0 老路径
```bash
python3 ~/.claude/skills/strategic-insight-longform-v3.0/scripts/memory_reader.py ...
```

**v5.0 正确**：从环境变量 / config 读 `SKILL_DIR`
```bash
python3 "${SKILL_DIR}/scripts/memory_reader.py" "${user_input}" "${WORKSPACE}/memory-context.json"
```

`memory-curator.md` 与 `pattern-crystallizer.md` 内部的所有 Bash 调用同步修正。

---

## Stage 6.5 Skill 调用签名

**v4.x 错误**（签名不完整）：
```python
Skill("obsidian-md-ac", args=final_file)
```

**v5.0 正确**（关键字参数 + 自然语言指令）：
```python
Skill(
  skill="obsidian-md-ac",
  args=f"美化文件 {final_file}：emoji 标题、==高亮==、Mermaid、callouts、YAML 合规、wikilinks 关系分析"
)
```

### L4 活人感闸门的 Skill 调用

```python
# output-finalizer 检测到 L4 软违规（AI 味密度超阈值 / 破折号过多）
Skill(
  skill="de-slop",
  args=f"检测并改写以下文本的AI味：{text}"
)
```

> 注意是 `de-slop` 不是 `humanizer-zh`。de-slop 是双语引擎且包含 register-aware 检测。

---

## Leader 自检清单

派单前 Leader 应自查：
1. ✅ 每个 `Task(prompt=...)` 是否先 `Read` 了对应 agent .md
2. ✅ Stage 2a 的 3 个 Task 是否在同一 turn 发出
3. ✅ Stage 2b 是否声明了 `blocked_by=[t_spatial, t_temporal, t_domain]`
4. ✅ Stage 6.5 调用是否为 `Skill(skill=..., args=...)` 完整签名
5. ✅ memory_reader.py 路径是否用 `${SKILL_DIR}` 而非 v3.0 硬编码
6. ✅ 所有 `tools:` 字段是否为 CC 原生命名（无 `read_file`/`write_file`/`dispatch_teammate`）
7. ✅ 修订循环是否使用 `SendMessage(task_id, ...)` 而非新建 Task
