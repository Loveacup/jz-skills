# macOS 巡检命令参考

## 磁盘 (APFS)

```bash
# ✅ 正确 — Container 级别真实用量
diskutil info / | grep -E "Container (Total|Free) Space|Volume Used Space"

# ✅ 详细 APFS 卷分解
diskutil apfs list | grep -E "Capacity In Use|Capacity Not Allocated|Name:|Capacity Consumed"

# ❌ 错误 — APFS 多卷共享容器，df 显示单个卷视图
# 真实案例: df -h / 显示 28%, 实际 Container 级别 80.4% used
df -h /

# 真实用量公式: Container Total - Container Free
# 如 245.1GB - 48.1GB = 197GB used ≈ 80.4%

# 快照
tmutil listlocalsnapshots /
```

## CPU

```bash
# 总览
top -l 1 -n 0 | head -4
# Load Avg + idle% 是核心指标

# 进程 (BSD ps, 不用 Linux --sort)
ps -eo pid,%cpu,%mem,comm -r | head -12

# 按内存排序
ps -eo pid,%cpu,%mem,comm -m | head -12
```

## 内存 + Swap

```bash
# 总量
sysctl hw.memsize | awk '{printf "%.1f GB\\n", $2/1073741824}'

# 压力
memory_pressure

# VM 统计 (page size = 16384)
vm_stat | head -10

# Swap — 关键指标 (Swap used > 2GB → 内存偏紧)
sysctl vm.swapusage
```

## 进程

```bash
# BSD ps 排序: -r (CPU 降序), -m (内存降序)
ps -eo pid,%cpu,%mem,comm -r | head -12

# 搜索
pgrep -alf "pattern"
```

## 缓存

```bash
# 用户缓存
du -sh ~/.cache/*/ | sort -rh | head -10

# macOS 系统缓存
du -sh ~/Library/Caches/*/ | sort -rh | head -10

# npm
du -sh ~/.npm

# uv
du -sh ~/.cache/uv/
```

## Homebrew

```bash
brew --version
brew outdated | head -20
brew cleanup --dry-run
brew autoremove --dry-run
brew doctor 2>&1 | grep -iE "warning|error"

# brew upgrade: 忽略 exit code 1
# 40 包中 39 成功 1 失败 (如 memo) 仍会 exit 1
# 看输出底部 "Upgraded N outdated packages" 那行
brew upgrade 2>&1 | tail -5
```

## LaunchAgents

```bash
ls ~/Library/LaunchAgents/

# 死链检查
for plist in ~/Library/LaunchAgents/*.plist; do
  program=$(/usr/libexec/PlistBuddy -c "Print :ProgramArguments:0" "$plist" 2>/dev/null)
  [ -n "$program" ] && [ ! -e "$program" ] && echo "DEAD: $program"
done
```

## 安全清理命令

| 缓存 | 命令 | 风险 | 陷阱 |
|------|------|:--:|------|
| npm | `npm cache clean --force` | 无 | 5.7G→1.8G 典型 |
| uv | `uv cache clean --force` | 无 | **先 `lsof ~/.cache/uv`** 确认占用者（chroma-mcp/Claude 等持锁时普通 clean 会一直等） |
| brew | `brew cleanup` | 无 | 通常 300-500MB |
| Chrome | `rm -rf ~/Library/Caches/Google/Chrome/*` | 无 | Chrome 运行中 rm 可能超时，部分清理即可 |

### 不清理的项目

- `~/.cache/qmd/` — embedding/reranker 模型 (~2GB)
- `~/.cache/huggingface/` — Whisper/embedding 模型 (~2GB)
- `~/.cache/chroma/` — vector DB，MCP 在用
- `~/Library/Developer/` — Xcode 工具链

### 清理陷阱速查

| 陷阱 | 表现 | 解法 |
|------|------|------|
| `uv cache clean` 卡住 | "Cache is currently in-use, waiting..." | `uv cache clean --force` |
| `rm -rf` Chrome 超时 | 10s+ 不返回 | 部分清理已生效，接受残留 |
| `brew upgrade` exit 1 | 以为失败 | 看 `Upgraded N outdated packages` 行 |
| `brew autoremove` 无输出 | 以为没工作 | 正常——无非孤儿依赖 |
| df 误判磁盘 | 显示 28% 实际 80% | 用 `diskutil apfs list` Container 级别 |
