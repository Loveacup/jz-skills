# 委派包模板（delegation package）

OMP skill 的输入契约。Hermes 据此生成委派包，交 `omp-start.sh` 过 gate。
与 cc-tmux 委派包兼容：共享 `task / criterion / threshold / risk / auditor / independence_level`。

> 传输用 **JSON**（bash 零依赖下比 YAML 可靠，`omp-start.sh --package-json` 直接吃）。
> 下面的 YAML 仅为人类可读展示。

## 字段说明

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `task_id` | 否 | 缺省自动生成 `omp-YYYYMMDD-HHMMSS` |
| `channel` | 否 | `shell`（默认，已实测）/ `mcp` / `acp`（后两者待验证，send 会拒） |
| `mode` | 是 | `audit` 或 `govern:inspect|evidence|clean|deep-clean|sql` |
| `task` | 是 | 一句话明确任务 |
| `scope.allowed_paths` | 危险任务必填 | 允许访问/操作的路径数组 |
| `scope.denied_paths` | 否 | 明确禁止的路径 |
| `scope.cwd` | 建议 | omp 工作目录（`--cwd`，scope 的真实抓手） |
| `criterion` | 是 | 可裁决验收条件数组（≥1，gate-verify 强校验） |
| `threshold.round_limit` | 否 | 默认 3 |
| `threshold.reject_limit` | 否 | 默认 2 |
| `risk.level` | 否 | `low|medium|high`（默认 low；high 触发 scope 强校验） |
| `risk.dangerous_modes` | 否 | 声明的危险模式数组（如 `["clean"]`） |
| `risk.rollback` | clean/deep-clean/sql 必填 | 回滚说明（gate-danger 强校验） |
| `auditor.required` | 否 | 默认 true |
| `auditor.independence_level` | 否 | 默认 `independent_readonly` |
| `output.format` | 是 | 固定 `json` |
| `output.evidence_required` | 是 | 固定 `true` |

## YAML 展示形态

```yaml
task_id: omp-20260628-144500
channel: shell
mode: audit
task: 审查 src/auth 模块是否存在 SQL 注入与鉴权绕过
scope:
  allowed_paths: ["src/auth"]
  denied_paths: ["src/auth/secrets"]
  cwd: /path/to/repo
criterion:
  - 所有 SQL 走参数化查询，无字符串拼接
  - 每个受保护路由都校验 session
threshold: { round_limit: 3, reject_limit: 2 }
risk: { level: low, dangerous_modes: [] }
auditor: { required: true, independence_level: independent_readonly }
output: { format: json, evidence_required: true }
```

## JSON 传输形态（实际用这个）

```json
{"task_id":"omp-20260628-144500","channel":"shell","mode":"audit","task":"审查 src/auth 模块是否存在 SQL 注入与鉴权绕过","scope":{"allowed_paths":["src/auth"],"denied_paths":["src/auth/secrets"],"cwd":"/path/to/repo"},"criterion":["所有 SQL 走参数化查询，无字符串拼接","每个受保护路由都校验 session"],"threshold":{"round_limit":3,"reject_limit":2},"risk":{"level":"low","dangerous_modes":[]},"auditor":{"required":true,"independence_level":"independent_readonly"},"output":{"format":"json","evidence_required":true}}
```

## 两种发起方式

```bash
# 方式 A：直接喂完整 JSON（推荐——Hermes 用 jq 生成）
echo '<上面的 JSON>' | omp-start.sh --package-json -

# 方式 B：便捷参数拼装（适合手测）
omp-start.sh --mode audit --task "审查 auth" \
  --cwd /path/to/repo --allowed-path src/auth \
  --criterion "SQL 参数化" --criterion "路由校验 session"

# 治理 clean（必须带 rollback，否则 gate-danger 拦截 exit 10）
omp-start.sh --mode govern:clean --task "清理过期临时表" \
  --cwd /path/to/db --allowed-path /path/to/db \
  --dangerous-mode clean --risk-level high \
  --rollback "操作前 pg_dump 全量备份，可 restore" \
  --criterion "只删 7 天前的 tmp_ 前缀表"
```
