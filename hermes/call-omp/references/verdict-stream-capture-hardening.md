# verdict_v1 判决流采集加固合同

> 适用范围：`call-omp` 受控 OMP 调用运行时。本文描述判决流采集（verdict_v1）
> 的边界、隐私红线与失败即闭策略，供改动 supervisor / classifier / monitor 前
> 逐条对照。**未在真实 OMP 上取得成功结论**——下文「真跑证据」均为受资源治理
> 拒绝的运行样本，只用于说明熔断路径是否按设计触发。

## 1. call-omp 是受约束的通用 OMP 调用运行时

`call-omp` 不是「只做审计」的工具。它是一层**受约束的 OMP 调用运行时**，覆盖三类
用途，共享同一套资源治理与证据纪律：

- **audit（审计）**：让 OMP 对代码/bundle 产出结构化 verdict（severity / evidence /
  required_actions），交回本地裁决。
- **execute（执行）**：在 bundle_only 等受限、当前只读的工具范围内驱动 OMP 执行命令，
  产出可核验的执行证据；实际写入仍须转受控人工路径或 `cc-tmux`。
- **governance / evidence（治理与证据）**：无论审计还是执行，运行时都记录有界的
  取证元数据（字节数、SHA256、计数、状态），作为「是否可信」的唯一依据。

判决流采集只是其中一条**可选**能力，服务于「需要把 OMP 原始 stdout 变成可信规范
证据」的受监督场景，并非所有调用都会启用。

## 2. verdict_v1 的启用边界（默认不开）

`--capture-mode verdict_v1` **只**用于：

- **受监督的 bundle_only Shell** 调用；
- **RPC→Shell 回退**后的同类受监督 Shell 调用。

以下模式**一律不变**，继续走既有 legacy 直采/透传，不引入 classifier 分帧：

- 普通 Shell、普通 RPC、ACP；
- dry-run；
- 未显式 `--capture-mode verdict_v1` 的一切 legacy 路径。

即：capture 模式是窄口径特性，红线是「不得把 verdict_v1 的判决/剥离语义悄悄扩散到
未声明它的模式」。

## 3. 双流架构与容量上限

capture 模式把 OMP 的单条 stdout 物理流，按行分帧后经**纯函数 classifier**
（`scripts/omp_stream_classifier.py`）分裂为两条落盘流：

| 流 | 内容 | 默认上限 | 触顶行为 |
| --- | --- | --- | --- |
| ingress | 从 stdout 管道**物理读入**的总字节 | 128 MiB | 超限 → `resource_rejected:ingress_cap_exceeded`（熔断） |
| verdict（canonical raw） | 仅 `preserve` 记录重建出的**规范 JSONL** | 1 MiB | 超限 → `resource_rejected:verdict_cap_exceeded`（熔断） |
| diagnostic | 每条记录的固定 9 键有界元数据 | 512 KiB | 触顶只**截断**并置 `diagnostic_truncated=true`，继续 drain，不熔断 |

关键语义：**capture 模式下的 canonical raw 就是「被 sanitize 过的 verdict JSONL」**，
不是 OMP 原始 stdout。原始 thinking / tool 入参出参 / provider / model / usage /
prompt 文本都不落盘，只有严格白名单的 verdict envelope 被重建后写入。

## 4. classifier 判决合同与隐私红线

分类器是**可 import 的纯函数**：不读环境变量/文件系统/进程信息，不写文件，永不因
畸形输入抛异常。对单条 newline-terminated JSONL 记录输出三态：

- **preserve**——命中严格白名单（`message_end` 的 assistant text 块、
  `message_update.text_delta`、顶层 `text_delta`、`turn_end` 的 stopReason），
  重建**最小规范 JSON**，只保留结构必要字段。
- **deny**——已知的非 verdict 协议 envelope（session / 心跳 / 思考流 / 工具流，
  以及 §6 新增的 non-assistant `message_end`）。不产出 verdict。
- **unknown**——其余一切（含畸形/未识别形状）。按**结构键**判定
  `terminal_capable`（只看对象键名，绝不检查标量字符串内容）。

隐私红线（逐条硬约束）：

- `diagnostic_record` 只含固定 9 键：`seq / type / subtype / input_bytes /
  input_sha256 / decision / reason / terminal_capable / structure_code`。绝不携带
  原文 / 文本增量 / prompt / 工具入参出参 / provider / model / usage / 任意源字段。
- `type` / `subtype` / `structure_code` 只能取**模块级固定字面量白名单**，绝不从
  源字段（role / type / assistantMessageEvent.type）拷贝。攻击者自造的 canary 串
  一律归 `null`。
- **失败即闭**：以下情形一律不产出 verdict、且在最终态强制 `resource_rejected`：
  - **EOF / 无末尾换行**：末条记录缺 `\n` 即按 framing-invalid 拒绝
    （`incomplete_final_record`），不做 partial JSON parse；
  - **terminal-capable unknown**：即便后续有合法 end 事件，最终仍
    `classification_untrusted`；
  - **sidecar / digest / migration 不一致**：capture_mode 声明与实际状态、
    落盘 SHA256 与 state 记录、跨态迁移不匹配，任一失配即拒绝，绝不静默降级。

## 5. 真跑证据（均为被拒样本，非成功）

两次真实 P2B 运行用于验证熔断路径，**都没有产出被接受的 verdict**：

- **第一次重试**：ingress 达到约 **85.7 MiB** 才终止；最终因 terminal-capable
  unknown 判为 `resource_rejected:classification_untrusted`——大流量 thinking 之后
  仍出现无法归入白名单的终态形状记录，按设计拒绝。
- **第二次重试**：因 `incomplete_final_record` 被拒——末条记录缺末尾换行，framing
  校验失败，直接闭合。
- `--thinking off` **不能可靠抑制** thinking 流：即便请求关闭，OMP 仍可能输出大量
  `message_update` 思考增量，这正是 ingress 容易逼近上限、且必须靠 classifier
  deny + 上限熔断兜底的原因。

结论：capture 路径目前只验证了「拒绝路径按设计触发」，未验证「成功接受一份真
verdict」。任何文档/汇报都不得声称真 OMP 调用成功。

## 6. 当前已知协议漂移

- **non-assistant `message_end` 现判 deny**：`type=message_end` 且 `message` 为对象、
  但 `role` 不严格等于 `"assistant"` 时，在 preserve 契约下不可能承载 assistant 审计
  verdict，属「已知非 verdict envelope」，判 `deny`（`structure_code =
  message_end.non_assistant`）。deny 仍保留结构扫描得到的 `terminal_capable` 布尔，
  但因判决非 unknown，**绝不参与 terminal-capable-unknown 计数**、不触发
  `classification_untrusted`。两次真跑分别观察到该形状出现 8 次、10 次。
- **`message` 缺失 / 为 null / 非对象** 仍保持 `unknown`（fail-closed），不随之收窄
  为 deny——形状信息不足以判定「已知非 verdict」。
- **未识别的 `message_update` kind 刻意保持 fail-closed**：`assistantMessageEvent`
  是对象但 `type` 不属任一已识别 kind 时仍记 `unknown`
  （`structure_code = message_update.ame_unknown_kind`），等待更多固定形状遥测再决定，
  不提前放宽。
- **绝不**仅凭源字符串把某记录扩张为 deny 或 preserve。收窄/放宽判决必须基于固定
  结构形状证据，且经测试固化。

## 7. 操作规程

- **每次重试用新 task-id**：不复用旧 task-id，避免状态串味。
- **资源拒绝后不做 raw 恢复、不接受部分结果**：一旦 `resource_rejected`，落盘的
  verdict/diagnostic 只能作为「为何被拒」的取证，不得当作有效判决使用。
- **finish 走 reject / human-review**：被拒运行以拒绝或转人工复核收口，不静默通过。
- **只查有界元数据**：排障时读 state 的字节数 / SHA256 / 计数 / status / reason，
  不去翻原始流内容（capture 模式下本就没有原始流落盘）。
- **真正的 OMP 调用工作流对所有模式一致**：`start → send → monitor → finish`。
  capture 只是 send/monitor 阶段的一个可选采集开关，不改变整体四步骨架。
