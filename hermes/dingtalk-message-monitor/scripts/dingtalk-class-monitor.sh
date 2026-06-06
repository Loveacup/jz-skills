#!/bin/bash
# 钉钉班级群消息监控 v5 — 图片下载 + OCR 文字提取
set -euo pipefail

DINGTALK_DIR="/Users/alexcai/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application Support/DingTalkMac/c42eb52018ab1e103951_v3"
ENCRYPTED_DB="$DINGTALK_DIR/DBFiles/dingtalk.db"
USER_CONFIG="$DINGTALK_DIR/user_config"
USER_CONFIG_FALLBACK="$HOME/Desktop/user_config"
REAL_UID="39510005"
CLASS_CID="52993580719"

STATE_FILE="$HOME/.hermes/data/dingtalk_class_msgs/.last_msg_id"
DAILY_DIR="$HOME/.hermes/data/dingtalk_class_msgs"
IMAGE_OCR_SCRIPT="$HOME/.hermes/scripts/dingtalk-image-ocr.py"

TMP_ENC="/tmp/dd_enc_$$.db"
TMP_MERGED="/tmp/dd_merged_$$.db"
DATE=$(date +%Y-%m-%d)
DAILY_FILE="$DAILY_DIR/$DATE.txt"

mkdir -p "$DAILY_DIR"

[ -f "$ENCRYPTED_DB" ] || exit 0

# ─── Step 1: Copy DB + WAL + SHM ───
cp "$ENCRYPTED_DB" "$TMP_ENC" 2>/dev/null || exit 0
cp "${ENCRYPTED_DB}-wal" "${TMP_ENC}-wal" 2>/dev/null
cp "${ENCRYPTED_DB}-shm" "${TMP_ENC}-shm" 2>/dev/null

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

# ─── Step 3.5: Image download + OCR ───
OCR_OUTPUT=""
if [ -f "$IMAGE_OCR_SCRIPT" ]; then
  OCR_OUTPUT=$(python3 "$IMAGE_OCR_SCRIPT" "$TMP_MERGED" 2>/dev/null || echo "[]")
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
    desc = desc.replace('|', ' ').replace('\\\\n', ' | ')[:200]
    has_img = '[🖼] ' if 'authMediaId' in ext_s else ''
    print(has_img + (desc if desc else '[富媒体消息]'))
except:
    print('[解析失败]')
" 2>/dev/null <<< "$content")
    echo "| $time | $TEXT |"
  done
  
  echo ""

  # ── Image OCR results ──
  if [ -n "$OCR_OUTPUT" ] && [ "$OCR_OUTPUT" != "[]" ]; then
    echo "### 🖼 图片文字提取（视觉模型 OCR）"
    echo ""
    echo "$OCR_OUTPUT" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read() if sys.stdin.read() else '[]')
for item in data:
    ts = item.get('time', '')
    text = item.get('text', '').strip()
    size = item.get('size', '')
    if not text or text.startswith('[OCR'): continue
    # Truncate long texts
    display = text[:300] + ('...' if len(text) > 300 else '')
    print(f'- **{ts}** ({size})')
    for line in display.split('\\n')[:10]:
        line = line.strip()
        if line:
            print(f'  {line}')
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
