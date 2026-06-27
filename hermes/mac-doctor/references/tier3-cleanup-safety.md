# D2 清理安全三件套

> 来源：mole clean 模块（dry-run + whitelist + operation log）
> 实现：collector-daemon.py load_whitelist / is_whitelisted / write_oplog

mac-doctor Tier 3 安全清理的三道安全闸，防止误删和生产数据丢失。

## 1. Dry-Run 模式

任何清理操作执行前，先做**预估扫描**：

```
将删除 3 项，预计回收 5.7 GB:
  ~/.npm/_npx/abc123 → 1.2 GB
  ~/.cache/uv/old-version → 3.1 GB
  ~/Library/Caches/Chrome → 1.4 GB

确认执行？(yes/no)
```

### 使用方式

在 SKILL.md Tier 3 清理命令中，先跑预估再确认：

```bash
# 1. 预估
du -sh <target> 2>/dev/null

# 2. 展示预估结果给用户，等待确认

# 3. 确认后执行 rm
```

## 2. Whitelist（白名单）

清理时自动跳过白名单路径。配置在 `~/.hermes/inspection/cleanup-whitelist.txt`。

### 格式

```
# 每行一个绝对路径前缀，# 开头为注释
~/.cache/huggingface
~/.cache/qmd
~/.npm/_npx/<当前在用hash>
```

### 当前默认保护

| 路径 | 原因 |
|---|---|
| `huggingface/` | Whisper / embedding 生产模型 |
| `qmd/` | qmd 模型文件 |
| `_npx/` 当前版本 | Codegraph 等工具运行时依赖 |

### 实现

`collector-daemon.py` 中 `is_whitelisted()` 做前缀匹配，命中即跳过。

## 3. Operation Log

每次清理操作写入审计日志。

### 位置

`~/Library/Logs/mac-doctor/operations.log`

### 格式

```
[2026-05-30 20:33:15] DELETE 1.2G ~/.npm/_npx/abc123
[2026-05-30 20:33:16] DELETE 3.1G ~/.cache/uv/old-version
[2026-05-30 20:33:16] SKIP  0.5G ~/.cache/huggingface (whitelist)
```

每行：[时间戳] 操作 大小 路径 (备注)

### 控制

- 环境变量 `MAC_DOCTOR_NO_OPLOG=1` 禁用日志
- 配置项 `cleanup_safety.oplog_enabled: false` 也可关闭

### 目录自动创建

`write_oplog()` 会自动创建 `~/Library/Logs/mac-doctor/` 目录。
