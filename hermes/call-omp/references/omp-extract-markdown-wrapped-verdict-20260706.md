# 提取被 Markdown 包裹的 OMP verdict

> 记录：2026-07-06 / bilibili-video-analyzer 质量优化终审
> 场景：OMP 输出明确包含 `{severity: "pass", evidence: [...], summary: "..."}`，但 `omp-monitor` 因 JSON 被包裹在 ` ```json ... ``` ` 围栏中而解析失败，状态置为 `rejected`。

## 诊断信号

- `omp-monitor.sh --state ...` 输出 `status: rejected`， compact_debug 里 `failure_stage` 含 `no_valid_verdict` 或 `json_parse_failed`。
- 但 `/tmp/omp-raw-<task_id>.json` 文件存在且有可观字节数（如 900+ bytes）。
- raw 文本中能看到 ` ```json` 或 ` ``` ` 与 `{severity` 相邻。

## 复用脚本

```python
import json, re
from pathlib import Path

def extract_omp_verdict_from_raw(raw_path: str | Path) -> dict | None:
    """
    从 OMP raw JSONL 中提取最后一个 assistant text turn，并尝试从 markdown
    代码围栏或裸文本中解析合法 verdict JSON。
    """
    raw_path = Path(raw_path)
    assistant_text = ""
    with open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            # OMP v16.2.x JSONL 中 assistant 文本在 assistantMessageEvent.delta
            ame = ev.get("assistantMessageEvent") or {}
            if ame.get("type") == "text_delta":
                assistant_text += ame.get("delta", "")
            # 兼容旧字段名（如 message_update）
            if "message_update" in ev and isinstance(ev["message_update"], dict):
                delta = ev["message_update"].get("text_delta") or ""
                assistant_text += delta

    if not assistant_text.strip():
        return None

    # 1. 先尝试去掉常见 markdown 围栏
    fence_patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
    ]
    for pat in fence_patterns:
        m = re.search(pat, assistant_text, re.DOTALL | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # 2. 没有围栏时，枚举所有顶层 JSON 对象，选最后一个合法的 verdict
    candidates = []
    for m in re.finditer(r"\{.*?\}", assistant_text, re.DOTALL):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and "severity" in obj and "evidence" in obj:
                candidates.append(obj)
        except json.JSONDecodeError:
            continue
    if candidates:
        return candidates[-1]

    return None

# 示例用法
# verdict = extract_omp_verdict_from_raw("/tmp/omp-raw-bili-quality-opt-r5-20260705-184300.json")
# print(json.dumps(verdict, ensure_ascii=False, indent=2))
```

## 使用时机

1. 已明确要求 OMP "ONLY output valid JSON, no markdown" 但仍被包裹时。
2. 任务已收尾、不想再烧一轮 token 重新 prompt。
3. 人工确认 raw 文本中的 verdict 内容合理且 evidence 非空。

## 注意事项

- 这只是一种**事后补救**，不能替代 `omp-monitor` 的硬校验；accept 前仍需人工核对证据。
- 如果 raw 文本里没有合法 JSON，说明 OMP 没有给出 verdict，不能硬造。
- 应将提取出的 verdict 保存到单独文件（如 `/tmp/omp-extracted-verdict-<task_id>.json`），与 raw 一起归档。

## 归档示例

```bash
cd ~/.hermes/skills/autonomous-ai-agents/call-omp
# 提取并保存
python3 - <<'PY'
import json
from references.omp_extract_verdict import extract_omp_verdict_from_raw
v = extract_omp_verdict_from_raw("/tmp/omp-raw-bili-quality-opt-r5-20260705-184300.json")
with open("/tmp/omp-extracted-verdict-r5.json", "w") as f:
    json.dump(v, f, ensure_ascii=False, indent=2)
print("extracted severity:", v.get("severity"))
PY
```
