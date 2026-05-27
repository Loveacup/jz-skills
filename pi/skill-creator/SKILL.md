---
name: skill-creator
description: "Creates, audits, and improves Pi agent skills with compliance-first approach. 11-step flow: capture → grill → progressive disclosure audit → anti-rationalization → rule positioning → checklist → 7-dim scoring → trigger tests → deployment-grounded audit → failure classification (DISCOVERY/OPTIMIZATION/SKILL DEFECT/EXECUTION LAPSE) → targeted revision → deploy. Use when user says '创建skill', '审查skill', '优化skill', 'skill太长了', 'agent不遵循skill', 'audit skill', 'create skill'. Triggers on explicit skill-authoring requests. DO NOT use for general documentation or one-off tasks."
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  tags: [skill, authoring, compliance, deployment-grounded, pi-specific]
---

# Skill Creator — Compliance-First v3.0

不只是写 skill，更确保 agent 真正遵循。v3.0 吸收 SkillEvolver + EmbodiSkill (2026-05) 部署驱动进化。

---

## 🚨 Author Red Flags

| 你脑子里会想 | 现实 |
|-------------|------|
| "指令很清楚，agent 会跟的" | 清楚≠遵循。>200 行就被忽略 |
| "Red Flags 后面再加" | 没它在前 10%，agent 理性化跳过。现在加 |
| "300+ 行没问题" | 每多一行降低合规率。拆到 `references/` |
| "不需要验证清单" | Agent 需要显式自检触发器 |
| "描述差不多就行" | 描述决定触发率。不 pushy → 不触发 |
| "我教别人这些规则，自己的 skill 肯定没问题" | **自反性陷阱**。元 skill 最可能漏掉自己的规则 |
| "我自己审查就行，我写的" | **自审≠部署验证**。SkillEvolver: 另一个 agent 的信号比自审可靠 30% |

---

## 🔀 要不要创建 Skill？

```
用户请求 skill 相关操作？
├── YES → Grill 访谈 → 进入 11 步流程
└── NO → 是文档/一次性任务？ → ❌ 不创建
```

---

## 11 步创建流程

### Step 1: 捕获意图
要做什么？何时触发？期望输出？测试用例？

### Step 2: Grill 访谈
一次一问。能读代码就先读。

### Step 3: 渐进式披露审计

| 层级 | 内容 | 预算 |
|------|------|------|
| 1 | YAML frontmatter | ~100 tokens |
| 2 | SKILL.md body | **<300 行** |
| 3 | references/ | 无限（懒加载） |

**瘦身法则**：

| 膨胀内容 | 移到 | 引用 |
|----------|------|------|
| 详细模式说明 | `references/modes.md` | "See references/modes.md" |
| 查询示例 >3个 | `references/query-patterns.md` | "For patterns: references/..." |
| 完整 schema | `references/schema.md` | "Schema: references/..." |
| Pitfalls >5条 | `references/common-pitfalls.md` | "Full pitfalls: references/..." |

> 案例见 [references/slimming-case-studies.md](references/slimming-case-studies.md) 和 [references/example-web-research-router-v3.md](references/example-web-research-router-v3.md)

### Step 4: 反理性化（Red Flags）
**最重要的一步。** 正文 TOP 10%，预判 agent 借口。

### Step 5: 规则定位
- 决策树 → **TOP 15-30%**
- Red Flags → **TOP 10%**
- 验证清单 → **BOTTOM 10%**

### Step 6: 验证清单
3-7 条可执行的是/否检查项。在文件最底部。

### Step 7: 合规评分（7 维度）

| 维度 | 检查 | 目标 |
|------|------|------|
| 渐进式披露 | <300行？references/ 用于深度？ | ≥4 |
| 反理性化 | Red Flags？≥3 对借口-反驳？ | ≥4 |
| 规则定位 | 核心流程在 15-30%？清单在底部？ | ≥4 |
| 描述质量 | "Use when..." 明确？含 do-not？ | ≥4 |
| 验证 | 清单？3-7 可执行项？ | ≥4 |
| **运行时调用** | 部署到新 agent 确实调用了？无静默跳过？ | ≥4 |
| 部署 | 自同步规则？（多 profile 时） | ≥3 |

> 详细评分标准见 [references/compliance-research.md](references/compliance-research.md)

### Step 8: 测试用例
8-12 should-trigger + 8-12 should-not-trigger。存到 `references/trigger-tests.md`。

### Step 9: 部署驱动审计（SkillEvolver 2026）
**不自己审查。** 部署到新 agent 观察实际使用：
1. 部署到不同 agent/context
2. 执行应被 skill 处理的测试任务
3. 观察：agent 调用了 skill？遵循了关键指令？输出正确？

### Step 9a: 失败分类（EmbodiSkill 2026）

| 分类 | 含义 | 行动 |
|------|------|------|
| 🔍 DISCOVERY | skill 缺 agent 需要的内容 | 加新规则 |
| ⚡ OPTIMIZATION | 规则有效但有更优方案 | 修订具体规则 |
| 🐛 SKILL DEFECT | 规则错误/不完整 | 纠正规则 |
| 🏃 EXECUTION LAPSE | skill 正确但 agent 没遵循 | **不改正文！** 加 emphasis 标记 |

**关键规则：** Execution Lapse ≠ Skill Defect。Agent 忽略有效内容 → skill 是对的不是错的。

### Step 10: 定向修订
- **先积累** B=3-5 个反思再整合
- **合并** 重叠反思，解决冲突
- **定向改** 只改被证据牵连的内容
- **附录更新** Execution Lapse → 加标记不改变正文

### Step 11: 部署
放正确目录。验证触发。

---

## 仓库入库流程（推 jz-skills）

1. 加载 skill-creator → 合规审计
2. 识别差距：缺 Red Flags？没决策树？没验证清单？>300 行？
3. **瘦身**：膨胀内容 → references/
4. **跑 7 维评分**：展示位置证据（Red Flags X%, 决策树 Y%, 清单距底 Z 行）
5. **脱敏**：IP→`<redacted>`，路径→`~/`，API keys→`<redacted>`
6. 复制到 jz-skills
7. **更新 sync-all.sh AND sync-back.sh**（缺一不可）
8. 更新 README badge
9. 提交推送

---

## Pitfalls

| 陷阱 | 后果 |
|------|------|
| 描述不 pushy | 不触发 |
| 缺 do-not | 乱触发 |
| >300 行 | 后半被 agent 忽略 |
| 没 Red Flags | ⚠️ 必填，没它 = 死 skill |
| 决策树埋太深 | 必须在正文前 20% |
| 没验证清单 | Agent 无自检 |
| 自审而非部署验证 | 漏掉静默跳过和过度拟合 |
| 为一个 bug 改全篇 | 破坏有效内容 |
| 混淆 Execution Lapse 和 Skill Defect | 删了正确的规则 |
| 每出一个错就立刻改 | 震荡。先积累 3-5 个再整合 |
| 更新 sync 脚本时批量 patch 不复检 | shell 脚本容易合并掉相邻行 |
| 忘了更新 README badge | 显示错误计数 |

---

## References

| 文件 | 用途 |
|------|------|
| [compliance-research.md](references/compliance-research.md) | 合规优先设计的学术依据 |
| [skill-evolution-research.md](references/skill-evolution-research.md) | SkillEvolver + EmbodiSkill 论文细节 |
| [anti-rationalization-catalog.md](references/anti-rationalization-catalog.md) | Agent 借口全分类 |
| [example-web-research-router-v3.md](references/example-web-research-router-v3.md) | 案例：500→146 行重构 |
| [slimming-case-studies.md](references/slimming-case-studies.md) | 瘦身案例（513→130 等） |
| [absorption-analysis.md](references/absorption-analysis.md) | Skill 吸收分析 |
| [cross-project-evaluation.md](references/cross-project-evaluation.md) | 跨项目评估 |
| [deployment.md](references/deployment.md) | 部署和同步规则 |
| [changelog.md](references/changelog.md) | 版本变更记录 |

---

## 验证清单

- [ ] SKILL.md <300 行？细节在 references/？
- [ ] Red Flags 在 TOP 10%，≥3 对借口-反驳？
- [ ] 决策树在 TOP 15-30%？
- [ ] 描述含 "Use when..." + do-not？
- [ ] 验证清单（3-7 项）在 BOTTOM 10%？
- [ ] 7 维度评分全部 ≥4？
- [ ] 8-12 should-trigger + 8-12 should-not-trigger？
- [ ] 部署到新 agent 验证了运行时调用？
- [ ] 失败按 4 类系统分类？
- [ ] 积累 ≥3 个反思后才整合修订？
