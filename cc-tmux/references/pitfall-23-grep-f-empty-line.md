# Pitfall #23: grep -f 空行/注释行当 ERE 匹配一切

> 触发日期：2026-06-24 · 文件：`scripts/cc-finish.sh` residue gate  
> 根因：`grep -f FILE` 把 FILE 里**每一行**当 ERE，空行=空正则=匹配任何输入

## 症状

```bash
printf 'ls -la /tmp' | grep -iEf residue-danger-patterns.txt
# 输出: ls -la /tmp  ← 误匹配！"ls" 不包含任何危险命令
```

## 根因

`residue-danger-patterns.txt` 第 8 行是一个**空行**（段落分隔）。

`grep -f` 不支持注释语法——`#` 在 ERE 中是字面量，**不是注释**。空行作为 ERE 时（空正则）匹配所有行。

## 修复

```bash
# ❌ 直接 -f 原始文件
grep -iEf "$PATTERNS_FILE"

# ✅ 用 <() 过滤注释行和空行
grep -iEf <(grep -v '^[[:space:]]*#' "$PATTERNS_FILE" | grep -v '^[[:space:]]*$')
```

## 教训

> **任何 `grep -f` 的模式文件，都必须先过滤空行和注释行。不要假设 grep 会替你跳过。**
> 这与 `grep -c` 空输入 guard（Pitfall #8 的 `|| echo 0` / `|| true`）同源——grep 在 edge case 上的默认行为与直觉相反。
