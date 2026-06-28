# STDD-OMP 安装指南（Cross-OS）

本 skill 默认安装在 **agents lane**：`~/.agents/skills/stdd-omp/`。
如需 profile 隔离，可改用 **native lane**：`~/.omp/agent/skills/stdd-omp/`。

## 首次使用：快速配置

安装 skill 后，先跑一次 setup 脚本做「体检 + 生成配置」：

```bash
# 只读体检：看当前环境缺哪些组件、OMP 版本是否兼容
node scripts/setup.mjs

# 一键应用推荐配置（安装 hook/auditor/rules/WATCHDOG 并写入 ~/.stdd/config.json）
node scripts/setup.mjs --apply

# 自定义（示例）
node scripts/setup.mjs --apply \
  --with-hook \
  --with-auditor \
  --with-rules \
  --with-watchdog \
  --approval-mode write \
  --github-repo Loveacup/jz-skills
```

setup 脚本会：

1. 检测 OMP 版本、`~/.agents/skills/stdd-omp/` 或 `~/.omp/agent/skills/stdd-omp/` 安装位置。
2. 检查 opt-in 组件是否已安装：hook、auditor、rules、WATCHDOG。
3. 检查 `~/.omp/agent/config.yml` 中 `memory.backend`、`modelRoles`、`tools.approvalMode`、`task.isolation`、`task.async` 等关键项。
4. 生成 `~/.stdd/config.json`（用户偏好与版本源）。
5. `--apply` 时把缺失的 opt-in 组件复制到 `~/.omp/agent/` 下；**不会覆盖已有文件**（除非加 `--force`）。
6. 打印人类可读的体检报告和下一步建议。

> setup 脚本本身不会改 `~/.omp/agent/config.yml`。如果检测到你还没配 `memory.backend: local` 等关键项，它会打印一段推荐 YAML，让你手动合并或调用 **`/skill:omp-ops`** 协助配置。

## 自动检测 / 安装模式（推荐先跑）

skill 加载后，先运行 orchestrator 做只读检测：

```bash
node scripts/orchestrate.mjs
```

输出 JSON 含 `actions`：

- `install-hook`：建议安装的 opt-in 危险命令 hook 未安装
- `sync-version`：本地版本落后于 GitHub（需配置 `STDD_OMP_GITHUB_REPO`）
- `warning`：native agent 根目录（默认 `~/.omp/agent/`，可被 `PI_CODING_AGENT_DIR` / `PI_CONFIG_DIR` 覆盖）为空或不存在

两阶段纪律：

1. **status**：只读，不写文件。
2. **install**：用户确认后执行：

   ```bash
   # 先看会装什么
   node scripts/orchestrate.mjs --install --dry-run
   # 确认后安装缺失项（不覆盖已有）
   node scripts/orchestrate.mjs --install
   # 强制覆盖
   node scripts/orchestrate.mjs --install --force
   ```

配置 GitHub 仓库源（可选）：

```bash
export STDD_OMP_GITHUB_REPO=Loveacup/jz-skills
# 或完整 URL
export STDD_OMP_GITHUB_REPO=https://github.com/Loveacup/jz-skills
```

## 路径约定

- `~` 在 OMP 内按 OS 解析：
  - Windows: `%USERPROFILE%`，如 `C:\Users\<user>`
  - macOS/Linux: `$HOME`，如 `/Users/<user>` 或 `/home/<user>`
- `skill://stdd-omp/...` 指向 skill 根目录，跨 OS 有效。

## 方式 A：agents lane（默认，推荐）

```bash
# 仅复制 skill 目录；hook/auditor 仍需 native lane（见下方 opt-in）
cp -r stdd-omp ~/.agents/skills/
```

确保 OMP 启用 agents provider：

```yaml
skills:
  enableAgentsUser: true     # 或 enableAgentsProject: true（项目级）
```

验证：新 OMP session 中模型应能识别 `stdd-omp`；`read skill://stdd-omp/SKILL.md` 可返回内容。

## 方式 B：native lane（profile 隔离）

```bash
# Windows PowerShell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\skills"
copy stdd-omp "$env:USERPROFILE\.omp\agent\skills\stdd-omp" -Recurse -Force

# macOS/Linux
mkdir -p ~/.omp/agent/skills
cp -r stdd-omp ~/.omp/agent/skills/
```

启用 profile：

```bash
omp --profile stdd
# 或设置环境变量 OMP_PROFILE=stdd
```

此时 `~/.omp/agent/skills/stdd-omp/` 会整体迁移到 `~/.omp/profiles/stdd/agent/skills/stdd-omp/`。

## Opt-in 增强（非自动激活）

### 1. 危险命令 hook

> 前提：`~/.omp/agent/` 必须**存在且非空**（至少含 `config.yml` 或一个文件），否则 OMP 不会扫描 `hooks/` 子目录。

```bash
# Windows PowerShell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\hooks\pre"
copy assets\stdd-gate.hook.ts "$env:USERPROFILE\.omp\agent\hooks\pre\stdd-gate.ts"

# macOS/Linux
mkdir -p ~/.omp/agent/hooks/pre
cp assets/stdd-gate.hook.ts ~/.omp/agent/hooks/pre/stdd-gate.ts
```

重启 OMP session，尝试 `bash` 调用 `git push` → 应被 `{block:true}` 拦截。

### 2. 独立 auditor agent（可选增强）

默认 auditor 使用 OMP 内置 `reviewer` 或 `oracle`。若想用一个只审不改的自定义角色，可手动安装：

```bash
# Windows PowerShell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\agents"
copy assets\stdd-auditor.agent.md "$env:USERPROFILE\.omp\agent\agents\stdd-auditor.md"

# macOS/Linux
mkdir -p ~/.omp/agent/agents
cp assets/stdd-auditor.agent.md ~/.omp/agent/agents/stdd-auditor.md
```

验证：`task` 中 `agent:stdd-auditor` 能解析，且该 agent 不调用 `edit`/`write`。

### 3. STDD 规则模板（Rules）

本 skill 提供 `assets/stdd-rules/*.md`，按本机已验证的 `alwaysApply` 系统规则格式编写。要生效，需复制到 OMP 规则目录：

```bash
# Windows PowerShell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\rules"
copy assets\stdd-rules\*.md "$env:USERPROFILE\.omp\agent\rules\"

# macOS/Linux
mkdir -p ~/.omp/agent/rules
cp assets/stdd-rules/*.md ~/.omp/agent/rules/
```

> 本机 `~/.omp/agent/rules/omp-identity.md` 确认了该目录有效；`event`/`pattern`/`action` 等 TTSR stream 触发 schema 请先本地验证再使用。

### 4. WATCHDOG.md（Advisor 增强）

将 `assets/WATCHDOG.md` 复制到 Advisor 可发现位置之一：

```bash
# 用户级（全局生效）
# Windows PowerShell
copy assets\WATCHDOG.md "$env:USERPROFILE\.omp\agent\WATCHDOG.md"
# macOS/Linux
cp assets/WATCHDOG.md ~/.omp/agent/WATCHDOG.md

# 项目级（仅当前仓库）
New-Item -ItemType Directory -Force ".\.omp"    # Windows
copy assets\WATCHDOG.md .\.omp\WATCHDOG.md    # Windows

mkdir -p ./.omp                                 # macOS/Linux
cp assets/WATCHDOG.md .omp/WATCHDOG.md          # macOS/Linux
```

启用 Advisor（`~/.omp/agent/config.yml`）：

```yaml
modelRoles:
  advisor: anthropic/claude-sonnet-4-5:medium

advisor:
  enabled: true
  syncBacklog: 1
  subagents: true
```

验证：新 session 中 `/advisor status` 显示活跃模型；故意违反 P1/P2/P3/P4/P6 时 Advisor 应给出 concern/blocker。

### 5. 三梁模板复制到项目

将 `assets/three-beams/*.md` 复制到项目根目录的 `.stdd/` 或 `docs/` 下并填内容。它们不是 skill 激活所必需，而是项目级脚手架。

## 推荐 OMP 配置

```yaml
memory:
  backend: local

tools:
  approvalMode: write       # always-ask | write | yolo
  approval:
    bash: ask
    edit: ask
    write: ask
```

> 对 `config.yml`、modelRoles、API keys、search providers、profiles 等 OMP 配置有疑问，调用 **`/skill:omp-ops`**。stdd-omp 只给出与 STDD 流程相关的最小推荐值，具体 provider/key/profile 配置让 omp-ops 处理。

## 如何确认已生效

| 组件 | 验证动作 | 期望结果 |
|---|---|---|
| skill 发现 | 新 session 触发 `STDD` 关键词 | 模型引用 `stdd-omp` |
| gates.mjs | `eval` js 导入 `verifyArtifact` / `verifyTest` | 返回预期 code |
| hook | `bash git push` | `{block:true, reason:"STDD danger gate: ..."}` |
| auditor | `task agent:reviewer` / `oracle`（默认）；可选 `stdd-auditor` | 解析成功，只读输出 |
| memory | 任务全过后调用 recall/retain | 能读到历史经验 |

## 故障排查

- `skill` 未被发现：检查 agents provider 是否启用，或切换到 native lane。
- hook 未生效：确认 `~/.omp/agent/` 根目录非空；hook 文件后缀为 `.ts` 且位于 `hooks/pre/`。
- auditor 未找到：确认文件在 `~/.omp/agent/agents/` 且 frontmatter 含 `name: stdd-auditor`。
- Windows 路径报错：使用 `path.join` 的 API；避免在 `--test` 参数中直接传未加引号的 Windows 路径。

## 版本检查与手动升级

提供两个检查入口：

### 快速检查

```bash
node scripts/check-version.mjs --repo Loveacup/jz-skills
```

输出示例：

```text
STDD-OMP version check
======================
Skill (local) : 0.1.2
GitHub repo   : Loveacup/jz-skills
GitHub latest : 0.2.0
Sync status   : behind
OMP (local)   : 16.2.0
OMP required  : >=16.1.16
OMP compatible: yes

Action: local skill is behind remote; run `git pull` or re-install from GitHub.
```

退出码：

| 退出码 | 含义 |
|---|---|
| 0 | 全部正常 |
| 1 | 运行时错误 |
| 2 | skill 本地版本落后于 GitHub |
| 3 | 本地 OMP 版本不满足 `references/OMP_COMPATIBILITY` |

### orchestrator 综合检查

```bash
node scripts/orchestrate.mjs --repo Loveacup/jz-skills
```

除版本外，还会检测 hook/auditor 安装状态和 OMP 兼容性，返回 JSON。

## 版本兼容性

- `references/VERSION`：skill 自身版本。
- `references/OMP_COMPATIBILITY`：skill 所需的最低/兼容 OMP 版本（如 `>=16.1.16`）。

OMP 迭代很快。stdd-omp 本身是**被动知识包**，不随 OMP 升级而改变本地文件；只有当你主动启用 opt-in 组件时才落盘。

已知影响较大的变更：

- **OMP 16.2.0+**：`search` 工具重命名为 `grep`，`find` 工具重命名为 `glob`。本 skill 的文档/模板已按新名称更新；如果你仍在使用 16.1.x，请把文档中的 `grep` 读作 `search`、`glob` 读作 `find`。
- **OMP 16.1.16+**：`todo` 工具改为每次只接受一个 op（本 skill 已遵守）。
- **OMP 16.1.16+**：`bash` 工具被限制不能做 `ls`/`find`（与 skill 的“专用工具优先”原则一致）。

若后续 OMP 行为变化导致 skill 建议失效，优先在 `references/advanced-omp-wiring.md` 和本安装指南中补充兼容说明，而不是改 SKILL.md 核心指令。
