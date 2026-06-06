# DingTalk 班级群消息采集

## 概述

通过 dingwave 解密钉钉桌面端本地加密 SQLite 数据库，提取班级群消息，供 auto-diary 日记系统采集。

## 架构

```
钉钉桌面端 (macOS) → 加密 SQLite (dingtalk.db)
    ↓ dingwave 解密 (每30分钟 cron)
明文消息 → 每日文件 ~/.hermes/data/dingtalk_class_msgs/YYYY-MM-DD.txt
    ↓ collect_data.py 采集 (每天23:00 diary cron)
写入日记 Obsidian/50-Self/01_日记/
```

## 环境

- **平台**: macOS
- **钉钉路径**: `~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application Support/DingTalkMac/c42eb52018ab1e103951_v3/`
- **加密DB**: `DBFiles/dingtalk.db` (AES-256-CBC, V3 格式)
- **解密工具**: dingwave (`~/.local/bin/dingwave`, 源码 `https://github.com/chiehw/dingwave`)
- **解密密钥**: real_uid=39510005, salt 从同目录 `user_config` 文件 base64 解码获取
- **班级群**: 三年级2班, cid=52993580719, 消息表 messages（-merged-out 统一格式）

## 监控 cron

- **Job ID**: 458bec58ee72
- **调度**: 每 20 分钟（`every 20m`）
- **脚本**: `~/.hermes/scripts/dingtalk-class-monitor.sh` (v4: WAL checkpoint + `-export-only -merged-out`，无 hang 风险，无数据滞后)
- **输出**: 
  - 每日文件 `~/.hermes/data/dingtalk_class_msgs/YYYY-MM-DD.txt`
  - 状态文件 `~/.hermes/data/dingtalk_class_msgs/.last_msg_id`
  - 有新消息时 stdout 推送通知（`no_agent=true`，零 token）

## 完整技能文档

详见 `social-media/dingtalk-message-monitor` skill（解密、WAL 合并、表结构、实时方案对比、常见坑）。

## dingwave 编译

```bash
git clone https://github.com/chiehw/dingwave.git /tmp/dingwave
cd /tmp/dingwave/frontend && pnpm install && pnpm build
cd /tmp/dingwave/server && go build -ldflags "-s -w" -trimpath -o ../dingwave .
cp dingwave ~/.local/bin/
```

## 解密命令（手动 — v3 + WAL checkpoint）

钉钉使用 SQLite WAL (Write-Ahead Log) 模式，**新消息先写入 `dingtalk.db-wal`，不实时合并进主 DB**。
必须先做 WAL checkpoint 再解密，否则只能读到 N 小时前的旧数据。

```bash
DINGTALK_DIR="~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application Support/DingTalkMac/c42eb52018ab1e103951_v3"

# 1. 复制主DB + WAL + SHM
cp "$DINGTALK_DIR/DBFiles/dingtalk.db" /tmp/dd_enc.db
cp "$DINGTALK_DIR/DBFiles/dingtalk.db-wal" /tmp/dd_enc.db-wal
cp "$DINGTALK_DIR/DBFiles/dingtalk.db-shm" /tmp/dd_enc.db-shm

# 2. WAL checkpoint（强制合并最新写入；即使报 "not a database" 错误也成功）
sqlite3 /tmp/dd_enc.db "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
rm -f /tmp/dd_enc.db-wal /tmp/dd_enc.db-shm

# 3. 解密
dingwave -d /tmp/dd_enc.db \
  -k "39510005" \
  -userconfig "$DINGTALK_DIR/user_config" \
  -merged-out /tmp/dd_merged.db \
  -export-only
# ✅ -export-only 解密完即退出，不启动 HTTP server。输出为合并后的 SQLite。
# 查询：sqlite3 /tmp/dd_merged.db "SELECT datetime(created_at/1000,'unixepoch','+8 hours'), content_json FROM messages WHERE cid='52993580719' ORDER BY created_at DESC LIMIT 5"
```

## 故障排查

| 症状 | 诊断 | 修复 |
|------|------|------|
| 每日文件停更 | 钉钉是否在运行? DB 文件大小是否变化? | 确保钉钉桌面版登录且前台运行 |
| 解密后只有 N 小时前旧消息 | `dingtalk.db` 修改时间冻结但 `dingtalk.db-wal` 持续更新 → WAL 未合并 | 解密前先复制 WAL+SHM，`sqlite3` 跑 `PRAGMA wal_checkpoint(TRUNCATE)`（详见上方解密命令） |
| dingwave 挂死/120s 超时 | macOS TCC 沙箱拦截容器目录访问 | 系统设置→隐私→完全磁盘访问权限，添加 Terminal+Hermes |
| 解密失败 | dingwave 是否还在? real_uid 是否变化? | 重新从 gaea.log 提取 real_uid |
| dingwave 端口占用 | 解密后自动启动 8080 服务 | **v3 已修复**: 改用 `-export-only -merged-out`，不再启动 HTTP server |

## auto-diary 集成

`collect_data.py` 的 `get_dingtalk_class_msgs()` 读取每日文件, 在 `collect_diary_data()` 中作为 `dingtalk_class_msgs` 字段返回。日记 LLM 应将其放入"临时笔记"或专门的"📬 钉钉班级群消息"章节。
