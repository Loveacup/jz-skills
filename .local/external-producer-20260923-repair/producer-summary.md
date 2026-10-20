# call-omp repair producer summary

已完成唯一修复提交 `3c0caa8bdcb9c6b89a066ed8a7a00adab708fd60`，父提交 `aa44eecc4630e96c82f7688a44ec2e452b8fdfae`。仅修改两份 probe/test 源文件；正常 hook 启用，15 项 focused tests 通过。

| 场景（各一次，无重试） | worker exit | accept exit | 观察结果 |
|---|---:|---:|---|
| normal | 0 | 0 | 三个产物业务断言成立 |
| controlled failure | 1 | 2 | rejected、cleanup_confirmed |
| exact-owned cancel | 143 | 2 | 三个 owned PID 消失、独立 sentinel 存活、rejected、cleanup_confirmed |

Darwin numeric SID 来自原生 `getsid()`，由两次一致的 `ps -ww` 身份查询夹持；PID/PPID/PGID/SID、完整 command 显示与 start-time 均保留。`sess` 不再充当数字 SID。

**仍为 BLOCKED**：完整动态依赖加载不可证明；清单绑定已知 1083/1084/1083 个文件（含模板、harness、fixture、interpreter、OMP），不替代动态加载观察。禁止变更面只有受限 metadata／local Git 观察，且 `~/.hermes` 目录 mtime 发生变化、归因未知；credential/provider、Gateway/Kanban、远端 push audit 与 runtime 内容不作无变更认证。

旧 evidence 全部哈希未变。详见 `producer-summary.json` 的 rejected item 1–5 逐项映射、`producer-readback.json` 和三份 receipt。此为 producer 交付，**不授予 W1 PASS 或部署准入**；最终裁决归独立 reviewer。
