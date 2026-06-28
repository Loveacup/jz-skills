---
name: stdd-P4-role-separation
enabled: true
alwaysApply: true
---

P4 角色分离：producer ≠ judge。L2 用干净 session / 不同 modelRole，L3 必须起独立 auditor（reviewer / oracle / stdd-auditor）。

独立性两维：①上下文独立（换 session/子 agent，OMP task 子 agent 天然不继承历史）②模型独立（auditor 用不同 modelRole/provider，或 WATCHDOG.yml 委员会 per-advisor 跨模型）。同模型 fresh 子 agent 只买①；高风险判定须叠②或 P3 实态补偿。
