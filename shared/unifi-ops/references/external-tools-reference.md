# 第二轮搜索 — SSH 专精工具参考

## 最佳参考：patricegautier/unifiZabbix

GitHub: `github.com/patricegautier/unifiZabbix`

**核心价值**：通过 SSH + mca-dump 直接采集数据，无需 Controller API。和 unifi-ops 路线一致。

### mca-dump-short.sh — JSON 设备类型验证器

```bash
# 设备类型验证规则（jq 表达式）
AP:      '.vap_table? != null and .radio_table != null'
UDMP:    '.network_table? != null'
USG:     '.network_table? != null and .network_table | map(select(.mac!=null)) | length>0'
```

### ssh-run.sh — 通用 SSH 执行器

```bash
# 支持私钥或密码
./ssh-run.sh -u admin -p passfile -d <internal IP redacted> <command>

# Legacy 设备加 RSA 支持
./ssh-run.sh -u admin -p passfile -r -d <ip> <command>
```

## 其他工具

| 工具 | 方式 | 亮点 | 适用 |
|------|------|------|------|
| Kerwood/Ubiquiti-Tools | SSH | ARP 扫 MAC + SSH info | ✅ 发现设备 |
| stevejenkins/unifi-linux-utils | SSH | 批量固件升级 | ✅ 运维 |
| rvben/unifi-cli | API | Go CLI + TUI 仪表盘 | ❌ 需 API |
| hyperb1iss/unifly | API | 28 命令 + TUI | ❌ 需 API |
| nachtschatt3n/unifictl | API | Rust + AI-optimized | ❌ 需 API |

## 可借鉴的设计模式

### 1. 设备类型验证（来自 unifiZabbix）

在执行 SSH 命令后，验证返回 JSON 是否符合预期：

```python
VALIDATORS = {
    'uap': ['.vap_table', '.radio_table'],       # AP 必须有这两个
    'usw': ['.port_table'],                       # 交换机必须有
    'ugw': ['.network_table'],                    # USG 必须有
}
```

### 2. 超时 + 重试（来自 mca-dump-short.sh）

```bash
# 5 秒 SSH 连接超时
SSH_CONNECT_TIMEOUT=5
# 可重试错误码
RETRIABLE_ERROR=250
```

### 3. 批量并行采集

```bash
# Zabbix 的方式：为每类设备分别采集
for device_type in AP SWITCH USG; do
  mca-dump-short.sh -t $device_type -u admin -d $ip &
done
```

### 4. CLI 命令设计（来自 unifi-cli/unifly）

```
unifi devices list --watch          # 实时刷新
unifi clients list --wired          # 有线客户端
unifi tui                           # TUI 仪表盘
unifi system health                 # 子系统健康
```
