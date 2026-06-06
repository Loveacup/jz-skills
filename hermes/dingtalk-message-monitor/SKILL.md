---

name: dingtalk-message-monitor
description: Decrypt DingTalk's local encrypted SQLite database to read group messages, then set up automated polling and delivery. No admin permissions, no developer account needed. Use when the user wants AI to read/monitor DingTalk group chat messages (e.g., class group notifications).
type: routine
version: 1.1.0
platforms: [macos]
metadata:
  hermes:
    tags: [dingtalk, decrypt, sqlite, message-monitor, group-chat, school, class-group]
    related_skills: [web-research-router]

---

# DingTalk Message Monitor

> **核心洞察**: 钉钉桌面版把所有聊天记录加密存在本地 SQLite 里。解密后就能直接查 SQL，完全不需要企业管理员或开发者账号。

## 何时使用

- 用户想让 AI 读到钉钉群聊消息（如班级群通知、工作群消息）
- 用户问"怎么读钉钉消息"、"帮我监控钉钉群"
- 注意：用户的需求通常很具体（如"读小朋友班级群"），先问清楚目标群，不要泛泛地"连接钉钉"

## 整体流程

```
钉钉桌面版登录运行 → 本地加密 SQLite → dingwave 解密 → SQL 查询 → 定时推送
```

**前置条件**: 本机安装钉钉桌面版并保持登录运行。

## 步骤

### 1. 编译 dingwave

```bash
git clone https://github.com/chiehw/dingwave.git /tmp/dingwave
cd /tmp/dingwave/frontend && pnpm install && pnpm approve-builds && pnpm build
cd /tmp/dingwave/server && go build -ldflags "-s -w" -trimpath -o ../dingwave .
cp /tmp/dingwave/dingwave ~/.local/bin/
```

需要 Go、Node、pnpm。

### 2. 定位数据库 (macOS)

```bash
# 找 V3 数据目录
find ~/Library/Containers -path "*DingTalkMac" -name "*_v3" -type d

# 典型路径
DINGTALK_DIR=~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application\ Support/DingTalkMac/{id}_v3
DB="$DINGTALK_DIR/DBFiles/dingtalk.db"
USER_CONFIG="$DINGTALK_DIR/user_config"
```

### 3. 提取解密密钥

**real_uid**: 从 gaea 日志中找
```bash
grep "real_uid" "$DINGTALK_DIR/../log/gaea.log.*" | tail -1
# 输出如: real_uid=39510005@dingding
```

**salt**: user_config 是 Base64 编码的 JSON
```bash
base64 -d "$USER_CONFIG"  # {"salt": "fc8f2810...", "salt_md5": "d05e1ac9..."}
```

### 4. 解密数据库 (含 WAL checkpoint)

钉钉使用 SQLite WAL (Write-Ahead Log) 模式 — 新消息先写入 `dingtalk.db-wal` 日志文件，不会实时合并进主数据库 `dingtalk.db`。**不合并 WAL 就解密 = 只能读到 N 小时前的旧数据。**

```bash
# 先拷贝（防止原库被占用导致锁定）+ WAL + SHM
cp "$DB" /tmp/dingtalk_enc.db
cp "${DB}-wal" /tmp/dingtalk_enc.db-wal
cp "${DB}-shm" /tmp/dingtalk_enc.db-shm 2>/dev/null

# 强制 WAL checkpoint — 合并最近写入到主数据库
# sqlite3 会报错 "file is not a database"（钉钉加密了页面），
# 但文件级合并仍会成功（WAL 文件缩小到 0 字节）
sqlite3 /tmp/dingtalk_enc.db "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
rm -f /tmp/dingtalk_enc.db-wal /tmp/dingtalk_enc.db-shm

# 解密为合并格式
~/.local/bin/dingwave -d /tmp/dingtalk_enc.db \
  -k "39510005" \
  -userconfig "$USER_CONFIG" \
  -merged-out /tmp/dingtalk_plain.db \
  -export-only
```

> **关键**:
> - `-k` 只用数字部分（如 `39510005`），不含 `@dingding` 后缀。含后缀会导致解密失败。
> - **必须用 `-export-only` + `-merged-out`**，不要用 `-o`。`-o` 模式会启动 HTTP server 导致进程挂起不退出，cron 场景下必超时。
> - `-merged-out` 输出统一的 `messages` 表（含 `cid`, `created_at`, `content_json` 列），比旧版分片表 `tbmsg_NNN` 更容易查询。

### 5. 查找目标群聊

```sql
-- 列出所有群（type=2）
SELECT cid, title FROM conversations WHERE type=2 ORDER BY title;

-- 含关键词搜索
SELECT cid, title FROM conversations WHERE type=2 AND title LIKE '%班%';
```

### 6. 查消息

合并库使用统一的 `messages` 表，直接按 cid 查询：

```sql
SELECT datetime(created_at/1000, 'unixepoch', '+8 hours') as time,
       content_json
FROM messages
WHERE cid='52993580719'
ORDER BY created_at DESC
LIMIT 20;
```

消息内容在 `content_json` 字段的 JSON 中。关键提取路径：
- 文本: `attachments[0].extension.desc`
- 富文本: `attachments[0].extension.payloadV2.contents[0].text.items[].data.text`
- 图片: `attachments[0].extension.payloadV2.contents[].data.url`

### 7. 设置定时监控

脚本模板见 `scripts/dingtalk-class-monitor.sh`。推荐配置：

```bash
cronjob action=create \
  name="DingTalk 班级群消息监控" \
  schedule="every 5m" \
  script="dingtalk-class-monitor.sh" \
  no_agent=true
```

`no_agent=true` 意味着脚本的 stdout 直接作为消息推送，零 token 消耗。脚本在没有新消息时静默退出（exit 0 无输出）。**推荐 5 分钟间隔**：dingwave 解密+WALcheckpoint 约 5–8 秒，5 分钟频率完全无压力。

## 数据库表结构参考（合并格式 -merged-out）

| 表 | 用途 |
|---|---|
| `conversations` | 会话列表（type=1 单聊, type=2 群聊） |
| `messages` | 统一消息表（含 `cid`, `created_at`, `content_json`） |
| `users` | 用户资料 |

消息表关键列: `cid`, `mid`, `sender_id`, `content_type`, `content_json`, `created_at` (Unix ms), `recall_status`

## 备选方案：dws CLI（需要开发者账号）

如果用户有钉钉开发者账号，dws CLI 更强大（330+ 命令，实时读写）。安装和认证：

```bash
curl -fsSL https://raw.githubusercontent.com/DingTalk-Real-AI/dingtalk-workspace-cli/main/scripts/install.sh | sh
dws auth login --client-id <AppKey> --client-secret <AppSecret>
dws chat message list --conversation-id <cid>
```

但需要：在 open-dev.dingtalk.com 创建应用 → 获取 AppKey/AppSecret。对学校等组织可能无法通过审批。此时本 skill 的本地解密方案是唯一可行路径。

## 实时方案对比

关于替代方案（Stream Mode、RPA、企业事件订阅）的完整调研和对比，见 `references/alternative-approaches.md`。核心结论：**dingwave 本地解密是目前唯一能被动监听全部群消息的方案**。Stream Mode 机器人实时但只能收 @消息，RPA 脆弱，企业订阅需要管理员。

## 常见坑

- **数据库 4KB**: 钉钉刚装，数据未同步。等客户端运行几分钟再试。
- **解密后空库**: `-k` 用了完整 `real_uid@dingding`，应该只用数字部分。
- **原库被锁定**: 必须先 `cp` 再解密，不要直接对原库操作。
- **消息内容乱码**: content 字段是嵌套 JSON，需要多层解析。简单文本可用 `attachments[0].extension.desc`。
- **WAL 未合并导致数据滞后数小时**: 钉钉使用 SQLite WAL 模式，新消息写入 `dingtalk.db-wal` 但不自动合并到 `dingtalk.db`。**症状**: `dingtalk.db` 修改时间停留在 N 小时前，但 `dingtalk.db-wal` 持续更新。新消息解密后查不到。**修法**: 复制 DB 时同时复制 `.db-wal` 和 `.db-shm`，`sqlite3` 跑 `PRAGMA wal_checkpoint(TRUNCATE)` 后再解密。即使报 "not a database" 错误，文件级合并仍成功。
- **V2 vs V3**: V3 目录名形如 `{hex}_v3`，V2 形如 `{纯数字}_v2`。V3 需要 user_config 提供 salt，V2 直接用目录名数字 uid 做密钥。
- **macOS TCC 沙箱拦截**: 访问 `~/Library/Containers/...DingTalkMac...` 路径时，macOS 可能弹出 TCC 权限对话框。如果无人点击（cron 后台场景），所有对该目录的文件操作（`cp`、`cat`、`ls`、dingwave 内部文件读取）都会挂死，直到超时。**症状**: dingwave 进程卡住不动、脚本 120s 超时、文件操作无响应。**修法**: 系统设置 → 隐私与安全性 → 完全磁盘访问权限，添加 Terminal.app 和 Hermes 相关进程。验证：手动 `ls` 该目录文件不挂即修复。
