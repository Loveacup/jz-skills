# 12-Factor Agents × Hermes 审计结果与实施方案

> Session: 2026-05-26
> 审计执行: Claude Code agent team (2 轮，第1轮基于二手解读，第2轮基于原文)

---

## 第一轮审计（❌ 基于二手解读，已被第二轮修正）

主要偏差：F12 被标为 ❌ P0。原文称其 "mostly just for fun"。

## 第二轮审计（✅ 基于原文）

### 评分总览

| Factor | 评分 | 优先级 | 关键点 |
|--------|------|--------|--------|
| F1 Natural Language → Tool Calls | ✅ | — | delegate_task 即此范式 |
| F2 Own Your Prompts | ✅ | — | profiles 独立 prompt |
| F3 Own Your Context Window | 🟡 | P0 | 缺自定义 XML 上下文标签 |
| F4 Tools = Structured Outputs | ✅ | — | delegate_task + 门下封驳 |
| **F5 Unify State** | 🟡 | **P0** | **缺统一事件流，已通过 EmpireThread 修复** |
| F6 Launch/Pause/Resume | ✅ | — | Kanban block/unblock |
| F7 Contact Humans w/ Tools | 🟡 | P1 | 人机交互未建模为 tool call |
| **F8 Own Control Flow** | ✅✅ | — | **护城河：审批在工具选择与执行之间** |
| F9 Compact Errors | 🟡 | P1 | 缺连续错误计数升级 |
| F10 Small Focused Agents | ✅ | — | 三省六部天然小而专 |
| F11 Trigger From Anywhere | ✅ | — | Telegram + Cron + API |
| F12 Stateless Reducer | 🟡 | P2 | "mostly just for fun" |

### 总体合规度: ~78%

---

## 三件套实施方案

### Phase 1: EmpireThread ✅ 已完成
- empire_thread.py (523行, 14事件类型, 35测试)
- JSONL append-only 存储
- pre_tool_call hook 拦截 8 种工具

### Phase 2: 上下文标签集 ✅ 已完成  
- context_tags.py (299行, 10种XML标签, 23测试)
- thread_to_prompt() 折叠为 <system_history>
- SOUL.md + system_prompt 追加标签指令

### Phase 3: request_human_input ⏳ 待实施
- 人类交互建模为 tool call
- Telegram Gateway 降级为 channel router

---

## 知识库归档

- Obsidian: `30-审计/12-factor-agents-原文审计-Hermes对照-20260526.md`
- Obsidian: `10-制度/12-factor-三件套实施方案-20260526.md`
- 原文全文: `three-provinces-constitution/references/12-factor-agents-full-text.md`
- 审计摘要: `three-provinces-constitution/references/12-factor-audit-2026-05-26.md`
