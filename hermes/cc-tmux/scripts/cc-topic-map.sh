#!/usr/bin/env bash
# cc-topic-map.sh — R9b Topic↔Session 复用注册表（文件系统映射，纯 bash + jq + tmux）
#
# 数据：JSON 文件 /tmp/cc-topic-map.json
#   { "<topic_id>": {"session":"<tmux session>", "at":"<ISO ts>"}, ... }
#   key = topic_id（Telegram message_thread_id 或自定义 topic 标识）
#
# 命令：
#   cc-topic-map.sh get  <topic>            → 输出 session 名（无则空）
#   cc-topic-map.sh set  <topic> <session>  → 写入/覆盖映射（+ 时间戳）
#   cc-topic-map.sh unset <topic>           → 删除映射
#   cc-topic-map.sh unset-by-session <sess> → 反查：删所有 .session==<sess> 的条目（cc-finish --clean-topic-map 用）
#   cc-topic-map.sh cleanup                 → 遍历，session 已死（tmux has-session 失败）则删
#   cc-topic-map.sh list                    → 列出所有映射（topic<TAB>session<TAB>at）
#
# 注入（hermetic 测试）：CC_TOPIC_MAP_FILE（默认 /tmp/cc-topic-map.json）· CC_TOPIC_TMUX（默认 tmux）
# 退出码：0 正常 · 2 参数错。所有写操作原子（temp + mv）。

set -euo pipefail

MAP="${CC_TOPIC_MAP_FILE:-/tmp/cc-topic-map.json}"
# shellcheck disable=SC2086
tmuxc() { ${CC_TOPIC_TMUX:-tmux} "$@"; }

ensure() { [[ -f "$MAP" ]] || echo '{}' > "$MAP"; jq -e . "$MAP" >/dev/null 2>&1 || echo '{}' > "$MAP"; }
# atomic jq rewrite: write_jq <jq-filter> [--arg k v ...]
write_jq() {
  local tmp; tmp=$(mktemp)
  if jq "$@" "$MAP" > "$tmp" 2>/dev/null; then mv -f "$tmp" "$MAP"; else rm -f "$tmp"; return 1; fi
}
need() { [[ -n "${1:-}" ]] || { echo "❌ cc-topic-map: '$2' 缺参数" >&2; exit 2; }; }

CMD="${1:-}"; shift || true
case "$CMD" in
  get)
    need "${1:-}" topic; ensure
    jq -r --arg k "$1" '.[$k].session // ""' "$MAP" 2>/dev/null || echo ""
    ;;
  set)
    need "${1:-}" topic; need "${2:-}" session; ensure
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    write_jq --arg k "$1" --arg s "$2" --arg t "$ts" '.[$k] = {session:$s, at:$t}'
    ;;
  unset)
    need "${1:-}" topic; ensure
    write_jq --arg k "$1" 'del(.[$k])'
    ;;
  unset-by-session)
    need "${1:-}" session; ensure
    write_jq --arg s "$1" 'with_entries(select(.value.session != $s))'
    ;;
  cleanup)
    ensure
    while IFS= read -r k; do
      [[ -z "$k" ]] && continue
      s=$(jq -r --arg k "$k" '.[$k].session // ""' "$MAP" 2>/dev/null || echo "")
      [[ -z "$s" ]] && continue
      if ! tmuxc has-session -t "$s" 2>/dev/null; then
        write_jq --arg k "$k" 'del(.[$k])'
        echo "🧹 cleanup: topic=$k → session '$s' 已死，删除映射" >&2
      fi
    done < <(jq -r 'keys[]' "$MAP" 2>/dev/null || true)
    ;;
  list)
    ensure
    jq -r 'to_entries[] | "\(.key)\t\(.value.session)\t\(.value.at)"' "$MAP" 2>/dev/null || true
    ;;
  -h|--help)
    sed -n '2,18p' "$0" >&2
    ;;
  *)
    echo "Usage: cc-topic-map.sh get|set|unset|unset-by-session|cleanup|list [args]" >&2
    exit 2
    ;;
esac
exit 0
