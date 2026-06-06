#!/bin/bash
# 钉钉班级群消息监控 v3 — 用 dingwave -export-only 避免 HTTP server 挂起
set -euo pipefail

DINGTALK_DIR="/Users/alexcai/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application Support/DingTalkMac/c42eb52018ab1e103951_v3"
ENCRYPTED_DB="$DINGTALK_DIR/DBFiles/dingtalk.db"
USER_CONFIG="$DINGTALK_DIR/user_config"
REAL_UID="39510005"
CLASS_CID="52993580719"

STATE_FILE="$HOME/.hermes/data/dingtalk_class_msgs/.last_msg_id"
DAILY_DIR="$HOME/.hermes/data/dingtalk_class_msgs"

TMP_ENC="/tmp/dd_enc_$$.db"
TMP_MERGED="/tmp/dd_merged_$$.db"
DATE=$(date +%Y-%m-%d)
DAILY_FILE="$DAILY_DIR/$DATE.txt"

mkdir -p "$DAILY_DIR"

[ -f "$ENCRYPTED_DB" ] || exit 0

# Step 1: Copy DB + WAL + SHM, merge WAL into main DB
cp "$ENCRYPTED_DB" "$TMP_ENC" 2>/dev/null || exit 0
cp "${ENCRYPTED_DB}-wal" "${TMP_ENC}-wal" 2>/dev/null
cp "${ENCRYPTED_DB}-shm" "${TMP_ENC}-shm" 2>/dev/null

# Force WAL checkpoint — merges recent writes into the main DB file.
# sqlite3 may error ("file is not a database") because DingTalk encrypts pages,
# but the file-level merge still succeeds (WAL shrinks to 0 after this call).
sqlite3 "$TMP_ENC" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
rm -f "${TMP_ENC}-wal" "${TMP_ENC}-shm"

# Step 2: Decrypt (export-only: no HTTP server, clean exit)
~/.local/bin/dingwave \
  -d "$TMP_ENC" \
  -k "$REAL_UID" \
  -userconfig "$USER_CONFIG" \
  -merged-out "$TMP_MERGED" \
  -export-only 2>/dev/null

rm -f "$TMP_ENC"

[ -f "$TMP_MERGED" ] || exit 0

# Step 2: Extract class group messages (correct column names: created_at, content_json)
ALL_MSGS=$(sqlite3 "$TMP_MERGED" "
  SELECT datetime(created_at/1000, 'unixepoch', '+8 hours'),
         content_json
  FROM messages
  WHERE cid='$CLASS_CID'
  ORDER BY created_at DESC
  LIMIT 30;
" 2>/dev/null)

rm -f "$TMP_MERGED"

[ -n "$ALL_MSGS" ] || exit 0

# Step 3: Write daily summary
{
  echo "## 📬 钉钉班级群消息（三年级2班）"
  echo ""
  echo "> [!info] 数据来源"
  echo "> 钉钉桌面端本地数据库 → dingwave 解密 → 文本提取。每 30 分钟自动刷新。"
  echo ""
  echo "| 时间 | 内容 |"
  echo "|------|------|"
  
  echo "$ALL_MSGS" | while IFS='|' read -r time content; do
    TEXT=$(echo "$content" | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
    att = d.get('attachments', [{}])[0]
    if not att:
        print('[空]')
        sys.exit(0)
    ext_s = att.get('extension', '{}')
    ext = json.loads(ext_s)
    desc = ext.get('desc', '')
    if not desc:
        p2 = ext.get('payloadV2', '{}')
        if p2:
            p2d = json.loads(p2)
            texts = []
            for c in p2d.get('contents', []):
                for item in c.get('text', {}).get('items', []):
                    t = item.get('data', {}).get('text', '')
                    if t: texts.append(t)
            desc = ' '.join(texts)
    desc = desc.replace('|', ' ').replace('\\\\n', ' | ')[:120]
    print(desc if desc else '[富媒体消息]')
except:
    print('[解析失败]')
" 2>/dev/null <<< "$content")
    echo "| $time | $TEXT |"
  done
  echo ""
} > "$DAILY_FILE"

# Step 4: Check for new messages
FIRST_MID=$(echo "$ALL_MSGS" | head -1 | md5 2>/dev/null || echo "")
if [ -z "$FIRST_MID" ]; then exit 0; fi

if [ -f "$STATE_FILE" ]; then
  PREV_MID=$(cat "$STATE_FILE" 2>/dev/null || echo "")
  if [ "$FIRST_MID" = "$PREV_MID" ]; then
    exit 0  # No new messages
  fi
fi

echo "$FIRST_MID" > "$STATE_FILE"
