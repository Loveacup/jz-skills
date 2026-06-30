# WRR OB 三梁重构 case study（2026-06-29）

## 背景
WRR（web-research-router）OB 项目目录从 7 子目录 + 36 文件的传统结构，重构为 STDD 三梁模型。

## 成功的关键：短指令 + 读文件模式

5 次失败尝试（累计 40+ 分钟零产出）vs 1 次成功（2 分钟产出审查报告）：

**失败的：**
- `cc-start.sh --task "长中文指令（~500 字）"` → Opus high effort 3.5 分钟 thinking → idle
- `tmux send-keys "多行指令"` → CC 消息队列化，不执行
- `tmux send-keys "cat file && claude --resume"` → 同上
- `claude -p "非交互模式"` → 执行完即退出

**成功的：**
```bash
tmux new-session -d -s "cc-wrr-ob" -c /tmp "claude --model claude-opus-4-8"
sleep 5  # 等 ❯
tmux send-keys -t cc-wrr-ob "按 /tmp/cc-task-ob.md 执行。直接动手。" Enter
```

CC 自己读 `/tmp/cc-task-ob.md`（338 字节短文）→ 读 `/tmp/wrr-ob-restructure-plan.md`（361 行方案）→ 2 分钟产出 61 行审查报告 → 随后完成 50 文件迁移。

## 工作流模式

| 步骤 | 谁 | 工具 | 产物 |
|------|-----|------|------|
| ① Spec + ② Accept | 小黄 | 验收契约 | 8 条 criterion |
| 方案设计 | Codex | 读 STDD 方法论 + OB 目录 + v6 设计 + CC 评审 | 361 行重构方案 |
| ③ Build | CC | 裸 tmux + 短指令 + 读文件 | 审报 + 迁移执行 |
| ④ Verify | OMP + 小黄 | async shell audit + 交叉验证 | 审计 verdict + 验证报告 |

## 关键教训
1. CC 的过度思考由**输入复杂度**触发，不是模型问题（Opus/Sonnet 都中招）
2. persisted-output 污染会令新 session 假死
3. send-keys 多行 = 队列化，永不执行
4. 单行「读文件」指令 = 稳定通道
