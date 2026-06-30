# Hermes TDD → CC Review → CC Enhance → Hermes Validate 三方工作流

> 本 session（2026-06-29）中两轮实战验证的模式。
> 区别于 `codex-plan-cc-execute-stdd-pattern.md`（Codex 规划 + CC 执行）和 `three-party-prd-review-pattern.md`（PRD 评审）。

## 适用场景

需要**既有工程能力又有设计眼**的任务：
- 实现新组件 + 希望另一个"大脑"审阅增强
- 自己 TDD 做了 80%，剩下 20% 是设计决策密集区
- 希望有人从不同角度补测试缺口、发现边界

## 四步流程

```
Round 1: Hermes TDD 打底
  ├── 写测试（RED）
  ├── 实现最小可行版（GREEN）
  └── 13/13 全绿，标注"当前限制"留给 CC

Round 2: CC Review + 增强方案
  ├── cc-start.sh 拉起 CC，发 context（含"当前限制"列表）
  ├── CC 读源码 → 跑测试 → 出增强方案 Markdown
  ├── Hermes 审阅方案 → 回答决策点 → 确认
  └── ⚠️ 要求 CC 写方案到 /tmp/ 文件（防 tmux buffer 丢失，Pitfall #49）

Round 3: CC TDD 增强
  ├── 先补测试 → RED
  ├── 修复代码 → GREEN（13→21）
  ├── 全量回归
  └── 产出交付摘要

Round 4: Hermes 独立验证 + 接线 + 推送
  ├── 独立跑测试（不采信 CC 自报）
  ├── 接 Hermes 侧使用层（如 wiring scripts + guide）
  ├── 全量回归 → commit → push to GitHub
  └── 更新 AGENTS.md / SKILL.md 版本号和计数
```

## 成功要素

| 要素 | 为什么重要 |
|------|-----------|
| Hermes 先 TDD 打底 | 保证最小可用 + 测试骨架，CC 不会从零开始 |
| context 含"当前限制" | 给 CC 明确进攻方向，不打乱枪 |
| CC 先出方案再实施 | 避免 CC 埋头写代码方向跑偏 |
| 方案写文件不靠 pane | 防 tmux buffer 丢失（Pitfall #49） |
| Hermes 独立核验 | gate 独立性原则：不采信执行方自报 |
| Hermes 做接线层 | CC 产出脚本，Hermes 产出使用方式和集成 |

## 边界

- 不适合：纯 CRUD / 简单 bug fix / 单文件小改 → 直接用 Codex 或 CC 单干
- 不适合：CC 不稳定时（思考 >5min、OOM、高概率 freeze）
- Hermes 在 Round 4 不过度介入代码改动——只做接线、文档、验证、审查

## 本 session 实例

cc-route.sh 消息路由层：Hermes 13→21 项测试，CC 审出 8 项增强（P0-A SHELL 归 terminal、P0-B jq fallback、P1-A/B/C 输出字段补全、P2 TC14-TC21 测试缺口），全量 20 文件零回归。
