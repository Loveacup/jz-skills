---
name: skill-creator
description: "创建、编辑、审查 Pi agent skills (SKILL.md)，重点在确保 agent 真正遵循 skill 而非跳过。当用户说 '创建skill'、'写skill'、'审查skill'、'优化skill描述'、'skill 太长'、'agent 不执行 skill' 时使用。覆盖完整生命周期：grill 访谈 → 合规优先结构 → 评分 → 发布。不要用于一般文档或一次性任务。"
version: 6.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  tags: [skill, authoring, compliance, pi-specific]
---

# Skill Creator — 合规优先的 Skill 创作

不只是怎么写 skill，更是怎么让 agent 真正遵循。

---

## 🚨 Red Flags: 创作前自查（你脑子里会冒出来的）

| AUTHOR 借口 | Agent 现实 |
|-------------|-----------|
| "指令很清楚，agent 会跟的" | 清楚≠遵循。注意力窗口有限，超 200 行就被忽略 |
| "Red Flags 表格后面再加" | 没有它在前 10%，agent 会理性化跳过。现在就加 |
| "300+ 行无所谓，内容都重要" | 每多一行降低合规率。拆到 `references/` |
| "不需要验证清单" | Agent 需要显式自检触发器。没它步骤就被跳过 |
| "这个 skill 特殊，通用规则不适用" | 合规漏洞打所有 skill 类型，无一例外 |
| "描述写得差不多就行" | 描述决定触发率。不够 pushy → 不触发。缺 do-not → 胡乱触发 |

**如果你心里冒出了以上任何一句 → 停下，按下面流程来。**

---

## 🔀 决策树: 要不要创建 Skill？

```
用户请求 skill 相关操作？
├── 是 → 继续
│   ├── grill 访谈（一次一问）→ 理解意图
│   ├── 读现有 skill/code/doc → 补充上下文
│   └── 进入创作流程 ↓
└── 否 → 这是文档？一次性任务？→ ❌ 不创建 skill
```

---

## 创作流程（9 步）

### 1. 捕获意图
要做什么？何时触发？期望输出？需要什么测试用例？

### 2. Grill 访谈
一次一个问题。决不批量。能读代码/文档回答的就不问。

### 3. 合规优先结构
- **Red Flags** 在正文 TOP 10% — 拦截 AGENT 和 AUTHOR 的借口
- **决策树** 在 TOP 20% — agent 看到的第一件事
- **正文 < 300 行** — 细节移到 `references/`，标注"何时加载"
- **验证清单** 在 BOTTOM 10% — 3-7 个可执行的是/否检查项

### 4. 验证结构
Red Flags 在最顶？决策树在前 20%？清单在底部？术语一致？

### 5. 合规评分
6 个维度：渐进式披露、反理性化、规则定位、描述、验证、部署。
目标：所有维度 ≥4 分。

> 详细评分标准见 [references/compliance-research.md](references/compliance-research.md)

### 6. 写测试用例
8-12 个 should-trigger + 8-12 个 should-not-trigger。

### 7. 评估迭代
修过度/不足触发。如果批量编辑 ≥5 次，重新读完整文件检查结构。

### 8. 优化描述
第三人称、pushy、"Use when..." + 触发关键词 + 做什么 + 何时 + do-not。

> 反理性化技术细节见 [references/anti-rationalization-catalog.md](references/anti-rationalization-catalog.md)

### 9. 部署
放到正确的 skills 目录。验证触发。

> 部署工作流见 [references/deployment-workflow.md](references/deployment-workflow.md)

---

## Pitfalls

| 陷阱 | 后果 |
|------|------|
| 描述不够 pushy | 不触发（undertriggering） |
| 描述缺 do-not | 乱触发（overtriggering） |
| 正文超 300 行 | 后面内容被 agent 忽略 |
| 只解释 WHAT 不说 WHY | Agent 理解不了优先级 |
| 术语不一致 | Agent 混淆同类概念 |
| 缺测试用例 | 改了描述不知道是否破坏触发 |
| 模糊名称 | 用动名词形式（如 `recover-hindsight-mcp`） |
| 为一次性任务建 skill | 浪费 token，污染 skill 列表 |
| 批量访谈问题 | 用户只答最后一个，前面白问 |
| 能读文档却开口问 | 浪费用户时间，降低信任 |
| 漏 Red Flags 表格 | ⚠️ 必填。没有它 skill 形同虚设 |
| 决策树埋太深 | 必须在正文前 20% |
| 批量 patch 后不复检 | ≥5 次编辑后重新读全文 |
| 写给人类看而非 agent | Agent 是读者，人类是审阅者 |
| 没验证清单 | Agent 没有自检机制 |

---

## 验证清单

- [ ] Skill 文件在正确路径
- [ ] name 小写+连字符+动名词
- [ ] description 第三人称、pushy、含 do-not
- [ ] Red Flags 表格在正文 TOP 10%
- [ ] 决策树在正文 TOP 20%
- [ ] 正文 < 300 行；细节在 `references/`
- [ ] 验证清单（3-7 项）在 BOTTOM 10%
- [ ] 6 维度合规评分 ≥4
- [ ] should-trigger 全激活；should-not-trigger 全跳过
- [ ] 如果批量编辑过：重新读全文确认无结构缺陷