# Healthcheck TDD Loop — 验证驱动开发

> **模式：** 用 `scripts/cc-skill-healthcheck.sh` 作为 TDD 基线——先建红灯 → 改 → 跑 → 验证绿灯 → 继续下一个。

## 适用场景

任何需要对 `claude-code` skill 做结构化优化的任务——去分叉、瘦身、修编号、补 reference、验证规范段——都可以用这个循环。

## 循环步骤

```
1. RUN healthcheck → 记录基线分数（如 0/7）
2. 按 DP 计划改 1–2 项
3. RE-RUN healthcheck → 验证分数变化
4. 分数上升 → 提交，继续下一项
   分数不变/下降 → 检查改了什么，回滚或修正
5. 重复直到全部绿灯
```

## 基线 → 进度示例（2026-06-08 CQI 实施）

| 阶段 | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | 得分 | 根因 |
|------|----|----|----|----|----|----|----|----|------|------|
| 初测 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⏳ | 0/7 | `$HOME` override → 找不到所有文件 |
| 修路径后 | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ⏳ | 4/7 | 路径正确；md5 分叉、行数超标、缺规范段 |
| 目标 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | 7/7 | 全绿（T8 手动门闸不算自动化分数） |

## 关键约束

- **healthcheck 路径必须用绝对路径**（`/Users/alexcai/`），不能用 `$HOME`——Hermes profile 的 HOME override 会让 `$HOME` 指向 `~/.hermes/profiles/<name>/home/`，导致所有路径错误（见 Pitfall ★52）
- T8（行为手动闸门）永远 `⏳ PENDING`——它需要在真实 ≥10min 任务中实测 patrol + Final Input-Line Gate
- healthcheck 是 `fail-loud` 设计：每项打印 PASS/FAIL 与证据，不静默

## CC 执行健康检查的 context file 模板

```markdown
# 任务：跑 healthcheck，按结果修

## 已知事实
- healthcheck 位置：`hermes/claude-code/scripts/cc-skill-healthcheck.sh`
- 所有路径用绝对 `/Users/alexcai/`，禁止 `$HOME`（Pitfall ★52）
- 当前基线：从 `bash hermes/claude-code/scripts/cc-skill-healthcheck.sh` 开始
- 目标：T1–T7 全绿

## 指令
1. 先跑一遍 healthcheck，记录分数
2. 按失败项逐个修——每次修完重跑 healthcheck 验证
3. T7 的 canonical sections 必须在 SKILL.md 中作为独立段存在
```
