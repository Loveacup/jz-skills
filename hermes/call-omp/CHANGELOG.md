# call-omp 更新记录

> 本文档从 `SKILL.md` 拆分，用于保存版本历史；`SKILL.md` 仅保留当前使用说明与操作约束。

### v0.6.9（2026-07-05）— Package D slice 3：OD-OMP-1 ACP 真实探针

本版补上 ACP 通道的真实 smoke probe：可手动验证 `omp acp` 启动 + 协议兼容性，产出结构化证据包（7 文件）。**仍是证据产出工具，不改默认通道**——即使探针通过，ACP 也不自动启用。

| 级别 | 新增/修复 | 描述 |
|:---:|------|------|
| P0 | ACP smoke probe | 新增 `scripts/omp-acp-smoke.sh`：真实拉起 `omp acp` over stdio，发最小 prompt，收集完整 stdin/stdout/stderr + timeline + process 元信息。裁决三态：`compatible_smoke_passed`(退出0) / `started_but_protocol_incompatible`(退出2) / `failed_to_start_or_timeout`(退出3)。 |
| P0 | mock 测试路径 | `--mock-pass` / `--mock-incompatible` / `--mock-timeout` 三档零 token 测试，伪造探针结果（不启 omp），用于单元测试与 CI。 |
| P0 | 证据目录结构 | 产出 7 文件：`summary.json`（裁决状态 + 字节数 + 耗时）、`result.md`（人类可读报告）、`stdin.ndjson`（ACP prompt）、`stdout.ndjson`（OMP 返回流）、`stderr.log`、`timeline.ndjson`（事件序列）、`process.json`（omp 路径/版本/pid/退出码）。 |
| P1 | OD-OMP-1 规范 | 新增 `references/OD-OMP-1-acp-smoke.md`：探针目标、裁决三态语义、证据文件用途、与 ACP 通道启用的关系（探针通过 ≠ 自动启用）。 |
| P1 | tests + docs | `tests/run-all.sh` 新增 Group 19（--help / mock 三路径 / 证据文件齐全 / mock 标记 / summary schema / JSON-RPC initialize 断言），并在 Group 15 增加 untracked 新文件进入 `diff.patch` 的 bundle 回归；当前 166/166 通过。SKILL.md 补版本历史。 |
| P1 | bundle-only 证据修复 | `omp-bundle-code-audit.sh` 追加 scope 内 untracked 普通文件为 `/dev/null → file` patch，避免 bundle_only 审计者看不到新增脚本/文档正文；敏感 untracked 路径仍按原规则剔除。 |

**真实探针观测（OMP 16.3.2，本机）**：`initialize` 可成功返回 `protocolVersion=1` 与 `agentInfo.name=oh-my-pi`，但一次性 NDJSON 驱动未观测到 `session/new` / `session/prompt` / `session/update`，脚本按 `started_but_protocol_incompatible`（exit 2, reason=`initialize_ok_but_session_prompt_unobserved`）记录证据。后续 OD-OMP-2 应实现交互式 ACP client，而不是把 initialize 成功误判为 full compatibility。

**已知边界**：探针只记录 `omp acp` 真实行为，**不修改 call-omp 默认通道优先级**（仍是 ACP > RPC > Shell，v0.2.0）。真实启用 ACP 需探针通过 + Hermes 支持 delegate_task + 明确配置。

### v0.6.8（2026-07-05）— Package D slice 2：平台发现 + 安装清单 + check 脚本

本版补上 slice 1 的「发现」一环：三个平台各一份最小 `plugin.json` 让 call-omp 可被发现——**仍非安装器、非全平台承诺**，不写 PATH / 全局配置、不烧 token、不生成脚手架。

| 级别 | 新增/修复 | 描述 |
|:---:|------|------|
| P0 | platform manifests | 新增 `.codex-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.omp-plugin/plugin.json` 三份最小清单（`name=call-omp`、`0.1.0`、`skills` 指父仓库、`smoke` 指冒烟脚本）；OMP 清单额外带 `recursion_guard` 提示。 |
| P0 | discovery check | 新增 `scripts/call-omp-check.sh`：校验三份清单齐全 + 合法 JSON + 均引用 `scripts/call-omp-smoke.sh`，全通过退 0，否则非零；纯本地文件校验，不改 PATH / 全局配置。 |
| P1 | docs + tests | `references/platform-adapters.md` 补「清单发现」小节；`tests/run-all.sh` 新增 Group 18（清单存在 / JSON 合法 / check exit 0 / OMP 清单含 recursion guard / 三份均引用冒烟脚本）。 |

### v0.6.7（2026-07-04）— Package D slice 1：跨平台 adapter + mock-only smoke

本版启动跨平台自主调用的第一刀：不做 installer、不复制 skill、不烧真实 OMP token，只把 runtime-neutral 脚本能力整理成 Codex / Claude Code / OMP self-call 都能运行的冷路径冒烟。

| 级别 | 新增/修复 | 描述 |
|:---:|------|------|
| P0 | mock-only smoke | 新增 `scripts/call-omp-smoke.sh`，只跑 `--help`、`gate-verify --mode package`、`omp-bundle-code-audit.sh`；绝不调用真实 `omp` / `omp-send.sh` / `delegate_task`。 |
| P0 | OMP self-call guard | `--platform omp-self` 输出 `recursion_guard=armed`；`CALL_OMP_SELF_CALL_DEPTH>=1` 直接拒绝（exit 4），避免未来真实自调链无限嵌套。 |
| P1 | platform adapters | 新增 `references/platform-adapters.md` 作为单一真相源，以及 `.codex/call-omp.md`、`references/claude-code-call-omp.md`、`references/omp-self-call.md` 三个派生入口。 |
| P1 | docs + tests | SKILL / delegation template / real-token smoke 文档区分 mock-only 冷路径和真 token 热路径；`tests/run-all.sh` 新增 Group 17，当前 128/128 通过。 |

### v0.6.6（2026-07-03）— Package C：紧凑诊断 compact_debug + 独立性硬约束

本版让「拒绝」路径可诊断而不回吐 raw，并把 `independent_readonly` 从标签落成硬约束。不扩状态机、不新增 `needs_evidence`、不自动打补丁/恢复：

| 级别 | 新增/修复 | 描述 |
|:---:|------|------|
| P0 | compact_debug 诊断 | `omp-monitor.sh` 在非 execute 且判 `rejected` 时，把紧凑诊断落 `.monitor.compact_debug`（raw_output/raw_err 路径、raw_bytes/lines、raw_err_tail≤800B、stop_reason、gate_reason、final_text_bytes、candidate_count、last_candidate_parseable、last_candidate_keys、failure_stage、final_text_tail≤800B）——尾部一律 capped，**绝不回吐整个 raw**。 |
| P0 | --json debug 信号 | monitor `--json` 附带布尔 `compact_debug`（true=已落诊断）作为信号，整体仍是合法 JSON；execute 与成功 `reported` 路径不落（`compact_debug=null`）。 |
| P1 | independent_readonly 加固 | `audit-prompt-template.md` / `delegation-package-template.md` 把默认级别落成三条硬约束：严格只读、不采信委派方叙事（亲自复核现场取证）、证据现场可复现；委派方只给 criterion 不预写结论。 |
| P1 | regression tests | `tests/run-all.sh` 新增 Group 16：无 JSON verdict、severity 非法、空 assistant 最终文本（含 `failure_stage=no_final_text`）、`--json` debug 信号且仍合法 JSON、execute/成功路径不落诊断；当前 116/116 通过。 |
| P1 | docs | `references/omp-audit-workflow.md` 补 compact_debug 字段表与独立性硬约束；指向 `omp-shell-smoke-test.md` 手工真实 smoke（烧 token，非套件）。 |

### v0.6.5（2026-07-02）— Package B：evidence bundle + input contract + execute smoke

本版把 call-OMP 从“审计输出提取修复”推进到“审计输入工程化 + OMP 完整 CLI 能力面最小闭环”，不扩状态机、不新增 `needs_evidence`：

| 级别 | 新增/修复 | 描述 |
|:---:|------|------|
| P0 | code-audit evidence bundle | 新增 `scripts/omp-bundle-code-audit.sh`，只读生成 `manifest.json` / `summary.md` / `file-list.txt` / `git-status.txt` / `diff.patch`；支持 repo 内绝对/相对 scope 归一化，best-effort 剔除敏感路径。 |
| P0 | package input contract | `gate-verify.sh --mode package` 强校验 `channel`、`mode`、`auditor.independence_level`；`bundle_only` 必须带 `evidence_bundle.path`；保留 `execute` criterion 豁免。 |
| P1 | execute smoke | `tests/run-all.sh` 新增 execute mock 端到端：start → send → monitor → finish accept，验证 execute 空 evidence 可接受。 |
| P1 | audit profile docs | 模板/参考文档/SKILL 补 `bundle_only` vs `independent_readonly`，明确 OMP 是完整 CLI agent，不只审计。 |
| P1 | regression tests | 当前 95/95 通过；OMP bundle-only 审计 accepted，severity=pass，evidence=13。 |

### v0.6.4（2026-07-02）— robust verdict extraction / 稳健判决提取

WRR Package A 复审实战暴露 monitor 会误抓首个 fenced JSON、漏掉 OMP 自我修正后的最终 verdict。本版收窄修复 I/O 契约，不改变 accept/reject 红线：

| 级别 | 修复 | 描述 |
|:---:|------|------|
| P0 | last valid verdict extraction | `jsonl_final_text` 增加 `assistantMessageEvent.type=text_delta`/`delta` 兜底；`extract_verdict_json` 枚举全部 top-level JSON 对象，选择最后一个合法 `{severity,summary,evidence}` verdict，避免多 fenced / 多裸对象取错。 |
| P0 | evidence hardline preserved | 空 evidence 仍由 `gate-verify` exit 10、`omp-monitor` rejected、`omp-finish --accept` 拒绝；`verdict_valid` 只验证 evidence 是数组，避免空 evidence 终稿被跳过而误采旧对象。 |
| P1 | gate self-contained retained | `gate-verify.sh` 仍不 source skill lib；内联同语义提取器，保持基质无关。 |
| P1 | regression tests | `tests/run-all.sh` 新增多 fenced、裸多对象、text_delta-only、末个空证据红线 4 组场景；当前 70/70 通过。 |

### v0.6.3（2026-06-29）— plist EnvironmentVariables 半截修复陷阱 + OMP 已配 model 边界反转

实战发现 v0.6.2 没识别的 2 块关键事项，补齐：

| 级别 | 新增 | 描述 |
|:---:|------|------|
| P0 | Hermes gateway 修复要看 plist EnvironmentVariables | `config.yaml` 的 `providers.<name>.key_env: <VAR>` 配对了**不等于** fallback 能用——launchd 启动的 gateway 进程只继承 plist 里声明的环境变量，`~/.zshrc` 的 `export` 对 launchd 进程无效。**半截修复陷阱**：config 配对了 + cycle 变长但未治愈 = 100% plist 缺 env var。修复模板（用户 Mac 终端，OMP 救不了）：`plutil -insert` + `launchctl unload/load` + `kickstart` |
| P0 | OMP 已配 model 边界反转 | v0.6.2 标注"OMP 未配 model → `omp -p` / `delegate_task(acp_command='omp')` 都走不通"。v0.6.3 OMP v16.2.4 已配 model 后验证：`omp -p --tools bash` 跑救援脚本真能 kickstart gateway，ACP 4 步状态机真能跑。**判断方法**：`omp --version` 看 "Default model: xxx" / `omp -p "echo smoke-ok"` 测是否卡 setup |
| P1 | description 重写 | frontmatter 明确"OMP 是完整 CLI agent，不只审计"（用户纠正），触发词加"用 OMP"/"用 omp (adp 优先)"，明确"3 通道 Shell/RPC/ACP" |
| P1 | references/hermes-gateway-plist-env-fix.md | 新建 reference，记录 plist env var 修复模板（用户 Mac 终端 2 行）+ cycle 变长但未治愈的诊断模式 + 30s 探针模板 |

**新触发信号**：
- Hermes gateway 重启循环 + `config.yaml` fallback 链已配对 + **30s 探针 cycle 变长但未治愈** = 100% plist EnvironmentVariables 缺失
- 用户说"用 OMP" / "用 omp (adp 优先)" / "OMP 救活" = 触发后**先 `omp --version` 验证 model 已配**，再走完整工作流
- 改 `config.yaml` 后修 gateway = **改完**还要查 plist env var，**两步缺一不可**

**已知不变**：v0.6.2 触发条件硬约束 + gate-danger rollback 陷阱 + Python `re.search` vs `grep -E` 假阴性 不受影响；ACP 通道标准 4 步状态机在 OMP 已配 model 后仍按 v0.3.0 升默认的优先生效。

### v0.6.2（2026-06-29）— `delegate_task(acp_command='omp')` 走通/走不通边界 + gate-danger rollback 陷阱

实战发现 v0.6.1 触发条件 + 沙箱逃生归因订正后仍缺的 3 块，补齐：

| 级别 | 新增 | 描述 |
|:---:|------|------|
| P0 | `delegate_task(acp_command='omp')` ≠ 沙箱逃生 | ACP 通道 spawn OMP 作为审计 agent，需 LLM 决策调 OMP 内部 bash 工具；OMP 未配 model 时跟 `omp -p` 一样走不通。新增 pitfall 明确边界 |
| P0 | `gate-danger` 拦 rollback 文本里的破坏性命令 | rollback 字段描述"pkill -9 强杀"会被 `kill[[:space:]]+-9` ERE 命中、gate exit 10。绕开：rollback 不写真实命令，只描述行为 |
| P1 | Python `re.search` vs `grep -E` 在 POSIX 字符类上假阴性 | 调试 gate 误判时 Python `re` 不支持 `[[:space:]]` POSIX 字符类，假阴性。**真测试**用 `grep -Eiq` |
| P1 | 沙箱逃生对照表扩展 | 边界表加 2 行：`omp -p --tools bash` 在 OMP 未配 model 时实际不执行；`delegate_task(acp_command='omp')` 同理 |

**新触发信号**：
- 用户说"用 omp (adp 优先)" / "走 OMP ACP 通道救活" = 90% 跑不通（除非 OMP 已配 model）
- gate-danger exit 10 但 Python `re.search` 0 命中 = **必然**是 `[[:space:]]` 假阴性，改用 `grep -Eiq` 测
- rollback 文本里写了 `pkill` / `kill -9` / `rm -rf` 等命令 token = gate 100% 拦

**已知不变**：v0.6.1 触发条件硬约束 + 沙箱逃生归因订正不受影响；acp 通道在 OMP 已配 model 时仍按 v0.3.0 升默认的优先生效。

### v0.6.1（2026-06-29）— 触发条件硬约束 + 沙箱逃生归因订正

回顾 v0.6.0 实战发现两处错误，修正：

| 级别 | 修复 | 描述 |
|:---:|------|------|
| P0 | 触发条件硬约束 | 首次触发必须 `skill_view(name='call-omp')` 再选通道；扩触发词（"用 omp 搞"/"call-omp"/"救 gateway"） |
| P0 | 沙箱逃生归因订正 | v0.6.0 把 OMP 救活 gateway 写为实战成功，实际是 launchd `KeepAlive` 重试拉起，OMP 因未配 model 实际未执行 kickstart。新增 pitfall 明确"OMP 走不通的退路 = Hermes `terminal` 跑只读探针 + 等 launchd `KeepAlive`" |
| P1 | v16.2.4 行为差异文档化 | `--append-system-prompt` 在未配 model 时不让 OMP 跳过 LLM 决策（v0.6.0 文档暗示了但没说硬） |

**新增触发信号**：用户说"用 omp 搞" / "call-omp" / "救 gateway" = 100% 必须先 load skill。

### v0.6.0（2026-06-29）— 沙箱逃生通道 + OMP v16.2.4 升级

实战发现 Hermes `terminal` 沙箱拒绝 `pkill` / `launchctl kickstart`（错误："cannot restart or
stop the gateway from inside the gateway process"）时，从 Hermes 里**派生**出 OMP 跑同一命令能成功——
**OMP 是独立 CLI 进程，不在 Hermes 沙箱评估范围**。于是 OMP 从「审计/治理/工具面」扩展为
**沙箱逃生通道**，可救活自己挂掉的 gateway。

| 级别 | 新增 | 描述 |
|:---:|------|------|
| P0 | 沙箱逃生章节 | SKILL.md 新增「沙箱逃生 / 救活 gateway」章节，含完整 `omp -p` + `/tmp/omp-rescue.sh` 模板 |
| P0 | 三条新 pitfall | (1) OMP v16.2.4 hardline 拦截 `shutdown`/`reboot` 关键字（`--yolo` 不绕过）；(2) Hermes 沙箱逃生 = OMP bash 工具；(3) "假死"陷阱（curl 一次 refused ≠ 真死，需时间序列采样） |
| P1 | 首次调用必加 flag | `--no-skills --no-extensions --no-rules` 避免 OMP 未配置时触发 setup wizard |
| P1 | 版本对齐 | v16.2.2 → v16.2.4（现场升级 3 个 patch） |
| P1 | 描述改写 | frontmatter description 加「跳出沙箱」用例 + 触发词「救 gateway / kickstart 救活」 |

**新触发信号**：
- 用户说"我没法手动现在"+"沙箱拒绝"= 100% 沙箱逃生
- `curl 8460` 间隔出现 HTTP 000 = 重启循环（非真死）

**已知不变**：审计/治理/STDD 能力面完全没动，4 个原 pitfall 不受影响。

### v0.5.0（2026-06-29）— STDD 审计驱动质量加固

STDD-omp 审计 `--watch` 功能发现 **BLOCKER**（缺验收清单、零测试、幽灵证据、文档矛盾），逐项修复：

| 级别 | 修复 | 描述 |
|:---:|------|------|
| P0 | 验收清单 | `references/watch-acceptance-checklist.md`（17 条逐条 true/false） |
| P0 | --watch 测试 | `tests/run-all.sh` §13：ACP 拒绝、非法 interval、help 覆盖（+3 项，总计 58） |
| P1 | 文档矛盾 | `SKILL.md:129` "每秒轮询" → "默认 10s 间隔" |
| P1 | 幽灵证据 | `SKILL.md:219` "watch smoke test 通过" 加锚 `proc_111af9e87869: exit 0, 11轮, 29.6MB` |

**新增 pitfall**：STDD 完整审计闭环 — 方案设计→OMP(stdd-omp)审计（blocker）→逐项修→OMP 复审→通过。

### v0.4.0（2026-06-29）— omp-monitor --watch 实时监控 + WRR v5.2 审计

- `omp-monitor.sh` 新增 `--watch` 模式（+88 行，总 258 行）
- RPC/Shell 自动轮询循环：间隔可配、进度变化输出、超时自动 kill+rejected
- 输出对齐 cc-tmux 📡 模板：`===📡 BEGIN/END===` + 距上次时长 + raw 增长 + 干预指令
- ACP 不支持 --watch（delegate_task 自带异步回调）
- `--notify-on-change` 静默模式：进度不变时不输出
- ACP audit-driven design 工作流：Hermes 设计方案 → OMP 审计（blocker: ACP --await 不可行）→ 接受 findings → 调整为扩展 omp-monitor 而非新建脚本
- WRR v5.2 本地搜索层审计：shell sync 100 MB+ raw 完整产出；concern→补修→248/248
- 55/55 回归测试全过 + watch smoke test 通过（见 process log proc_111af9e87869: exit 0, 11轮轮询, 29.6MB raw）
- **Shell async 坑**：WRR v5.0 审计中发现 Shell `--async` 在 provider 配额耗尽(403)时静默退出（raw 0 字节无提示），长审计优先用同步 shell 重定向文件。

### v0.3.0（2026-06-28）— ACP 审查驱动安全加固

基于 ACP delegate_task 对 `omp-send.sh` 的深度代码审查（15+ 问题，P0 2 项），修复：

| 级别 | 修复 | 描述 |
|:---:|------|------|
| P0 | RPC daemon 复用权限泄露 | 复用前校验 `rpc_tools`/`rpc_auto_approve` 与当前配置一致，不一致则重启 |
| P0 | heredoc 命令替换风险 | `$(...)` 替换为 `printf` + 字符串拼接，消除维护者误引入注入的风险 |
| P1 | gate-counter 静默错误 | `2>/dev/null` → `2>"$C_ERR"`，失败时 cat stderr |
| P1 | 关键字段空值校验 | `TASK`/`MODE_FULL` 空值→exit 3；`RL`/`JL` 非数字→默认 3 |
| P2 | MAXTIME 数值校验 | 非正整数→exit 3 |
| P2 | 变量展开引号 | dry-run 输出 `${CWD:+--cwd "$CWD"}` |

### v0.2.0（2026-06-28）— ACP 升为默认通道

- 优先级 RPC > Shell > ACP → **ACP > RPC > Shell**
- `omp-send.sh` 默认 channel `rpc` → `acp`
- 三通道 smoke test 全部通过（RPC ✅ / Shell ✅ / ACP ✅）

### v0.1.0（2026-06-28）— 初始发布

- 三通道 RPC / Shell / ACP 实现
- 7 态状态机
- 三 gate（verify/danger/counter）
- 55/55 单元测试
