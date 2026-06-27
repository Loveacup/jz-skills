#!/usr/bin/env bash
set -euo pipefail
HOST="${OPENWRT_HOST:-<internal IP redacted>}"
USER="${OPENWRT_USER:-root}"
SSH_OPTS=(-o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)
REMOTE='echo SSH_OK
cat /etc/openwrt_release 2>/dev/null || true
ubus call system board 2>/dev/null || true
ubus call system info 2>/dev/null || true
uptime
df -h
ip -4 addr show br-lan 2>/dev/null | sed -n "1,6p"
ip route show'
if [[ -n "${OPENWRT_PASSWORD:-}" ]]; then
  exec sshpass -p "$OPENWRT_PASSWORD" ssh "${SSH_OPTS[@]}" \
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \
    "$USER@$HOST" "$REMOTE"
else
  exec ssh "${SSH_OPTS[@]}" "$USER@$HOST" "$REMOTE"
fi
