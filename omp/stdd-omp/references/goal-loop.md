# L3 / full-auto GOAL 闭环

仅在用户明确选择 L3/full-auto 或项目治理文件已采用该模式时使用。Full-auto 是验收循环，不是无限权限。

## GOAL 最小模板

```yaml
GOAL: <一句话目标>
AUTHORIZED_SCOPE:
  - <允许的文件/系统/动作>
ACCEPT:
  - id: A1
    criterion: <可证伪项>
    verifier: <相关证据动作>
    threshold: <PASS 阈值>
REJECT_IF:
  - <反例/危险边界>
STOP_AFTER:
  regen: 3
  slice: 2
EXECUTOR:
  runtime_agent: <从当前 roster 按写入能力选择>
AUDITOR:
  runtime_agent: <从当前 roster 按只读审计能力选择>
  independence: <fresh-context + high-risk model/view requirement>
FORBIDDEN_UNLESS_SEPARATELY_AUTHORIZED:
  - commit/push/publish/deploy/external-send
  - install/upgrade/runtime-config/repoint
  - login/auth/credential/privilege-change
  - delete/overwrite/destructive-rollback
ESCALATE:
  - counter-limit
  - blocked-evidence
  - unknown-writer-state
  - danger-or-irreversible
MODE: interactive | full-auto
```

不要把示例 agent 名写死。GOAL 编译时先读取当前 runtime 的 agent 列表和权限；缺少所需独立 auditor 时，L3 为 BLOCKED。

## Verdict

```yaml
id: A1
verdict: PASS | FAIL | BLOCKED
anchor: <file:line | exit code | log line | agent://id>
blocks: <依赖项/acceptance/release>
next_action: continue | rebuild | revise-contract | escalate
```

- PASS：证据直接覆盖 criterion 与 threshold。
- FAIL：存在明确反例。
- BLOCKED：证据缺失、验证崩溃、部分产出、timeout 或能力不可用。
- coordinator 只能按 verdict 路由，不能自行把 FAIL/BLOCKED 改成 PASS。

## 循环

```text
Plan: Spec + Accept + authorized scope
  ↓
Assign: capability-first 选择 executor/auditor；锁定 single-writer 所有权
  ↓
Build: executor 仅执行已授权动作
  ↓
Verify: 客观证据 + 独立 auditor
  ├─ PASS    → 下一项；全部 PASS 才可收口
  ├─ FAIL    → Build/Accept；对应 counter +1
  └─ BLOCKED → 独立 slice 可继续；依赖链停止并升级
```

## 依赖与合流

只在任务之间有依赖、共享写入或合流时适用，与 L 档无关；单个工作单元不需要。每个任务记录：前置任务及必需产出、服务的验收项、写入所有权、当前执行事实、验收证据与契约引用。

1. 前置任务执行完成不等于交付可用：前置产出通过当前契约的验收、证据可达且版本匹配，才解除依赖。就绪由依赖关系判定，不交给模型猜。
2. 前置结果缺失、超时、未知或被放弃都不满足依赖：冻结受影响后继，无关任务继续。删除任务不等于完成；取消必需产出先重开受影响的 Accept。
3. 依赖成环或引用不存在的任务时先修正分解，相关任务不派发。
4. 并发容量只限制同时运行数，不限制总任务数；共享写入或无法证明所有权独立时串行；没有已确认的并发能力时一次一个任务。
5. 上游产物或契约改变后，原验收只证明旧版本，受影响后继重新核验。
6. 合流时核对每个必需输入与集成版本；子任务各自 PASS 不代替组合产物的验收。分别报告执行完成、验收通过和用户预期效果。

## 独立性

1. executor 不能审自己的 L3 产出；
2. auditor 使用 fresh context，且对被审对象只读；
3. 高风险判定叠不同 modelRole/provider/模型视角，或由更强实态证据补偿；
4. 实际 agent 名来自本次 runtime roster，写入 GOAL 与梁3；
5. runtime 不提供满足能力的 agent 时，不猜名字，BLOCKED。

## Timeout 与重派

沉默、心跳中断或 timeout 只表示未收到完成证据，不表示 writer 已停止。

重派同一所有权前，必须取得至少一种可定位 stop proof：

- executor 明确确认停止并释放所有权；
- 受监督进程已经退出；
- 锁/lease/worktree ownership 已释放；
- runtime 给出等价的终止证明。

缺少 stop proof 时冻结该所有权并升级人工，不自动重派。无依赖且所有权不重叠的 slice 可以继续。

## Full-auto 权限

Full-auto 不隐含 commit、push、publish、deploy、对外发送、安装、升级、运行时配置/repoint、登录、认证、凭据、权限或删除授权。命中这些动作时：

1. 保留当前证据与状态；
2. 停止相关依赖链；
3. 请求该具体动作的授权；
4. 通过 `scanDanger` 或已启用的 hook 留下门控证据。

已有普通任务授权不能自动扩大为上述动作。

## 失败路由

| 情况 | 动作 |
|---|---|
| regen 达 3 | 不再开新一轮；进行中的一轮完成 Verify 后仍失败或被作废 → BLOCKED，停止自动循环，输出证据，升级人工 |
| slice 达 2 | BLOCKED；停止继续切分；升级人工 |
| auditor FAIL | 回 Build；regen +1 |
| Acceptance 本身错误 | 回 Accept；slice +1 |
| 无人值守整轮不可锚率 >40% | 本轮作废；regen +1（即使产物没改） |
| 契约或上游产物改变 | 受影响后继的旧验收失效，重新核验；无关任务继续 |
| 证据不足/崩溃/部分产出 | 相关项 BLOCKED；仅独立工作继续 |
| timeout/沉默 | 相关项 BLOCKED；先取得 stop proof，再决定重派 |
| danger/不可逆/越授权 | 停止并请求具体授权 |

## Runtime 接线

需要可执行集成时，使用当前 OMP runtime 实际提供的 `task`/agent orchestration、消息/等待与 artifact 机制。不要假定 `agent()`、`parallel()`、`irc`、某个 agent 名或配置键在所有版本存在；以当前工具 schema/帮助和 roster 为准。

客观 gate 使用 `scripts/gates.mjs`：

```js
const { verifyArtifact, verifyTest, scanDanger, bumpCounter } =
  await import('./scripts/gates.mjs');
```

计数硬顶保持 regen ≤3、slice ≤2。
