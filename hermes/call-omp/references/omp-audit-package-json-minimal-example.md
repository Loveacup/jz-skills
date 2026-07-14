# OMP audit 委派包 JSON 最小可用示例与常见错误

生成 OMP 委派包时，字段层级必须与 `gate-verify` 的契约完全一致。`omp-start.sh --package-json` 只认完整 JSON，不接受命令行参数与 JSON 混合。

## 最小可用 audit 包（JSON）

```json
{
  "task_id": "bili-quality-audit-20260705",
  "channel": "shell",
  "mode": "audit",
  "task": "Audit the bilibili-video-analyzer quality optimization changes. Review the evidence bundle and verify correctness, backward-compatibility, and no regressions. Output structured JSON verdict only.",
  "scope": {
    "allowed_paths": ["shared/bilibili-video-analyzer"],
    "denied_paths": [],
    "cwd": "/path/to/jz-skills"
  },
  "criterion": [
    "新增 claim-first 数据结构完整、类型安全、无破坏现有接口",
    "D6-D8 / G8-G10 gates 默认关闭，向后兼容",
    "CLI --depth-profile / --claim-qa-gate 不带参数时行为不变",
    "v2.4 prompt 恢复保留 claim/warrant/evidence/boundary 四要素",
    "pytest 全量通过且新增测试覆盖充分"
  ],
  "threshold": {
    "round_limit": 3,
    "reject_limit": 2
  },
  "risk": {
    "level": "low",
    "dangerous_modes": []
  },
  "auditor": {
    "required": true,
    "independence_level": "bundle_only"
  },
  "evidence_bundle": {
    "path": "/tmp/bili-audit-bundle/manifest.json"
  },
  "output": {
    "format": "json",
    "evidence_required": true
  }
}
```

## 常见错误：`gate-verify` 拒绝

### 错误示例 1：字段层级错误 + 缺少字段

```json
{
  "mode": "audit",
  "channel": "acp",
  "task": "...",
  "cwd": "/path/to/jz-skills",
  "allowed_path": ["shared/bilibili-video-analyzer"],
  "criterion": [...]
}
```

会报：

```
{"ok":false,"reason":"委派包缺必填字段或字段值非法","missing_fields":["scope","threshold.round_limit","threshold.reject_limit","output.format","output.evidence_required"]}
```

原因：
1. `cwd` 和 `allowed_path` 不能放在顶层，必须放在 `scope` 对象内（`scope.cwd`、`scope.allowed_paths`）。
2. `scope` 是危险任务必填，即使低风险 audit 也建议提供。
3. `threshold.round_limit`、`threshold.reject_limit`、`output.format`、`output.evidence_required` 必须显式给出。

### 错误示例 2：`scope` 写成字符串而非对象

```json
{
  "task_id": "...",
  "mode": "audit",
  "channel": "shell",
  "task": "...",
  "scope": "P3-1 HackerNews fix",
  "criterion": [...]
}
```

会报 `missing_fields: ["scope"]`。`gate-verify` 要求 `scope` 是对象，即使内容为空也要写：

```json
"scope": { "domain": "P3-1", "focus": "HackerNews fix" }
```

### 错误示例 3：`output.evidence_required` 写成数组而非 `true`

```json
{
  "output": {
    "format": "json",
    "evidence_required": ["git diff", "unit tests"]
  }
}
```

会报 `missing_fields: ["output.evidence_required"]`。该字段必须是布尔值 `true`，而不是证据清单数组。证据清单应放在 `evidence_bundle` 或任务描述中。

### 错误示例 4：缺少 `risk` 对象

即使 `level` 是 low，也建议提供：

```json
"risk": { "level": "low", "dangerous_modes": [] }
```

某些版本的 `gate-verify` 把 `risk` 当作必填对象解析；缺少时会被拒绝。

## 证据包生成

```bash
scripts/omp-bundle-code-audit.sh \
  --repo ~/code/jz-skills \
  --scope shared/bilibili-video-analyzer \
  --out /tmp/bili-audit-bundle
```

产出 `manifest.json` 后，委派包 `evidence_bundle.path` 必须指向该 `manifest.json`。

## 验证委派包骨架（零 token）

```bash
scripts/call-omp-smoke.sh --platform codex --repo ~/code/jz-skills
```

只跑结构关口 + 证据包生成，不烧 token，适合在真实 audit 前快速验证 JSON 和 scope 正确。
