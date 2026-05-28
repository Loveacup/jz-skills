# CC Home & Sandbox — 完整排障指南

## 问题背景

Hermes 的 profile 机制使用 `HOME` 环境变量重定向来隔离各 profile 的配置与数据。
当 CC (Claude Code CLI) 从 Hermes 环境中启动时，继承了这个被修改的 HOME，
导致两个连锁问题：

1. **HOME override** → CC 找不到 OAuth token 和配置
2. **macOS TCC 沙箱** → CC 无法访问受保护的目录

这两个问题常同时出现，形成"沙箱+HOME 组合陷阱"。

---

## 问题 1：HOME override

### 症状

```bash
$ claude auth status --text
Not logged in. Run claude auth login to authenticate.

$ which claude
/opt/homebrew/bin/claude  # ✅ 二进制能找到

$ ls ~/.claude.json
ls: No such file or directory  # ❌ 因为 HOME 不是 /Users/alexcai
```

### 根因

Hermes 在运行时会设置 `HOME=~/.hermes/profiles/<profile>/home/`。
而 `claude auth login` 将 OAuth token 写入 `~/.claude.json`，这个 `~` 解析到的是 `/Users/alexcai/`（真实 HOME），不是 profile HOME。

### 修复方案

**方案 A：显式 HOME（临时，每次命令都需要）**
```bash
HOME=/Users/alexcai claude -p 'your prompt' --dangerously-skip-permissions
```

**方案 B：符号链接（部分有效，不推荐）**
```bash
# ⚠️ 已验证：symlink 对 CC auth 不完全生效
# CC 的 OAuth 验证可能拒绝跟随 symlink，导致 auth status 仍返回 Not logged in
# 虽然 ~/.claude.json 和 ~/.claude/ 的 symlink 创建成功，但 CC 内部路径解析
# 可能使用 realpath() 或其他机制绕过了 symlink
# 结论：优先使用方案 A（显式 HOME=），方案 B 仅作兜底尝试
PROFILE_HOME=~/.hermes/profiles/regent/home
ln -sf /Users/alexcai/.claude.json $PROFILE_HOME/.claude.json
ln -sfn /Users/alexcai/.claude $PROFILE_HOME/.claude
```

**方案 C：环境变量注入（用于 cron / launchd）**
```xml
<!-- 在 launchd plist 中添加 -->
<key>EnvironmentVariables</key>
<dict>
    <key>HOME</key>
    <string>/Users/alexcai</string>
</dict>
```

### 影响范围

不止 CC。所有从 Hermes 环境启动的子进程都受此影响：
- `hermes-a2a` 的 `launchctl` 命令需要显式 `HOME=/Users/alexcai`
- `terminal()` 工具调用中的 `claude` 命令
- `delegate_task` 中的子 agent
- A2A task handler 触发的 subprocess

---

## 问题 2：macOS TCC 沙箱

### 症状

```bash
$ claude -p 'read ~/Documents/obsidian-vault/note.md'
EPERM: operation not permitted, access '~/Documents/...'
```

### 根因

macOS 的 TCC (Transparency, Consent, and Control) 框架保护 `~/Documents/`、`~/Desktop/`、
`~/Downloads/` 等目录。CLI 工具需要用户在系统设置中显式授权才能访问这些目录。

### 修复方案

**一次性授权（永久解决）**：
系统设置 → 隐私与安全性 → 文件与文件夹 → 找到「终端」(Terminal.app) → 开启「文档文件夹」

**临时绕过（无需授权）**：
```bash
# 复制到非保护目录
cp ~/Documents/target-file.md /tmp/
# CC 操作 /tmp/ 中的文件
claude -p 'process /tmp/target-file.md'
# 完成后复制回去
cp /tmp/target-file.md ~/Documents/
```

### 影响范围

- 本机终端已授权 Documents 文件夹 → 大多数情况正常
- A2A 任务 / launchd 守护进程 → 可能未授权（取决于运行上下文）
- CI / cron → 几乎总是未授权

---

## 问题 3：组合陷阱

当 CC 同时遇到 HOME override 和 TCC 沙箱时：

1. HOME 指向 profile home → CC 找不到 auth → `Not logged in`
2. 即使解决了 auth（显式 HOME），TCC 仍阻止访问 Documents
3. 即使 TCC 已授权，profile HOME 下可能没有需要的文件

### 诊断步骤

```bash
# 1. 确认当前 HOME
echo $HOME

# 2. 确认 CC auth
HOME=/Users/alexcai claude auth status --text

# 3. 确认文件可访问性
ls -la <target-file>

# 4. 测试 TCC 沙箱
touch ~/Documents/.test_write 2>&1
```

### 一揽子修复

```bash
# 1. 符号链接 auth
ln -sf /Users/alexcai/.claude.json ~/.hermes/profiles/regent/home/.claude.json
ln -sf /Users/alexcai/.claude ~/.hermes/profiles/regent/home/.claude

# 2. 确认 TCC 授权（一次性，需手动操作）
# 系统设置 → 隐私与安全性 → 文件与文件夹 → 终端 → 开启「文档文件夹」

# 3. 如果 TCC 未授权，用 /tmp 中转
cp ~/Documents/target-file /tmp/
HOME=/Users/alexcai claude -p "process /tmp/target-file"
cp /tmp/target-file ~/Documents/
```

---

## 相关文档

- hermes-a2a skill：`CRITICAL: HOME override` 章节
- CC skill pitfall #6（TCC 沙箱）、#7（HOME override）、#18（组合陷阱）
