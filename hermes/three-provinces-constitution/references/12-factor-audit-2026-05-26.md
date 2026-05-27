# 12-Factor Agents 审计摘要 (2026-05-26)

> 来源: regent 三省六部 session，基于原文对照审计

## 审计结果

- ✅ **7 项优秀**: F1, F2, F4, F8, F9, F10, F11
- 🟡 **5 项部分符合**: F3, F5, F6, F7, F12
- ❌ **0 项严重缺口**

## 关键发现

**护城河**: F8(控制流) — Hermes Kanban block/unblock + 门下封驳精准解决原文"所有框架第一大痛点": 不能在工具选择与执行之间中断。

**最大短板**: F3(上下文窗口) + F5(统一事件流) — 无自定义 XML 标签集，无统一 EmpireThread。

**纠正**: 第一轮凭二手解读的审计将 F12 错标为 ❌ P0。原文称其 "mostly just for fun"，修正为 🟡 P2。

## 优先行动

1. P0: EmpireThread 统一事件流 → 已实施 (empire_thread.py)
2. P0: 自定义上下文标签集 → 已实施 (context_tags.py)
3. P1: request_human_input 一等工具 → 待实施

## 原文出处

humanlayer/12-factor-agents @ GitHub
全文: `references/12-factor-agents-full-text.md`
Obsidian 审计报告: `30-审计/12-factor-agents-原文审计-Hermes对照-20260526.md`
