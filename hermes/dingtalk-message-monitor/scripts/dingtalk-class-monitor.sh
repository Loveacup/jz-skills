#!/bin/bash
# 钉钉班级群消息监控 v6 — 图片 + 文件统一下载与内容提取
set -euo pipefail

DINGTALK_DIR="~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application Support/DingTalkMac/c42eb52018ab1e103951_v3"
ENCRYPTED_DB="$DINGTALK_DIR/DBFiles/dingtalk.db"
USER_CONFIG="$DINGTALK_DIR/user_config"
USER_CONFIG_FALLBACK="$HOME/Desktop/user_config"
REAL_UID="39510005"
CLASS_CID="52993580719"

STATE_FILE="$HOME/.hermes/data/dingtalk_class_msgs/.last_msg_id"
DAILY_DIR="$HOME/.hermes/data/dingtalk_class_msgs"
MEDIA_PIPELINE="$HOME/.hermes/scripts/dingtalk-media-pipeline.py"

TMP_ENC="/tmp/dd_enc_$$.db"
TMP_MERGED="/tmp/dd_merged_$$.db"
DATE=$(date +%Y-%m-%d)
DAILY_FILE="$DAILY_DIR/$DATE.txt"

mkdir -p "$DAILY_DIR"

[ -f "$ENCRYPTED_DB" ] || exit 0

# ─── Step 1: Copy DB + WAL + SHM ───
cp "$ENCRYPTED_DB" "$TMP_ENC" 2>/dev/null || exit 0
[ -f "${ENCRYPTED_DB}-wal" ] && cp "${ENCRYPTED_DB}-wal" "${TMP_ENC}-wal" 2>/dev/null || true
[ -f "${ENCRYPTED_DB}-shm" ] && cp "${ENCRYPTED_DB}-shm" "${TMP_ENC}-shm" 2>/dev/null || true

# Force WAL checkpoint
sqlite3 "$TMP_ENC" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
rm -f "${TMP_ENC}-wal" "${TMP_ENC}-shm"

# ─── Step 2: Decrypt (use Desktop user_config as fallback for TCC) ───
USERCONFIG_PATH="$USER_CONFIG"
if [ ! -r "$USER_CONFIG" ] && [ -f "$USER_CONFIG_FALLBACK" ]; then
  USERCONFIG_PATH="$USER_CONFIG_FALLBACK"
fi

~/.local/bin/dingwave \
  -d "$TMP_ENC" \
  -k "$REAL_UID" \
  -userconfig "$USERCONFIG_PATH" \
  -merged-out "$TMP_MERGED" \
  -export-only 2>/dev/null

EXIT_CODE=$?
rm -f "$TMP_ENC"

if [ $EXIT_CODE -ne 0 ] || [ ! -f "$TMP_MERGED" ]; then
  echo "[dingtalk-monitor] dingwave failed (exit $EXIT_CODE)" >&2
  exit 0
fi

# ─── Step 3: Extract class group messages (text) ───
ALL_MSGS=$(sqlite3 "$TMP_MERGED" "
  SELECT datetime(created_at/1000, 'unixepoch', '+8 hours'),
         content_json
  FROM messages
  WHERE cid='$CLASS_CID'
  ORDER BY created_at DESC
  LIMIT 30;
" 2>/dev/null)

# ─── Step 3.5: Media download + content extraction (images + files) ───
MEDIA_OUTPUT=""
if [ -f "$MEDIA_PIPELINE" ]; then
  MEDIA_OUTPUT=$(python3 "$MEDIA_PIPELINE" "$TMP_MERGED" 2>/dev/null || echo "[]")
fi

rm -f "$TMP_MERGED"

[ -n "$ALL_MSGS" ] || exit 0

# ─── Step 4: Write daily summary ───
{
  echo "## 📬 钉钉班级群消息（三年级2班）"
  echo ""
  echo "> [!info] 数据来源"
  echo "> 钉钉桌面端本地数据库 → dingwave 解密 → 文本提取。每 20 分钟自动刷新。"
  echo ""

  # ── Text messages ──
  echo "### 📝 文字消息"
  echo ""
  echo "| 时间 | 内容 |"
  echo "|------|------|"
  
  echo "$ALL_MSGS" | while IFS='|' read -r time content; do
    TEXT=$(echo "$content" | /usr/bin/python3 "$HOME/.hermes/scripts/dingtalk-msg-parser.py" 2>/dev/null)
    echo "| $time | $TEXT |"
  done
  
  echo ""

  # ── Media content extraction (images + files) ──
  if [ -n "$MEDIA_OUTPUT" ] && [ "$MEDIA_OUTPUT" != "[]" ]; then
    echo "### 📎 图片与文件内容提取"
    echo ""
    echo "$MEDIA_OUTPUT" | python3 -c "
import sys, json
for item in json.loads(sys.stdin.read()):
    ts = item.get('time',''); text = item.get('text','').strip()
    mtype = item.get('type','?'); name = item.get('name', item.get('file',''))
    size = item.get('size','')
    if not text: continue
    emoji = '🖼' if mtype == 'image' else '📄'
    display = text[:300] + ('...' if len(text) > 300 else '')
    print(f'- **{ts}** {emoji} {name}')
    for line in display.split(chr(10))[:10]:
        line = line.strip()
        if line: print(f'  {line}')
    print()
" 2>/dev/null
  fi

} > "$DAILY_FILE"

# ─── Step 5: Check for new messages ───
FIRST_MID=$(echo "$ALL_MSGS" | head -1 | md5 2>/dev/null || echo "")
if [ -z "$FIRST_MID" ]; then exit 0; fi

if [ -f "$STATE_FILE" ]; then
  PREV_MID=$(cat "$STATE_FILE" 2>/dev/null || echo "")
  if [ "$FIRST_MID" = "$PREV_MID" ]; then
    exit 0  # No new messages
  fi
fi

echo "$FIRST_MID" > "$STATE_FILE"
