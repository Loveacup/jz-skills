# CC Hook 月度复查 → cron 自动化

> 2026-06-24。原 `cc-hook-bug-registry.md` 的 hook 正确性复查靠**人工每月跑一遍**——违背
> `design-principles.md`「LLM/人不擅长定时重复义务」。本文把**「hook 还在不在烧」这半**搬到
> cron（每月 1 号自动跑 `scripts/cc-hook-check.sh`，结果走 Hermes cron deliver 回报）。

## 分工：cron 自动化哪半、人工仍管哪半

| 复查项 | 谁来做 | 为什么 |
|--------|--------|--------|
| **hook 是否仍在触发**（心跳/状态权威/生命周期日志如期落盘） | ✅ **cron 自动**（`cc-hook-check.sh`） | 纯客观、可被动检视产物，正是「定时重复」该外包给机器的 |
| 4 个上游 GitHub bug（#43407/#18312/#52822/#40506）是否已修复 | 👤 人工/agent | 需读 GitHub issue 状态，cron 的 no-agent 脚本做不了；命中变化才动设计 |
| `--settings` 双写、SessionEnd reason 取值等实测事实 | 👤 人工/agent | 需真跑实验核实，非产物检视 |

cron 把**最易被忘、又最纯客观**的那半（hook 在不在烧）变成自动跘线；剩下需要判断的留给人。

## `cc-hook-check.sh` 做什么

对**当前活跃**的 `hermes-cc-*` session **被动检视** hook 产物（**不**主动驱动真 CC，不打扰运行中的任务）：

- 核心① `cc-status-<s>.json` 有效（含 `.state` 且 `.seq≥1`）→ 证 `cc-status-writer` 接的 8 事件在触发
- 核心② `cc-heartbeat-<s>` 存在 → 证 PreToolUse 等热心跳 hook 在烧
- 信息项：`cc-state-<s>.log` 行数、`cc-turn-done-<s>` 是否在、SessionStart context 注入痕迹（capture-pane best-effort）

退出码：`0` 无活跃 session **或** 全部核心信号健康 · `1` ≥1 session 核心信号缺失（疑似 hook 回归）。
无活跃 session → 打印 `(no active CC sessions)` 且 `exit 0`（脚本自身不依赖活 session）。

## 安装（一键，用 Hermes 官方 cron CLI）

> 仓库内交付脚本；本片段把它接到 Hermes cron。复制粘贴即可，**不需手改 `~/.hermes/cron/jobs.json`**。

```bash
# 1) 让 cron 能找到脚本：软链到 ~/.hermes/scripts/（软链 → 跟随仓库更新，不漂移）
mkdir -p ~/.hermes/scripts
ln -sf "$HOME/code/jz-skills/hermes/cc-tmux/scripts/cc-hook-check.sh" \
       ~/.hermes/scripts/cc-hook-check.sh
# （若偏好拷贝而非软链：cp 上述源到 ~/.hermes/scripts/，但需在脚本更新后重拷）

# 2) 注册每月 1 号 00:00 的 no-agent job，stdout 直接 deliver
hermes cron create '0 0 1 * *' \
  --name cc-hook-monthly-check \
  --script cc-hook-check.sh \
  --no-agent \
  --deliver local
```

`--no-agent` = 不过 LLM，脚本本身就是 job，stdout 原样回报（经典 watchdog 模式）。
`--deliver local` 走本地投递；要发到具体 IM 改成 `--deliver telegram` / `--deliver platform:chat_id`。

## 验证

```bash
hermes cron list | grep cc-hook-monthly-check         # 确认已登记，schedule=0 0 1 * *
hermes cron run cc-hook-monthly-check                 # 下一个 scheduler tick 触发一次，看 deliver
bash ~/.hermes/scripts/cc-hook-check.sh; echo "rc=$?" # 手动直跑，肉眼看报告
```

## 卸载

```bash
hermes cron remove cc-hook-monthly-check
rm -f ~/.hermes/scripts/cc-hook-check.sh
```

## 手动注册兜底（不想用 CLI 时）

`hermes cron create` 等价于往 `~/.hermes/cron/jobs.json` 追加一条（字段对齐现有 `cron-worker-skill-cleanup`）：

```json
{
  "name": "cc-hook-monthly-check",
  "prompt": "",
  "script": "cc-hook-check.sh",
  "no_agent": true,
  "schedule": { "kind": "cron", "expr": "0 0 1 * *", "display": "0 0 1 * *" },
  "enabled": true,
  "deliver": "local"
}
```

> 优先用 CLI（它会补全 id/created_at/next_run_at 等内部字段并落 scheduler.db）；手改 JSON 仅兜底，改前先备份 `jobs.json`。
