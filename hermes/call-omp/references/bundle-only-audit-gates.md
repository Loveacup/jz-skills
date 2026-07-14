# Bundle-only 审计包与 tool-loop 熔断

适用于：代码写入完成后，用 OMP 做独立、离线、只读后审。

## 委派包硬字段

`auditor.independence_level` 为 `bundle_only` 时，除常规 `evidence` 外，必须显式提供：

```json
{
  "evidence_bundle": {
    "path": "/tmp/<bundle-dir>",
    "manifest": "/tmp/<bundle-dir>/manifest.json"
  }
}
```

只写 `evidence.bundle_root`、`evidence.bundle_manifest` 或 artifacts 列表不够；`gate-verify` 会以 `missing_fields: ["evidence_bundle.path"]` 拒绝。

推荐包内容：

- `manifest.json`
- `diff.patch`
- `file-list.txt`
- `git-status.txt`
- `test-summary.txt`：Hermes 亲自运行的命令、exit code、通过数

生成器参数是 `--out <dir>`，不是 `--output`。

## Raw 体积熔断

异步 shell 审计启动后，只采样 raw 文件大小和 PID 存活，不回吐 raw 正文：

```bash
RAW=/tmp/omp-raw-<task>.json
PID=<omp-pid>
bytes=$(stat -f %z "$RAW" 2>/dev/null || echo 0)
if [ "$bytes" -gt 20971520 ] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
fi
```

超过 20MB 且仍是 `toolUse`、没有合法 JSON verdict：立即熔断；随后只运行一次 `omp-monitor.sh` 提取紧凑诊断。

## 裁决规则

- `stopReason=toolUse` + 无 `{severity,evidence,summary}` = OMP 审计工具失败，不是 PASS，也不是代码 blocker。
- 不对同一包做等价重试；只有委派包发生实质变化（例如补齐 `evidence_bundle.path`）才允许重新 `start`。
- 正式 `omp-finish --reject`，保留 raw 供诊断。
- 降级裁决必须同时具备：
  1. Hermes 从当前工作区亲自运行的 targeted/full/build 证据；
  2. 独立只读 reviewer（例如 Codex FINAL blocker audit）；
  3. 明确披露 OMP 无 verdict，不能写成 OMP pass。

## 避坑

- 不把工具失败描述成代码失败。
- 不因 OMP 沉默就跳过真实测试。
- 不让 auditor 只读执行方自报；测试摘要必须来自 Hermes 原始命令输出。
- bundle scope 应包含未追踪新文件的 diff；生成后核对 `files` 与 `diff_lines`。
