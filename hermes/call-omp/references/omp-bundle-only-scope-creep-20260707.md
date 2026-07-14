# OMP bundle_only 审计 scope creep 事件记录（2026-07-07）

> 背景：WRR v6.1.1 → P3 早期新闻捕获（P3-1 RSS 适配器 + P3-3 early-news 路由模式）。
> 两次 bundle_only OMP 审计中，审计者为验证"红线文件未改动"而越界读取 `.git/`，导致整轮 verdict 失效。
> 本文记录触发条件、现象、根因、修复方法和证据包模板，供后续 bundle_only 审计委派参考。

## 事件时间线

### 事件 A：P3-1 R3 审计（task_id=`omp-p31-r3`）

- **审计范围**：P3-1 wechat_rss detect bug 修复后重审，只关注 blocker 项（3 条 criterion）。
- **allowed_paths**：`wrr/engines/community.py`、`tests/unit/test_rss_source_adapter.py`、`/tmp/omp-bundle-p31-r3/manifest.json`。
- **越界行为**：
  - 读取 `~/code/web-research-router/.git/logs/HEAD`（查 `bcb73c2` 提交日志）。
  - 读取 `~/code/web-research-router/.git/objects/bc/b73c2f...`（读 commit object）。
  - `grep ~/code/web-research-router/.git`（搜索 `bcb73c2`）。
- **verdict**：`severity=blocker`，summary="审计方法失效"（criterion 1-2 在 scope 内已通过，criterion 3 因越界污染不可消除）。
- **处理**：`omp-finish --reject`；Hermes 独立 `git diff --name-only v6.1.1..HEAD` 验证红线文件未改动，给出人工裁决通过。

### 事件 B：P3-3 R1 审计（task_id=`omp-p33-audit`）

- **审计范围**：P3-3 early-news 路由模式（4 条 criterion）。
- **改进**：evidence_bundle 已预填 `git diff --name-only v6.1.1..HEAD`（`/tmp/omp-bundle-p33-audit/git-diff-name-only.txt`）。
- **allowed_paths**：`wrr/config.py`、`wrr/router.py`、`wrr/engines/community.py`、`tests/unit/test_router_early_news_mode.py`、`/tmp/omp-bundle-p33-audit/`。
- **越界行为**：
  - 读取 `~/code/web-research-router/wrr/engines/community_sources.py`（不在 allowed_paths 中）。
- **verdict**：`severity=blocker`，summary="审计者越界读取未授权文件 community_sources.py，违反 scope 契约」。
- **处理**：`omp-finish --reject`；Hermes 独立取证 4 条 criterion 全部通过，给出人工裁决通过。

## 根因分析

1. **信息缺口**：审计者被问到"红线文件是否改动"，但 `router.py` / `registry.py` / `deps.py` 不在 allowed_paths 内；审计者想独立验证，只能自行调用 git 或读取相关文件。
2. **相邻文件好奇**：即使 evidence_bundle 预填了 `git diff --name-only`，审计者仍可能出于理解完整上下文而读取相邻文件（如 `community_sources.py`）。
3. **bundle_only 的独立性强**：OMP 被明确要求"bundle_only"，它倾向于只相信自己读到的文件，而不是委派方提供的 manifest。

## 修复/预防方法

### 方法 1：把红线文件加进 allowed_paths（推荐）

如果审计任务需要验证红线文件未改动，就把这些文件本身加入 `allowed_paths`：

```json
"allowed_paths": [
  "/path/to/web-research-router/wrr/router.py",
  "/path/to/web-research-router/wrr/registry.py",
  "/path/to/web-research-router/wrr/deps.py",
  "/path/to/web-research-router/wrr/config.py",
  ...
]
```

这样审计者可以合法读取它们，不会越界到 `.git/`。

### 方法 2：在 evidence_bundle 中预填红线检查结果（次推荐）

如果出于安全考虑不想把红线文件本身开放，就在 evidence_bundle 中提供充分的只读证据：

```bash
# 生成证据包时预填
git diff --name-only v6.1.1..HEAD > evidence_bundle/git-diff-name-only.txt
git diff --stat v6.1.1..HEAD > evidence_bundle/git-diff-stat.txt
git status --short > evidence_bundle/git-status-short.txt

# 明确声明红线文件状态
for f in wrr/router.py wrr/registry.py wrr/deps.py; do
  if git diff --quiet v6.1.1..HEAD -- "$f"; then
    echo "UNCHANGED: $f" >> evidence_bundle/red-line-check.txt
  else
    echo "MODIFIED: $f" >> evidence_bundle/red-line-check.txt
  fi
done
```

然后在 `manifest.json` 中内联或引用这些文件：

```json
{
  "red_line_check": {
    "router.py": "unchanged",
    "registry.py": "unchanged",
    "deps.py": "unchanged",
    "git_diff_name_only": ["wrr/config.py", "wrr/router.py", ...],
    "evidence_files": {
      "git-diff-name-only.txt": "...",
      "red-line-check.txt": "..."
    }
  }
}
```

### 方法 3：把相邻上下文文件也加入 allowed_paths

对于审计者可能"好奇"的相邻文件（如 `community_sources.py`），如果它们不是红线文件、不含敏感信息，可以一并加入 allowed_paths，避免越界：

```json
"allowed_paths": [
  "/path/to/web-research-router/wrr/engines/community.py",
  "/path/to/web-research-router/wrr/engines/community_sources.py",
  ...
]
```

## 证据包生成脚本模板

```bash
#!/bin/bash
set -euo pipefail
REPO="${HOME}/code/web-research-router"
BASE="v6.1.1"
OUT="/tmp/omp-evidence-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

cd "$REPO"

git diff --name-only "$BASE"..HEAD > "$OUT/git-diff-name-only.txt"
git diff --stat "$BASE"..HEAD > "$OUT/git-diff-stat.txt"
git status --short > "$OUT/git-status-short.txt"

{
  echo "Red-line check against $BASE"
  for f in wrr/router.py wrr/registry.py wrr/deps.py; do
    if git diff --quiet "$BASE"..HEAD -- "$f"; then
      echo "UNCHANGED: $f"
    else
      echo "MODIFIED: $f"
    fi
  done
} > "$OUT/red-line-check.txt"

cat > "$OUT/manifest.json" <<EOF
{
  "version": "1.0",
  "generator": "hermes-omp-evidence",
  "repo": "$REPO",
  "base": "$BASE",
  "head": "$(git rev-parse --short HEAD)",
  "files": {
    "git-diff-name-only.txt": "$OUT/git-diff-name-only.txt",
    "git-diff-stat.txt": "$OUT/git-diff-stat.txt",
    "git-status-short.txt": "$OUT/git-status-short.txt",
    "red-line-check.txt": "$OUT/red-line-check.txt"
  },
  "red_line_check": {
    "router.py": "unchanged",
    "registry.py": "unchanged",
    "deps.py": "unchanged"
  }
}
EOF

echo "Evidence bundle: $OUT"
```

## 当越界已经发生时如何裁决

1. **不要 accept**：按 call-omp 规则，越界即失败，整轮 verdict 作废。
2. **提取 in-scope 证据**：OMP 越界前可能已经产出了大量 in-scope evidence（如 P3-3 R1 中 criterion 1-4 的正面证据都已在 scope 内生成）。这些证据仍然可用。
3. **Hermes 独立取证**：重新运行关键命令（`git diff --name-only`、targeted tests、读关键源文件），确认所有 criterion 通过。
4. **给出人工裁决**：记录"OMP 越界导致本轮 verdict 作废，但 in-scope evidence + Hermes 独立取证证明所有 criterion 通过"。
5. **reject 本轮**：`omp-finish --reject`，保留 raw 文件供后续分析。

## 关联文件

- `references/omp-audit-package-json-minimal-example.md` — 最小委派包 JSON 示例，含 evidence_bundle 引用。
- `references/omp-audit-workflow.md` — 完整审计工作流（start → send → monitor → finish）。
- `references/omp-extract-markdown-wrapped-verdict-20260706.md` — 从 raw JSONL 手动提取 verdict 的方法。

## 教训总结

- **bundle_only 不等于"只看 bundle"**：审计者可能想独立验证 bundle 中的声明，从而读取 bundle 外的文件。
- **红线文件验证要么开放文件，要么预填充分证据**：不要让审计者只能自己跑 git。
- **相邻文件越界是常见好奇**：把审计者可能需要理解的上下文文件也加入 allowed_paths，或提供足够 source snippet。
- **越界后的 verdict 不可采信，但越界前的 in-scope evidence 可以保留**。
