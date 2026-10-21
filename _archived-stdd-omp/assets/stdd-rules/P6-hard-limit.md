---
name: stdd-P6-hard-limit
enabled: true
alwaysApply: true
---

P6 终止条件：regen max=3，slice max=2。达到硬顶必须停止自动循环并升级人工。

证据不足、超时、崩溃或部分产出使相关验收项 BLOCKED：无依赖工作可以继续，依赖该项的 Acceptance、合并、发布和交付不得继续。软失败不是低置信度放行。

沉默/timeout 只证明未收到完成证据，不证明 writer 停止；没有 stop proof 时禁止自动重派同一 ownership。
