# cc-tmux 自审计工作流

> 2026-06-24 · 用 CC 审计和优化 cc-tmux 本身的元工作流

## 四阶段

| 阶段 | 谁做 | 内容 |
|------|:--:|------|
| ① CC 审计 | CC | 读全代码库 → 逐文件审查 → 实测跑测试 → md5 parity → 产出结构化报告 |
| ② Hermes 审核 | Hermes | Gate verify + 主观审查每项发现 → 确认报告可靠性 |
| ③ 并行实施 | Hermes + CC | Hermes 修 P0/P1（patch 快）· CC 修 P2（实现复杂功能） |
| ④ OB 闭环 | Hermes | 更新 CQI 文档 + 审计报告落 OB + 版本号同步 |

## 与常规 CC 任务的区别

| 维度 | 常规 CC 任务 | 自审计 |
|------|:--:|:--:|
| effort | high（实现类） | high（分析类就够了，xhigh 会 Boogie 黑洞） |
| 审查对象 | 项目代码 | cc-tmux 自身脚本 |
| 审查后 | 不用 | Hermes 逐条裁判后执行修复 |
| 闭环 | 不用 | CQI 文档 + OB 落库 |

## 踩坑记录

| 坑 | 修复 |
|----|------|
| xhigh + Opus 4.8 → 20min Boogie 零产出 | 降 high + 分两轮（代码审计 → 架构审计） |
| API 500 打断 → CC 状态损坏（queued messages） | kill session 重建 |
| 第一次 wait 15min 超时 | CC 在自己复述理解，实际在干活，重发 context 后正常 |
| CC 主动纠正任务文字错误（PostCompact 不存在 → 改用 PreCompact） | 这是**正向行为**，说明 CC 质量高 |

## 复用模板

`templates/architecture-review-context.md` — 用于构造给 CC 的审查任务 context
