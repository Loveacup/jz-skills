#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-bundle-code-audit.sh —— 只读证据包生成器（code-audit evidence bundle）
#
# 【只读】 只读 --repo 内容，只写 --out 目录；绝不改动被审仓库。
#          为 auditor.independence_level=bundle_only 的委派场景准备证据基座——
#          让 OMP 审计者「离线只看这一包」也能核查，而非现场访问工作区。
#
# 产物（全部落在 --out 目录）：
#   manifest.json   证据包元数据（repo/scope/base/git 与否/文件数/排除的敏感路径数）
#   summary.md      人类可读摘要
#   file-list.txt   纳入证据包的文件清单（已剔除敏感路径）
#   git-status.txt  git 工作区状态（非 git 目录写占位说明）
#   diff.patch      相对 --base（或 HEAD）的差异（非 git 目录写占位说明；敏感路径不入 diff）
#
# 参数：
#   --repo <path>     被审仓库根（必填）
#   --out  <dir>      证据包输出目录（必填；不存在则创建）
#   --scope <path>    纳入范围（可重复；相对 --repo 或绝对；缺省=整个 repo）
#   --base <ref>      diff 基线 git ref（可选；缺省=HEAD）
#   -h|--help         打印本头注
#
# 敏感路径（best-effort 排除，不入 file-list / diff）：
#   .env* · *secret* · *token* · *credential* · *.pem · *.key · id_rsa* · *.p12 · *.pfx · *.keystore
#
# 退出码： 0 正常 · 3 参数错误
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

REPO=""; OUT=""; BASE=""; SCOPES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)  REPO="$2"; shift 2 ;;
    --out)   OUT="$2";  shift 2 ;;
    --scope) SCOPES+=("$2"); shift 2 ;;
    --base)  BASE="$2"; shift 2 ;;
    -h|--help) sed -n '2,33p' "$0"; exit 0 ;;
    *) echo "omp-bundle-code-audit: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -n "$REPO" && -d "$REPO" ]] || { echo "omp-bundle-code-audit: --repo 须为存在的目录（'$REPO'）" >&2; exit 3; }
[[ -n "$OUT" ]] || { echo "omp-bundle-code-audit: --out 必填" >&2; exit 3; }
REPO="$(cd "$REPO" && pwd)"
mkdir -p "$OUT" || { echo "omp-bundle-code-audit: 无法创建 --out '$OUT'" >&2; exit 3; }
OUT="$(cd "$OUT" && pwd)"

# 敏感路径判定（best-effort；只按路径字面量匹配，不读文件内容）
_SENSITIVE_RE='(^|/)(\.env([.].*)?|id_rsa[^/]*|.*secret.*|.*token.*|.*credential.*|.*\.(pem|key|p12|pfx|keystore))$'
is_sensitive() { printf '%s' "$1" | grep -Eiq "$_SENSITIVE_RE"; }

# git 探测（tolerate 非 git 目录）
IS_GIT=false
if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then IS_GIT=true; fi

# ── 收集范围内文件清单 ──
# git 仓库用 git ls-files（含未跟踪、排除 ignored）；非 git 用 find。
# --scope 接受相对路径或 repo 内绝对路径；统一归一化为 repo-relative，避免 git pathspec
# 因绝对路径失效，也避免 file-list.txt 泄出本机绝对路径。repo 外 scope 忽略。
normalize_scope() { # <scope> -> repo-relative path or empty
  local sc="$1" abs rel
  [[ -n "$sc" ]] || return 0
  if [[ "$sc" = /* ]]; then
    abs="$(cd "$(dirname "$sc")" 2>/dev/null && pwd)/$(basename "$sc")" || return 0
  else
    abs="$REPO/$sc"
  fi
  case "$abs" in
    "$REPO") rel="." ;;
    "$REPO"/*) rel="${abs#$REPO/}" ;;
    *) return 0 ;;
  esac
  rel="${rel#./}"
  [[ -n "$rel" ]] || rel="."
  printf '%s\n' "$rel"
}
RAW_LIST="$OUT/.raw-file-list.tmp"; : > "$RAW_LIST"
declare -a SCOPE_ARGS=()
if [[ ${#SCOPES[@]} -eq 0 ]]; then
  SCOPE_ARGS=(".")
else
  for sc in "${SCOPES[@]}"; do
    norm="$(normalize_scope "$sc")"
    [[ -n "$norm" ]] && SCOPE_ARGS+=("$norm")
  done
  [[ ${#SCOPE_ARGS[@]} -gt 0 ]] || SCOPE_ARGS=(".")
fi
if $IS_GIT; then
  for sc in "${SCOPE_ARGS[@]}"; do
    git -C "$REPO" ls-files --cached --others --exclude-standard -- "$sc" 2>/dev/null >> "$RAW_LIST" || true
  done
else
  for sc in "${SCOPE_ARGS[@]}"; do
    if [[ -e "$REPO/$sc" ]]; then
      ( cd "$REPO" && find "$sc" -type f 2>/dev/null ) >> "$RAW_LIST" || true
    fi
  done
fi
# 去重排序
sort -u "$RAW_LIST" -o "$RAW_LIST" 2>/dev/null || true

# ── 剔除敏感路径，落 file-list.txt ──
INCLUDED=0; EXCLUDED=0
: > "$OUT/file-list.txt"
while IFS= read -r f; do
  [[ -n "$f" ]] || continue
  f="${f#./}"                    # find 在 scope="." 时产出 ./ 前缀，归一化掉
  [[ -n "$f" ]] || continue
  if is_sensitive "$f"; then EXCLUDED=$((EXCLUDED+1)); continue; fi
  printf '%s\n' "$f" >> "$OUT/file-list.txt"
  INCLUDED=$((INCLUDED+1))
done < "$RAW_LIST"
rm -f "$RAW_LIST"

# ── git-status.txt ──
if $IS_GIT; then
  git -C "$REPO" status --porcelain=v1 2>/dev/null > "$OUT/git-status.txt" || : > "$OUT/git-status.txt"
else
  printf '# 非 git 目录，无 git status。\n' > "$OUT/git-status.txt"
fi

# ── diff.patch（相对 --base 或 HEAD；剔除敏感路径）──
DIFF_BASE="${BASE:-HEAD}"
if $IS_GIT; then
  # :(exclude) pathspec 剔除敏感文件类；对不存在的 base 优雅退化为空 diff。
  if git -C "$REPO" rev-parse --verify --quiet "$DIFF_BASE" >/dev/null 2>&1; then
    git -C "$REPO" diff "$DIFF_BASE" -- "${SCOPE_ARGS[@]}" \
      ':(exclude)*.env' ':(exclude)*secret*' ':(exclude)*token*' \
      ':(exclude)*credential*' ':(exclude)*.pem' ':(exclude)*.key' \
      ':(exclude)id_rsa*' ':(exclude)*.p12' ':(exclude)*.pfx' ':(exclude)*.keystore' \
      2>/dev/null > "$OUT/diff.patch" || : > "$OUT/diff.patch"
  else
    printf '# base ref "%s" 不存在或无提交，diff 为空。\n' "$DIFF_BASE" > "$OUT/diff.patch"
  fi
else
  printf '# 非 git 目录，无 diff。\n' > "$OUT/diff.patch"
fi

# ── manifest.json ──
_scopes_json="$(printf '%s\n' "${SCOPE_ARGS[@]}" | jq -R . | jq -sc .)"
diff_lines=$(wc -l < "$OUT/diff.patch" | tr -d ' ')
jq -nc \
  --arg repo "$REPO" \
  --arg out "$OUT" \
  --argjson scopes "$_scopes_json" \
  --arg base "$DIFF_BASE" \
  --argjson is_git "$IS_GIT" \
  --argjson included "$INCLUDED" \
  --argjson excluded "$EXCLUDED" \
  --argjson diff_lines "$diff_lines" \
  '{
    kind: "omp-code-audit-evidence-bundle",
    version: 1,
    repo: $repo,
    out: $out,
    scopes: $scopes,
    diff_base: $base,
    is_git: $is_git,
    files_included: $included,
    sensitive_excluded: $excluded,
    diff_lines: $diff_lines,
    artifacts: ["manifest.json","summary.md","file-list.txt","git-status.txt","diff.patch"]
  }' > "$OUT/manifest.json"

# ── summary.md ──
{
  echo "# OMP Code-Audit Evidence Bundle"
  echo
  echo "- repo: \`$REPO\`"
  echo "- scopes: ${SCOPE_ARGS[*]}"
  echo "- diff_base: \`$DIFF_BASE\`"
  echo "- git repo: $IS_GIT"
  echo "- files included: $INCLUDED"
  echo "- sensitive paths excluded: $EXCLUDED"
  echo "- diff lines: $diff_lines"
  echo
  echo "## Artifacts"
  echo "- \`manifest.json\` — 结构化元数据（供 gate 的 evidence_bundle.path 引用）"
  echo "- \`file-list.txt\` — 纳入证据包的文件清单（已剔除敏感路径）"
  echo "- \`git-status.txt\` — 工作区状态"
  echo "- \`diff.patch\` — 相对 base 的差异（敏感路径不入 diff）"
  echo
  echo "> 只读证据包：本脚本不改动 repo，供 bundle_only 审计者离线核查。"
} > "$OUT/summary.md"

echo "omp-bundle-code-audit: 证据包已生成 → ${OUT} （files=${INCLUDED}, excluded=${EXCLUDED}, diff_lines=${diff_lines}, git=${IS_GIT}）"
exit 0
