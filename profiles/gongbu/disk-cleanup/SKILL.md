---
name: disk-cleanup
description: "工部磁盘清理策略 — cron output 自动清理、缓存回收、日志轮转。参考 docker_cleanup.sh + homebutler 模式"
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [gongbu, infra, cleanup, disk, cron]
    related_skills: [infra-health-check]
---

# 工部磁盘清理

## When to Use

- `infra-health-check` 报告 cron output 超标时
- 磁盘使用 >60% 预警
- 手动清理过期缓存
- 月度例行维护

## 清理策略

### cron output 自动清理（推荐 cron job）
```bash
# 清理 30 天前的 cron output
find ~/.hermes/profiles/regent/cron/output -type f -mtime +30 -delete 2>/dev/null
# 清理空目录
find ~/.hermes/profiles/regent/cron/output -type d -empty -delete 2>/dev/null
```

### Kanban workspace 清理
```bash
# 归档 60 天前的 scratch workspace
find ~/.hermes/kanban/workspaces -maxdepth 1 -type d -name 't_*' -mtime +60 -exec rm -rf {} \; 2>/dev/null
```

### 缓存清理
```bash
# Hermes 缓存
find ~/.hermes/profiles/regent/home -name '*.pyc' -delete
find ~/.hermes/profiles/regent/home/__pycache__ -type d -exec rm -rf {} \; 2>/dev/null

# npm/bun 缓存
npm cache clean --force 2>/dev/null
bun pm cache rm 2>/dev/null

# pip 缓存
pip cache purge 2>/dev/null
```

### 日志轮转
```bash
# 压缩 7 天前的 .log 文件
find ~/.hermes -name '*.log' -mtime +7 -exec gzip {} \;
# 删除 90 天前的 .gz
find ~/.hermes -name '*.log.gz' -mtime +90 -delete
```

## cron job 配置

推荐两个 cron job（`no_agent=true` 静默模式）：

```bash
# 每日清理过期 cron output（凌晨3点）
hermes cron create "gongbu-daily-cleanup" \
  --script gongbu/disk-cleanup.sh \
  --schedule "0 3 * * *" \
  --no_agent true \
  --deliver local

# 每周深度清理（周日凌晨4点）
hermes cron create "gongbu-weekly-cleanup" \
  --script gongbu/deep-cleanup.sh \
  --schedule "0 4 * * 0" \
  --no_agent true \
  --deliver local
```

## 阈值告警

| 指标 | 正常 | 警告 | 严重 |
|------|------|------|------|
| cron output 文件数 | <5000 | 5000-10000 | >10000 |
| cron output 总大小 | <10MB | 10-30MB | >30MB |
| kanban workspace | <100 dirs | 100-300 | >300 |
| 磁盘使用率 | <60% | 60-80% | >80% |

## 安全规则

- **从不删除** .env, config.yaml, SOUL.md, .git
- **从不删除** 30 天内的 cron output（可能有未处理任务）
- **删除前** 先 dry-run：`find ... -print` 确认无重要文件
- **清理后** 运行 `infra-health-check` 确认系统正常
