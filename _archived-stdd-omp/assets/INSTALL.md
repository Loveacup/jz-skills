# STDD-OMP 安装指南（Cross-OS）

本 skill 默认安装在 **agents lane**：`~/.agents/skills/stdd-omp/`。
如需 profile 隔离，可改用 **native lane**：`~/.omp/agent/skills/stdd-omp/`。

## 首次接入：按需体检

只有首次接入、新 session 需要可执行集成、版本变化或集成报错时才跑体检；简单 L1 不需要。

```bash
# 只读体检
node scripts/setup.mjs --status

# 写入安装；仅在用户明确授权安装这些组件后执行
node scripts/setup.mjs --apply
```

```bash
# 自定义（示例）
node scripts/setup.mjs --apply \
  --with-hook \
  --with-auditor \
  --with-rules \
  --with-watchdog \
  --approval-mode yolo \
  --github-repo Loveacup/jz-skills
```

setup 脚本可检测 OMP/skill 版本、安装位置、opt-in hook/auditor/rules/WATCHDOG 与建议配置。`--status` 只读；`--apply` 会写入用户目录，不能由检测结果、full-auto 或普通任务授权自动触发。

> setup 不直接修改 `~/.omp/agent/config.yml`，但生成配置、安装组件、升级、登录或凭据动作仍需各自明确授权。配置事实以当前版本 `omp --help` 和 schema 为准。

## Orchestrator 诊断

仅在需要诊断可执行集成时运行：

```bash
node scripts/orchestrate.mjs
```

输出中的 `actions` 是建议，不是执行授权：

- `sync-version`：显式远程检查发现版本差异；
- `warning`：native agent 路径或输入异常；
- opt-in 组件状态：仅用于判断当前任务所需能力是否可用。

写入命令必须单独获授权：

```bash
node scripts/orchestrate.mjs --install --dry-run
node scripts/orchestrate.mjs --install
node scripts/orchestrate.mjs --install --with-hook
node scripts/orchestrate.mjs --install --with-hook --force
```

`--force` 可能覆盖已有文件，应作为高风险动作。检测、L3/full-auto 或“推荐配置”都不隐含 install/upgrade/config/auth 权限。

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

Optionally, install the hook manually:

```bash
# Windows PowerShell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\hooks\pre"
copy assets\stdd-gate.hook.ts "$env:USERPROFILE\.omp\agent\hooks\pre\stdd-gate.ts"

# macOS/Linux
mkdir -p ~/.omp/agent/hooks/pre
cp assets/stdd-gate.hook.ts ~/.omp/agent/hooks/pre/stdd-gate.ts
```

不要用真实 `git push` 验证 hook。使用 `gates.mjs scanDanger` 或明确的 dry-run/模拟输入验证拦截逻辑。

### 2. 独立 auditor agent（可选增强）

先读取当前 runtime 的 agent roster；按只读审计能力选择，不假定任何内置名称存在。只有在已明确授权安装自定义 agent 时，才复制模板：

```bash
# Windows PowerShell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.omp\agent\agents"
copy assets\stdd-auditor.agent.md "$env:USERPROFILE\.omp\agent\agents\stdd-auditor.md"

# macOS/Linux
mkdir -p ~/.omp/agent/agents
cp assets/stdd-auditor.agent.md ~/.omp/agent/agents/stdd-auditor.md
```

安装后重新读取 runtime roster，确认实际名称可解析且 agent 对被审对象无 `edit`/`write` 能力。L3 所需 auditor 能力不可用时应 BLOCKED，而不是猜名称。

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

### 4. WATCHDOG（Advisor 增强，v3 委员会 + 单 advisor 回退）

**16.2.3+（推荐）**：复制 v3 多 advisor 委员会到 Advisor 可发现位置：

```bash
# 用户级（全局生效）
# Windows PowerShell
copy assets\WATCHDOG.yml "$env:USERPROFILE\.omp\agent\WATCHDOG.yml"
# macOS/Linux
cp assets/WATCHDOG.yml ~/.omp/agent/WATCHDOG.yml

# 项目级（仅当前仓库）
New-Item -ItemType Directory -Force ".\.omp"    # Windows
copy assets\WATCHDOG.yml .\.omp\WATCHDOG.yml    # Windows

mkdir -p ./.omp                                 # macOS/Linux
cp assets/WATCHDOG.yml .omp/WATCHDOG.yml          # macOS/Linux
```

校验：`/advisor configure` TUI 确认 Reviewer + Claim Verify 两个 advisor 已加载。

**≤16.2.2（回退）**：复制单 `WATCHDOG.md`：

```bash
# 用户级
cp assets/WATCHDOG.md ~/.omp/agent/WATCHDOG.md
# 项目级
cp assets/WATCHDOG.md .omp/WATCHDOG.md
```

启用 Advisor（`~/.omp/agent/config.yml`）：

其中 `advisor` 角色需要：批判性分析、客观判断、细节审查。

```yaml
modelRoles:
  advisor: <批判审查>

advisor:
  enabled: true
  subagents: false     # 防多模型 fan-out 审查风暴
  syncBacklog: 3       # 控频降本（默认 3）
```

验证：新 session 中 `/advisor status` 显示活跃模型；`/advisor dump` 可导出审查结果。故意违反 P1/P2/P3/P4/P6 时 Advisor 应给出 concern/blocker。

### 5. 三梁模板复制到项目

将 `assets/three-beams/beam1-requirements.md`、`beam2-implementation.md`、`beam3-control.md` 复制到项目根目录的 `.stdd/` 或 `docs/` 下并填内容。它们不是 skill 激活所必需，而是项目级脚手架。


## 推荐 OMP 配置

```yaml
memory:
  backend: local

tools:
  approvalMode: yolo        # always-ask | write | yolo
  approval:
    bash: allow
    edit: allow
    write: allow
```

> 对 `config.yml`、modelRoles、API keys、search providers、profiles 等 OMP 配置有疑问，以当前安装版本的 `omp --help` 与版本匹配的官方文档为准。stdd-omp 只给出与 STDD 流程相关的最小推荐值；密钥使用 `/login`、环境变量或凭据存储。

## 如何确认已生效

| 组件 | 验证动作 | 期望结果 |
|---|---|---|
| skill 发现 | 明确请求“使用 STDD” | 模型引用 `stdd-omp`；泛词不误触发 |
| gates.mjs | 导入 `verifyArtifact` / `verifyTest` / `scanDanger` / `bumpCounter` | 返回预期结构/exit code |
| hook | 向 `scanDanger` 或 hook 测试入口提供模拟危险文本 | 拦截；不执行真实 push/publish |
| auditor | 从当前 runtime roster 选择只读审计能力 | 实际名称可解析，只读输出 |
| L 档 | L1 内联；L2 fresh context；L3 independent auditor | 行为与档位一致 |

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
OMP (local)   : 16.2.3
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

- **OMP 16.2.3+**：`WATCHDOG.yml` 多 advisor 委员会已落地（推荐）；≤16.2.2 用单 `WATCHDOG.md` 回退。
- **OMP 16.2.2+**：新增 `tiny` modelRole（更轻量、更低成本任务）。
- **OMP 16.2.0+**：`search` 工具重命名为 `grep`，`find` 工具重命名为 `glob`。本 skill 的文档/模板已按新名称更新；如果你仍在使用 16.1.x，请把文档中的 `grep` 读作 `search`、`glob` 读作 `find`。
- **OMP 16.1.16+**：`todo` 工具改为每次只接受一个 op（本 skill 已遵守）。
- **OMP 16.1.16+**：`bash` 工具被限制不能做 `ls`/`find`（与 skill 的"专用工具优先"原则一致）。
若后续 OMP 行为变化导致 skill 建议失效，优先在 `references/advanced-omp-wiring.md` 和本安装指南中补充兼容说明，而不是改 SKILL.md 核心指令。
