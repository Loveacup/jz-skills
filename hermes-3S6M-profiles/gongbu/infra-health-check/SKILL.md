---
name: infra-health-check
description: "工部基础设施健康巡检 — 检查 system/gateway/config/disk/process/cron 状态，参考 sudoyasir/OverWatch + cubyverse/health-checks + rz0re/spyd"
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [gongbu, infra, monitoring, health-check]
    related_skills: []
---

# 工部基础设施健康巡检

## When to Use

- 定期系统健康检查（建议 cron 每日）
- 六部冒烟测试后执行
- Gateway 异常时诊断
- 部署变更后验证

## 检查项目

### 1. Gateway 状态
```bash
hermes profile list 2>/dev/null | grep -c running
ps aux | grep hermes-gateway | grep -v grep | wc -l
```

### 2. 磁盘使用
```bash
df -h ~/.hermes
du -sh ~/.hermes/profiles/regent/cron/output/
du -sh ~/.hermes/kanban/
```

### 3. 内存/CPU
```bash
ps aux | grep hermes | awk '{sum+=$6} END {print sum/1024 " MB"}'
top -l 1 | head -10
```

### 4. 进程健康
```bash
# 检查 gateway 进程
pgrep -f hermes-gateway && echo "OK" || echo "DOWN"
# 检查 kanban watchdog
hermes cron list 2>/dev/null | grep watchdog | grep -c active
```

### 5. Config 完整性
```bash
for p in engineer gongbu budget protocol tester registry; do
  f="~/.hermes/profiles/$p/config.yaml"
  [ -f "$f" ] && echo "$p: $(wc -l < $f)L" || echo "$p: MISSING"
done
```

### 6. Cron 输出膨胀检查
```bash
find ~/.hermes/profiles/regent/cron/output -type f | wc -l
du -sh ~/.hermes/profiles/regent/cron/output/
# 阈值：>10000 文件或 >20MB 告警
```

## 输出格式

```
📊 工部健康巡检 — 2026-05-27
─────────────────────────────
✅ Gateway: 3/3 running
✅ 磁盘: 1.2G used / 50G free
⚠️  Cron输出: 13600 文件 (50MB) — 超标
✅ 进程: gateway PID 49006
✅ Config: 6/6 profiles 完整
─────────────────────────────
评级: 🟡 WARNING (1 issue)
```

## 集成参考

- **OverWatch** (sudoyasir/OverWatch): Rich 终端仪表盘，可做 `hermes infra dashboard` 命令
- **spyd** (rz0re/spyd): AI 驱动的异常检测 + Telegram 告警，可集成到 cron
- **defib** (alexknowshtml/defib): 自动恢复模式，gateway 崩溃时自动重启
- **cron-health** (indiekitai/cron-health): cron 任务自身健康监控，防静默失败
- **health-checks** (cubyverse/health-checks): 最简 bash 巡检，50 行以内可部署

## 自动修复

以下情况可自动修复（无需父皇审批）：
- cron output 文件 >30 天 → 自动清理
- gateway 进程不存在 → 自动 `hermes gateway start`
- kanban watchdog 未运行 → 自动启用

以下需父皇决策：
- 磁盘 >80% → 报告 + 建议清理方案
- config 缺失 → 报告 + 建议重建
