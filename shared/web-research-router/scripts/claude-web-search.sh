#!/bin/bash
# Claude Code WebSearch wrapper — pi-web-providers custom provider contract
# stdin:  {"capability":"search","query":"...","maxResults":5}
# stdout: {"results":[{"title":"...","url":"...","snippet":"..."}]}
set -euo pipefail

INPUT=$(cat)
QUERY=$(echo "$INPUT" | jq -r '.query // empty')
MAX_RESULTS=$(echo "$INPUT" | jq -r '.maxResults // 5')

if [ -z "$QUERY" ]; then
  echo '{"results":[],"error":"missing query"}' >&2
  exit 1
fi

>&2 echo "[claude] searching: $QUERY (max $MAX_RESULTS)"

# Claude Code web search via text output — more reliable than JSON mode for search
RAW=$(claude -p "Do a web search for: $QUERY
Return exactly $MAX_RESULTS results in this format, one per line:
TITLE | URL | SNIPPET
No other text. No analysis. No markdown formatting. Just the lines." \
  --max-turns 4 \
  --output-format text \
  2>/dev/null || echo "")

>&2 echo "[claude] raw output: $(echo "$RAW" | wc -l) lines"

# Parse TITLE | URL | SNIPPET lines into JSON
RESULTS=$(echo "$RAW" | grep -E '^[^|]+\|[^|]+\|' | head -n "$MAX_RESULTS" | while IFS='|' read -r title url snippet; do
  title=$(echo "$title" | xargs)
  url=$(echo "$url" | xargs)
  snippet=$(echo "$snippet" | xargs)
  jq -nc --arg t "$title" --arg u "$url" --arg s "$snippet" '{title: $t, url: $u, snippet: $s}'
done | jq -sc '.')

RESULT_COUNT=$(echo "$RESULTS" | jq 'length // 0')
>&2 echo "[claude] parsed $RESULT_COUNT results"

jq -nc --argjson results "${RESULTS:-[]}" '{results: $results}'
