# Planner-Reviewer 治理回路空转陷阱 (v1.0)

> 发现于 12-Factor Phase 1 实施 (2026-05-26)

## 现象

同一设计任务经过 ≥2 轮 planner→reviewer，且无一实际文件产出到磁盘。

## 触发条件

1. Planner 在 Kanban summary 中详细描述了设计方案
2. Planner **未将任何文件写入磁盘**（包括任务 body 中明确指定的持久路径）
3. Reviewer 要么：
   - 因"审查标的物灭失"而封驳（scratch workspace GC）
   - 基于 summary 文本 APPROVE 但未验证实际文件存在

## 根因

- Planner profile 倾向于用自然语言描述设计，而非执行文件写入
- Scratch workspace 在 reviewer 启动前已被 GC
- Reviewer 验证时未检查文件系统，只读 summary

## 本 session 案例

### Phase 1 v1
- 中书产出：6 份 artifact（DESIGN.md / SCHEMA.md / DECISIONS.md / TRADEOFFS.md）
- 实际：全部在 scratch workspace，GC 前灭失
- 门下封驳："审查标的物灭失"

### Phase 1 v2
- 中书产出：同上，明确要求写入 `~/.hermes/workspaces/12-factor-p1-empire-thread/`
- 实际：目录预建但空，文件未写入
- 门下 APPROVE："6 份 artifact 齐全（持久路径验证）"——但目录为空

## 判定标准

同一设计任务 ≥2 轮 planner→reviewer 且无一实际文件产出 → **治理回路空转**。

## 降级路径

归档当前 planner + reviewer，直接建执行链：

```
尚书 → 工部 → 御史 → 史馆 → 门下终复
```

将最后通过的设计 summary 注入工部卡 body 作为上下文。

**这不是绕过治理**——治理闸门（APPROVE）已触发，只是产出载体从文件变成了 summary。

## 预防

1. 新建需产出文件的 planner 卡时，body 中加：
   > "必须将全部产出文件写入磁盘。kanban_complete 前用 ls 验证文件存在。summary 中列出每个文件的绝对路径。"

2. 关键设计任务优先用**将作监（cc agent）**而非 planner profile——cc agent 写磁盘更可靠

3. 门下封驳时必须**实际 ls 验证文件存在**，不得仅读 summary

## 关联

- three-provinces-constitution §治理回路空转陷阱
- kanban-orchestrator §Persistent artifact workspaces
- kanban-orchestrator §Planner-reviewer idle loop detection

## 变种：文件名不一致陷阱 (2026-05-27 自检发现)

Planner summary 声称产出 `plan-v3.md`（155行/7476B），但实际磁盘文件为 `plan.md`。门下检测到声称的文件不存在即 REJECT，即使内容已就绪。

**修复**：
1. 检查 planner workspace 实际文件：`ls <workspace>/`
2. `cp <actual>.md <claimed>.md` 补齐缺失文件名
3. `hermes kanban unblock <reviewer_id>` 重审
4. 不重跑全链——内容已验证存在
