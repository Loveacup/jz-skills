# gates.mjs 使用手册

`scripts/gates.mjs` 是 STDD-OMP 的客观门控脚本，单一 ES module，纯 Node/Bun API，无 shell builtin。

## 设计目标

- **跨 OS**：同一份代码在 Windows / macOS / Linux 跑，结果一致。
- **双入口**：OMP 内优先用 `eval` js 导入；CI/外部可用 `node`/`bun` CLI。
- **单一权威源**：`DANGER_PATTERNS` 只存在 `gates.mjs`；hook 与文档均按当前文件内容复制/引用。

## 导出函数

```js
import {
  DANGER_PATTERNS,
  parseArgv,
  verifyArtifact,
  verifyTest,
  scanDanger,
  bumpCounter
} from 'skill://stdd-omp/scripts/gates.mjs';
```

| 函数 | 用途 | 返回 |
|---|---|---|
| `verifyArtifact(path)` | 文件存在且大小 > 0 | `{ok, code, size}` |
| `verifyTest(cmd, {shell=false})` | 运行用户 ② 验证命令；默认 `shell:false` 按 argv 拆分；`shell:true` 用于真管道 | `{ok, code, rawExit, signal, stdout, stderr}` |
| `scanDanger(text)` | 扫描危险模式 | `{ok, code, matches}` |
| `bumpCounter({key, kind, max, action})` | 计数器；`action`：`incr`/`reset`/`get` | `{ok, code, count, max}` |
| `parseArgv(str)` | 引号感知 argv 拆分；不解析反斜杠转义 | `string[]` |
| `DANGER_PATTERNS` | 危险模式数组（RegExp） | — |

## CLI 用法

```bash
# verify
node scripts/gates.mjs verify --artifact ./dist/app.js
node scripts/gates.mjs verify --test 'npm test'
node scripts/gates.mjs verify --test 'pytest tests/ -q'

# danger
node scripts/gates.mjs danger --command "rm -rf /tmp/x"
node scripts/gates.mjs danger --diff ./proposed.patch

# counter
node scripts/gates.mjs counter --key task-id --kind regen --max 3 --incr
node scripts/gates.mjs counter --key task-id --kind slice --max 2 --incr
node scripts/gates.mjs counter --key task-id --kind regen --reset
node scripts/gates.mjs counter --key task-id --kind regen --get
```

## 退出码

| 码 | 含义 |
|---|---|
| 0 | PASS / clean / 未超限 |
| 1 | FAIL（artifact 缺失/空，测试非 0 退出） |
| 10 | DANGER 命中 |
| 20 | COUNTER 超过硬顶 |

## 危险模式表（单一权威源）

以下数组必须与 `scripts/gates.mjs` 内 `DANGER_PATTERNS` **逐行一致**。

```js
[
  /rm\s+-\w*[rf]/i,
  /dd\s+if=/i,
  /mkfs/i,
  /\b(shutdown|reboot|halt|poweroff)\b/i,
  /\b(kill|pkill|killall)\b/i,
  /\/etc\/(passwd|shadow)|>\s*\/etc\//i,
  /\bgit\s+push\b/i,
  /\bgit\s+commit\b/i,
  /\b(npm|pnpm|yarn)\s+publish\b/i,
  /\bcargo\s+publish\b/i,
  /docker\s+.*\bpush\b/i,
  /(curl|wget)\b.*\|\s*(sh|bash)/i,
]
```

## Hook 安装（opt-in）

OMP hook 只能放在 **native lane** 的 `~/.omp/agent/hooks/pre/`。

> 注意：`~/.omp/agent/` 必须**存在且非空**（至少含 `config.yml` 或一个文件），否则 OMP 不会扫描 hooks/agents 子目录。

1. 确认目录存在：
   ```bash
   # Windows (PowerShell)
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\hooks\pre"
   # macOS/Linux
   mkdir -p ~/.omp/agent/hooks/pre
   ```
2. 复制 hook：
   ```bash
   cp assets/stdd-gate.hook.ts ~/.omp/agent/hooks/pre/stdd-gate.ts
   ```
3. 确保 `~/.omp/agent/` 根目录非空（已有 `config.yml` 即可）。
4. 新建 OMP session，尝试 `bash` 调用 `git push` → 应被 block，返回 `{block:true, reason:"STDD danger gate: ..."}`。

## 三级门控配置示例

在 `~/.omp/agent/config.yml` 或 `<cwd>/.omp/config.yml`：

```yaml
tools:
  approvalMode: write        # always-ask | write | yolo
  approval:
    bash: ask
    edit: ask
    write: ask
```

配合 hook，危险命令在 tool_call 层被拦截，**在任何 OS 都先于 shell 执行**。

## Cross-OS notes

- `eval` js 使用 OMP 内置 Bun VM，不依赖系统 PATH，是主入口。
- CLI fallback 需要系统 `node` 或 `bun` 在 PATH；Windows 上可用绝对路径调用（如 `C:\...\node.exe scripts\gates.mjs ...`）。
- 状态目录默认 `cwd/.stdd`；可用环境变量 `STDD_STATE_DIR` 覆盖。
- 所有路径内部使用 `path.join`；外部文档使用 `~`/`skill://`。
