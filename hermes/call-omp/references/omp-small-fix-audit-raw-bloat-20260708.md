# OMP 小型修复审计 raw 膨胀事件（2026-07-08）

## 背景

WRR P3-1 后审：只改 2 个文件（`wrr/engines/community.py` + `tests/unit/test_community.py`）的 RSS datetime/timezone bugfix。委派 OMP bundle_only 审计时，证据包里塞了 `pytest tests/unit -q` 的完整输出（700+ 行），导致 OMP raw 文件膨胀到 50MB+，`omp-monitor --watch --timeout 240` 超时仍未完成。

## 事件时间线

| 轮次 | task_id | 状态 | 关键问题 |
|---|---|---|---|
| R1 | omp-rss-time-fix | concern | `_recency_score` 未防御归一化 `created`；criterion 4 证据不足 |
| R2 | omp-rss-time-fix-r2 | warn | raw 24MB，被 rejected（解析问题）；但人工提取出 verdict=warn |
| R3 | omp-rss-time-fix-r3 | 超时 | raw 52MB+，watch 240s 未完成；Hermes 独立取证后 override pass |

## 根因

证据包把 `pytest tests/unit -q` 的完整输出（含每个通过的 `.` 和 warnings summary）直接喂给 OMP。OMP 在处理大段文本时进入 tool loop 或长思考，输出 JSONL 文件体积极速膨胀。

## 教训

小型修复（≤3 文件）的证据包应只包含：

1. **targeted 测试**（覆盖改动函数/模块的测试）：`pytest tests/unit/test_community.py -q`
2. **CLI smoke**（1-2 条，证明功能修复）：`wrr search --provider community "AI 热点"`
3. **commit stat**：`git show --stat HEAD`
4. **redline**：`git diff --name-only v6.1.1..HEAD`
5. 需要全量测试时，只保存 `pytest tests/unit -q --tb=no` 的最后几行摘要，或单独存 `passed/total` 结果

不要把 `pytest -v` 或逐行完整输出喂给 OMP。

## 可复用命令

```bash
# 生成小型修复证据包（精简版）
OUT=/tmp/omp-bundle-small-fix
mkdir -p "$OUT"
git show --stat HEAD > "$OUT/commit.txt"
git diff --name-only v6.1.1..HEAD > "$OUT/redline.txt"
pytest tests/unit/test_community.py -q > "$OUT/test_community.txt" 2>&1
pytest tests/unit -q --tb=no > "$OUT/test_unit_summary.txt" 2>&1
wrr search --provider community "AI 热点" > "$OUT/cli_smoke.txt" 2>&1

# 生成 manifest.json
cat > "$OUT/manifest.json" <<EOF
{
  "task": "small fix audit",
  "repo": "$(pwd)",
  "files": {
    "commit": "$OUT/commit.txt",
    "redline": "$OUT/redline.txt",
    "test_community": "$OUT/test_community.txt",
    "test_unit_summary": "$OUT/test_unit_summary.txt",
    "cli_smoke": "$OUT/cli_smoke.txt"
  }
}
EOF
```

## 超时后的降级流程

1. 确认 OMP 进程是否仍在：`ps -p <pid>` 或看 `omp-send` 输出。
2. 若进程仍在但 watch 超时，先 `kill <pid>`。
3. 手动提取 verdict：
   ```python
   import json
   with open('/tmp/omp-raw-xxx.json') as f:
       for line in f:
           ev = json.loads(line)
           if ev.get('type') == 'message_update':
               ame = ev.get('assistantMessageEvent', {})
               if ame.get('type') == 'text_delta':
                   print(ame.get('delta', ''), end='')
   ```
4. 若已输出 verdict（哪怕 markdown 包裹），按 verdict 处理；若未输出，改用同步 shell 重跑。
5. 同步 shell 重跑模板：
   ```bash
   omp -p --no-session --mode json --max-time 90 --tools read,grep \
     --append-system-prompt /path/to/audit-prompt-template.md \
     "<精简后的 task + 只输出 JSON 的要求>" > /tmp/omp-sync-raw.json 2>&1
   ```
6. 仍失败则 Hermes 独立取证，给出人工裁决，并记录"OMP 审计方法失效，Hermes override"。
