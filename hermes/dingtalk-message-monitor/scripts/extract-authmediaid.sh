#!/bin/bash
# 从钉钉本地加密数据库中提取 authMediaId（用于图片/文件下载的鉴权 token）
# 依赖：dingwave、sqlite3、python3
# 
# 用法：./extract-authmediaid.sh
# 输出：每行格式 AUTH|<时间>|<authMediaId>|<宽x高>|<url>
# 
# 前置条件：钉钉桌面版已登录运行。
# 注意：此脚本需要访问 ~/Library/Containers/...DingTalkMac... 路径，
# 可能被 macOS TCC 沙箱拦截。若直接运行失败，可通过 cron-worker one-shot job 执行。
set -e

DINGTALK_DIR="/Users/alexcai/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Application Support/DingTalkMac/c42eb52018ab1e103951_v3"
CID="${1:-52993580719}"  # 班级群 cid，可通过参数覆盖
ENCRYPTED_DB="$DINGTALK_DIR/DBFiles/dingtalk.db"
USER_CONFIG="$DINGTALK_DIR/user_config"
TMP_ENC="/tmp/dd_auth_enc_$$.db"
TMP_MERGED="/tmp/dd_auth_merged_$$.db"

cleanup() { rm -f "$TMP_ENC" "${TMP_ENC}-wal" "${TMP_ENC}-shm" "$TMP_MERGED"; }
trap cleanup EXIT

# 1. Copy DB + WAL checkpoint
cp "$ENCRYPTED_DB" "$TMP_ENC"
cp "${ENCRYPTED_DB}-wal" "${TMP_ENC}-wal" 2>/dev/null || true
cp "${ENCRYPTED_DB}-shm" "${TMP_ENC}-shm" 2>/dev/null || true
sqlite3 "$TMP_ENC" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
rm -f "${TMP_ENC}-wal" "${TMP_ENC}-shm"

# 2. Decrypt
dingwave -d "$TMP_ENC" -k "39510005" -userconfig "$USER_CONFIG" -merged-out "$TMP_MERGED" -export-only 2>/dev/null

# 3. Extract authMediaId
sqlite3 "$TMP_MERGED" "
  SELECT datetime(created_at/1000, 'unixepoch', '+8 hours'), content_json
  FROM messages
  WHERE cid='$CID'
    AND content_json LIKE '%authMediaId%'
  ORDER BY created_at DESC
  LIMIT 10;
" 2>/dev/null | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    parts = line.split('|', 1)
    if len(parts) < 2: continue
    ts, raw = parts
    try:
        d = json.loads(raw)
    except:
        continue
    for att in d.get('attachments', []):
        try:
            ext = json.loads(att.get('extension', '{}'))
        except:
            continue
        p2 = ext.get('payloadV2', '{}')
        if isinstance(p2, str):
            try: p2 = json.loads(p2)
            except: continue
        if not p2: continue
        for c in p2.get('contents', []):
            if c.get('type') != 'image': continue
            img = c.get('data', {})
            auth = img.get('authMediaId', '')
            url = img.get('url', '')
            w = c.get('style', {}).get('width', '?')
            h = c.get('style', {}).get('height', '?')
            if auth:
                print(f'AUTH|{ts}|{auth}|{w}x{h}|{url}')
"
