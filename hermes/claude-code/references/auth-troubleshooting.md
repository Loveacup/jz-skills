# CC Auth Troubleshooting — 401 系统性排查

> 触发：CC 返回 `⏺ Please run /login · API Error: 401 Invalid authentication credentials`

## 五步排查法（2026-06-11 实战验证）

### Step 1：确认 auth 状态

```bash
HOME=~ claude auth status
```

关注 `loggedIn` 字段。**注意：`loggedIn: true` 不代表 API 调用可用**——auth status 可能读缓存，API 层凭证可能独立过期。

### Step 2：print mode 隔离 tmux

```bash
HOME=~ claude -p "reply 'OK'" --model claude-opus-4-8
```

- 成功 → 问题在 tmux/pty 层
- 同样 401 → 凭证问题，继续排查

### Step 3：检查 HOME 劫持

```bash
# 不带 HOME override 试
claude --version
# 若报 "no installed version found in ~/.hermes/profiles/..."
# → 确认是 HOME 劫持，需要 HOME=~
```

同时检查 `.claude/` 的 symlink 状态：
```bash
ls -la ~/.hermes/profiles/regent/home/.claude
# 应该是 → ~/.claude 的 symlink
```

### Step 4：检查凭证文件

```bash
ls ~/.claude/auth* ~/.claude/credentials*
```

v2.1+ 凭证可能存 Keychain 而非文件，文件缺失属正常。

### Step 5：重新认证

```bash
HOME=~ claude auth logout
HOME=~ claude auth login    # 需浏览器，headless 终端无法完成
```

⚠️ `claude /login` 在某些环境下不可用（"isn't available in this environment"），需用 `claude auth login`。

## 常见误判

| 误判 | 实际 |
|------|------|
| "HOME 劫持导致 401" | HOME 劫持会导致 binary not found，但 401 是凭证过期，与 HOME 无关 |
| "Fable 5 不让用" | Fable 5 和 Opus 4.8 同报 401 → 确认是通用凭证问题，非模型限制 |
| "auth status 说已登录就该能用" | auth status 可能读缓存，API 层 token 独立过期 |

## Fable 5 模型信息

- 模型 flag：`--model claude-fable-5`
- 可用性：Claude Max 订阅包含，限时免费至 2026-06-22
- banner 文本："Fable 5 is here! Our newest model for complex, long-running work"
- 2026-06-11 实测：可正常启动（显示 banner），但 401 阻止了实际 API 调用（凭证问题，非模型问题）
