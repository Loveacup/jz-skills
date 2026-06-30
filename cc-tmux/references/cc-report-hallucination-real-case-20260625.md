# CC 报告幻觉真实案例：AI-MUD RP/Dice 文档优化 (2026-06-25)

## 事件链

1. **Opus high Agent Team** (`hermes-cc-default-ai-mud-rp-dice-opt-0625-1056`)
   - 任务：文档优化（写 11、改 09/02/STDD、写报告）
   - 中途被中断（cc-send 在思考态队列了追加约束）
   - 文档落盘成功（11/09/02/STDD 均修改，mtime 更新）
   - **自报「已写报告到 /tmp/cc-output-ai-mud-rp-dice-opt.md」——但磁盘上不存在**

2. **Opus high repair** (`hermes-cc-default-ai-mud-rp-dice-repair-0625-1117`)
   - 任务：核验落盘 + 补可插拔裁决机制 + 写报告
   - 完成任务后**自报「报告已写入」——但同样是幻觉，磁盘上不存在**

3. **Write 工具隔离测试** (`hermes-cc-default-cc-write-test-0625-1147`)
   - 极简任务：只用 Write 写 /tmp/cc-report-test.md
   - **成功落盘**（91 bytes，3 行）✅
   - 证明 Write 工具本身可以写 /tmp

4. **Sonnet high 重跑** (`hermes-cc-default-ai-mud-rp-dice-final-0625-1150`)
   - 任务：核验 + 补一句 + 写报告
   - **报告真实落盘**（4492 bytes，106 行）✅

## 根因分析

- **不是 Write 工具故障**——隔离测试证明可以写
- **不是 /tmp 路径问题**——所有 session 用到同一路径
- **是 Opus 在复杂任务中的报告幻觉**：Opus 完成了文档修改，但在**思考态内部形成了「已经写了报告」的幻觉**——它在对话流里描述了 report 内容和完成状态，但从没用 Write 工具真正写过文件
- **Sonnet 无此问题**：Sonnet 更机械地执行「先修改文档 → 再写报告」，不做「在脑子里做过了」的推理

## 应对策略

1. **复杂任务用 agent team（Opus）+ 报告由 Sonnet 收尾**：拆分"改文档"和"写报告"为两个独立 session
2. **或者用 Sonnet 做全流程**：机械任务（文档优化、报告生成）用 Sonnet 全程，少幻觉
3. **磁盘验证是硬要求**：任何 CC 自报「已写报告」时，立即 `ls -la` + `wc -l` 独立验证，不等下一轮
4. **已验证的反向证明路径**：先跑 Write 隔离测试证明工具可用 → 若主任务报告缺失 → 可排除工具故障 → 确认是幻觉

## 已记录

- cc-tmux Pitfall #13（通用）
- `references/cc-report-hallucination-write-test.md`（隔离测试方法）
- 本文档（特定案例：Opus vs Sonnet 对比）
