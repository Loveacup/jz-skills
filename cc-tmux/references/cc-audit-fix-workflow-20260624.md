# CC 代码审计 + Hermes 修复工作流

> 2026-06-24 · cc-tmux v1.22.0+ 自审工作流 · 4 轮迭代

## 核心理念

CC 审计找 bug → Hermes 审核报告可靠性 → Hermes 动手修 → CC 实现新功能 → Hermes 验证。

**CC 做需要读大量代码的分析，Hermes 做需要精确 patch 的修改。**

## 四轮工作流

### 第 1 轮：CC 审计
```
Hermes 写 context（审查清单 + 代码库路径 + 约束）
→ cc-start --effort high（非 xhigh，避 boogie 黑箱）
→ cc-send
→ cc-wait-marker 等 turn-done
→ Hermes 审核报告（gate-verify + 主观判断）
```
**产出**：结构化审计报告（文件:行号 + 优先级 + 修复建议）

### 第 2 轮：Hermes 分级修复
```
Hermes 读审计报告
→ P0 先修（崩溃/正确性）
→ P1 再修（可靠性/可信度）
→ 每批修完跑 run-tests.sh
→ deploy sync + md5 parity
```

### 第 3 轮：CC 实现新功能
```
Hermes 写功能 context（精确任务 + 参考代码）
→ cc-start --effort high
→ cc-send
→ 巡检 cc-status（每 3-5min，防 BLOCKED/AskUserQuestion）
→ 及时响应 AskUserQuestion（选推荐项 + Enter）
→ turn-done → Hermes review diff
→ 跑测试 + deploy
```

### 第 4 轮：CC 修复 + 去重
```
Hermes 审计 CC 产出 → 发现测试不兼容 → 修测试适配
→ 跑全量测试确认
→ deploy sync
```

## 关键教训

| 教训 | 详情 |
|------|------|
| **xhigh→high** | 实现类任务用 high effort，xhigh 导致 20+min boogie 无产出 |
| **API 500 后重建** | CC 被 API 500 打断后，重发同一任务会陷入 queue 循环 → 直接 kill session 重建 |
| **主动巡检** | 等 turn-done 时每 3-5min 查 cc-status，BLOCKED 时立即响应 AskUserQuestion |
| **CC 主动纠偏** | CC 发现"PostCompact 事件不存在"时主动追问方案，值得信任——回复后 CC 产出正确代码 |
| **兼容 rc change** | refactor 后 test 的预期退出码可能变化，需适配测试 |
| **deploy sync 每轮做** | 每轮修改后立即 cp + md5，不攒到最后 |

## 本 session 数据

2026-06-24 · 总计修改 ~20 文件 · 测试 15/15 138 断言 · CC 启动 4 次（1 次 API 500 + 1 次 boogie 黑箱 + 2 次成功）
