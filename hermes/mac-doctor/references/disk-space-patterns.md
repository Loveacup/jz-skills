# 磁盘空间模式与隐藏大户

> 来源：2026-05-30 全量审计实战发现 + 2026-06-04 profile 缓存膨胀诊断

## 大户清单

| 目录 | 典型大小 | 说明 |
|------|:----:|------|
| `~/Library/Application Support/Claude/vm_bundles` | 3-8G | Claude Code 沙箱环境，每个项目一个。旧会话残留可能占 50%+ |
| `~/Library/Application Support/Google/Chrome` | 2-10G | Chrome 用户数据（勿清，高危） |
| `~/Library/Application Support/Google/GoogleUpdater` | 500-800M | Chrome 更新器缓存 |
| `~/Library/Application Support/Trae` | 1-4G | Trae IDE 数据，卸载 App 时一并清理 |
| `~/Library/Application Support/Cursor` | 1-4G | Cursor IDE 数据，卸载 App 时一并清理 |
| `~/Library/Application Support/BraveSoftware` | 500M-1G | Brave 残留（浏览器卸载后常见） |
| `~/Library/Application Support/Discord` | 200-500M | Discord 缓存 |
| `~/Library/Caches/Homebrew` | 300-800M | brew 下载的 bottle 文件。`brew cleanup` 通常只清 10-20M |
| **Hermes Profile 缓存** | **3-10G** | ⚠️ 新增 — 见下方专项 |

## Hermes Profile 缓存重复（2026-06-04 新增）

### 根因

每个 Hermes profile 有自己的 home 目录（`~/.hermes/profiles/<name>/home/`），大体积模型和缓存被重复克隆：

```
qmd 模型（1.2G gguf 文件）被复制 3 份：
  ~/.cache/qmd/                   2.3G  👤 用户
  profiles/regent/home/.cache/qmd/             2.3G  🤴 regent
  profiles/cron-worker/home/.cache/qmd/        1.0G  ⚙️ cron
  合计：5.6G（实际只需 2.3G，浪费 3.3G）
```

### 重复大户清单

| 缓存 | 用户级 | regent | cron-worker | 其他 profile | 浪费 |
|------|:---:|:---:|:---:|:---:|:---:|
| qmd 模型 | 2.3G | 2.3G | 1.0G | — | 3.3G |
| ms-playwright | — | 1.0G | 0.5G | — | 1.5G |
| npm | 0.7G | 1.8G | 0.4G | — | 2.2G |
| uv/pip | 1.2G | 1.2G | — | — | 1.2G |
| puppeteer | — | 0.5G | — | — | 0.5G |
| Homebrew | — | 0.06G | 0.07G | — | 0.1G |
| node-gyp/python | — | 0.15G | 0.06G | — | 0.2G |

### 诊断命令（全量排查）

```bash
echo "=== 各 profile 的 cache 大小 ==="
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  cache_size=$(du -sh "$p/home/.cache/" 2>/dev/null | awk '{print $1}')
  npm_size=$(du -sh "$p/home/.npm/" 2>/dev/null | awk '{print $1}')
  lib_size=$(du -sh "$p/home/Library/Caches/" 2>/dev/null | awk '{print $1}')
  echo "  $name → cache:$cache_size npm:$npm_size lib:$lib_size"
done

echo ""
echo "=== qmd 模型重复检测 ==="
echo "用户:     $(du -sh $HOME/.cache/qmd/ 2>/dev/null | awk '{print $1}')"
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  qmd=$(du -sh "$p/home/.cache/qmd/" 2>/dev/null | awk '{print $1}')
  [ -n "$qmd" ] && echo "  $name: $qmd"
done
```

### 根治方案：models/ 子目录 symlink（CC 审计验证）

> [!IMPORTANT] 2026-06-04 CC Agent Team 源码级审计
> `external_dirs` 被否决——它是 **skills 专用配置**，不碰子进程 env/HOME/缓存，用在 qmd 上是 no-op。
> 正确方案见 `references/qmd-model-dedup.md`：只 symlink `models/` 子目录，保留各自 `index.sqlite`。

```bash
# 对每个使用 qmd 的 profile
PROFILE_HOME=~/.hermes/profiles/<name>/home
ln -sfn /Users/<user>/.cache/qmd/models "$PROFILE_HOME/.cache/qmd/models"
# 验证：HOME="$PROFILE_HOME" qmd status
```

**为什么不能设 `XDG_CACHE_HOME`**：qmd 把不可变模型和实时写索引塞在同一缓存根。搬整根 = 索引撞库 + SQLite WAL 并发写争用。详见 `qmd-model-dedup.md`。

### 安全清理（立即回收）

```bash
# 清 profile dev 缓存（不动模型）
rm -rf ~/.hermes/profiles/regent/home/.cache/uv
rm -rf ~/.hermes/profiles/regent/home/.cache/puppeteer
rm -rf ~/.hermes/profiles/regent/home/.npm/_cacache
rm -rf ~/.hermes/profiles/regent/home/Library/Caches/ms-playwright
rm -rf ~/.hermes/profiles/regent/home/Library/Caches/pip
rm -rf ~/.hermes/profiles/regent/home/Library/Caches/node-gyp
rm -rf ~/.hermes/profiles/regent/home/Library/Caches/Homebrew
rm -rf ~/.hermes/profiles/regent/home/Library/Caches/com.apple.python

rm -rf ~/.hermes/profiles/cron-worker/home/.npm/_cacache
rm -rf ~/.hermes/profiles/cron-worker/home/Library/Caches/ms-playwright
rm -rf ~/.hermes/profiles/cron-worker/home/Library/Caches/Homebrew
rm -rf ~/.hermes/profiles/cron-worker/home/Library/Caches/node-gyp
rm -rf ~/.hermes/profiles/cron-worker/home/Library/Caches/pip
```

## 扫描技巧

### APFS Time Machine 快照自动瘦身

macOS APFS 在容器剩余空间 < ~12% 时会自动删除旧 TM 本地快照，无需手动干预。本机实测：磁盘跌至 19GB (8%) 后的几分钟内，24 个快照自动缩减到 4 个，空间回升 16GB。

```bash
# 监测
tmutil listlocalsnapshots / | wc -l
diskutil info / | grep "Container Free"
# 手动触发（通常不需要，自动瘦身已生效）
sudo tmutil thinlocalsnapshots / 999999999999 4
```

> [!TIP] 不要被快照数量吓到。24 个快照看起来吓人，但 APFS 的写时复制意味着它们共享大部分数据块。关键是 `diskutil info /` 的 Container Free Space 绝对值，不是快照数量。

### 全量 `du` 超时时的轻量扫描

当 `du -d 1 -h ~/Library/` 超时（swap >90% 时常见，或目录太深），改用：

```bash
# 逐子目录扫描，避免一次性遍历过深
for d in ~/Library/Application\ Support/*/; do
  du -sh "$d" 2>/dev/null
done | sort -rh | head -15
```

### 先扫已知大户

在深扫之前先打已知目标——Claude、Google、Trae、Cursor、BraveSoftware 等——通常已经覆盖 60-80% 的空间。剩余的再逐项拆。

### 磁盘满时用 ls 代替 du

当磁盘 <15% 导致 `du` 和 `find -size` 全超时：

```bash
# 轻量：只列目录大小（ls + 手动 du 目标目录）
ls -lht /Users/<user>/Downloads/ | head -15
du -sh /Users/<user>/.hermes/profiles/<name>/home/.cache/

# 避免用 du -sh /Users/<user>/Library/ 或 find -size +100M — 磁盘满时 15s+ 超时
```

## 实测数据（2026-05-30）

| 目录 | 大小 | 占比 |
|------|:----:|:--:|
| Claude (vm_bundles) | 7.6G | 30% |
| Google/Chrome | 5.2G | 21% |
| Trae | 1.8G | 7% |
| Cursor | 1.4G | 5.6% |
| BraveSoftware | 707M | 2.8% |
| Discord | 330M | 1.3% |
| GoogleUpdater | 743M | 3% |
| 其余 | ~7.3G | 29% |
| **合计** | **~25G** | 100% |

清理后回收 ~3.9G（Trae 1.8G + Cursor 1.4G + BraveSoftware 707M）。

## 实测数据（2026-06-04 — Profile 缓存膨胀）

| 类别 | 大小 | 占比 |
|------|:----:|:--:|
| regent profile (home) | 5.4G | 47% |
| cron-worker profile (home) | 2.3G | 20% |
| s6m 旧归档 | 3.0G | 26% |
| 其余 dev 缓存 (uv/npm/pip) | 0.8G | 7% |
| **合计** | **~11.5G** | 100% |

其中 qmd 模型实际重复：regent 已 symlink（0 额外占用），仅 cron-worker 有独立副本 ~1.0G 且为损坏状态（半截下载 + 缺 reranker）。清理后 .hermes 从 32G → 11G，回收 21G（含 s6m 归档 3G + dev 缓存 5.7G + TM 快照自动瘦身 ~12G）。
