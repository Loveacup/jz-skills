# STDD-OMP 新用户 Onboarding

从零到第一个 STDD 任务，约 5 分钟。

## 5 分钟快速开始

### 1. 确认 skill 已加载

在 OMP 中输入 `STDD`，如果 agent 引用了 stdd-omp 说明已加载。如果没反应，检查 agents lane 是否启用（见 `assets/INSTALL.md`）。

### 2. 跑体检

```bash
node scripts/orchestrate.mjs --text
```

期望输出：
```
✅ All components installed. No action needed.
```

如果有 `Missing opt-in components`，告诉 agent「帮我装」，agent 会执行 `--install`。

### 3. 跑完整体检

```bash
node scripts/setup.mjs --status
```

期望输出：
```
STDD-OMP 0.2.0 | OMP 16.2.3 | compatible
✅ hook  ✅ rules  ✅ wdog.md  ✅ wdog.yml
No action needed.
```

如果 config 缺项，agent 会帮你补上（见 `assets/INSTALL.md` 推荐配置）。

### 4. 发第一个 STDD 任务

选一个不超过 2 个文件的小改动，对 agent 说：

> 「用 STDD 帮我做一件事：[你的任务描述]」

Agent 会自动走 Spec → Accept → Build → Verify 四步。

## 部署检查清单

逐条打勾，缺什么补什么：

- [ ] `node scripts/orchestrate.mjs --text` → `All components installed`
- [ ] `node scripts/setup.mjs --status` → 全部 ✅
- [ ] `~/.omp/agent/config.yml` 含 `memory.backend: local` + `approvalMode: write` + `task.isolation` + `task.async`
- [ ] `~/.omp/agent/WATCHDOG.yml` 存在（v3 双 advisor，16.2.3+）
- [ ] `~/.omp/agent/rules/` 含 P1-P6 规则文件
- [ ] 重启 OMP session 后 `/advisor status` 显示 Reviewer + Claim Verify

## 第一个 STDD 任务（可直接复制粘贴）

选一个小任务试试水：

> 用 STDD 帮我在项目根目录加一个 `.stdd/` 目录和 `.gitkeep` 文件，确保 `.stdd/` 在 `.gitignore` 里。

这是 L1 任务，agent 会：
1. 写一句 Spec
2. 让你确认 Accept checklist
3. Build（创建文件）
4. Verify（检查文件存在 + gitignore 正确）

通过后试试 L2 任务：

> 用 STDD 帮我重构 `src/utils/helpers.ts`，把日期处理函数抽到单独文件，保持原有测试通过。

## 常见坑

| 坑 | 现象 | 解法 |
|---|---|---|
| **跳过 Accept 直接 Build** | agent 没让你确认 checklist 就开始改代码 | 说「先给我 Accept checklist」；这是 P2 铁律 |
| **agent 自审** | executor 改完代码后自己说「通过了」 | 说「起独立 auditor 审」；P4 要求 producer ≠ judge |
| **推测放行** | agent 说「应该没问题」「大概过了」 | 说「拿证据：gates.mjs verify 或 lsp diagnostics」；P3 禁止推测 |
| **opt-in 组件没装全** | agent 没拦截危险命令、没回合级审查 | 跑 `setup.mjs --status`，缺的用 `--apply` 补 |
| **L0 草稿当 L2 交付** | 小改动走了全套流程，浪费时间 | L0 口头确认即可；对照 SKILL.md 分档表选正确的档位 |

## 核心概念速览

| 术语 | 一句话 |
|---|---|
| 梁1（需求基准线） | What / Why，不写 How |
| 梁2（共维实现方式） | 设计决策、接口、风险 |
| 梁3（agent 执行层） | 任务切片、审计链、退出条件 |
| P1 可裁决 | 每条验收能判 true/false |
| P2 验收不可省 | 没有 Accept 契约不 Build |
| P3 证据优先 | 实态 > 测试 > diff > 报告 |
| P4 角色分离 | executor ≠ auditor |
| P6 终止条件 | regen ≤3, slice ≤2 |

详细定义见 `SKILL.md` 硬规则区。

## 下一步

- **日常使用**：对任何 L1+ 任务说「用 STDD 帮我做 X」
- **无人值守**：L3 任务可配 full-auto 档（见 `references/goal-loop.md`）
- **自定义角色**：需要专门 auditor 时参考 `references/agent-roles.md`
- **深入理解**：读 `SKILL.md` 的四步微循环和角色编排
