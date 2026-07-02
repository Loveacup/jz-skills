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

## 触发条件

- 设计方案涉及通道/协议/安全/竞态等复杂交互
- 想在写代码前让独立审计者过一遍架构
- 与 cc-tmux 配合：cc-tmux 做实现，OMP 做审计
