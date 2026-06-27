# References 索引 — 完整目录

> 从 `SKILL.md ## 📦 References` 下沉（v4.1.2 slim）。SKILL.md 只保留最常用入口 + 本文件指针。

| 文件 | 何时读取 |
|------|---------|
| `references/cli-reference.md` | 需要完整 CLI flags（7 张表） |
| `references/effort-routing.md` | Effort 完整体系：五级表 / 智能路由三档表 / 自检决策树 / 实战配置 / 成本换算 / `/effort` 切换陷阱（v4.1.0 从主体下沉） |
| `references/print-mode.md` | Print 模式深度：JSON/流式/管道/Schema/Session/Bare |
| `references/interactive-reference.md` | Slash Commands + 键盘快捷键 |
| `references/configuration.md` | Settings/CLAUDE.md/Subagents/Hooks/MCP/环境变量/同步 |
| `references/critical-pitfalls-table.md` | 完整坑表（39 条） |
| `references/red-flags-table.md` | 完整 16 条「借口 → 反驳」表 |
| `references/core-rules-detail.md` | Core Rules 完整 13 条（#0–#12） |
| `references/decision-trees.md` | 三棵决策树 + 单 CC/Team/并行对照表 |
| `references/occupancy-scan.sh` | 占用检测唯一权威脚本 |
| `references/claude-octopus-hermes-mcp.md` | MCP 桥接配方 |
| `references/obsidian-agent-team-rewrite.md` | Obsidian 大规模重写模式 |
| `references/alex-longterm-agent-team-preference.md` | 用户偏好：默认 tmux 长会话 > print mode |
| `references/two-phase-research-build.md` | 两阶段研究→构建模式 |
| `references/two-phase-review-polish.md` | 两阶段审查→优化模式（2026-05-31） |
| `references/worker-stall-detection.md` | Worker 假死检测：token stalls → ls → tell cc |
| `references/worker-true-stall-no-disk-output.md` | Worker 真死（无磁盘产出）：杀会话 → 手动接管 |
| `references/cc-agent-team-content-research.md` | CC agent team 做内容研究简报的 fallback 工作流 |
| `references/cc-agent-team-parallel-implementation.md` | 并行实施：Leader-wiring 避免共享文件冲突 |
| `references/post-deploy-verification-pattern.md` | 部署后验证：curl 模式、token 脱敏陷阱、持久化字段验证 |
| `references/cc-session-isolation.md` | CC 多 Agent session 隔离完整调查 |
| `references/cc-clean-start-and-residual-input.md` | Clean-start + residual input guard |
| `references/agent-team-multi-lens-review.md` | Agent Team 多 Lens 并行审查模式（2026-05-31） |
| `references/agent-team-disk-verification.md` | Agent Team 磁盘验证：`find -newer` 绕过 tmux UI 盲区（Core Rule #12） |
| `references/teammate-mode-tmux-verified.md` | `--teammate-mode tmux` 官方文档验证（2026-05-31） |
| `Obsidian: CC tmux Agent Team 稳定性优化方案` | 稳定性全流程：session 生命周期、worker 诊断树、异常恢复 |
| `references/progress-reporting-enhanced.md` | 增强进度模板：emoji 状态映射、worker 树、token 跟踪、4 场景模板 |
| `references/cc-status-watchdog-after-complaint.md` | 用户指出未监控后的立即恢复序列（Hermes 自身轮巡，非 watchdog） |
| `references/destructive-cleanup-shadow-review.md` | 高风险删除让 CC shadow-review 成为破坏性步骤前的安全门 |
| `references/direct-numbered-batch-shadow-review.md` | 编号要求"直接处理让 CC 协助"时：解码、先推进确定部分、隔离 shadow-review |
| `references/CHANGELOG.md` | 版本历史：v3.1.0→v4.1.1 完整变更记录 |
| `references/de-slop-cc-integration.md` | de-slop（AI 味去除）CC skill 集成（2026-05-31） |
| `references/taste-skill-mobile-prototype.md` | CC + taste-skill 移动端原型图快速生成（2026-05-31） |
| `references/home-and-sandbox.md` | HOME override 认证 + macOS TCC 沙盒完整方案 |
| `references/cc-agent-team-document-audit.md` | CC agent team 文档审计模式 |
| `references/hermes-research-to-cc-strategic-insight.md` | Hermes 研究 → CC 战略洞察长文的交接模式 |
| `references/claude-octopus-upstream.md` | Claude Octopus 上游项目参考 |
| `references/literary-rewrite-pattern.md` | 文学化重写模式 |
| `references/license-verification-pattern.md` | CC 驱动外部项目许可证核查 |
| `references/cc-self-audit-instruction-following.md` | CC 自审计模式：用讨论协议优化自身 skill 的指令遵循 |
| `references/agent-team-model-selection.md` | CC Agent Team worker 模型选择机制（2026-06-01） |
| `references/hermes-production-env-verification.md` | CC 部署生产服务后按真实 `HOME/HERMES_HOME/PYTHONPATH` 验证 |
| `references/cqi-audit-v41-runtime-fork.md` | v4.1.0 CQI 反审：同版本号分叉、测 A 跑 B、去分叉前暂停单侧 patch |
| `references/cc-output-file-discovery.md` | CC 输出文件定位：`mdfind` vs `find`、`/tmp` 假设陷阱（2026-06-01） |
| `references/three-phase-redesign-pattern.md` | 三阶段大规模重构：讨论→侦察验证→Agent Team 执行（2026-06-02） |
| `references/reference-drift-debugging.md` | Reference 漂移诊断：SKILL.md 已更新但 references 仍教旧模式（2026-06-02） |
| `references/skill-redesign-via-cc-discussion.md` | 通过 CC 讨论协议做 skill 架构重设计（2026-06-02） |
| `references/destructive-system-cleanup-pattern.md` | 四阶段系统清理模式：Archive → Pre-Review → Destroy → Post-Audit（2026-06-03） |
| `references/cqi-instance-pattern.md` | CQI Instance 模式：skill CQI 计划重构为母计划实例的 8 节骨架 + 三桶分流（2026-06-04） |
| `references/jz-skills-cc-first-pattern.md` | jz-skills 仓库改动走 CC agent team 先审查后执行模式（2026-06-03） |
| `references/jz-plugin-ecc-roadmap-pattern.md` | Jz-Plugin 路线图吸收 ECC 优点的 CC 文档重写模式：context 边界、OB+源码+网络 evidence、CQI handoff、残留输入 guard（2026-06-05） |
| `references/gateway-restart-context-preservation.md` | 🆕 Gateway 调试期间的上下文保全：restart 前写 handoff、capture+📡、restart 后先读 handoff，避免 Telegram typing/session 调试把 in-flight agent loop 和 CC 监控打断（2026-06-06） |
| `references/hermes-infrastructure-self-audit.md` | Hermes 基础设施自审计模式（2026-06-03） |
| `references/kanban-swarm-practical-syntax.md` | Kanban Swarm CLI 实测语法 vs 概念语法对照表（2026-06-03） |
| `references/cc-session-mass-cleanup.md` | CC session 批量清理命令序列（2026-06-03） |
| `references/agent-direct-output.md` | 🆕 Agent-direct-output 模式：agent 各自写文件、leader 只 cat，避 max-effort 思考循环（2026-06-05） |
| `references/max-effort-recovery.md` | 🆕 Max-effort 思考循环恢复 recipe：Ctrl+C→窄化→单行短命令→文件传递（2026-06-05） |
| `references/architecture-production-pattern.md` | 🆕 CC agent team 架构文档生产模式：内联 spec + agent 直写文件 + leader cat 合并（2026-06-05） |
| `references/research-agent-team-pattern.md` | 🆕 CC agent team 多论文研究模式：context file → 按角度 spawn → 并行搜 → Leader 简报（2026-06-05 验证） |
| `references/manual-patrol-after-report.md` | 用户要手动持续轮巡时：📡 后必须实际起下一轮 patrol，不能只承诺（不建 watchdog/cron/脚本） |
| `references/turn-based-patrol-truthfulness.md` | 用户质疑"你没在自动轮巡/干预"时：先抓屏不解释 → 立即 📡；turn-based 下别说"自动轮巡"，叫"手动 patrol" |
| `references/tmux-bridge-integration.md` | tmux-bridge MCP pilot：read-act-read 双向通道 + 安装/配置坑 + raw tmux fallback（DP2） |
| `references/agent-team-full-stall-recovery.md` | 🆕 Agent team 全队冻结恢复：症状识别 → 直接杀 → 降复杂度重启（2026-06-08 SIL 复现） |
| `references/delegate-task-cc-fallback.md` | 🆕 CC 反复卡思考循环时的 delegate_task 兜底方案（2026-06-08 验证） |
| `references/cross-project-analysis-with-ob-verification.md` | 🆕 跨项目对比分析 + OB 核实：哲学预检 → 3 Lens 并行 → worker OB 源文件核实 → Leader 合并（2026-06-08） |
| `references/worker-continue-dialog-recovery.md` | 🆕 多 worker 集体卡 "1. Continue" 文件写入权限弹窗 → 批量 `send-keys Enter` 解除（Pitfall ★46） |
| `references/common-pitfalls.md` | 坑表深度细节（#21/#23/#26 等） |
