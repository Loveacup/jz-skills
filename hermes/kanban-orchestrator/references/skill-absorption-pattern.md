# 外部 Skill 吸收模式（三省六部版）

> 验证于 v0.11：吸收 4 个外部 skill（systematic-debugging、spike、content-polishing、humanizer）入 3 部 profile（engineer、planner、protocol）。

## 模式结构

```
中书拟制吸收方案 → 门下封驳 → 尚书拆解为 N 路并行
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          engineer吸收      planner吸收     protocol吸收
          debugging         spike           polishing+humanizer
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                     御史稽核（验证注入正确 + 无回归）
                              │
                              ▼
                         史馆归档
```

## 与多轨 Rollout 的区别

| | 多轨 Rollout | Skill 吸收 |
|---|---|---|
| 是否新建 profile | 是 | 否 |
| 修改范围 | SOUL.md + config.yaml 全量 | SOUL.md 或 system_prompt 增量 |
| Fan-in 聚合 | 需要（名册/qmd 更新） | 通常不需要 |
| 并行度 | 中（有 P0→P1/P2 依赖） | 高（各路完全独立） |

## 何时用此模式

- 发现外部 skill 的方法论可增强现有 profile 能力
- 不需要新建 profile——现有部的职责覆盖了 skill 的领域
- 吸收方式是"注入规则"而非"添加工具"

## 实战步骤

### 1. 扫描 → 映射

```
systematic-debugging → engineer（四阶段调试法）
spike → planner（预研验证）
content-polishing + humanizer → protocol（表达润色+去AI味）
```

### 2. 中书拟制吸收方案

Planner 产出每条 skill 的核心提炼 + 目标注入位置 + 验收标准。

### 3. 尚书拆解并行卡

三部完全并行，无 parent 依赖：
```bash
T_eng=$(hermes kanban create "engineer吸收debugging" --assignee engineer ...)
T_pln=$(hermes kanban create "planner吸收spike" --assignee planner ...)
T_pro=$(hermes kanban create "protocol吸收polishing" --assignee protocol ...)
```

### 4. 御史验证

检查注入完整性、不破坏现有职责、可触发。

## 已验证

| 版本 | skill 数 | 目标部 | 子任务 | 结果 |
|------|---------|--------|--------|------|
| v0.11 | 4 | 3 | 3 | ✅ |
| v0.12 | 12 (Taste Skill) | 4 (翰林院新 + 礼/工/将作监) | 5 | ✅ |

## Taste Skill 吸收变种（v0.12）

v0.12 引入了一个新变种：吸收的外部 skill 集**既是现有部的能力增强，也触发了新建 profile**。

### 结构

```
Taste Skill 12 项
  ├── imagegen-frontend-web/mobile, brandkit → 翰林院（新建 profile）
  ├── soft/minimalist/brutalist → 翰林院 SOUL.md 视觉风格预设
  ├── design-taste-frontend → 礼部 protocol（前端设计质量标准）
  ├── output-skill → 工部 engineer（防半成品输出）
  ├── redesign-existing-projects → 工部 engineer（审计→修复流程）
  └── image-to-code → 将作监（图像→分析→编码流水线）
```

### 与 v0.11 的区别

| | v0.11 纯吸收 | v0.12 翰林院变种 |
|---|---|---|
| 是否新建 profile | 否 | 是（翰林院） |
| 吸收方式 | 仅 SOUL.md 注入 | 新建 profile SOUL.md + config.yaml |
| 并行度 | 高（各路独立） | 中（翰林院需先建→再注入其他部） |
| 依赖关系 | 无 | 翰林院卡 → 其他部注入 + registry 更新 |

### 翰林院设计要点

- 身份：翰林院大学士，奉监国太子之命负责视觉设计与品牌呈现
- 模型：deepseek-v4-flash
- 工具：hermes-cli, file, todo, image_gen（调用 ComfyUI/FAL）
- 职责边界：不替 engineer 写实现代码，不替 protocol 定表达标准
- 核心规则：视觉风格切换（soft/minimalist/brutalist）+ 图像生成调度

## 常见坑

- **规则重复**：对比现有 SOUL.md，只注入增量
- **职责越界**：如 humanizer → protocol 需加限制"仅对用户汇报场景"
- **注入生效**：system_prompt 修改需重启 session；SOUL.md 与 system_prompt 需同步
