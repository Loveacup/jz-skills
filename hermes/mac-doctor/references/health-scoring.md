# 健康评分

> 来源：gfreedman/mac_audit + lu-zhengda/macos-toolkit/machealth

## 扣分规则

| 严重度 | 扣分 | 示例 |
|--------|:---:|------|
| 🔴 Critical（安全/系统） | -15 | FileVault 关闭、Firewall 禁用 |
| 🔴 Critical（其他） | -10 | 磁盘 <5%、Swap 满载 |
| 🟡 Warning（安全/系统） | -4 | 屏幕锁 >10min |
| 🟡 Warning（其他） | -3 | 电池 <85%、缓存 >5GB |

## 评分带

| 分数 | 等级 |
|------|------|
| 95-100 | 卓越 🟢 |
| 85-94 | 很好 🟢 |
| 70-84 | 良好 🟡 |
| 55-69 | 一般 🟠 |
| <55 | 差 🔴 |

## 子系统权重

| 子系统 | 权重 |
|--------|:---:|
| Security | 25% |
| Memory | 20% |
| Disk | 15% |
| CPU | 15% |
| Hardware | 10% |
| Network | 10% |
| Dev Env | 5% |

## Exit Code

| Code | 含义 | 范围 |
|:----:|------|:----:|
| 0 | 健康 | 80-100 |
| 1 | 降级 | 50-79 |
| 2 | 危险 | 0-49 |
