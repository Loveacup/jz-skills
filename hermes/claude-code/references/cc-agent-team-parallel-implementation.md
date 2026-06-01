# CC Agent Team Parallel Implementation Pattern

> 建立时间：2026-06-01（v3.1.0 引用，v4.0 补全文档）
> 适用：需要多 worker 并行实施（写文件、修改代码）的场景，区别于 `agent-team-multi-lens-review.md`（纯分析/评审）

## 与 Multi-Lens Review 的区别

| 维度 | Multi-Lens Review | Parallel Implementation |
|------|------------------|------------------------|
| 目标 | 产出分析文档 | 产出实际文件/代码变更 |
| 冲突风险 | 低（各自写独立输出） | 高（可能竞争同一共享文件） |
| Leader 角色 | 合并分析报告 | 串行整合到共享文件 |
| Worker 产出 | Markdown 分析块 | 独立领域文件 + patch |

---

## Leader-Wiring 策略：避免共享文件冲突

**核心原则：Worker 各自产出独立领域，Leader 串行整合到共享文件。**

```
并行阶段（Workers）               串行阶段（Leader）
─────────────────────────        ──────────────────────────
Worker A → domain-a-output.md ─┐
Worker B → domain-b-output.md ─┤→ Leader 读取所有输出
Worker C → domain-c-output.md ─┘         ↓
                                  串行写入 shared-file.md
                                  串行写入 config.yaml
                                  串行写入 SKILL.md
```

**禁止模式：** 多 Worker 直接写同一个文件（`SKILL.md`、`config.yaml` 等）——会产生交错写入、内容覆盖或 git 冲突。

### 拆分原则

按"关注点"拆分，不按"文件"拆分：

| 好的拆分 | 差的拆分 |
|---------|---------|
| Worker A 负责数据层、Worker B 负责 API 层 | Worker A 写第 1-50 行、Worker B 写第 51-100 行 |
| Worker A 负责 pitfall 补充、Worker B 负责 changelog | Worker A 和 Worker B 都写 common-pitfalls.md |
| Worker A 研究现有 schema、Worker B 写验证脚本 | Worker A 和 Worker B 都改 SKILL.md |

---

## Context 文件模板

每次实施任务写一个 context file 到 `~/.hermes/tmp/cc-impl-{task-slug}.md`：

```markdown
# CC Parallel Implementation: {task-name}

## 任务背景
{2-3 句：目标、为什么这么做、上下文}

## Worker 分工

### Worker A — {domain-a}
- 负责范围：{具体文件/模块/功能}
- 产出路径：`/tmp/cc-impl-{task}-worker-a.md`
- 约束：{语言、格式、禁止事项}
- 超时：8 分钟

### Worker B — {domain-b}
- 负责范围：{具体文件/模块/功能}
- 产出路径：`/tmp/cc-impl-{task}-worker-b.md`
- 约束：{语言、格式、禁止事项}
- 超时：8 分钟

## Leader 整合阶段（串行）
Workers 完成后，Leader 按以下顺序串行写入：
1. 读取 /tmp/cc-impl-{task}-worker-a.md
2. 读取 /tmp/cc-impl-{task}-worker-b.md
3. 写入 {shared-target-file}（整合，不覆盖已有内容）
4. 验证：{具体验证步骤}

## Schema 验证要求
{如果涉及 API/storage 写入，列出验证步骤，见 post-deploy-verification-pattern.md}
```

---

## Schema 验证集成

并行实施涉及持久化数据时，Leader 整合阶段必须包含 schema 验证：

```
Leader 串行整合步骤：
  1. 合并 worker 产出到 artifact dict
  2. POST artifact（Python subprocess curl）
  3. sleep 2s
  4. GET artifact
  5. 断言所有预期字段存在
  → 详见 post-deploy-verification-pattern.md
```

---

## 会话管理

并行 Implementation 任务必须使用独立 session：

```bash
# 启动专用 session（不复用 longterm）
tmux new-session -d -s "hermes-cc-impl-{task-slug}"
# 任务完成后清理
tmux kill-session -t "hermes-cc-impl-{task-slug}"
```

共享 session 风险：见 common-pitfalls #25（Session 被另一 agent /clear 劫持）。

---

## 典型时序

```
T+0     Leader 收到 context file，解析分工
T+1     Worker A、B、C 并行启动（同一 CC agent team 内）
T+3~8   Workers 各自在独立领域工作（读文件/调用工具/生成产出）
T+8~12  Workers 返回，Leader 进入串行整合
T+12~18 Leader 写入共享文件，执行 schema 验证
T+18    Leader 返回完整报告
```

Workers 超时（>8min）：Leader 从已完成 worker 产出整合，记录未完成部分，不等待。

---

## 相关条目

- `agent-team-multi-lens-review.md` — 分析/评审模式（无共享文件冲突问题）
- `post-deploy-verification-pattern.md` — 持久化字段验证
- common-pitfalls #25 — Session 被另一 agent /clear 劫持
- common-pitfalls #9 — Agent Team Schema 持久化
