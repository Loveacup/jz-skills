---
name: infra-monitoring
description: 工部基础设施监控 — 基于 kOlapsis/maintenant + Tracer-Cloud/opensre 模式，Docker/K8s 自动发现、HTTP/TCP/SSL 检测、心跳监控、资源指标、告警引擎
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [gongbu, infra, monitoring, devops]
    source: [kOlapsis/maintenant, Tracer-Cloud/opensre]
---

# 工部基础设施监控

参考项目：
- **kOlapsis/maintenant** (310⭐, Go) — 容器自动发现、HTTP/TCP端点检测、SSL跟踪、资源指标、告警
- **Tracer-Cloud/opensre** (5.1K⭐, Python) — AI-SRE 平台，60+工具集成

## 核心能力

### 容器监控
```bash
# Docker 容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
# 资源使用
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### 进程监控
```bash
# Hermes gateway 进程
pgrep -f hermes-gateway && echo "gateway: UP" || echo "gateway: DOWN"
# profile 进程数
ps aux | grep "hermes.*chat" | grep -v grep | wc -l
```

### 端点检测
```bash
# HTTP 健康检查
curl -s -o /dev/null -w "%{http_code}" http://localhost:11434  # Ollama
# TCP 端口检查
nc -z localhost 8000 && echo "port 8000: UP" || echo "port 8000: DOWN"
```

### 磁盘/资源阈值
| 指标 | 正常 | 警告 | 严重 |
|------|------|------|------|
| 磁盘使用率 | <60% | 60-80% | >80% |
| Cron output 文件 | <5000 | 5000-10000 | >10000 |
| 内存 (Hermes) | <2GB | 2-4GB | >4GB |

### 告警输出
```
📊 工部巡检 — 2026-05-27 09:00
───────────────────────────
✅ gateway: UP (PID 49006)
✅ Docker: 3/3 running
⚠️  磁盘: 68% (warning)
✅ HTTP: 200
✅ Cron: 4521 files
───────────────────────────
评级: 🟡 1 warning
```

## 集成

- `infra-health-check` — 完整健康巡检
- `disk-cleanup` — 自动磁盘清理
- 可扩展 MCP 端点供 AI agent 查询实时指标
