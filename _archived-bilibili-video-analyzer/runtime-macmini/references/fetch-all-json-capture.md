# `fetch_all.py` JSON capture contract

## Why this exists

`fetch_all.py` is a positional CLI: passing `--help` is interpreted as a BVID and triggers the pipeline rather than printing usage. Its successful stdout ends with a machine-readable payload bracketed by `RESULT_JSON_START` and `RESULT_JSON_END`; do not assume it also writes `/tmp/<BVID>_fetch_all.json`.

## Safe capture pattern

```bash
cd /path/to/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/fetch_all.py "$BVID" \
  > "/tmp/${BVID}_fetch_all.log" 2>&1

python3 - "$BVID" <<'PY'
import json, sys
bvid = sys.argv[1]
src = f"/tmp/{bvid}_fetch_all.log"
dst = f"/tmp/{bvid}_fetch_all.json"
s = open(src, encoding="utf-8").read()
a, b = s.rfind("RESULT_JSON_START"), s.rfind("RESULT_JSON_END")
if a < 0 or b <= a:
    raise SystemExit("fetch_all RESULT_JSON markers not found")
payload = json.loads(s[a + len("RESULT_JSON_START"):b])
if not payload.get("ok"):
    raise SystemExit(f"fetch_all incomplete: {payload.get('failed_steps')}")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
print(dst)
PY
```

Only run `generate_report.py --input /tmp/<BVID>_fetch_all.json` after the capture step has succeeded. This preserves the evidence bundle separately from a human-readable log and prevents a false start on a nonexistent input file.

## Evidence gate reminder

Before a formal `B站笔记_*.md`, confirm `subtitle.status == "ok"` and retain the subtitle method/trace in the note's source-boundary section. ASR is valid transcript evidence, but label it as ASR rather than an official subtitle.
