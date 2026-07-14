# OMP 审计：blocker → concern → raw 文本提取 pass（bilibili-video-analyzer 2026-07-05）

> 任务：审计 bilibili-video-analyzer v3.0 质量优化改动（claim-first 架构 + v2.4 深度恢复）。
> 本次审计最终 verdict 为 pass，但经历了 R2 blocker、R3 concern、R4 aborted、R5 从 raw 文本提取 pass 的曲折路径。

## 迭代序列

| 轮次 | 启动 | 模式 | 结果 | 关键问题 |
|---|---|---|---|---|
| R1 | `omp-start --package-json package-r1.json` | Shell sync | rejected | OMP 输出非合法 JSON（stopReason=toolUse，无 verdict） |
| R2 | `omp-start --package-json package-r2.json` | Shell async | **blocker** | `depth_profile` 空操作；`build_claim_bundle` 无条件调用；`WRITER_PROMPTS` 全局替换；reference doc 类型不匹配 |
| R3 | `omp-start --package-json package-r3.json` | Shell async | **concern** | 5/6 AC 满足；reference doc 中 `source_type`/`target_section`/`action` 仍声明为 `str` |
| R4 | `omp-start --package-json package-r4.json` | Shell async | aborted | OMP 进程被中断，raw 文件仅 5 字节 |
| R5 | `omp-start --package-json package-r5.json` | Shell async | rejected（monitor 解析失败） | OMP 文本输出含合法 pass verdict，但被 markdown code fence 包裹，monitor 无法解析 |

## 最终 verdict 提取

R5 的 raw 文件 `/tmp/omp-raw-bili-quality-opt-r5-*.json` 中，最后一个 assistant turn 文本为：

```text
All three acceptance criteria verified. ...

```json
{
  "severity": "pass",
  "summary": "reference doc 中 source_type、target_section、action 三个字段均已使用正确的 Literal 类型名...",
  "evidence": [...]
}
```

`omp-monitor` 因 JSON 被 markdown 包裹而判定 `rejected`。手动提取内部 JSON 块后，得到合法 pass verdict，保存为 `/tmp/bili-omp-verdict-r5.json`。

## 关键教训

1. **长代码审计务必用 `--async --max-time 300`**：Shell 同步模式会被 Hermes `terminal` 默认 120s 超时截断，导致 raw 不完整、verdict 被误判。
2. **委派包 `task` 字段要极其明确要求只输出裸 JSON**：即使写了 "ONLY JSON"，OMP 仍可能输出 markdown 包裹。可追加 "Do not wrap in markdown code fences."
3. **R2 blocker 必须 reject 后 revise 再重新委派**：不能直接 accept。R3 的 concern 是 R2 修复后的自然降档。
4. **monitor 解析失败 ≠ OMP 没给出 verdict**：大证据包审计中 OMP 常在 toolUse 循环后生成 verdict，但格式不合 monitor 预期。应手动检查 raw 文本。
5. **证据包要包含 pytest 报告**：R2 的 blocker 中 OMP 指出 "声称的 187 个测试通过无法验证"，后续把 `pytest-report.xml` 复制进 bundle 才闭合。

## 复用命令

```bash
# 生成证据包
~/.hermes/skills/autonomous-ai-agents/call-omp/scripts/omp-bundle-code-audit.sh \
  --repo ~/code/jz-skills \
  --scope shared/bilibili-video-analyzer \
  --out /tmp/bili-audit-bundle-v3

# 生成 pytest 报告
cd ~/code/jz-skills/shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py --junitxml=/tmp/bili-pytest-report.xml
cp /tmp/bili-pytest-report.xml /tmp/bili-audit-bundle-v3/pytest-report.xml

# 从 raw 文本提取被 markdown 包裹的 verdict
python3 - <<'PY'
import json, re, glob
raw = glob.glob('/tmp/omp-raw-*.json')[0]
assistant_text = ''
with open(raw) as f:
    for line in f:
        ev = json.loads(line)
        if ev.get('type') == 'message_update':
            ame = ev.get('assistantMessageEvent', {})
            if ame.get('type') == 'text_delta':
                assistant_text += ame.get('delta', '')

m = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', assistant_text)
if m:
    verdict = json.loads(m.group(1))
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
PY
```
