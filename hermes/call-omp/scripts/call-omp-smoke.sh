#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# call-omp-smoke.sh —— 跨平台「只读冒烟」编排（mock-only，零 token）
#
# 【只读 · 不烧 token】 本脚本**绝不**调用真实 `omp` / `omp-send.sh` / `delegate_task`。
#   它只跑三件本地可验证的事，用于在任意基质（Codex / Claude Code / OMP 自调）上
#   确认 call-omp 的「结构关口 + 证据包生成」这条冷路径可用：
#     1. 打印各底层脚本 --help（不产生任何 agent 调用）；
#     2. gate-verify.sh --mode package 校验一个内联生成的最小委派包；
#     3. omp-bundle-code-audit.sh 在一个临时/指定 repo 上生成只读证据包。
#   → 这是 **mock-only 冒烟**，与「真 token 冒烟」（references/omp-shell-smoke-test.md，
#     真的拉起 omp 跑 audit）严格区分：本脚本永不触网、永不起 OMP 进程。
#
# 平台派生视图（仅影响标签与文案，不改行为）：
#   codex        Codex CLI 侧调用视图（.codex/call-omp.md）
#   claude-code  Claude Code 侧调用视图（references/claude-code-call-omp.md）
#   omp-self     OMP 自调用视图（references/omp-self-call.md）——额外武装递归护栏
#
# OMP 自调递归护栏（防 OMP 调 call-omp 又拉起 OMP 的无限自嵌套）：
#   --platform omp-self 时输出 `recursion_guard=armed`；
#   若环境变量 CALL_OMP_SELF_CALL_DEPTH>=1 → 直接拒绝（退出码 4），不跑任何嵌套 agent 调用。
#
# 参数：
#   --platform codex|claude-code|omp-self   派生视图（缺省 claude-code）
#   --repo <dir>   被冒烟证据包的 repo（缺省：临时新建一个最小 git repo）
#   --out  <dir>   证据包 + 冒烟产物输出目录（缺省：临时目录）
#   -h|--help      打印本头注
#
# 退出码： 0 冒烟通过 · 3 参数错误 · 4 递归护栏拒绝 · 1 冒烟内部步骤失败
# stdout： 人类可读冒烟报告，含 gate 结果与 bundle 产物路径（manifest.json 等）
# ─────────────────────────────────────────────────────────────────
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
GATE_VERIFY="$HERE/gate/gate-verify.sh"
BUNDLE="$HERE/omp-bundle-code-audit.sh"

PLATFORM="claude-code"; REPO=""; OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="${2:-}"; shift 2 ;;
    --repo)     REPO="${2:-}"; shift 2 ;;
    --out)      OUT="${2:-}"; shift 2 ;;
    -h|--help)  sed -n '2,39p' "$0"; exit 0 ;;
    *) echo "call-omp-smoke: 未知参数 $1" >&2; exit 3 ;;
  esac
done

case "$PLATFORM" in
  codex|claude-code|omp-self) : ;;
  *) echo "call-omp-smoke: --platform 须 codex|claude-code|omp-self（得 '$PLATFORM'）" >&2; exit 3 ;;
esac

# ── OMP 自调递归护栏 ──────────────────────────────────────────────
# 无论平台如何，DEPTH>=1 都意味着已经在一次 OMP 自调链里，禁止再向下嵌套。
DEPTH="${CALL_OMP_SELF_CALL_DEPTH:-0}"
if [[ "$DEPTH" =~ ^[0-9]+$ ]] && [[ "$DEPTH" -ge 1 ]]; then
  echo "recursion_guard=tripped depth=$DEPTH"
  echo "call-omp-smoke: 检测到 CALL_OMP_SELF_CALL_DEPTH=${DEPTH}（>=1），拒绝嵌套 OMP 自调冒烟" >&2
  exit 4
fi
if [[ "$PLATFORM" == "omp-self" ]]; then
  echo "recursion_guard=armed"
fi

# ── 输出目录 ──────────────────────────────────────────────────────
if [[ -z "$OUT" ]]; then
  OUT="$(mktemp -d "${TMPDIR:-/tmp}/call-omp-smoke-out.XXXXXX")" || { echo "call-omp-smoke: 无法建临时 --out" >&2; exit 3; }
  # 保留自动创建的输出目录：stdout 会打印 bundle manifest 路径，调用方需要事后可读。
fi
mkdir -p "$OUT" || { echo "call-omp-smoke: 无法创建 --out '$OUT'" >&2; exit 3; }
OUT="$(cd "$OUT" && pwd)"

# ── 被冒烟 repo：缺省临时新建最小内容 ─────────────────────────────
REPO_MADE=""
if [[ -z "$REPO" ]]; then
  REPO="$(mktemp -d "${TMPDIR:-/tmp}/call-omp-smoke-repo.XXXXXX")" || { echo "call-omp-smoke: 无法建临时 --repo" >&2; exit 3; }
  REPO_MADE="$REPO"
  printf 'print("hello smoke")\n' > "$REPO/app.py"
  printf '# smoke repo\n' > "$REPO/README.md"
fi
[[ -d "$REPO" ]] || { echo "call-omp-smoke: --repo 须为存在的目录（'$REPO'）" >&2; exit 3; }

cleanup() { [[ -n "$REPO_MADE" ]] && rm -rf "$REPO_MADE"; }
trap cleanup EXIT

FAIL=0
echo "════════ call-omp mock-only 冒烟 · platform=$PLATFORM ════════"
echo "（本冒烟绝不调用真实 omp / omp-send.sh / delegate_task —— 零 token、不触网）"
echo

# ── 步骤 1：底层脚本 --help（纯打印，无 agent 调用）──────────────
echo "── [1/3] 脚本 --help 自检 ──"
for s in "$GATE_VERIFY" "$BUNDLE"; do
  if bash "$s" --help >/dev/null 2>&1; then
    echo "  ✅ $(basename "$s") --help ok"
  else
    echo "  ❌ $(basename "$s") --help 失败"; FAIL=1
  fi
done
echo

# ── 步骤 2：gate-verify --mode package（内联最小委派包）──────────
echo "── [2/3] gate-verify --mode package ──"
PKG="$OUT/smoke-package.json"
cat > "$PKG" <<JSON
{"task_id":"smoke-$PLATFORM","channel":"shell","mode":"audit","task":"冒烟：结构关口连通性自检","scope":{"allowed_paths":["."],"denied_paths":[],"cwd":"$REPO"},"criterion":["冒烟仅验证结构关口可用"],"threshold":{"round_limit":3,"reject_limit":2},"risk":{"level":"low","dangerous_modes":[]},"auditor":{"required":true,"independence_level":"independent_readonly"},"output":{"format":"json","evidence_required":true}}
JSON
GATE_OUT="$(bash "$GATE_VERIFY" --mode package --file "$PKG" 2>&1)"; GATE_RC=$?
echo "  gate package: rc=$GATE_RC  file=$PKG"
echo "  gate verdict: $GATE_OUT"
if [[ "$GATE_RC" -eq 0 ]]; then echo "  ✅ 委派包结构通过 gate-verify"; else echo "  ❌ gate-verify 未通过（rc=${GATE_RC}）"; FAIL=1; fi
echo

# ── 步骤 3：omp-bundle-code-audit.sh 只读证据包 ────────────────────
echo "── [3/3] omp-bundle-code-audit.sh（只读证据包）──"
BUNDLE_OUT="$OUT/bundle"
if bash "$BUNDLE" --repo "$REPO" --out "$BUNDLE_OUT" >/dev/null 2>&1; then
  echo "  ✅ bundle 生成成功"
else
  echo "  ❌ bundle 生成失败"; FAIL=1
fi
MANIFEST="$BUNDLE_OUT/manifest.json"
echo "  bundle manifest: $MANIFEST"
echo "  bundle summary : $BUNDLE_OUT/summary.md"
echo "  bundle files   : $BUNDLE_OUT/file-list.txt"
if [[ -r "$MANIFEST" ]]; then echo "  ✅ manifest.json 可读"; else echo "  ❌ manifest.json 缺失"; FAIL=1; fi
echo

# ── 汇总 ──────────────────────────────────────────────────────────
echo "════════ 冒烟汇总 ════════"
echo "platform      : $PLATFORM"
echo "gate 结果      : rc=${GATE_RC}（0=结构通过）"
echo "bundle manifest: $MANIFEST"
if [[ "$FAIL" -eq 0 ]]; then
  echo "SMOKE: PASS"
  exit 0
else
  echo "SMOKE: FAIL"
  exit 1
fi
