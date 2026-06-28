---
name: stdd-P3-evidence-first
enabled: true
alwaysApply: true
---

P3 证据优先：实态 > 测试 > diff > 报告。禁用推测放行。请用 gates.mjs verify / lsp / debug / browser 给出客观证据。

claimcheck 反幻觉门：每条 verdict 须附可定位证据锚（file:line / exit code / 日志行 / agent://<id>）；无锚或锚不可达即判不通过；整轮不可锚率 >40% 则本轮作废重跑（无人值守强制开）。
