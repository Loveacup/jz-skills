# Profile 缓存重复诊断

> 诊断 profile home 下 `.cache/`、`.npm/`、`Library/Caches/` 异常膨胀的根因与修复。

## 根因

`tools/environments/local.py:337` 给子进程注入 `HOME=<profile_home>` 做隔离，但 **从不设 `XDG_CACHE_HOME`**。

以 qmd 为例 (`~/.bun/.../qmd/dist/store.js:415`)：

```js
const cacheDir = process.env.XDG_CACHE_HOME || resolve(homedir(), ".cache");
const qmdCacheDir = resolve(cacheDir, "qmd");
```

优先级：`XDG_CACHE_HOME` > `HOME/.cache`。由于 Hermes 无 XDG override，所有 XDG 兼容工具（qmd、huggingface、pip、npm）都落到 profile home 下，每 profile 独立副本。

## 诊断命令

```bash
# 快速对比：用户级 vs profile 级缓存大小
echo "用户级:"
du -sh ~/.cache/qmd ~/.npm 2>/dev/null

echo "regent:"
du -sh ~/.hermes/profiles/regent/home/.cache/*/ 2>/dev/null | sort -rh | head -5

echo "cron-worker:"
du -sh ~/.hermes/profiles/cron-worker/home/.cache/*/ 2>/dev/null | sort -rh | head -5
```

## 修复：models/ 子目录 symlink

**不要设 `XDG_CACHE_HOME`**——那会把整个缓存根（models+index+vault）合并，破坏每 profile 的索引隔离 + 引入 SQLite 并发写争用。

正确做法：只 symlink 不可变的 `models/` 子目录：

```bash
CW=~/.hermes/profiles/<name>/home/.cache/qmd
mkdir -p "$CW"
ln -sfn ~/.cache/qmd/models "$CW/models"
HOME=$(dirname "$CW"/../..) qmd status  # 验证
```

### 为什么不是 external_dirs

`external_dirs` 是 **skills 专用配置**（`config.yaml:1628`，定义在 skills 块下），消费方只有 skill 加载链路，不碰子进程 env/HOME/缓存。用于 qmd 是 no-op。

### 已确认可共享的缓存

| 内容 | 共享方式 | 风险 |
|------|---------|------|
| qmd `models/*.gguf` | symlink → 用户级 | ✅ 下载后不可变 |
| huggingface `models/` | symlink → 用户级 | ✅ 同上 |
| qmd `index.sqlite` | **不可共享** | ❌ 每 profile collection 不同 + 实时写 |
| npm `_cacache/` | 直接删除（npm 会重建） | ✅ 纯缓存 |
| uv cache | `uv cache clean` | ✅ 纯缓存 |
| ms-playwright | 删除旧副本 | 可有可无 |
