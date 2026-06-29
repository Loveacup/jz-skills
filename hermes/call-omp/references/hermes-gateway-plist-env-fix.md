# Hermes Gateway · plist EnvironmentVariables 修复

> 2026-06-29 实战：default profile gateway 重启循环，半截修复（config.yaml fallback 链配对）后
> cycle 变长（13-19s 活）但未治愈。最终根因 = launchd plist 缺 `EnvironmentVariables` 块，fallback
> chain 注册的 `providers.<name>.key_env: <VAR>` 引用 `os.environ['<VAR>']`，launchd 进程里**没有
> 这个 var** → fallback API 调出去 auth fail → cycle 略变长但还是 fail。

## TL;DR

- `config.yaml` 改完**不等于**修好 —— **launchd plist 也要改**。
- `config.yaml` 的 `key_env: FOO_API_KEY` 是声明 key 来自哪个 env var；**真正注入 env var 的地方是
  plist 的 `EnvironmentVariables` 块**。
- `~/.zshrc` / `~/.bash_profile` 里的 `export FOO_API_KEY=*** 对 launchd 启动的进程**完全无效**
  （launchd 不读 user shell rc files）。
- 修复 = 2 行 plist 命令（`plutil -insert` + `launchctl unload/load`）+ 1 行 kickstart，**用户 Mac
  终端跑**，OMP 救不了（需要 user-level launchctl 权限）。

## 完整修复命令（用户跑）

```bash
# 步骤 1：plist 注入 DEEPSEEK_API_KEY（值从当前 shell 环境取，或从 vault 取）
plutil -insert EnvironmentVariables.DEEPSEEK_API_KEY \
  -string "${DEEPSEEK_API_KEY}" \
  ~/Library/LaunchAgents/ai.hermes.gateway.plist

# 步骤 2：unload + load 让 plist 生效
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist

# 步骤 3：kickstart 拉起新进程（已注入 env var）
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway

# 步骤 4：30s 探针验证（全部 HTTP 200 = 修好）
for i in 1 2 3 4 5 6; do
  sleep 5
  curl -sS -o /dev/null -w "probe $i (t+$((i*5))s): HTTP %{http_code}\n" \
    --max-time 2 http://127.0.0.1:8460/health
done
```

**取 DEEPSEEK_API_KEY 实际值**：

```bash
echo $DEEPSEEK_API_KEY                              # 当前 shell 环境
grep DEEPSEEK_API_KEY ~/.zshrc ~/.bash_profile 2>/dev/null   # shell rc
security find-generic-password -s DEEPSEEK_API_KEY -w 2>/dev/null  # keychain
```

## 根因诊断（v0.6.3 实战序列）

### 阶段 1：发现重启循环

- `curl 127.0.0.1:8460/health` 一次 refused
- 30s 探针：t+0/5s = 200，t+10/15s = 000，t+20/25s = 200 — **重启循环**（launchd 拉得起但 gateway 自杀）
- `ps` 看 PID 持续在换（每次 etime < 30s）

### 阶段 2：怀疑 kimi 配额

- `tail -50 ~/.hermes/logs/gateway.error.log | grep -i kimi` → 8+ 条 403 quota
- 假设：主 model kimi 配额耗尽 → agent 死 → SIGTERM

### 阶段 3：修 fallback chain

- `config.yaml` 加 `providers.deepseek` 块（`key_env: DEEPSEEK_API_KEY`）
- `fallback_providers: deepseek` 已存在，配置结构对了
- **以为修好**

### 阶段 4：30s 探针看修复效果

- 修复前 cycle：HTTP 200 持续 5s → 000 → launchd 拉起
- 修复后 cycle：HTTP 200 持续 **13-19s** → 000 → launchd 拉起
- **cycle 变长但未治愈** ← 关键信号：fallback **部分** 接住了 kimi 403，但**最终还是死**

### 阶段 5：识别 plist 缺 env var

- `cat ~/Library/LaunchAgents/ai.hermes.gateway.plist` 看 `EnvironmentVariables` 块
- **只有** `PATH / VIRTUAL_ENV / HERMES_HOME` —— **没有** `DEEPSEEK_API_KEY`
- launchd 启动的 Python 进程只继承 plist 里声明的 env vars
- fallback chain 调 deepseek API → `os.environ['DEEPSEEK_API_KEY']` = KeyError 或 auth fail
- **半截修复**：config 配对了，env var 没注入 = fallback 仍 fail

## 诊断信号速查

| 信号 | 含义 |
|------|------|
| `curl 8460` 间隔 000 = 重启循环 | launchd 拉得起但 gateway 自杀 |
| `error.log` 满屏 403 quota | 主 model 配额耗尽（kimi 之类） |
| `error.log` 0 出现 deepseek / fallback 关键字 | fallback 链根本没被触发 |
| `config.yaml` 的 `key_env: FOO` 但 `error.log` 0 出现 `FOO` / 0 出现 fallback provider 名 | plist 缺 env var（v0.6.3 新增） |
| 修复后 cycle 变长（10-20s 活）但未治愈 | fallback 接住了一部分但**最终还是 fail**（多半是 plist env var） |
| 修复后 cycle **持续 HTTP 200 ≥ 30s** | 真治好了 |

## 为什么 OMP 救不了这一步

- `launchctl unload/load` 需要 user-level launchctl 权限
- OMP 调 shell 也得经 macOS 沙箱（v16.2.4 已配 model，但 macOS 沙箱层跟 Hermes 沙箱层是**两层**）
- 实际：OMP 跑 `launchctl unload/load` 可能被 macOS TCC（Transparency, Consent, and Control）拦
- **用户 Mac 终端直接跑** = 最稳路径，2 行命令 5 秒

## OMP 在这里能做的（不是 plist 修复本身）

1. **诊断**：OMP 跑 shell 看 `~/Library/LaunchAgents/ai.hermes.gateway.plist` 内容 + `printenv | grep <KEY>`
   （在 launchd 进程上下文中），输出 "plist 缺 KEY" verdict
2. **生成修复脚本**：OMP 写 `~/Desktop/fix-gateway-plist.sh`（`plutil -insert` + `launchctl unload/load`
   + `kickstart`），用户跑
3. **30s 探针验证**：OMP 跑 `for i in 1..6; do curl ... ; done` 输出 verdict

完整 4 步工作流（call-omp standard）：

```bash
# Step 1: start
scripts/omp-start.sh --mode audit --task "诊断 default gateway 重启循环的 plist env var 缺失" \
  --cwd /Users/alexcai/.hermes --allowed-path /Users/alexcai/.hermes \
  --allowed-path /Users/alexcai/Library/LaunchAgents \
  --criterion "plist EnvironmentVariables 块声明了 DEEPSEEK_API_KEY" \
  --criterion "launchd 启动的 gateway 进程内 os.environ['DEEPSEEK_API_KEY'] 非空" \
  --criterion "30s 探针全部 HTTP 200"

# Step 2: send (ACP default)
scripts/omp-send.sh --state /tmp/omp-state-*.json

# Step 3: delegate_task(acp_command='omp')
delegate_task(acp_command='omp', goal=<PROMPT>, context=<背景>)

# Step 4: monitor + finish
scripts/omp-monitor.sh --state /tmp/omp-state-*.json
scripts/omp-finish.sh --state /tmp/omp-state-*.json --accept|--reject
```

verdict = pass 时，OMP 给出修复命令清单，用户在 Mac 终端跑（不是 OMP 自己跑）。

## 给后续 session 的可复用信号

**下次遇到 Hermes gateway 重启循环**：

1. 跑 30s 探针 → 是重启循环还是真死？
2. 读 `error.log` 找主 model 403 模式
3. 读 `config.yaml` 看 fallback chain 是否配对
4. **新增 (v0.6.3)**：读 `~/Library/LaunchAgents/ai.hermes.gateway.plist` 看 `EnvironmentVariables`
   块是否包含 `key_env` 引用的所有 vars
5. **改 config + 改 plist 两步都做**才能真治
6. 改完跑 30s 探针验证

**单步改 = 半截修复**。信号 = cycle 变长但未治愈。
