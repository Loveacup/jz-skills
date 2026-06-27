#!/bin/bash
# WRR 引擎连通性 + fallback 验证（v3.12，2026-06-27）
#
# HTTP 层探测各引擎，镜像 extension.ts 的真实调用方式。
# extension.ts 自身依赖 hermes 运行时无法独立跑，故此脚本验证底层 API 可达性，
# fallback 控制流另由 fallback-logic-test.mjs 单测覆盖（7/7）。
#
# 用法:
#   PROFILE=default ./test-engines.sh         # 自动 source ~/.hermes/profiles/$PROFILE/.env
#   ./test-engines.sh                          # 用当前环境已有的 key
#
# 退出码: 0=至少 exa 或 brave 可用(fallback 链有活路); 1=主链路全挂

set -uo pipefail

PROFILE="${PROFILE:-default}"
ENV_FILE="$HOME/.hermes/profiles/$PROFILE/.env"
if [ -f "$ENV_FILE" ]; then
  echo "[i] sourcing $ENV_FILE"
  set -a; # shellcheck disable=SC1090
  . "$ENV_FILE"; set +a
else
  echo "[!] $ENV_FILE 不存在，使用当前环境变量"
fi

Q="claude opus release notes"
PASS=0; FAIL=0; SKIP=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
skip() { echo "  ⊘  $1"; SKIP=$((SKIP+1)); }

echo "═══ 1. Exa (EXA_API_KEY) ═══"
if [ -z "${EXA_API_KEY:-}" ]; then skip "EXA_API_KEY 未设置"; else
  code=$(curl -s -o /tmp/wrr_exa.json -w "%{http_code}" -X POST https://api.exa.ai/search \
    -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
    -d "{\"query\":\"$Q\",\"numResults\":3}" 2>/dev/null)
  n=$(jq '.results | length' /tmp/wrr_exa.json 2>/dev/null || echo 0)
  [ "$code" = "200" ] && [ "${n:-0}" -gt 0 ] && ok "Exa OK ($n results)" || bad "Exa HTTP $code, results=$n"
fi

echo "═══ 2. Brave (BRAVE_API_KEY) ═══"
if [ -z "${BRAVE_API_KEY:-}" ]; then
  # 显式检查旧命名是否残留（技术债回归保护）
  [ -n "${BRAVE_SEARCH_API_KEY:-}" ] && bad "发现旧命名 BRAVE_SEARCH_API_KEY，应统一为 BRAVE_API_KEY" || skip "BRAVE_API_KEY 未设置"
else
  code=$(curl -s -o /tmp/wrr_brave.json -w "%{http_code}" \
    "https://api.search.brave.com/res/v1/web/search?q=$(printf %s "$Q" | jq -sRr @uri)&count=3" \
    -H "Accept: application/json" -H "X-Subscription-Token: $BRAVE_API_KEY" 2>/dev/null)
  n=$(jq '.web.results | length' /tmp/wrr_brave.json 2>/dev/null || echo 0)
  [ "$code" = "200" ] && [ "${n:-0}" -gt 0 ] && ok "Brave OK ($n results)" || bad "Brave HTTP $code, results=$n"
fi

echo "═══ 3. Tavily (TAVILY_API_KEY) — 限流专用, 不入自动链 ═══"
if [ -z "${TAVILY_API_KEY:-}" ]; then skip "TAVILY_API_KEY 未设置"; else
  code=$(curl -s -o /tmp/wrr_tavily.json -w "%{http_code}" -X POST https://api.tavily.com/search \
    -H "Content-Type: application/json" \
    -d "{\"api_key\":\"$TAVILY_API_KEY\",\"query\":\"$Q\",\"max_results\":3}" 2>/dev/null)
  n=$(jq '.results | length' /tmp/wrr_tavily.json 2>/dev/null || echo 0)
  if [ "$code" = "200" ] && [ "${n:-0}" -gt 0 ]; then ok "Tavily OK ($n results)"
  elif [ "$code" = "432" ] || [ "$code" = "429" ]; then skip "Tavily 限流 HTTP $code (符合预期，fallback 已绕过)"
  else bad "Tavily HTTP $code, results=$n"; fi
fi

echo "═══ 4. SearXNG (SEARXNG_URL) — env-gated fallback 末端 ═══"
if [ -z "${SEARXNG_URL:-}" ]; then skip "SEARXNG_URL 未设置 (fallback 链将自动跳过, 符合设计)"; else
  base="${SEARXNG_URL%/}"
  code=$(curl -s -o /tmp/wrr_searx.json -w "%{http_code}" \
    "$base/search?q=$(printf %s "$Q" | jq -sRr @uri)&format=json" -H "Accept: application/json" 2>/dev/null)
  n=$(jq '.results | length' /tmp/wrr_searx.json 2>/dev/null || echo 0)
  [ "$code" = "200" ] && [ "${n:-0}" -gt 0 ] && ok "SearXNG OK ($n results)" || bad "SearXNG HTTP $code, results=$n (SKILL.md 实测实例可能已损坏)"
fi

echo ""
echo "═══ 5. Fallback 控制流单测 ═══"
MJS="$HOME/.hermes/skills/research/web-research-router/scripts/fallback-logic-test.mjs"
[ -f "$MJS" ] || MJS="/tmp/cc-output/hermes-cc-default-wrr-optimization-0627-1537/fallback-logic-test.mjs"
if [ -f "$MJS" ]; then node "$MJS" && ok "fallback 逻辑单测通过" || bad "fallback 逻辑单测失败"; else skip "未找到 fallback-logic-test.mjs"; fi

echo ""
echo "═══ 汇总: PASS=$PASS FAIL=$FAIL SKIP=$SKIP ═══"
# 主链路有活路判定: exa 或 brave 至少一个 OK
if jq -e '.results | length > 0' /tmp/wrr_exa.json >/dev/null 2>&1 || jq -e '.web.results | length > 0' /tmp/wrr_brave.json >/dev/null 2>&1; then
  echo "[✓] 主 fallback 链路至少一个引擎可用"
  exit 0
else
  echo "[✗] 主链路 (exa/brave) 全部不可用 — fallback 无活路"
  exit 1
fi
