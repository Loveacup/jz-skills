# MongoDB 集合说明

UniFi Controller (v6.x) 数据库 `ace`，MongoDB 2.4。

## 核心集合

| 集合 | 说明 | 关键字段 |
|------|------|---------|
| `device` | 所有网络设备 | name, model, type, ip, mac, version, state, adopted, uptime |
| `user` | 已知客户端 | mac, ip, hostname, oui, is_wired, last_seen, tx_bytes, rx_bytes |
| `alarm` | 告警 | msg, time, archived, subsystem |
| `event` | 事件日志 | msg, time, key, subsystem |
| `site` | 站点 | name, desc |
| `wlanconf` | WiFi 配置 | name, security, enabled, wpa_mode |
| `networkconf` | 网络配置 | name, vlan, ip_subnet |
| `setting` | 站点设置 | key (各种设置) |
| `admin` | 管理员 | name, email |
| `account` | UniFi 账户 | name, email, local_id |

## 常用查询

```javascript
// 设备清单
db.device.find({}, {name:1, model:1, ip:1, version:1, state:1})

// 在线设备
db.device.find({state: 1})

// AP 设备
db.device.find({type: "uap"})

// 最近活跃客户端 (24h)
db.user.find({"last_seen": {$gt: <timestamp_ms>}})

// 客户端总数
db.user.count()

// 当前告警 (未归档)
db.alarm.find({archived: {$ne: true}})
```

## 注意事项

- MongoDB 2.4 不支持 `_id: 0` 投影，需用 `JSON.stringify()` 时手动过滤
- 时间戳为毫秒级 Unix timestamp
- MAC 地址小写无分隔符 (如 `18e829be9a67`)
- `state`：1=在线，0=离线，2=待采纳，3=升级中
- ⚠️ CLI 是 `mongo`（不是 `mongosh`），客户端超时可能因旧认证协议
- `_id` 字段为 `{str: "..."}` 格式（MongoDB ObjectId 旧序列化），解析时需转换
- 查询时用 `--quiet` 避免 mongo shell 启动 banner 混入 JSON
