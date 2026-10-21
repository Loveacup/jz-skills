# Jev shadow 执行与收据

Jev 是已明确许可后的、只读 `pick_context_file` shadow，不是计划器或控制器。正常 STDD、协调者选择、依赖判断、权限、AC、风险、计数与 PASS 不依赖 Jev。Jev 建议永不替换已提交的协调者选择。默认禁用；不得仅因安装脚本存在而调用。唯一的常设例外是下文「可行性试验」节：Alex 已授权，只在合格的已许可项目检查点上调用。

## 触发与正式样本条件

只有同时满足以下条件才能登记一次正式样本：

- 协调者已确认当前任务允许发送该输入给所选 provider，输入不是敏感数据；否则不调用、不读 Keychain、不做网络请求。
- 明确声明 `provider`/原生协议/模型，候选 ID 与描述已经授权并冻结，候选集是闭合可选集且包含 `no-match`。
- 独立标注/基线在看 Jev 结果前完成冻结。标注回执只登记 `receiptId`、来源及时点；真实标签值在独立评估记录中，不得放入此 CLI 输入、CLI 输出、协调者上下文或 Jev request state。
- 正式取样点须在采样前固定为同一项目/任务首次候选完整且具备数据许可的检查点，不能在观察 Jev 结果后挑点或择样；每个 task 最多一个 `prepare`，不能通过新 `sampleId` 或后续 checkpoint 重新入样。动态计划仍在每个工作单元校准，不因正式票已消费而停止。
- 协调者首次看到候选即由 `prepare` 返回 `candidate_delivery` 事件和冻结候选；协调者据此独立选择，`commit-choice` 由工具记下提交时间。二者同属一条输入摘要链。缺事件、摘要不匹配或基线缺失的样本不参与收益分析。

没有可核验基线时不创建样本。本工具不替协调者伪造选择时长，不允许事后填时间来回算收益。由 CLI 产生的本地时间戳是待复核仪器记录，不单独证明人工未改记录。

完整采集顺序是：先形成含 `no-match` 的授权候选和输入快照 → 独立评审者在未见协调者/Jev 输出时标注，将真实标签保存在受限评估侧、只把回执引用交给仪器（真值不进入协调者或 Jev 推断输入）→ `prepare` 实际交付冻结候选并启动计时 → 协调者独立选择并由 `commit-choice` 实际接收、冻结选择 → 再执行 shadow 并记录脱敏结果。未完成独立标注或输入冻结时，先完成这些前置条件，不能倒序调用后补。完整采样规则见现有托管 pilot 预注册；本段只说明执行接口，不授权实际任务内容外发。

## 命令接口

运行时由协调者按需调用下列三个命令；JSON 从 stdin 提供，不得将 state、选择、凭据或权限放进 argv。收据固定写入 `~/.stdd/jev/receipts.jsonl`，避免由调用者换收据路径绕过 task 样本上限。不要把密钥写入 stdin、命令行或配置文件。`shadow` 失败会打印脱敏 JSON `{status:"failed", sample_id, error, receipt_written, ...}` 并以 0 退出，表示 coordinator 可以继续原流程，不表示 Jev 成功；准备/选择操作、用法和未能记录的命令错误以非零退出。shadow 失败不重试、不换 provider。

`prepare` 的输入形状：

```json
{
  "sampleId": "optional-stable-sample-id",
  "samplePurpose": "synthetic_smoke",
  "projectId": "project-id",
  "taskId": "task-id",
  "checkpointId": "first-eligible-checkpoint",
  "coordinatorId": "coordinator-id",
  "contractRef": "acceptance-revision",
  "provider": "hosted",
  "protocol": "typesafe-systemone-v1",
  "model": "jev-latest",
  "language": "en",
  "templateVersion": "pick-context-v1",
  "candidateStrategyVersion": "path-summary-v1",
  "permission": {"authorized": true, "sensitive": false},
  "baseline": {"receiptId": "frozen-baseline-id", "frozenAt": "ISO-8601"},
  "labelReceipt": {"receiptId": "independent-label-receipt", "frozenAt": "ISO-8601", "source": "independent-source"},
  "question": "Which context file best fits the task?",
  "state": {"authorized_task_summary": "synthetic or explicitly permitted state"},
  "candidates": [
    {"id": "context-a", "description": "Short authorized description"},
    {"id": "context-b", "description": "Short authorized description"},
    {"id": "no-match", "description": "None fits or the evidence is insufficient"}
  ]
}
```

`provider` 为 `self-hosted` 时 `protocol` 必须为 `jev27-bare-v1`、`model` 必须为 `autotrust/JEV-27B-VL`；hosted 固定为 `typesafe-systemone-v1` / `jev-latest`。每组必须含至少 2 个选项并显式包含 `no-match`；`prepare` 不会自动补候选，避免在独立基线/标签冻结后改变已冻结候选集。Hosted 最多 255 项，Self-hosted 最多 256 项，id 唯一；state 限 1 MB。基线与标注冻结时间必须是完整、有效且不晚于 prepare 送达事件的 ISO-8601 timestamp（含 `Z` 或时区偏移）。`prepare` stdout 返回给协调者的 `candidate_delivery`：`status, sample_id, project_id, task_id, checkpoint_id, coordinator_id, sample_purpose, started_at, input_digest, candidate_set_digest, candidate_ids, question, state, candidates`。请把该输出作为协调者实际收到候选的证据，不要把真实标注回执正文拼进去。命令必须从当前实际加载的 skill 根目录按需执行，不应硬编码某个 source/pool 路径。

`samplePurpose` 必填为 `synthetic_smoke` 或 `formal_pilot`；source/pool/fixture 请求必须标 `synthetic_smoke`，不得混入正式 pilot。正式 pilot 仍每项目每任务一次；工具也对同一 project/task 的所有 purpose 执行单条上限，避免跨 checkpoint 换 sample id 重复提交。

从 Node 执行 CLI 时通过子进程 stdin 传递 JSON（state/permission/选择均不得进入 argv）；真实协调者先调用 `prepare` 并展示实际 stdout，再独立决定 choice：

```js
import { spawnSync } from 'node:child_process';

function runJev(command, payload) {
  const result = spawnSync('node', ['scripts/jev.mjs', command], {
    input: JSON.stringify(payload),
    encoding: 'utf8',
  });
  if (result.error || result.status !== 0) throw new Error('STDD Jev command failed');
  return JSON.parse(result.stdout);
}

const delivered = runJev('prepare', preparedInput);
// Coordinator independently chooses an ID from delivered.candidate_ids:
const frozen = runJev('commit-choice', {
  sampleId: delivered.sample_id,
  choiceId: coordinatorChoiceId,
});
const shadowResult = runJev('shadow', {
  sampleId: delivered.sample_id,
  permission: { authorized: true, sensitive: false },
  currentContext: {
    contractRef: activeCurrentContractRef,
    inputDigest: confirmedCurrentInputDigest,
  },
});
```

`currentContext` 必须由协调者按 shadow 时的活动契约与当前 state/candidate 快照确认；只有确认没有新事实、合同或候选变化时，当前摘要才会与 `delivered.input_digest` 相同。不可无条件照抄旧收据摘要。`contractRef` 或 `inputDigest` 不匹配时返回 `stale_context`，在读取 Keychain、发请求或消费 shadow claim 之前退出；任务继续用正常 STDD 路由，旧候选不继续送 Jev。

`prepare` 具体命令为 `node scripts/jev.mjs prepare`。准备输出必须由实际 stdout 返回，不能由调用者自填或从事后启动 shadow 推算。


提交必须来自工具实际返回的候选 ID。收据含 `committed_at` 和基于 `started_at` 的真实耗时；重复提交或越界选择拒绝，不能覆盖首条事实。

提交完成后执行 shadow：


Self-hosted 必须由协调者显式设置 `STDD_JEV_SELF_HOSTED_ENDPOINT=http://127.0.0.1:<port>/v1/decide` 作为可信进程环境；CLI 不接受可重定向 endpoint 命令行参数或 JSON stdin 字段。端点须为 `http://localhost|127.0.0.1|[::1]:<port>/v1/decide`，不带用户信息、query、fragment；不读取或转发 hosted key。

## 原生 provider 协议

**Hosted** 固定调用 [TypeSafe API `POST /v1/systemone`](https://docs.typesafe.ai/api.md)，参考其 [Choice schema](https://docs.typesafe.ai/primitives/choice.md) 和 [Confidence 语义](https://docs.typesafe.ai/confidence.md)，`redirect: error`；请求体为 `{state, model:"jev-latest", questions:{pick_context_file:{type:"choice", instructions, criteria:{candidateId:description}}}}`，Authorization bearer key 只通过请求头传递。仅在权限、数据类别、基线、choice commitment、输入摘要和固定 hosted 配置均校验通过后，才从 macOS Keychain 原位读取 `security find-generic-password -a alexcai -s typesafe-jev-api-key -w`。接口/凭据错误都转换为固定错误码，不输出 key、HTTP body 或异常反射。`JEV_TEST_API_KEY` 只作为导出的 in-process 测试函数 seam，不能作为 CLI 参数或文档化部署配置。Choice 的 `choice` 必须在候选中，概率必须完整对齐所有候选、为有限 [0,1] 且和为 1（容差 0.01），confidence 必须为有限 [0,1]；真实返回 model 记录为 calibration identity 的实测 model，不能由 alias 代替。

Choice `confidence` 表示选项概率分布的集中程度，不是所选项的概率，更不是该选项客观正确的概率。官方定义为 `(max(probabilities) - 1/n) / (1 - 1/n)`；校准判据使用所选项的原始 probability，并仍需独立真值。高 confidence 不产生质量通过、计划控制权或权限。

**Self-hosted** 固定发 AutoTrust [model card revision `f34b598d4ef4bcefd337bee8d8e7ddd3b7733ccc`](https://huggingface.co/autotrust/JEV-27B-VL/blob/f34b598d4ef4bcefd337bee8d8e7ddd3b7733ccc/README.md) 定义的 `POST /v1/decide`，协议体 `{kind:"choice", state:{context, candidates:[{id, description}]}, question, options:[candidate IDs]}`。`options` 顺序与冻结候选 ID 顺序完全相同，state 同时携带授权状态与每个候选的 ID/描述。仅支持 loopback HTTP，不要求/读取 hosted key。接受原生返回仅当 `protocol:"jev27-bare-v1"`、`model:"autotrust/JEV-27B-VL"`、options 顺序与候选完全相同、choice index/name 一致、每个候选都有位置对齐的有限 [0,1] 概率且和为 1（容差 0.01）。原生协议未定义 confidence，收据记 `confidence:null`，不能从概率推造 confidence；CLI 的 loopback fixture 仅验证协议实现，不是部署该 GPU 模型的实证。

两条路线是明确分支，不做 provider framework、自动 fallback 或重试。所有请求有 1–30 秒上限（默认 10 秒）；超时后 AbortSignal 取消请求，样本已消费且记失败，不自动再试。模型身份未知、响应畸形、概率缺失/越界、候选集合变化、输入陈旧、HTTP 错误都是 shadow 失败，不成为有效选择。

## 收据、隔离和故障

JSONL 收据是 append-only，进程间独占锁，文件权限 0600、目录权限 0700。每条事件保存 `sample_id`、项目/任务/checkpoint、coordinator、contract ref、provider/protocol/configured 与实际 model、语言、模板和候选策略版本、候选 ID 集合摘要、输入摘要、label/baseline receipt id 与冻结时点、协调者选择、开始/提交时点/真实耗时、shadow choice、原始概率/协议所支持的 confidence、请求开始结束/延迟、usage、状态或固定错误码。失败在 shadow 请求发出前记录 `shadow-start`，按失败也消费唯一资格。

原始 state/候选描述保存在独立权限收紧的 `.inputs/<sample_id>.json` 文件，而非 JSONL 收据；输入文件哈希与 commit 绑定，调用前再次校验。receipt 不包含原始状态、标注真值、API key、原始 server error/body。若日志/快照写入失败，命令明确报失败，不报告有效 shadow。权限拒绝不执行 keychain、fetch；shadow 网络失败只记固定状态，coordinator 正常流程继续，独立的非 Jev 工作不阻塞。

不要把 Jev 结果写入协调者后续推理输入后，再声称原始选择盲标。`candidate_delivery` 和 `commit-choice` 必须先于 `shadow-start`；shadow 输出仅给独立评估/仪器关联，不改写已冻结协调者选择。工具不承担人工真值、候选授权或记录未被篡改的真实性证明。

## 可行性试验（托管，2026-10-07 启用）

完整方案以 Obsidian `01-Staging/Jev托管路线Pilot预注册_20261004.md` 第七节为准；下面是执行要点，冲突时以预注册为准。

1. **检查点**：STDD 任务中协调者需要从多个检索结果里决定先读哪个文件的时刻。每个不同的 (project, task, checkpoint) 首次遇到时，向 `~/.stdd/jev/feasibility-screening.jsonl`（0600）追加一行：`at, project_id, task_id, checkpoint_id, sampled, exclusion_reason, sample_id`。
2. **排除原因**（取第一个命中）：`project_not_permitted` → `sensitive` → `candidates_lt_2` → `task_already_sampled` → `budget_exhausted` → `other:<短码>`。只有公开 GitHub 仓库默认许可；其他项目需 Alex 逐个放行；凭据、私密内容、家庭/未成年人、知识库 `50-Self` 与关系类内容永不发送。被排除时不读 key、不请求。
3. **冻结**：`samplePurpose: formal_pilot`、`templateVersion: pick-context-feas-v1`、`candidateStrategyVersion: path-summary-feas-v1`，hosted 固定配置。候选为检索结果前 2–8 个路径，ID `c001`…`c008` 加 `no-match`；description 只写路径，外加确认安全的自然语言 Markdown 标题，绝不取文件首行或正文。state 为不超过 500 字符的任务摘要，不含代码、凭据或个人信息。问句按任务语言使用预注册 7.3 的原文。
4. **顺序**：写受限基线快照 `~/.stdd/jev/baselines/<baselineId>.json`（含 ID↔路径映射）→ 起 fresh 只读标注 agent，只看 state 与候选，把正确集合与必须 split 条件写入 `~/.stdd/jev/labels/<labelId>.json`（0600，含标注者名与运行时长），真值不回传协调者 → `prepare`（`labelReceipt.source` = `labeler:<sampleId>`）→ 协调者独立选择 → `commit-choice` → `shadow`。失败不重试，协调者照常继续。
5. **上限**：有效样本 60 条，或实际请求（`request_started_at` 非空）60 次，或 2027-01-04，或 Alex 叫停，先到即停。之后台账只记 `budget_exhausted`。连续 5 次服务失败或出现任何 key/隐私事件，立即暂停并报告 Alex。不得因 Jev 与协调者是否一致、或标注结果而暂停、延长或挑选样本。

## Calibration 与结果解释（J1–J7）

- J1 未启用/未授权（包括可行性试验中被排除的检查点）：零 key read、零请求；默认 STDD 不受影响。
- J2 真实验收要求从已加载 STDD 入口经过候选冻结、prepare、独立 coordinator commit、真实脚本请求和同一 sample id 收据；直接调用成功或 fixture 通过不等于 hosted 服务实证。Jev 不覆盖 commit 选择。
- J3 基线/标签收据及送达/提交事件在 shadow 前冻结；没基线、缺事件或事后补填的数据不评估收益；重复提交不可覆写。
- J4 需验证无授权/敏感/未知数据许可时不读 key/不发请求、HTTP 错误与超时后主流程继续、任务重复不再采样；shadow 时 current contractRef 与当前 inputDigest 必须再次匹配，不匹配在 key/network/claim consumption 前 BLOCKED；越界/畸形/未知 identity/过期输入不转成功；无自动 fallback/retry。
- J5 self-hosted 原生请求/错误及概率顺序映射可用本地 HTTP fixture 验证；无真实部署 GPU 服务证据时仍 BLOCKED。
- J6 key 不出现在 stdout/stderr/收据/CLI argv，不发送到 self-hosted 或其他 URL。
- J7 正式 pilot 每任务最多一条，按原预注册的项目聚类与一次最终分析；校准身份包含 provider/protocol、实际 model、language、完整问题模板版本、候选生成/编码策略版本。策略或完整问题语义变化须停止沿用旧阈值、重新开发并冻结，新数据不得混入旧留出分析；正常名单变化本身不等于策略变化。缺少有效校准基线时只报告未校准的原始信号，不声称 sharp、准确度收益或节省时间。API 连通不等于 pilot 质量或收益通过；即便正式 pilot 达标，也只能向 Alex 提议，启用实际路由仍需其单独明确授权，shadow 本身不允许启用或覆盖已提交选择。
