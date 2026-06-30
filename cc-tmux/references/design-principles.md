# cc-tmux 设计原则

> 源于 2026-06-15 四轮 CC 讨论 + GitHub 调研（AEGIS/Citadel/governai）
> 完整推导：`/tmp/cc-skill-redesign-output.md` 或 Obsidian `00-Inbox/CC Skill v5 架构重设计方案_20260615.md`

## 核心诊断

v4 claude-code skill 的病根是 **curse of instructions**：80+ 条义务同时在现场。
单条 95% 合规 → `0.95²⁵ ≈ 28%` prompt 级准确率。首要失败模式 = **omission（遗漏）**。

## 六条设计原则

### 1. 砍 n，不是砍字
优化每 turn 活跃**义务数**（p^n 的指数），不是字符数。每条没砍掉的规则成本是乘性的。

### 2. ergonomics 优于 enforcement
agent 跟 effort 梯度走。让祝福脚本比手搓 tmux 更省事，合规就自发发生。

### 3. 重复义务塌缩成脚本
命名/占用/日志/报告打包，从"每次记得 × N"变成"一次脚本调用"。

### 4. 按失败成本分诊
只对**破坏性 + 不可逆 + 竞态**的失败上硬点（占用）。
可恢复的 omission（汇报/复核）软 + 审计就好。

### 5. 只在你拥有基座处强制
子 CC 环境是我们的 → 占用锁硬得起来。
Hermes runtime 不是 → 别假装能硬。硬度放在能真硬的地方。

### 6. 优雅降级优先
选"被绕过就退回旧行为"的机制，而非"失败就 wedge 全局"的硬门。

## 四个组件

| 组件 | 硬度 | 落点 |
|------|------|------|
| B：phase 化 + 祝福脚本 | 软，优雅降级 | cc-start/send/monitor/finish.sh |
| 占用硬点 | 硬 | cc-start.sh 内置 flock 锁 |
| eval harness | 测量 | fixture + 3 症状判定 |
| watcher 审计 | 反应式 | flag only, don't fix |

## 明确不建

- ❌ CC hook 硬门（#43407/#18312 已知开放 bug）
- ❌ gateway 排他卡脖子（需沙箱 Hermes）
- ❌ MCP proxy / 容器（过度工程）
- ❌ Formal Skill runtime（CC + 脚本已覆盖）
- ❌ 重型状态机（phase 文件轻版即可）
- ❌ "自动修"的 watcher（daemon 无 agent 上下文）

## 实施次序

1. eval 最小版（先有尺子）
2. B 分解 + 祝福脚本 ← **当前状态**
3. claude wrapper 占用锁（cc-start.sh 已内置）
4. watcher 审计
5. 重型 L1/L2 → 默认不做

## 与 claude-code v4.2.0 对比

| 维度 | v4 (claude-code) | v5 (cc-tmux) |
|------|-----------------|-------------|
| SKILL.md | 446 行 | ~100 行 |
| 活跃义务数 | 80+ | ~10 per turn |
| 占用检测 | prose 指令 | flock 硬锁 |
| 汇报 | prose 指令 | cc-monitor.sh 格式输出 |
| CC hook 依赖 | 假定的硬门 | 不依赖 |
| 验证 | 15 项 checklist | 5 项 checklist |
