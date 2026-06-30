# WRR v6.0 OB 三梁重构 — STDD 多 Agent 案例研究

> 日期：2026-06-29
> 模式：Codex 规划 → CC 审查+执行 → Hermes 协调验收
> 产出：36 文件 OB 知识库从功能型目录重构为 STDD 三梁结构

## 背景

WRR OB 目录原有 7 个子目录（01_架构与路线/、02_实施与报告/...、06_文档与手册/），按版本号和文档类型组织。v6.0 架构重塑后需按 STDD 三梁模型（梁1 需求/梁2 实现/梁3 执行/派生路线图）全面重构。

## 工作流

### Phase 1: Codex 出方案（成功）
- 输入：STDD 方法论全文、当前 OB 文件树、v6 Codex 设计(859行)、CC 评审(191行)
- Codex 读取 4 个事实源 + 枚举 35 文件 → 361 行完整重构方案
- 方案包含：目标三梁目录、35 文件逐项迁移映射、12 个新增文档清单、8 步执行顺序、验收标准
- 模型：GPT-5.5，read-only sandbox，300s 内完成

### Phase 2: CC 审查方案（成功）
- CC 原生 tmux 启动（避开 cc-start.sh 的旧 persisted-output 污染）
- 审查结论：通过。36 文件全覆盖（方案计数有 1 个偏差）、三梁分层正确、来源可追溯
- 3 个非阻塞执行注意项：空子目录清理、wikilink 改名（2 个 generic 文件）、v5 status 降级

### Phase 3: CC 执行迁移（进行中）
- 先写审查报告到 `/tmp/cc-output-wrr-ob-review.md`
- 然后按方案 8 步执行：备份 → 建骨架 → 写入口 → 迁主线 → 迁历史 → 重写导航 → 写 v6 专题 → 验证
- 完成报告到 `/tmp/cc-output-wrr-ob-restructure-final.md`

## 发现的 Pitfall（已录入 cc-tmux SKILL.md）

### Pitfall #56：macOS tmux send-keys 多行文本被 CC 队列吞掉
根因：CC CLI 将换行符解释为消息分隔符，触发队列模式。
修复：单行指令 + 引用文件路径。`按 /tmp/cc-task.md 执行。`
此 pitfall 消耗约 20 分钟试错（3 次 kill+restart session）。

### Pitfall #57：CC persisted-output 污染旧会话上下文
根因：CC 自动注入 `<persisted-output>` 包含数月前的无关会话摘要（iii × cc-tmux roadmap），占满 scrollback buffer。
应对：不依赖 pane 输出，用 cc-monitor.sh + 检查产物文件。

## 关键决策

1. **放弃 cc-start.sh，直接用原生 tmux** — 避开 persisted-output 污染和 agent team queue 问题。`tmux new-session -d -s "name" -c /tmp "claude --model claude-opus-4-8"`
2. **任务通过文件传递，不通过 send-keys** — `/tmp/cc-task-ob.md` 398 字节，CC 自己读取，避免多行队列。
3. **审查→执行两阶段合并为一个任务** — "审查并执行"比"先审查等待确认再执行"更高效（OB 文件迁移风险低，备份可回滚）。

## 教训

- CC agent team 模式对分析型任务有效，但对文件迁移类任务过度（增加通信开销和不确定性）
- 短指令 + 文件引用 > 长指令 send-keys
- 原生 tmux > cc-start.sh（当 persisted-output 污染时）
- WRR OB 重构这类低风险、可回滚任务，审查+执行一次委托即可
