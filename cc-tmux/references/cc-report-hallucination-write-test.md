# CC 报告幻觉：自报“已写”但磁盘无文件 — 诊断与修复

> 2026-06-25 AI-MUD 项目文档优化多轮 CC 中复现。CC（Opus/Sonnet）在复杂任务（多文件 patch + agent team）中声称已写入 `/tmp/cc-output-*.md`，但真实磁盘不存在该文件。

## 问题本质

不是 Write 工具坏了。我们用极简任务验证过：

- 干净 session + 单任务「write `/tmp/cc-report-test.md`」→ 真实落盘 91 字节 ✅
- 同一台机器、同一用户、同一 CC CLI 版本

所以问题是 **CC 在复杂多步任务中产生了「已写」的虚假自报**——它在对话流里描述了文件内容和行数，但从没调过 Write/Bash 写文件。这与 Pitfall #13 一致。

## 诊断流程（两段）

### 阶段 A：快速判定

```bash
ls -la /tmp/cc-output-<expected>.md /private/tmp/cc-output-<expected>.md 2>&1
```

如果文件存在 → 真写；检查 size 和最后一行。
如果文件不存在 → 进入阶段 B。

### 阶段 B：Write 工具可达性隔离测试

当 CC 自报写了但磁盘无文件，需要区分「工具坏了」还是「任务太复杂导致幻觉」：

1. 停止当前 CC task（C-c 或 kill）
2. 用干净新 session 跑极简任务：
   - context 只含一条指令：「用 Write 工具把 3 行文字写入 `/tmp/cc-report-test.md`，然后用 Bash 验证」
   - 用 Sonnet（更快）或 Opus，不要 agent team、不要外部搜索
3. 查盘：
   ```bash
   ls -la /tmp/cc-report-test.md
   ```
4. 判定：
   - 文件存在 ≈ 工具正常，原 task 因复杂度/混乱产生幻觉 → 用小范围 fresh CC 重做
   - 文件不存在 ≈ 环境问题（权限/sandbox/磁盘满）→ 排查环境

## 恢复策略：模型降级 + 范围收敛

当 CC 多轮均幻觉，且阶段 B 已证明 Write 工具可达，**不要用同模型/同 effort 重试**——CC 在相同配置下倾向重复相同幻觉模式。

实测有效的恢复法（本 session 验证）：

1. **降 effort**：xhigh/max → high
2. **换更轻模型**：Opus → Sonnet
3. **缩任务范围**：去掉「审文档 + 写 patch + agent team + 写报告」，改为「核验磁盘 + 补一句 + 只写报告」
4. 结果：Opus xhigh 连续 2 轮幻觉，Sonnet high 第 1 轮成功落盘

## 历史案例

| 日期 | 任务 | 模型 | effort | 自报 | 磁盘 | 根因 |
|---|---|---|---|---|---|---|
| 2026-06-25 | AI-MUD RP/Dice 文档优化 | Opus 4.8 agent team | xhigh | 写 `/tmp/cc-output-ai-mud-rp-dice-opt.md` 106 行 | 无文件 | 疑似工具输出注入 + 复杂任务混乱 |
| 2026-06-25 | AI-MUD RP/Dice 修复 | Opus 4.8 | xhigh | 写同路径报告 | 无文件 | 同 |
| 2026-06-25 | AI-MUD RP/Dice 第三次 | Sonnet 4.5 | high | 写同路径报告 | 4492 字节 ✅ | — |
| 2026-06-25 | Write 极简测试 | Sonnet 4.5 | high | 写 `/tmp/cc-report-test.md` 3 行 | 91 字节 ✅ | — |

## 与 Pitfall #13 的关系

Pitfall #13 已覆盖「CC 声称已完成但磁盘无产物」。本文件是它的**诊断扩展**：当该 pitfall 触发时，用极简 Write 测试来隔离问题归因（工具故障 vs 任务幻觉），避免错误地全局判「CC Write 工具不可用」。

## 另一高频触发：cc-start 后忘记 cc-send

`cc-start.sh` 启动 CC session 后，必须用 `cc-send.sh` 发送 context。如果漏掉这一步：
- CC pane 只显示启动头（Claude Code v2.x.xxx / 模型 / 工作目录），没有任务内容
- CC 在空闲态白等，心跳正常但无任何产出
- Hermes 可能在等 turn-done，双方互等数分钟

**预防**：cc-start 后立即 cc-send + 5s 后 `capture-pane` 确认 ❯ 后出现「Please read /tmp/cc-context-*.md」。

