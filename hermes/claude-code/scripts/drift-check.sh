#!/bin/bash
# drift-check.sh — claude-code skill 防漂移 read hook（fail-open / DP3）
#
# 加载本 skill 时调用：对比源仓库 ↔ 运行端 SKILL.md 的 md5。
# 漂移 → 打印告警；一致 → 静默。无论结果如何 **永远 exit 0**（fail-open）：
# 校验是安全网，绝不能因校验失败让 skill 不可用。
#
# Usage: bash ~/code/jz-skills/hermes/claude-code/scripts/drift-check.sh

SRC="$HOME/code/jz-skills/hermes/claude-code/SKILL.md"           # 源 = 唯一真源
DEP="$HOME/.hermes/skills/autonomous-ai-agents/claude-code/SKILL.md"  # 运行端

md5q() { md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | awk '{print $1}'; }

if [ ! -f "$SRC" ] || [ ! -f "$DEP" ]; then
  echo "⚠️ claude-code drift-check: SKILL.md 缺失（源或运行端），跳过校验"
  exit 0   # fail-open
fi

if [ "$(md5q "$SRC")" != "$(md5q "$DEP")" ]; then
  echo "⚠️ claude-code skill 漂移：源 ↔ 运行端 md5 不一致，先 cp 同步再用"
  echo "   src=$SRC"
  echo "   dep=$DEP"
fi

exit 0   # ← fail-open：告警但绝不 block skill 加载
