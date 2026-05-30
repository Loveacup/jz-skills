# 磁盘空间模式与隐藏大户

> 来源：2026-05-30 全量审计实战发现

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

## 扫描技巧

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
