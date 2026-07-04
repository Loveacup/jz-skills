# ACP Audit-Driven Design Workflow

> 用 OMP 的 ACP 通道做架构审计，而非直接跳进实现。
> 一次成功的实战：`--watch 模式` 方案被 OMP 审出 blocker → 大改设计 → 落地。

## 流程

```
Hermes 设计方案（口头描述/文字）
  ↓
call-omp: omp-start --mode audit → omp-send --channel acp
  ↓
OMP ACP (delegate_task) 审计方案
  ↓ verdict: blocker/concern/nit/pass
Hermes 阅读审计报告，决策：
  ├─ blocker → 修改方案，不回退直接实现
  ├─ concern → 评估取舍
  ├─ nit → 接受并记录
  └─ pass → 直接实现
  ↓
按 accept findings 后的方案实现
```

## 关键决策点

- **blocker ≠ 放弃**：OMP 给 blocker 是告诉你"这样有问题"，不是"别做了"。
  本次 `--watch 模式` 被标 blocker（ACP --await 不可行），修正后方案从"新建 80 行脚本"改为"扩展 omp-monitor +20 行"——方案更优。
- **ACP 审计比找 bugs 更划算**：一次审计发现 6 个维度的问题，避免按错方案投入数小时实现再重写。

## 本次实例

| 阶段 | 动作 |
|------|------|
| Hermes 提出 | `--watch 模式` 独立进程 + ACP --await + 📡 监控 |
| OMP 审计 | ACP delegate → verdict: blocker（ACP --await 架构不可行）|
| 证据 | `omp-monitor.sh:57-86` 已实现轮询逻辑 · `omp-send.sh:245-255` ACP= pending_acp 非 running |
| 修正 | 扩展 `omp-monitor.sh` + --watch（+88行），ACP 走回调 |
| 结果 | v0.4.0 落地，58/58 测试 + smoke test 通过 |

## 审计独立级别 · `bundle_only` vs `independent_readonly`

委派包 `auditor.independence_level` 决定审计者如何取证：

- `independent_readonly`（默认）：OMP 现场只读访问工作区（read/grep/glob/lsp/web_search）。
- `bundle_only`：OMP **不**现场访问，仅凭离线证据包核查。证据包由只读生成器产出（不改动被审仓库）：

```bash
scripts/omp-bundle-code-audit.sh --repo <被审仓库> --out <证据包目录> \
  --scope src/auth --base HEAD
# 产出 manifest.json / summary.md / file-list.txt / git-status.txt / diff.patch（非 git 目录优雅退化）
# 委派包填 evidence_bundle.path = <证据包目录>/manifest.json（gate-verify 强校验：bundle_only 必带此字段）
# best-effort 剔除 .env / *secret* / *token* / *credential* / *.pem / *.key 等敏感路径
```

## OMP 完整 CLI / execute 通道

OMP 是完整 CLI agent，不止审计。委派包 `mode=execute` 走 `execute-prompt-template.md`（通用执行者），
可跑 build/test/lint/任意 shell 任务。execute 模式豁免 criterion 与 evidence 红线（通用执行无需可裁决验收），
但状态机不变——仍走 start → send → monitor → finish 四步，不新增状态。

## 审计独立级别硬约束（`independent_readonly`）

默认 `independent_readonly` 的独立性不是标签，是三条硬约束（模板 `audit-prompt-template.md` 强制注入）：

1. **严格只读**——审计者只用 read/grep/glob/lsp/web_search，绝不写文件/改代码/跑破坏性命令。
2. **不采信委派方叙事**——委派包里的「已修复/已通过」只是待核对声明，审计者亲自复核现场重新取证。
3. **证据现场可复现**——evidence 的 `ref` 指向工作区当前真实状态；守 scope 即守独立，越界取证作废。

因此委派方只给可裁决 `criterion`，不预写「结论」——让 OMP 独立得出 severity，避免锚定偏差。

## 解析/校验失败诊断 · `.monitor.compact_debug`（Package C）

非 execute 模式下若 monitor 判 `rejected`（缺 turn_end / gate-verify 结构不合格 / 空 evidence /
severity 非法 / 缺 summary / omp 退出码非 0），会把**紧凑诊断**落到 `.monitor.compact_debug`，
**绝不把上百 KB raw 回吐进上下文**。字段（尾部一律 capped）：

| 字段 | 含义 |
|------|------|
| `raw_output` / `raw_err` | raw JSONL 与 stderr 落盘路径（不内联内容，需要时自行按需读） |
| `raw_bytes` / `raw_lines` | raw 大小 / 行数 |
| `raw_err_tail` | stderr 尾部（≤800B，存在时才有） |
| `stop_reason` | 末轮 stopReason |
| `gate_reason` | gate-verify 拒绝原因（结构/空证据） |
| `final_text_bytes` | assistant 最终文本字节数（0 = 空最终文本） |
| `candidate_count` | 最终文本里 top-level JSON 候选对象数（0 = 无 verdict JSON） |
| `last_candidate_parseable` | 最后一个候选是否合法 JSON 对象 |
| `last_candidate_keys` | 最后一个候选的键列表（诊断缺字段/拼错键） |
| `failure_stage` | 诊断阶段。第一层阶段：`turn_end`/`gate_verify`/`evidence_empty`/`no_verdict_json`/`severity`/`summary`/`exit_code`；紧凑诊断会进一步精化：`no_final_text`=assistant 最终文本为空，`no_candidate`=最终文本无 JSON 候选对象，`invalid_inner`=gate-verify 拒收且内层 JSON 不可解析。 |
| `final_text_tail` | 最终文本尾部（≤800B，看模型到底吐了什么） |

`--json` 输出附带布尔 `compact_debug`（true=已落诊断）作为信号，整体仍是合法 JSON。
execute 模式与成功 `reported` 路径不落 compact_debug（`compact_debug=null`）。

> 手工真实 smoke（烧 token，非套件）：`references/omp-shell-smoke-test.md`。跑真 OMP 触发一次解析失败后，
> `jq '.monitor.compact_debug' <state>` 即可拿到诊断而无需 relay 整个 raw。

## 触发条件

- 设计方案涉及通道/协议/安全/竞态等复杂交互
- 想在写代码前让独立审计者过一遍架构
- 与 cc-tmux 配合：cc-tmux 做实现，OMP 做审计
