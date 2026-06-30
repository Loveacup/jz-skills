# CC Sonnet 过度思考陷阱 — WRR v6 架构分析案例 (2026-06-29)

## 场景

触发任务：分析 `/tmp/wrr-v6-architecture-brief.md` 中的 5 个设计问题，产出分析报告。

**第一次尝试**：cc-start.sh 启动 session，注入简报 + 任务说明（含"深度分析专家"角色描述）

**结果**：
- Sonnet 进入「Choreographing… (13m 0s · almost done thinking with high effort)」
- 持续 15+ 分钟停留在 THINKING 状态
- 仅 Read 了简报文件（1 次 Read），未创建任何产物
- cc-wait-marker.sh 超时（600s），无 turn-done 标记

**第二次尝试**：C-c 中断 → send-keys 新指令（"不要过度思考。直接写..."）

**结果**：
- 指令 paste 到了 CC prompt 但未自动提交（Pitfall #54）
- 额外 send-keys Enter 后才提交
- CC 再次进入「Deciphering… thinking with high effort」模式
- 持续 3+ 分钟，无产物

**第三次尝试**：kill-session → 新 cc-start.sh（砍掉"分析/研究"措辞，改为"直接写"）

**结果**（截至案例记录时）：
- CC 进入「Deciphering… almost done thinking with high effort」模式
- 仍无产物

## 根因

Sonnet 的 "high effort" 推理模式对分析类任务（特别是"对比方案""分析优劣"这类开放式问题）会触发深度推理循环。模型认为需要穷举所有方案的所有维度，无法自限。

即使 prompt 中写了「不要深度思考」「不要查资料」「直接写」，模型仍会覆盖这些指令进入 high effort 模式。

## 对策（已写入 SKILL.md Pitfall #53）

1. **轻量**：C-c → 简指令 → 重试
2. **中度**：kill → 新 session → 紧凑任务（砍掉"分析/思考/研究"措辞）
3. **重度**：放弃 CC 做架构分析/方案设计 → 改用 Codex（GPT-5.x 不陷入此模式），CC 只做执行类任务

## 关键教训

- "almost done thinking with high effort" >8 分钟 = 中招，**不是**「快了」
- 架构讨论类任务优先走 Codex（planning-only）模式
- CC 最擅长的是执行类任务（读代码、写 patch、跑测试），不是开放式分析
- 此案例补充了已有的 Pitfall #50（CC Opus 49min 零输出）——不仅是 Opus，Sonnet 也有此问题
