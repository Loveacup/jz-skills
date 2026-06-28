---
name: stdd-P6-hard-limit
enabled: true
alwaysApply: true
---

P6 终止条件：regen max=3，slice max=2。超过硬顶必须升级人工，禁止无限循环。

硬失败 = regen 达 3 → 停升级。软失败 = 超时/崩溃/部分产出 → 降级放行 + 标低置信度 + 不阻塞下游，绝不静默当通过。沉默即失败：约定时间无 turn-done 即异常。
