---
name: stdd-omp
description: |
  STDD workflow for OMP. Use only when the user explicitly selects STDD /
  Spec-and-Test / 验收驱动 / full-auto GOAL, or when the current project has
  already adopted STDD in its governing instructions. Do not trigger merely
  because a request mentions planning, tests, acceptance, audit, evidence,
  agents, or similar generic words. Do not use for one-off exploration or L0
  drafts unless the user explicitly asks to adopt STDD.
type: workflow
theme: methodology
best_for:
  - 已明确采用 STDD 的项目
  - 需要 Spec → Accept → Build → Verify 可证伪闭环的任务
  - 需要 producer ≠ judge 的 L2/L3 交付
scenarios:
  - 用户明确要求“用 STDD”
  - 项目治理文件明确启用 STDD
  - 明确选择的 L3/full-auto GOAL 闭环
---
# stdd-omp

在 OMP 内运行 STDD（Spec → Accept → Build → Verify）。本文件只做路由；细节按需读取 `references/`，不要预加载全部文档。

## 入口与边界

仅在以下任一条件成立时启用：

1. 用户明确选择 STDD、Spec-and-Test、验收驱动或 full-auto GOAL；
2. 当前项目的有效治理文件明确采用 STDD。

普通的“计划、测试、验收、审计、证据、agent”等词不构成触发。临时探索、一次性查询、L0 草稿默认不用。

### Preflight 不是每次必跑

简单 L1 在当前已工作的 session 内直接进入四步循环，不跑安装/版本体检。仅在以下情况运行只读 preflight：

- 首次接入或新 session 需要确认可执行集成；
- OMP/skill 版本变化；
- `gates.mjs`、agent、hook、Advisor 或安装路径报错；
- 准备启用 L2/L3 的隔离、异步、auditor、WATCHDOG 等可执行接线。

只读检测：`node scripts/orchestrate.mjs --text`。安装、升级、改配置、登录或凭据操作不是 preflight 的隐含后续；必须有对应的明确授权。详见 `references/orchestrate.md` 与 `assets/INSTALL.md`。

## 五条承重墙

| 编号 | 规则 | 未满足时 |
|---|---|---|
| P1 可裁决 | 每条验收项能判 `true/false`，模糊词有量化判据。 | 回 Spec/Accept。 |
| P2 验收不可省 | 没有 Acceptance checklist 不 Build。 | BLOCKED。 |
| P3 证据优先 | 实态 > 测试 > diff > 报告；verdict 必须有可定位证据锚。 | 该验收项 BLOCKED。 |
| P4 分级独立 | L1 当前执行者内联验证；L2 用独立上下文评估；L3 用独立 auditor，高风险再叠不同模型/视角或更强实态证据。 | 不得宣告通过。 |
| P6 终止条件 | regen max=3，slice max=2；达到硬顶停止并升级人工。 | `counter exceeded max`。 |

## L 档与最小流程

| 档位 | 典型范围 | Build / Verify |
|---|---|---|
| L0 | 口头决定、草稿、不落地 | 不启用 STDD，除非用户明确要求。 |
| L1 | 单文件/单模块、低风险、可逆 | 主 agent 内联完成；写 1–2 条验收并拿相关证据，不强制委派或独立 auditor。 |
| L2 | 跨模块、接口/指标变化、需要设计选择 | Plan/梁2；executor 与独立上下文 evaluator 分离。 |
| L3 | 高风险、无人值守、对外交付、多 agent | 梁3/GOAL；独立 auditor 必需，高风险判定叠模型/视角独立或 P3 实态补偿。 |

能 L1 不 L2，能 L2 不 L3。改动两次仍不能收敛、接口/评价口径变化或风险上升时升级档位。

## 四步微循环

### 1. Spec

- 用一句话写 What/Why，不预先扩张 How。
- L1 内联；L2/L3 才创建与复杂度相称的 Plan/三梁工件。
- 先从仓库、工具和现有授权自答；只把真实分叉交给用户。

### 2. Accept

- 在 Build 前写逐条可证伪 checklist。
- 用户已经明确授权且 scope 无歧义时，记录 checklist 后继续，不重复要求确认。
- scope、不可逆动作或验收口径存在真实分叉时才请求决定。
- L3 在 Build 前让独立 auditor 检查契约可证伪性；缺这份证据则相关 Build 阻塞。Build 后的最终 Verify 仍由独立 auditor 裁决，契约审计不能替代它。

形式见 `references/acceptance-forms.md`。

### 3. Build

- L1 由当前 agent 内联执行。
- L2/L3 才按需要委派；从当前 runtime 实际列出的 agent 中按能力选择，不假定任何固定名称存在。找不到满足能力的 agent 时，使用可用的独立 session/模型路径；L3 缺少独立审计能力则 BLOCKED。
- 单一文件/工作区同时只允许一个 writer。并行只用于所有权不重叠的 slice；并发容量只限制同时运行数，不限制总任务数。
- 有前置依赖时，前置任务执行完成不等于交付可用：前置产出通过当前契约的验收、证据可达且版本匹配，才解除依赖。依赖与合流规则见 `references/goal-loop.md`。
- executor 只做已授权 scope；不得把 full-auto 解释为授权 publish/push/deploy/install、认证/登录/密钥、权限提升或运行时配置变更。

角色和 capability 选择见 `references/agent-roles.md`。

### 4. Verify

- 只运行与变更相关的证据动作；没有新变更、失败或未决风险时不重复验证。
- 客观门使用 `scripts/gates.mjs` 的真实 API：`verifyArtifact`、`verifyTest`、`scanDanger`、`bumpCounter`；也可按表面使用 `lsp`、`browser`、`debug` 或实际命令。
- 每条 verdict 附 `file:line`、exit code、日志行或 `agent://<id>` 等可定位锚；无人值守时不可锚率 >40% 整轮作废并计入 regen（即使产物没改）。
- 证据缺失、命令崩溃、部分产出或超时使相关验收项 **BLOCKED**。无依赖的其他 slice 可以继续；依赖该项的 Build、Acceptance、合并、发布或交付不能继续。
- 超时只证明未收到完成证据，不证明 writer 已停止。重新分配前必须取得 stop acknowledgement、进程退出、锁/租约释放或其他可定位的 writer 终止证据；否则保持单 writer 并升级人工。
- 可选 advisor 不替代 auditor：advisor 超时或不可用只记录，不新增阻塞；必需的 auditor 证据缺失则 BLOCKED。

### 动态计划校准与 Jev shadow

- Spec/Accept/Build/Verify 阶段及独立验收工作单元结束、失败或阻塞后，协调者都校准现有计划；新指令、事实、授权或所有权风险立即触发校准。无需制造计划差异；默认只更新受影响部分。
- 计划修订不改验收契约、授权、regen/slice 或所有权。Jev 仅在明确获准、敏感级别允许且存在冻结候选与基线时按需用于 `pick_context_file` shadow；永不控制计划或协调者选择。按需读取 `references/dynamic-plan.md` 与 `references/jev.md`。
- 仅在候选集首次交付给协调者时运行 `node scripts/jev.mjs prepare`，再用 `node scripts/jev.mjs commit-choice` 冻结协调者选择；之后才可调用 `node scripts/jev.mjs shadow`。shadow 失败不会阻止正常协调者流程，也不代表候选/任务验收通过。命令 JSON 输入/回执字段见 `references/jev.md`。
- **托管可行性试验（Alex 2026-10-07 启用）**：STDD 任务中遇到「从多个检索结果中决定先读哪个文件」的检查点时，按 `references/jev.md` 的「可行性试验」节写筛选台账，并在合格时采一个样本。默认只放行公开 GitHub 仓库；私有、无远端、家庭/未成年人与知识库内容不发送，除非 Alex 逐个放行。达到上限或截止即停；结果不改变任何路由。
- regen 达 3 或 slice 达 2：不再开新一轮；进行中的一轮可完成 Verify，仍失败或被作废则停止自动循环并升级人工。计数事件见 `references/verify-evidence.md`。

证据与失败语义见 `references/verify-evidence.md`。

## Full-auto / GOAL 边界

Full-auto 只自动执行 GOAL 中已授权的可逆动作。它不隐含授权：

- git commit/push、发布、部署或对外发送；
- 安装/升级、运行时 repoint 或配置修改；
- 登录、认证、密钥/凭据或权限变更；
- 删除、覆盖、破坏性回滚或其他不可逆动作。

命中上述动作、验收无法判定、writer 状态未知或硬顶到达时，停止相关依赖链并升级人工。完整 GOAL 路由见 `references/goal-loop.md`。

## Runtime 角色选择

不要把文档示例中的 agent 名当作保证。每次需要委派时：

1. 读取当前 runtime/tool 暴露的 agent 列表与能力；
2. 按只读/写入、领域能力、隔离和模型独立要求选择；
3. 把实际 agent 名写入梁3/GOAL；
4. 若所需能力不可用，BLOCKED，不用相似名称猜测。

L1 不要求起角色；L2 要求独立上下文 evaluator；L3 要求独立 auditor。详见 `references/agent-roles.md`。

## 计数与危险门

```bash
node scripts/gates.mjs counter --key <task> --kind regen --max 3 --incr
node scripts/gates.mjs counter --key <task> --kind slice --max 2 --incr
```

发布/推送/部署等危险动作必须有该动作的明确授权并经过 `scanDanger` 或已启用的 hook；“任务已授权”不自动扩大为这些动作。

## 按需读取

- `references/acceptance-forms.md` — checklist 形式。
- `references/agent-roles.md` — L1/L2/L3 独立性与 runtime capability 选择。
- `references/verify-evidence.md` — 证据、BLOCKED、timeout 与 single-writer。
- `references/goal-loop.md` — L3/full-auto GOAL。
- `references/omp-integration.md` — 当前 OMP 接线；仅在需要可执行集成时读。
- `references/macro-calibration.md` — 项目级校准。
- `references/three-beams.md` — 三梁模板纪律。
- `references/gates.md` — gate API/CLI 和退出码。
- `references/orchestrate.md` / `assets/INSTALL.md` — 首次接入、版本变化或集成故障。
- `references/dynamic-plan.md` — 四步计划校准、增量重规划、迟到结果与 D1–D7。
- `references/jev.md` — Jev 的许可边界、prepare/commit-choice/shadow 命令与 J1–J7。

## 交付检查

- [ ] STDD 是显式选择或项目已采用，而非泛词误触发。
- [ ] Acceptance checklist 可逐条判真假；已授权无歧义事项未重复确认。
- [ ] L1 内联、L2 独立上下文、L3 独立 auditor 的强度匹配。
- [ ] 每条 verdict 有相关证据；缺证据项为 BLOCKED。
- [ ] timeout 后未在缺少 stop proof 时重派 writer。
- [ ] regen ≤3、slice ≤2；整轮作废已计入 regen。
- [ ] 有依赖时，前置产出已验收才启动后继；合流后的组合产物单独验收。
- [ ] 未把 full-auto 扩张成 publish/install/auth/config 授权。
