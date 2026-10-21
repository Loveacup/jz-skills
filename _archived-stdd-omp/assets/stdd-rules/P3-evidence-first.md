---
name: stdd-P3-evidence-first
enabled: true
alwaysApply: true
---

P3 证据优先：实态 > 测试 > diff > 报告。禁用推测放行。使用与验收直接相关的运行表面，或 `gates.mjs` 的 `verifyArtifact` / `verifyTest` / `scanDanger` / `bumpCounter` 取得客观证据。

每条 verdict 须附可定位证据锚（file:line / exit code / 日志行 / agent://<id>）。无锚、锚不可达、验证崩溃、部分产出或 timeout 时，相关验收项 BLOCKED；无依赖工作可继续，依赖的 Acceptance/release 不得继续。无人值守整轮不可锚率 >40% 时本轮作废并计入 regen。
