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
- **班级群**: 三年级2班, cid=52993580719, 消息表 tbmsg_112

## 监控 cron

- **Job ID**: 458bec58ee72
- **调度**: 每 30 分钟
- **脚本**: `~/.hermes/scripts/dingtalk-class-monitor.sh` (v3: `-export-only -merged-out`, 不再启动 HTTP server, 无 hang 风险)
- **输出**: 
  - 每日文件 `~/.hermes/data/dingtalk_class_msgs/YYYY-MM-DD.txt`
  - 状态文件 `~/.hermes/data/dingtalk_class_msgs/.last_msg_id`
  - 有新消息时 stdout 推送通知

## dingwave 编译

```bash
git clone https://github.com/chiehw/dingwave.git /tmp/dingwave
cd /tmp/dingwave/frontend && pnpm install && pnpm build
cd /tmp/dingwave/server && go build -ldflags "-s -w" -trimpath -o ../dingwave .
cp dingwave ~/.local/bin/
```

## 解密命令（手动 — v3: 推荐 -export-only 模式）

```bash
DINGTALK_DIR=~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application\ Support/DingTalkMac/c42eb52018ab1e103951_v3
cp "$DINGTALK_DIR/DBFiles/dingtalk.db" /tmp/dd_enc.db
dingwave -d /tmp/dd_enc.db \
  -k "39510005" \
  -userconfig "$DINGTALK_DIR/user_config" \
  -merged-out /tmp/dd_merged.db \
  -export-only
# ✅ -export-only 解密完即退出，不启动 HTTP server。输出为合并后的 SQLite。
# 查询：sqlite3 /tmp/dd_merged.db "SELECT datetime(created_at/1000,'unixepoch','+8 hours'), content_json FROM messages WHERE cid='52993580719' LIMIT 5"
```

### 旧版 -o 模式（不推荐，会启 HTTP server）

```bash
dingwave -d db -k uid -userconfig cfg -o /tmp/dec.db
# ⚠️ 解密后自动启动 Web 服务器在 :8080, 需 kill 或 timeout。已弃用。
```

## 故障排查

| 症状 | 诊断 | 修复 |
|------|------|------|
| 每日文件停更 | 钉钉是否在运行? DB 文件大小是否变化? | 确保钉钉桌面版登录且前台运行 |
| 解密失败 | dingwave 是否还在? real_uid 是否变化? | 重新从 gaea.log 提取 real_uid |
| 消息表变更 | V3 格式可能变化 | 检查 tbmsg_* 表结构, 确认 cid 匹配 |
| dingwave 端口占用 | 解密后自动启动 8080 服务 | **v3 已修复**: 改用 `-export-only -merged-out`, 不再启动 HTTP server |

## auto-diary 集成

`collect_data.py` 的 `get_dingtalk_class_msgs()` 读取每日文件, 在 `collect_diary_data()` 中作为 `dingtalk_class_msgs` 字段返回。日记 LLM 应将其放入"临时笔记"或专门的"📬 钉钉班级群消息"章节。
