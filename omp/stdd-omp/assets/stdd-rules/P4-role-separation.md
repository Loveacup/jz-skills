---
name: stdd-P4-role-separation
enabled: true
alwaysApply: true
---

P4 分级独立：L1 由当前 agent 内联执行和验证，不强制委派；L2 的 evaluator 必须使用 fresh context 且只读被审对象；L3 必须由独立 auditor 裁决，高风险判定再叠不同 modelRole/provider/模型视角或更强 P3 实态证据。

需要委派时先读取当前 runtime 暴露的 agent roster 与能力，不假定 reviewer/oracle/stdd-auditor 等固定名称存在。所需独立能力不可用时，相关验收 BLOCKED。

同一文件/worktree/state 同时只允许一个 writer。timeout 不证明 writer 已停止；取得 stop acknowledgement、进程退出或锁/lease 释放证据前不得重派同一 ownership。
