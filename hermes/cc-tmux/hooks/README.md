# cc-tmux driven-CC hooks (§3.3–3.7)

被 cc-tmux 驱动的 CC 的 **L2(CC-native)hook 层**。七类事件 / 八个 hook 条目全部坐落在
**non-deny 路径**(PostToolUse / Notification / SessionStart / Stop-block)上,
任何一个不触发都只会**静默降级**回 L0/L1 行为,绝不 wedge 住 turn(原则⑥
graceful degradation)。

**hook 配置的唯一真相源(single source of truth):**
[`../templates/settings.runtime.json`](../templates/settings.runtime.json)
(stdin-jq 变体,D-4 key 已统一,两个脚本路径经 `$CC_TMUX_HOOK_DIR` **自定位**到 skill 目录)。
cc-start.sh 启动 CC 时用 `claude --settings <此文件>` **会话级注入**(§3),不再 merge 进
全局 `~/.claude`。旧的 env-based 模板与 global-merge 模板均已删除,以终结模板分裂。

> 命名约定:本文档里的 `<key>` / `<s>` 一律指 **D-4 规范键**
> `${CC_TMUX_SESSION:-<stdin session_id>}`,详见 [§D-4 key 统一](#d-4-key-统一the-key)。

---

## 0. 七类事件总览（§Phase-2/3 状态总线）

hook 共同维护一条**事件驱动状态总线**，让 Hermes **无需定时轮询**：心跳 = freshness、`cc-turn-done` = 完成权威、`cc-freeze` = 异常告警。

| 事件 | 实现位置 | matcher | 角色（状态总线） |
|---|---|---|---|
| **PreToolUse**(`async`) | inline | (无,全部) | `touch` 心跳（高频 freshness beat，CC 调工具时心跳恒新鲜） |
| PostToolUse(Bash) | inline | `Bash` | >4KB `tool_response` 归档 + `touch` 心跳 |
| PostToolUse(Write\|Edit\|MultiEdit) | `cc-posttool.sh` | `Write\|Edit\|MultiEdit` | best-effort 格式化 + >8KB 归档 + `touch` 心跳 |
| **UserPromptSubmit** | inline | (无) | `touch` 心跳 + 记 `received` + **清掉上一轮 `cc-turn-done`**（新 turn） |
| Notification | inline | `idle_prompt\|permission_prompt` | 写 `{event:notification}` 到 state log + `touch` 心跳 |
| SessionStart | inline | (无) | 注入 cc-tmux run-context + 最近 state 尾巴 |
| **SessionEnd** | inline | (无) | 记 `{state:GONE,reason}` 到 state log（区分正常退出 vs 崩溃） |
| Stop | `cc-stop-check.sh` | (无) | 软门 `--expect` 缺失则 `block`（gate-counter 有界）；非 block 收尾时写 **`cc-turn-done-<key>`** 标记 |

两个 `.sh` 是真实脚本文件（经 `--settings` 的 `$CC_TMUX_HOOK_DIR` 自定位到 skill 目录），其余是 `templates/settings.runtime.json` 里的 inline command。
**所有 hook 全程非 deny、`exit 0`、best-effort**（Stop 靠输出的 JSON 而非 rc 来 block）——这是 hook 的安全车道，避开全部 deny 类 bug（见 `../references/cc-hook-bug-registry.md`）。
**冻结探针**由 `cc-watcher.sh --watch`（cc-start 后台拉起的守护进程）在心跳陈旧时跑 `cc-monitor` 完成，写 `cc-freeze-<key>` 告警——这是唯一无法靠 hook 实现的部分（TUI 计时器无 hook 可读）。

---

## 1. 逐 hook 详解

### 1.1 PostToolUse(Bash) — tool_response 归档

- **触发条件:** 每次 `Bash` 工具调用**完成后**触发(matcher `Bash`)。
- **数据流:**
  - **stdin JSON:** `{ "session_id": "<uuid>", "tool_name": "Bash", "tool_input": {...}, "tool_response": "<命令的完整输出>" }`
  - **处理逻辑:** `in=$(cat)` 一次性吞 stdin(关键:stdin 只能读一次);
    `jq` 取 `session_id` → 算出 `k=${CC_TMUX_SESSION:-$sid}`;取 `tool_response`,
    若长度 `>4096` 字节,追加写到 `/tmp/cc-output/<k>/responses-<epoch>.log`。
  - **副作用:** 大 Bash 输出落盘冗余备份,防 scrollback 丢失。`mkdir -p` 与写入
    全部 `2>/dev/null`,失败也 `exit 0`。
- **为什么是 4KB 而不是 8KB:** Bash 输出比文件产物更碎、更频繁,阈值取低一档
  以多兜住中等输出。

### 1.2 PostToolUse(Write|Edit|MultiEdit) — `cc-posttool.sh`

- **触发条件:** 每次 `Write` / `Edit` / `MultiEdit` 完成后触发。
- **数据流:**
  - **stdin JSON:** `{ "session_id": "<uuid>", "tool_input": { "file_path": "<绝对路径>", ... } }`
    (MultiEdit 可能只带 `edits[]` 而无顶层 `file_path`)。
  - **处理逻辑:**
    1. `IN=$(cat)`;`jq` 取 `.tool_input.file_path`,为空或文件不存在 → 直接 `exit 0`
       (MultiEdit 无 `file_path` 的情形即走这条 skip)。
    2. **按扩展名 best-effort 格式化**(命令存在才跑,全 `2>/dev/null`):
       `.ts/.tsx/.js/.jsx/.json/.css`→`prettier`;`.py`→`ruff format`+`ruff check --fix`;
       `.go`→`gofmt -w`;`.sh`→`shfmt -w`。**`.md` 故意排除**,避免 prettier
       改写 SKILL.md / references 破坏仓库自有风格。
    3. **大产物归档(对任意扩展名,含 .md;只有格式化按扩展名 gate):**
       `wc -c` 取大小,`>8192` 字节则 `cp` 到 `/tmp/cc-output/<key>/<basename>.<epoch>.<pid>`。
       `.<pid>` 后缀防同一秒内覆盖。
  - **副作用:** 文件被原地格式化(若有 formatter)+ 大文件冗余归档。
- **契约:** `set -uo pipefail` 但**无 `-e`**;格式化/归档是 icing,绝不阻断 tool result。
- **timeout:** template 中配 `15s`。

### 1.3 Notification — state log + heartbeat

- **触发条件:** CC 发出 notification 且 matcher 命中 `idle_prompt|permission_prompt`
  (空闲等待输入 / 等待权限确认)时触发。
- **数据流:**
  - **stdin JSON:** `{ "session_id": "<uuid>", ... }`(本 hook 只需 session_id)。
  - **处理逻辑:** 算出 `k`,追加一行 JSONL
    `{"ts":"<UTC ISO>","event":"notification","session":"<k>"}` 到
    `/tmp/cc-state-<k>.log`,并 `touch /tmp/cc-heartbeat-<k>`。
  - **副作用:** 喂养 state bus —— `cc-monitor.sh` 读这个 log 判活;heartbeat
    供外层判 CC 是否卡死。
- **为什么 matcher 是这两个:** 这两类 notification 正好对应"CC 停下来等人",
  是外层最需要感知的状态切换点。

### 1.4 SessionStart — 注入 run-context

- **触发条件:** 每次 session 启动 / resume / compaction 后触发(无 matcher,全部触发)。
- **数据流:**
  - **stdin JSON:** `{ "session_id": "<uuid>", ... }`。
  - **处理逻辑:** 算出 `k`,`echo` 一段中文 run-context(告诉 CC 它是被 cc-tmux
    驱动的、session=`<k>`、大输出必须 Write 到 `/tmp/cc-output/<k>/`),再
    `tail -3 /tmp/cc-state-<k>.log` 把最近状态贴进上下文。
  - **副作用:** **stdout 即被注入 CC 上下文**(SessionStart hook 的 stdout 会进 prompt)。
    这就是每个 session 开头那段 `[cc-tmux] 你是被 cc-tmux 驱动的 CC…` 的来源。
- **D-4 收益:** key 统一后,`tail` 的 state log 不再是空的(Notification 用同一个
  key 写、SessionStart 用同一个 key 读)。

### 1.5 Stop — `cc-stop-check.sh` soft gate

- **触发条件:** turn 即将结束(Stop 事件)时触发。
- **数据流:**
  - **stdin JSON:** `{ "session_id": "<uuid>", ... }`。
  - **处理逻辑:**
    1. `IN=$(cat)` → 算 `S=${CC_TMUX_SESSION:-$sid}` → `EXPECT=/tmp/cc-expect-<S>`。
    2. `EXPECT` 文件不存在 / 内容为空 → `exit 0`(没声明期望 → 永不 block,保守)。
    3. 读出 glob `PATTERN`,`find -L /tmp -maxdepth 3 -name "$PATTERN" -type f -size +0c`;
       命中非空文件 → `exit 0`(产物已在,正常结束)。
    4. **缺失:** 经 `gate-counter.sh --key stop-precheck-<S> --kind reject --inc --limit 2`
       做**确定性 re-block 上限**。用**独立 key**,不消耗人审 reject 预算
       (`/tmp/cc-counter-<sid>.json`)。已 block 满 2 次 → `exit 0` 放行
       (cc-finish 是 backstop)。
    5. 否则输出 `{"decision":"block","reason":"期望产物 … 缺失或为空…"}` 并 `exit 0`。
  - **副作用:** 输出的 block JSON 把 turn 推回去补产物;reason 回喂给 CC。
- **Stop 语义:** **没有 `approve`**。产物在 → 静默 `exit 0`;缺失 → 输出 block JSON
  (是 JSON 在 block,不是 rc)。即使 block 也 `exit 0`。
- **非终审:** Stop 通过 ≠ 完成("被审计者不能是自己的终审")。`cc-finish.sh`
  才是永远独立运行的 witness。
- **timeout:** template 中配 `30s`。

---

## 2. D-4 key 统一(the `<key>`)

每个 per-session 文件都以 **`${CC_TMUX_SESSION:-<stdin session_id>}`** 为 key:

- `cc-start.sh` 用 `HOME=… CC_TMUX_SESSION=<tmux session name> claude …` 启动
  (见 `cc-start.sh:165`)。该变量传给每个 command-type hook(子进程),于是
  in-CC hook 用 **tmux session name** 这个 key 写输出 —— 与外层
  `cc-monitor.sh` / `cc-send.sh` / `cc-finish.sh` 用的**同一个 key**。
- 这统一了 state bus(Notification 写的 log 正是 cc-monitor 读的;SessionStart
  的 "recent state" 尾巴不再空)、把 Stop soft gate 端到端接通(它现在解析的
  `/tmp/cc-expect-<tmux-name>` 正是 `cc-send.sh --expect` 写的那个文件),并让
  `cc-finish.sh` 能清掉每一个产物。
- **安全降级:** 若 `CC_TMUX_SESSION` 缺失(不是 cc-tmux 拉起的 CC,或 env 没传到),
  key 回退到 stdin 里的 CC UUID(`CLAUDE_SESSION_ID` 在 hook env 里是空的 —— Pitfall
  #15)。相比旧的 UUID-keyed 行为**无回归**;Stop gate 此时简单 no-op(绝不误 block)。

---

## 3. 配置 / 部署(§Phase-1 2026-06-17 起:`--settings` 会话级注入,**已替代全局**)

**不再需要任何手动部署。** cc-start.sh 在启动每个 CC 时自动注入本 skill 的 hook 配置:

```bash
# cc-start.sh 启动行(节选)——无需人工操作,改 skill 即生效:
HOME=… CC_TMUX_SESSION="$SESSION" CC_TMUX_HOOK_DIR="$SKILL_ROOT/hooks" \
  claude --model … --effort … --settings "$SKILL_ROOT/templates/settings.runtime.json"
```

- **声明式 + 自动同步:** skill 改 `templates/settings.runtime.json` 或 `hooks/*.sh`,
  **下一个 CC 启动时自动拿到最新版**(每个任务 = 全新 CC)。零 cp、零 jq merge、零"记得重启"。
- **脚本自定位:** 模板里 `bash "$CC_TMUX_HOOK_DIR/cc-*.sh"`,`CC_TMUX_HOOK_DIR` 由启动行
  导出、在 hook 触发时于 hook shell 内展开(已实测 R2 PASS)。所以脚本只存在于 skill 目录,
  **不再往 `~/.claude/hooks/` 拷贝**(那会造成"改错文件"陷阱)。
- **隔离:** 只对 cc-tmux 拉起的 CC 生效,不污染机器上其它 CC session。

> ⚠️ **绝不要再把这些 hook merge 进全局 `~/.claude/settings.json`。** 已实测(R1)
> `--settings` 的 hooks 与全局 hooks **累积/双触发** —— 同时存在会双写心跳、Stop 双 block、
> 大输出双归档。全局 cc-tmux hooks 已于 Phase 1 摘除,保持摘除状态。
> 详见 [`../references/cc-hook-facts-v2.1.178-20260617.md`](../references/cc-hook-facts-v2.1.178-20260617.md)。

---

## 4. CC_TMUX_SESSION 环境变量(注入 → 使用 → 降级)

| 环节 | 行为 |
|---|---|
| **注入** | `cc-start.sh:165` 以 `CC_TMUX_SESSION="$SESSION" claude …` 启动,把 tmux session name 写进 claude 进程环境 |
| **传播** | command-type hook 是 claude 的子进程,自动继承该 env var |
| **使用** | 每个 hook 第一步算 `k=${CC_TMUX_SESSION:-$sid}`,用 `k` 给所有 per-session 文件命名 |
| **降级** | 变量缺失 → 回退到 stdin `session_id`(CC UUID)。`CLAUDE_SESSION_ID` 在 hook env 里**恒为空**(CC v2.1.178),不能用 |

**为什么不用 `CLAUDE_SESSION_ID`:** 在 hook 执行环境里它是空字符串(Pitfall #15),
所以 D-4 一律从 stdin JSON 的 `.session_id` 取 UUID 做兜底。

---

## 5. 排障指南

| 症状 | 根因 | 处理 |
|---|---|---|
| 归档落到 `/tmp/cc-output/unknown/` | `CC_TMUX_SESSION` 没传到 hook **且** stdin 没 `session_id` | 确认 CC 由 `cc-start.sh` 拉起;`env \| grep CC_TMUX` 应在 CC 进程里非空 |
| 归档落到 UUID 目录而非 tmux 名 | `CC_TMUX_SESSION` 未传播(env 没继承) | 检查 `cc-start.sh:165` 的启动行是否真的带了 `CC_TMUX_SESSION=`;CC 是否 restart 过 |
| **`CLAUDE_SESSION_ID` 空** | CC v2.1.178 在 hook env 里不导出它 | 这是已知事实,不是 bug;一律读 stdin `.session_id`,勿依赖该 env var |
| hook 里 `jq` 第二次读不到数据 | **stdin 只能消费一次** | 必须 `in=$(cat)` 一次性吞,之后所有 `jq` 都喂 `"$in"`,不要再 `cat`/直接管道给第二个 jq |
| Stop gate 从不 block | `EXPECT` 文件不存在 / D-4 key 不匹配 | 确认 `cc-send.sh --expect <glob>` 写了 `/tmp/cc-expect-<tmux-name>`,且 Stop hook 解析同一个 `<key>` |
| Stop gate 反复 block 卡住 turn | 不应发生(有 gate-counter 上限 2) | 检查 `/tmp/cc-counter-stop-precheck-<s>.json`;满 2 次后必放行,cc-finish 兜底 |
| state log / SessionStart 尾巴为空 | Notification 与 SessionStart 用了不同 key | D-4 已修;若仍空,说明 `CC_TMUX_SESSION` 在某一端缺失 → 两端不一致 |
| 非 cc-tmux 的 CC 也触发了 cc-tmux hook | 误把 hooks merge 回了全局 `~/.claude` | §Phase-1 起只走 `--settings` 注入,不应再有全局 cc-tmux hooks;`jq '.hooks' ~/.claude/settings.json` 应为 null/无 cc-tmux 键 |

---

## 6. Smoke test 清单(部署后逐项验证)

单测在隔离环境过了(`tests/test-hooks.sh`,**21/21**),但**实际触发**依赖目标 CC 版本。
下列每项给一个**最小可复现 shell 命令**,可直接在 shell 里喂 stdin JSON 验证脚本逻辑;
标 *(live)* 的项必须在真实 CC build 里跑。

### 6.1 PostToolUse(Bash) — inline

```bash
# 提取 inline 命令并喂一个 >4KB tool_response
CMD=$(jq -r '.hooks.PostToolUse[0].hooks[0].command' ../templates/settings.runtime.json)
BIG=$(head -c 5000 /dev/zero | tr '\0' 'x')
printf '{"session_id":"uuid-x","tool_response":"%s"}' "$BIG" \
  | CC_TMUX_SESSION="smoke" bash -c "$CMD"
ls -l /tmp/cc-output/smoke/responses-*.log   # 期望:存在且非空
```

### 6.2 PostToolUse(Write|Edit|MultiEdit) — `cc-posttool.sh`

```bash
# >8KB 文件应被归档,key 用 CC_TMUX_SESSION(非 UUID、非 unknown)
F=/tmp/smoke-big.txt; head -c 9000 /dev/zero | tr '\0' 'y' > "$F"
printf '{"session_id":"uuid-x","tool_input":{"file_path":"%s"}}' "$F" \
  | CC_TMUX_SESSION="smoke" CC_OUTPUT_ROOT=/tmp/cc-output bash cc-posttool.sh; echo "rc=$?"
ls -l /tmp/cc-output/smoke/smoke-big.txt.*   # 期望:存在(.<epoch>.<pid> 后缀)

# MultiEdit 无 file_path → 必须安全 skip 且 rc=0
echo '{"session_id":"uuid-x","tool_input":{"edits":[]}}' \
  | CC_TMUX_SESSION="smoke" bash cc-posttool.sh; echo "rc=$?  (期望 0)"
```

### 6.3 Notification — inline

```bash
CMD=$(jq -r '.hooks.Notification[0].hooks[0].command' ../templates/settings.runtime.json)
echo '{"session_id":"uuid-x"}' | CC_TMUX_SESSION="smoke" bash -c "$CMD"
tail -1 /tmp/cc-state-smoke.log     # 期望:一行 {"event":"notification",...}
ls -l /tmp/cc-heartbeat-smoke        # 期望:heartbeat 文件存在
```

### 6.4 SessionStart — inline

```bash
CMD=$(jq -r '.hooks.SessionStart[0].hooks[0].command' ../templates/settings.runtime.json)
echo '{"ts":"x","state":"THINKING","marker":"SEEN"}' > /tmp/cc-state-smoke.log
echo '{"session_id":"uuid-x"}' | CC_TMUX_SESSION="smoke" bash -c "$CMD"
# 期望 stdout:含 "[cc-tmux] 你是被 cc-tmux 驱动的 CC" + 贴出 marker=SEEN 的尾巴
```

### 6.5 Stop — `cc-stop-check.sh`

```bash
# A. 无 expect 文件 → 永不 block(静默 rc=0,无 stdout)
rm -f /tmp/cc-expect-smoke
echo '{"session_id":"uuid-x"}' | CC_TMUX_SESSION="smoke" bash cc-stop-check.sh; echo "rc=$?"

# B. 声明期望但产物缺失 → 输出 decision:block
echo 'smoke-artifact-*.md' > /tmp/cc-expect-smoke
echo '{"session_id":"uuid-x"}' | CC_TMUX_SESSION="smoke" bash cc-stop-check.sh   # 期望:{"decision":"block",...}

# C. 产物存在 → 静默放行
touch /tmp/smoke-artifact-1.md; echo content > /tmp/smoke-artifact-1.md
echo '{"session_id":"uuid-x"}' | CC_TMUX_SESSION="smoke" bash cc-stop-check.sh; echo "rc=$?  (期望无 block 输出)"
```

### 6.6 必须在真实 CC 里验证的项 *(live,单测覆盖不到)*

1. **CC_TMUX_SESSION 传播 *(live)*:** 在 cc-tmux 驱动的 CC 里写一个 >8KB 文件,
   确认归档落到 `/tmp/cc-output/<tmux-session-name>/`(**不是** UUID、**不是** `unknown/`)。
   这是单测唯一覆盖不到的假设。
2. **PostToolUse 在交互模式触发 *(live)*:** 不只是 `claude -p`,交互式也要 fire。
3. **字段名一致 *(live)*:** `session_id` / `tool_response` / `tool_input.file_path`。
4. **Notification matcher *(live)*:** `idle_prompt|permission_prompt` 真能命中。
5. **Stop round-trip *(live)*:** `decision:block` + `reason` 能回喂;只在
   `cc-send.sh --expect <glob>` 在写的地方部署(否则它是安全 no-op)。

清理:`rm -rf /tmp/cc-output/smoke /tmp/cc-state-smoke.log /tmp/cc-heartbeat-smoke /tmp/cc-expect-smoke /tmp/smoke-* /tmp/cc-counter-stop-precheck-smoke.json`

---

## 7. 清理契约(已实现)

`cc-finish.sh` step 7(`--kill-session`)按 tmux session name 移除整套 per-session
文件:`cc-heartbeat-<s>`、`cc-state-<s>.log`、`cc-expect-<s>`、`cc-turn-done-<s>`、`cc-freeze-<s>`、`cc-watch-<s>.log`、
`cc-counter-stop-precheck-<s>.json`、`cc-output/<s>/`；watcher PID 由 cc-finish step7 `kill`。
覆盖。若 `CC_TMUX_SESSION` 当时没传播,hook 文件是 UUID-keyed 的,这里匹配不到 ——
属无害 miss,非错误。
