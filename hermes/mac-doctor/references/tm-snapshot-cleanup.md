# Time Machine 本地快照批量清理

## 为什么需要这个

当 Time Machine 备份盘未连接时，macOS 每小时自动创建一个本地 APFS 快照。几天未备份可积累 20-30 个快照，吞噬 15-35GB 磁盘空间——这是磁盘占用率突然飙升（70%→90%）的最常见原因。

## 诊断

```bash
# 列出所有本地快照
tmutil listlocalsnapshots /
# 计数
tmutil listlocalsnapshotdates / | grep -c "2026-"
```

## 清理方法对比

| 方法 | 效果 | 适用场景 |
|------|------|---------|
| `tmutil thinlocalsnapshots / 1000000000 4` | 只薄一个，需多次运行 | 少量快照（<5） |
| `tmutil deletelocalsnapshots <YYYY-MM-DD-HHMMSS>` | 逐个删除 | 批量清理 |
| Python 批量循环 | 一次清完所有 | 大量快照（10+） |

## 批量清理脚本模式

`tmutil thinlocalsnapshots` 单次只薄一个快照，面对 20+ 快照时效率低。推荐用 Python 批量循环：

```python
import subprocess, re

output = subprocess.check_output(
    ["tmutil", "listlocalsnapshotdates", "/"], text=True, timeout=10
)
dates = re.findall(r"(\d{4}-\d{2}-\d{2}-\d{6})", output)

for date in dates:
    try:
        subprocess.check_output(
            ["tmutil", "deletelocalsnapshots", date],
            text=True, timeout=30
        )
        print(f"  ✅ {date}")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {date}: {e}")
```

## 验证效果

```bash
# 确认快照清零
tmutil listlocalsnapshots / | grep -c "2026-"
# 磁盘变化（数据卷）
df -h /System/Volumes/Data
```

## 注意事项

- 快照删除是安全的——数据已存在于当前文件系统，快照只是时间点引用
- 清理后下次连接备份盘时，Time Machine 会自动创建新快照继续备份
- 不要删 `com.apple.TimeMachine.` 前缀以外的快照（如 APFS 系统快照）
- 磁盘满时 `du`/`find` 会超时——优先清理快照后再深挖其他大户
