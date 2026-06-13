#!/bin/bash
# 安装 jz-skills git hooks（幂等，不覆盖非本仓库 hook）
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/deploy/hooks/pre-commit"
HOOK="$REPO_ROOT/.git/hooks/pre-commit"

chmod +x "$SRC"
if [ -e "$HOOK" ] && [ ! -L "$HOOK" ] && ! grep -q "pdf-drift-gate" "$HOOK" 2>/dev/null; then
  echo "⚠️  已存在 .git/hooks/pre-commit 且非本 hook，未覆盖。"
  echo "    请手动合并: $SRC"
  exit 1
fi
ln -sf "$SRC" "$HOOK"
echo "✅ pre-commit hook 已安装 → $HOOK -> $SRC"
