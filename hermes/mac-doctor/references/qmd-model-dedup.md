# qmd 模型跨 Profile 去重方案

> 2026-06-04 CC Agent Team (Claude Opus 4.8 xhigh) 源码级审计验证。
> 原方案 `external_dirs` 被否决——它是 skills 专用配置，不碰子进程 env/缓存。

## 根因

`tools/environments/local.py:337` 注入了 `HOME=<profile_home>` 但不设 `XDG_CACHE_HOME`。
qmd `store.js:415` 按 `XDG_CACHE_HOME || HOME/.cache` 解析缓存路径，落到 profile home 下产生副本。

```js
// qmd store.js:415
const cacheDir = process.env.XDG_CACHE_HOME || resolve(homedir(), ".cache");
const qmdCacheDir = resolve(cacheDir, "qmd");
```

## 为什么不能用 XDG_CACHE_HOME

qmd 把三类东西塞在同一缓存根 `~/.cache/qmd/`：

| 内容 | 可变性 | 共享安全？ |
|------|--------|:---:|
| `models/*.gguf` | 下载后只读 | ✅ 可共享 |
| `index.sqlite` | 实时写 | ❌ 每 profile 独立 collection |
| `*-vault.sqlite` | 每 vault | ❌ 独立 |

设 `XDG_CACHE_HOME` 搬整根 → 索引撞库 + SQLite WAL 并发写争用（与 Kanban torn-page 同一失效类）。

## 正确方案：只 symlink models/ 子目录

```bash
# 对每个使用 qmd 的 profile
PROFILE_HOME=~/.hermes/profiles/<name>/home
QMD_CACHE="$PROFILE_HOME/.cache/qmd"
USER_MODELS=~/.cache/qmd/models

# 1. 确保 qmd 无活跃进程
pgrep -fl qmd

# 2. 备份旧 models（如有独立副本）
[ -d "$QMD_CACHE/models" ] && [ ! -L "$QMD_CACHE/models" ] && \
  mv "$QMD_CACHE/models" "$QMD_CACHE/models.broken.bak.$(date +%Y%m%d)"

# 3. 建 symlink
mkdir -p "$QMD_CACHE"
ln -sfn "$USER_MODELS" "$QMD_CACHE/models"

# 4. 验证
HOME="$PROFILE_HOME" qmd status

# 5. 回收备份（验证通过后）
rm -rf "$QMD_CACHE"/models.broken.bak.*
```

## 并发安全

- models/ 下载后只读 → 无锁冲突。唯一边角：两个 profile 首次同时下载同一模型，ipull 写 `.ipull` 临时文件再 rename，风险低。
- index.sqlite 每 profile 独立 → 无并发写争用。
- **整目录 symlink 是陷阱**：会共享 index.sqlite，定时任务 + 交互用户并发 `qmd update` 会争用 WAL。

## 已执行状态

| Profile | 模型 | 索引 |
|---------|:---:|:---:|
| 用户级 `~/.cache/qmd/` | 2.1G（唯一真源） | 独立 |
| regent | symlink → 用户级 ✅ | 独立（已从整目录收紧） |
| cron-worker | symlink → 用户级 ✅ | 独立（修复前为损坏副本） |

## 关联

- 主技能：`mac-doctor` Tier 3 清理规则表
- CC 审计报告：`/tmp/cc-qmd-sharing-audit-conclusion.md`
- 文档：`Obsidian 00-Inbox/Hermes Profile 设置指南.md`
