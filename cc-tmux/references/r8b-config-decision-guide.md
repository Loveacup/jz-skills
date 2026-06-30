# R8b CC 配置自动决策指南

> **落地版本**：v1.21.0（决策指南，零脚本）。**需求来源**：PRD `CC-TMUX核心需求.md` §6 R8b。
> **一句话**：Hermes 接任务 → 分析信号 → 生成推荐配置（effort / 模型 / 4 个模式开关）→ 启动。
> **不是硬编码规则**——是决策指南，Hermes 读后**自主判断**，细则留给实跑调优。
> **配套**：SKILL.md §2 决策树（单一入口）；`cc-start.sh --effort/--model/--task` 接口不变。

---

## 0. 落地通道（关键：每项配置走哪条路）

配置项分两类落地通道——**别把不是 cc-start 参数的东西当参数传**：

| 配置项 | 落地通道 | 怎么落 |
|--------|---------|--------|
| **Effort** | ✅ cc-start 参数 | `cc-start.sh --effort high\|xhigh\|max` |
| **模型** | ✅ cc-start 参数 | `cc-start.sh --model claude-opus-4-8\|claude-sonnet-4-6` |
| **Agent Team** | 📝 context 指示 CC | 在任务 context 里写「本任务用 Agent Team 拆，按关注点（非按文件），timeout 10min/worker」 |
| **Ultra Code** | 📝 context 指示 CC | context 里写「开 Ultra Code 做深度调研/批量搜索」 |
| **Ultrathink** | 📝 context 指示 CC | context 里**单条命令级**指示（「这一步 ultrathink」），**不是全局开关**（PRD 明确） |
| **Workflow** | 🛠️ Hermes 侧编排 | Hermes 自己用 Workflow 工具编排多阶段，不是发给 CC 的参数 |

> cc-start 只有 `--effort`/`--model`/`--task`/`--target`/`--agent`/`--ack-active`。模式开关都不是脚本参数，
> 别杜撰 `--ultracode` 之类不存在的 flag。

---

## 1. Effort 决策（地板 high，绝不降到 high 以下）

```
分析任务信号 → 选 effort：
├── 简单 / 单点 / 无明显信号        → high（地板，默认）
├── 多文件 / 代码审查 / 批量改动     → xhigh
└── 架构设计 / 根因调试 / 写 skill   → max
```

| 信号 | effort |
|------|:--:|
| 单文件小改、明确无歧义、机械任务 | `high` |
| 跨多文件、代码审查、重构、批量操作 | `xhigh` |
| 架构/系统设计、深度根因调试、写/审 skill、复杂推理 | `max` |

> **铁律**：地板是 `high`，绝不降到 high 以下。拿不准 → 往高选（宁可多花，别欠思考）。
> **冻结风险提示**：xhigh/max 在**工程实现类**任务上易长思考冻结（Pitfall #14/#16）——
> 实现类（写代码/跑命令为主）任务即便复杂也优先 `high`，把 max 留给**思考/设计/调试**类。

---

## 2. 模型决策（默认 Opus）

```
├── 杂活 / 机械 / 格式化 / 简单提取    → Sonnet（claude-sonnet-4-6）
└── 复杂推理 / 设计 / 调试 / 写作      → Opus（claude-opus-4-8，默认）
```

| 信号 | 模型 |
|------|:--:|
| 文本搬运、格式转换、简单脚本、确定性高的杂活 | `claude-sonnet-4-6` |
| 需要推理/权衡/创造/深度理解的任务（默认） | `claude-opus-4-8` |

> token 预算敏感（用量紧张，见 R8c）时，杂活更应降 Sonnet 省额度；但**推理类任务不为省钱降级**。

---

## 3. 模式开关（按需开启，默认关）

| 开关 | 默认 | 开启条件 | 落地 |
|------|:--:|---------|------|
| **Agent Team** | 拆分型任务**默认启用** | 任务可按**关注点**拆（非按文件）成并行子任务 | context 指示：按关注点拆、timeout 10min/worker |
| **Ultra Code** | 关 | 深度调研 / 批量搜索 / 多源交叉验证 | context 指示 CC 开 |
| **Workflow** | 关 | 持续**数天**的大型项目才启用 | Hermes 侧 Workflow 编排 |
| **Ultrathink** | 关 | 某一步需要额外深推 | context 里**单条命令级**指示，非全局 |

> Agent Team 拆分原则：**按关注点拆，不按文件拆**（如「测试 / 实现 / 文档」三 worker，不是「file1 / file2 / file3」）。

---

## 4. 边界案例与例外

| 情况 | 处理 |
|------|------|
| 实现类任务但很复杂（多文件重构） | effort `xhigh`（不上 max，避冻结），可配 Agent Team 拆 |
| 纯思考/设计但产物小（写一段架构决策） | effort `max` + Opus，不需要 Agent Team |
| 用量紧张（R8c 提醒不足） | 杂活降 Sonnet；effort 仍守地板 high，不为省钱降思考质量；必要时**提醒 Alex**（不代决暂停） |
| 任务同时是「调研 + 实现」 | 🔴 **必须拆两段 session**（2026-06-27 教训：Opus+Ultra Code 混合任务→49min 思考 0 代码落地+工具故障）。调研段 Sonnet Agent Team 做只读→写方案文档（落盘验证）→实现段另起 session Opus high。**绝不**在同一 session 内让 Ultra Code 做调研后又要求代码落地。 |
| 拿不准复杂度 | 往高选 effort + Opus；可在 R2.1 澄清阶段让 CC 自评复杂度后再定 |

---

## 5. 何时问 Alex（决策流的人审触发）

**默认 Hermes 自主决策**（生成推荐配置 → 启动）。**仅以下情况问 Alex**：

- **从未见过的任务类型**——信号无法映射到已知配置档，没有先例可参照
- **配置含红线代价**——如必须开 Workflow（数天项目，占用大量资源）且 Alex 未预期
- **用量天花板风险**——预估消耗逼近额度上限（R8c），暂停与否是 Alex 的资源决策

> 其余一律 Hermes 自己拍：接任务 → 分析信号 → 套本指南 → 生成 `cc-start.sh --effort X --model Y` + context 模式指示 → 启动。
> 决策可在 R2.1 澄清阶段与 CC 二次确认（可选），但不必每次问 Alex。

---

## 6. 与现有机制的关系

- **SKILL.md §2 决策树**：本指南是 §2「调哪个 effort？」小树的系统化增强——§2 是单一入口（含 effort+模型+模式），细则查本文件。
- **R2.1 澄清式交接**：复杂任务可在澄清阶段让 CC 自评复杂度/工具需求，反过来校准配置。
- **R8c 用量管理**：用量紧张时影响模型选择（杂活降 Sonnet）与「何时问 Alex」。
- **cc-start.sh**：接口不变；effort/模型走参数，模式开关走 context 指示 / Hermes 侧。
