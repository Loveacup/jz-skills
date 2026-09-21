# call-omp P0 — 资源监督器与 send/monitor 接入 实证记录

> Slice：资源监督器（`scripts/omp-resource-supervisor.py`）+ 单元/集成测试，**并已接入 send/monitor 热路径**。
> 本文档记录 P0A（standalone supervisor）与 P0B（send/monitor 集成、认证 sidecar、脱敏 forensic state）合并后的最终交付状态。
> 验收：42 项 supervisor 专项测试 + 342 项全量套件全绿；一次真实 OMP 审计触发硬 cap 拒绝（非审计通过）。

## 修改文件清单

| 路径 | 类型 | 用途 |
|---|---|---|
| `scripts/omp-resource-supervisor.py` | 新增 | 独立 supervisor：把 OMP 子进程放在独立 session/pgrp，流式写入 raw，硬性执行 raw_bytes ≤ --raw-cap（默认 20 MiB），child pre-exec 继承 `RLIMIT_FSIZE`（内核级 cap），可选速率熔断，原子写 bounded/脱敏 forensic state |
| `scripts/lib/omp-lib.sh` | 修改 | bundle-only Shell（直连与 RPC→Shell 回退）统一走 supervisor-backed 强制异步路径，取消同步回退 |
| `scripts/omp-send.sh` | 修改 | bundle-only Shell 发送经 supervisor 包裹执行；不再有绕过 supervisor 的同步 shell 执行 |
| `scripts/omp-monitor.sh` | 修改 | 解析 raw/verdict 前先认证资源 sidecar；`resource_rejected` 先于 JSONL/verdict 解析转 `rejected`；forensic monitor state 白名单化脱敏 |
| `tests/test-resource-supervisor.sh` | 新增 | supervisor 专项 TDD 场景：raw_cap、rate_fuse、SHA-256 一致性、进程身份（PGID/session）、setsid 逃逸后代仍受内核 cap 等（不含 monitor sidecar 认证） |
| `tests/run-all.sh` | 修改 | 纳入 supervisor 与 send/monitor 集成回归（monitor sidecar 认证在此覆盖），全量 342 |

## 交付契约（当前有效）

- **强制异步 + supervisor-backed**：真正经由 Shell 执行的 bundle-only 审计（直连 shell 与 RPC→Shell 回退两条路径）一律强制异步且受 supervisor 监督，**不再有同步回退**。
- **硬 cap 抗逃逸**：supervisor 使用 `start_new_session`、owned PGID 处理，并在 child pre-exec 继承 `RLIMIT_FSIZE`。即使某个 `setsid` 逃逸的后代进程仍持有 stdout FD，20 MiB raw cap 依然成立（内核级熔断，不只依赖轮询）。
- **终态有界且原子，全部 fail-closed**：资源终态有界、原子写入。`raw_cap`、`rate_fuse`、未被回收的直连子进程 containment 失败、以及硬性 pre-exec 错误，均 fail-closed。
- **monitor 先认证再解析**：monitor 在解析 raw/verdict **之前**先认证资源 sidecar——校验规范化路径；拒绝 symlink / 非常规文件的 sidecar 与 raw；精确 v1 task/state/raw/pid 绑定；带类型的 shape/status 检查；pid/pgid/session 身份交叉核对。只允许一个很窄的启动窗口。
- **拒绝先行 + forensic 脱敏**：`resource_rejected` 先于 JSONL/verdict 解析成为主流程 `rejected`。forensic monitor state 白名单化：不写 argv/prompt/raw/tail/未知嵌套数据；`reason`/`issue` 限长 512，同时保留 containment 标记。
- **`--watch` 不盲杀**：超时时 `--watch` 不再盲目 kill 受监督的 wrapper。

## 已验证本地结果

（以下命令在所有 writer 停止后由 Hermes 复跑）

```text
python3 -m py_compile scripts/omp-resource-supervisor.py   -> 0
bash tests/test-resource-supervisor.sh                     -> PASS=42 FAIL=0
bash tests/run-all.sh                                       -> PASS=342 FAIL=0
bash scripts/call-omp-check.sh                             -> 0
```

## L2 审查：blocker → 修复 历史（高层）

独立 L2 审查者在 **P0B1R** 与最终 **P0B3R2** 通过前，先各抓到了真实 blocker 并被逐项修复：

- rate-fuse 场景下 `setsid` 逃逸后代仍能继续增长 raw（后以 child pre-exec 继承 `RLIMIT_FSIZE` 的内核级 cap 收口）。
- 陈旧 sidecar 绑定 + argv/prompt 泄漏（后以 monitor 的精确 v1 绑定 + 身份交叉核对 + forensic 白名单脱敏收口）。

这些是 supervisor / monitor 契约得以成立的关键修复。**注意：不得据此声称 OMP 给出了最终审计通过。**

## 真实 OMP 审计尝试 —— 事实结果，非裁决

- 证据包：`/tmp/omp-bundle-p0-final-1784450848-17190`，6 文件 / 1618 diff 行。
- 任务 id `p0-final-audit-20260719`，bundle-only Shell，真实 supervisor-backed 异步。
- OMP raw 精确到达 20 MiB / 3,883 行，supervisor 退出码 2，`resource_rejected` 原因 `raw_cap_exceeded:20971520>20971520`；monitor 在 verdict 解析前即 rejected。
- **没有产出可信的 OMP verdict。** `omp-finish --reject --keep` 记录 reject 计数 1。这是**熔断生效的证据，不是审计批准**。
- bounded raw tail 显示 OMP 反复推断证据包缺少测试执行输出；**不要把 tail 或 prompt 文本抄进文档**。

## 已知边界 / 剩余限制

1. 没有产出可信 OMP verdict —— P0 只证明资源熔断与拒绝路径成立，不代表这份改动已通过 OMP 独立审计。后续若要真正取得 verdict，需用重新划定范围、体积更小的证据包，或转人工复核（**不得把资源 cap 拒绝改成同步重跑或手动接受**）。
2. rate fuse 当前用累计字节差 / 时间窗实现，对慢启动（burst-then-idle）敏感；后续若需平滑 burst 容忍，可改用 EMA。默认仍关闭。
3. `os.truncate(raw_cap)` 假设 raw_fh 已被内核 flush 落盘；极端断电场景下 raw 实际体积可能略小于 cap——这是可接受的失败模式（fail-small, not fail-large）。
4. supervisor 用 `argparse.REMAINDER` 解析 `--` 后的子命令，子命令内再含 `--` 需要 double-dash quoting。
5. 内核级 cap（`RLIMIT_FSIZE`）覆盖 raw 文件写入这一路径；对不经该 FD 的其它侧信道输出不构成约束，仍以 bundle-only 只读 + monitor 认证作为整体防线。
