# STDD-OMP Onboarding

STDD 必须由用户明确选择，或由项目治理文件明确采用。仅出现“测试、验收、计划、审计”等泛词不启用。

## 第一个 L1

对 agent 明确说：

> 用 STDD 完成这个低风险小改动：[任务描述]。

L1 的最小行为：

1. 内联写一句 Spec；
2. 内联写 1–2 条可证伪 Acceptance；
3. scope 已授权且无歧义时直接 Build，不重复要求确认；
4. 运行直接相关的验证并给出证据锚。

L1 不要求 subagent、独立 auditor、安装体检或配置修改。

## 何时跑 preflight

仅在以下情况运行：

- 首次接入或新 session，需要确认 gate/agent/hook/Advisor 等可执行集成；
- OMP/skill 版本变化；
- 集成、路径或 runtime 能力报错；
- 准备使用 L2/L3 的隔离、异步或独立审计。

只读命令：

```bash
node scripts/orchestrate.mjs --text
node scripts/setup.mjs --status
```

检测不会授权 `--install`、`--apply`、`--upgrade`、改配置、登录或凭据变更。这些动作都需要对应的明确授权。

## L2 与 L3

| 档位 | 要求 |
|---|---|
| L2 | executor 与 fresh-context evaluator 分离；actual agent name 从当前 runtime roster 按能力选择。 |
| L3 | 独立 auditor 必需；高风险叠模型/视角独立或更强实态证据；regen ≤3、slice ≤2。 |

不要照抄历史 agent 名。若 runtime 没有满足能力的 evaluator/auditor，标记 BLOCKED。

## 常见坑

| 坑 | 正确做法 |
|---|---|
| 泛词触发 STDD | 只接受明确选择或项目 adoption。 |
| 每个 L1 都跑体检/起 subagent | L1 内联；preflight 只在集成需要时。 |
| 已授权 scope 仍要求确认 checklist | 记录 checklist 后继续；只对真实分叉提问。 |
| L2/L3 使用固定 agent 名 | 查询当前 roster，按 capability 选并记录实际名字。 |
| 软失败低置信度放行 | 相关项 BLOCKED；仅无依赖 slice 继续。 |
| timeout 后立即重派 | 先拿 stop acknowledgement、进程退出或锁/lease 释放证据。 |
| full-auto 自动 publish/install/auth | 这些动作需要各自明确授权。 |
| executor 自报即通过 | L2/L3 由独立上下文/独立 auditor 复算证据。 |

## 快速检查

- [ ] STDD 已被明确选择/采用；
- [ ] Acceptance 可判真假；
- [ ] scope 已授权且无歧义时未重复确认；
- [ ] L1 内联、L2 独立上下文、L3 独立 auditor；
- [ ] agent 名来自当前 runtime；
- [ ] BLOCKED 未被当作 PASS；
- [ ] timeout 后没有在缺少 stop proof 时重派；
- [ ] full-auto 没有扩大 publish/install/auth/config 权限；
- [ ] regen ≤3、slice ≤2。

进一步阅读：`SKILL.md`；L2/L3 读 `agent-roles.md`，失败语义读 `verify-evidence.md`，full-auto 读 `goal-loop.md`。
