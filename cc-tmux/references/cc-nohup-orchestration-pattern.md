# CC Nohup 后台编排模式

> 2026-06-17 Phase 0 冒烟验证中产生。CC 写脚本 → nohup 后台跑 → 等待器监听 REPORT → 醒来消化结果。

## 问题

CC 在 xhigh effort 下长思考会超过 10 分钟。如果需要跑一系列独立的 shell 验证（如 5 个冒烟测试），逐项等 CC 思考→执行→思考→执行 效率极低且易冻结。

## 模式

CC **自己写一个编排脚本**，nohup 到后台独立运行。脚本完成所有工作后写一个 `REPORT.txt`。CC 起一个等待器（shell `for` 循环）监听 REPORT 文件，文件就绪后醒来读结果。

```
CC 思考: 设计验证方案
  → Write 编排脚本 (run.sh)
  → Bash: nohup bash run.sh &
  → Bash: for i in $(seq 1 180); do
            if [ -s REPORT.txt ]; then cat REPORT.txt; exit 0; fi
            sleep 2
          done
  → [CC 在此阻塞，等待器在后台轮询]
  → REPORT.txt 就绪 → waiter 退出 → CC 读到 REPORT 内容
  → CC 思考: 消化结果，产出结论
```

## 编排脚本模板

```bash
#!/usr/bin/env bash
# 编排脚本：独立运行全部验证，完成后写 REPORT.txt
set -euo pipefail
OUTDIR="$(dirname "$0")"
REPORT="$OUTDIR/REPORT.txt"
PROGRESS="$OUTDIR/progress.log"

echo "start $(date)" > "$PROGRESS"

# 各测试写标记文件 + 进度
run_test() {
  local name="$1"; shift
  echo "running $name..." >> "$PROGRESS"
  if "$@"; then
    touch "$OUTDIR/${name}_ok"
    echo "  $name: PASS" >> "$PROGRESS"
  else
    echo "  $name: FAIL" >> "$PROGRESS"
  fi
}

# --- 测试体 ---
run_test "r1_accumulate" bash -c '...'
run_test "r2_hookdir"    bash -c '...'

# --- 产出 REPORT ---
{
  echo "===== 实测结果 ====="
  for f in "$OUTDIR"/*_ok; do
    [ -f "$f" ] || continue
    name=$(basename "$f" _ok)
    echo "$name: PASS"
  done
  echo "===== END ====="
} > "$REPORT"
```

## CC 侧的等待器（内联 Bash）

```bash
# CC 在一个 Bash 调用中跑：
cat /tmp/cc-phase0/nohup.out 2>/dev/null
for i in $(seq 1 180); do
  if [ -s /tmp/cc-phase0/REPORT.txt ]; then
    echo "REPORT ready after ~$((i*2))s"
    cat /tmp/cc-phase0/REPORT.txt
    exit 0
  fi
  sleep 2
done
echo "TIMEOUT: REPORT not ready after 6min"
exit 1
```

## 适用场景

- 多个独立的 shell 验证（冒烟测试、批量检查）
- CC 长思考可能超时的任务
- 需要精确计时/计数的重复操作

## 不适用

- 需要 CC 逐项判断结果的（编排脚本只能做机械判断）
- 任务间有依赖需要 CC 推理的
- 产物需要 CC 阅读理解后才能决定下一步的

## 注意事项

- 等待器设硬超时（如 180×2s=6min），防永久阻塞
- 编排脚本必须 `set -e`，单测失败不阻断后续
- 清理：CC 完成消化后应清理 `/tmp/cc-phase0/` 等临时目录
- 模型选择：编排脚本本身用 haiku 足够（省钱）
