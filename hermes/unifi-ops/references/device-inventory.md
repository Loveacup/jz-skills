# 家中 UniFi 设备清单

> 通过 MongoDB `db.device.find()` + SSH `mca-dump` 双重验证

| 名称 | 型号 | 类型 | IP | MAC | 固件 | SSH |
|------|------|------|-----|-----|------|-----|
| 网关 | UGW3 (USG-3P) | ugw | WAN 60.176.157.47 | 18:e8:29:4c:6e:f2 | v4.4.57 | ❌ (公网IP) |
| 交换机 | US16P150 | usw | <internal IP redacted> | 18:e8:29:2a:0c:93 | v7.4.1 | ✅ |
| 起居室 | UHDIW (UAP-HD-IW) | uap | <internal IP redacted> | 18:e8:29:be:9a:67 | v6.7.41 | ✅ |
| 客厅 | UHDIW (UAP-HD-IW) | uap | <internal IP redacted> | 18:e8:29:be:99:a7 | v6.7.41 | ✅ |
| 客卧 | U7NHD (UAP-nanoHD) | uap | <internal IP redacted> | b4:fb:e4:2b:89:71 | v6.7.41 | ✅ |
| 主卧 | UHDIW (UAP-HD-IW) | uap | <internal IP redacted> | 18:e8:29:bc:fa:a3 | v6.7.41 | ✅ | mesh 卫星 |

## 备注

- **主卧 AP** 是 mesh 卫星节点（无线 uplink），satisfaction=-1 属正常，无直接有线回程
- **网关** 为 USG-3P (UGW3)，WAN IP 60.176.157.47 无法内网 SSH
| 次卧 | UHDIW (UAP-HD-IW) | uap | <internal IP redacted> | 18:e8:29:be:a1:8f | v6.7.41 | ✅ |
| 可乐罐 | UFLHD (UAP-FlexHD) | uap | <internal IP redacted> | 68:d7:9a:46:5c:8b | v6.7.17 | ✅ |

## SSH 凭据

- Controller: `root:<password redacted>@<internal IP redacted>`
- 所有设备: `admin:<password redacted>`
- Controller MongoDB: `127.0.0.1:27117`，数据库 `ace`

## Controller

- OS: Debian 8 (jessie)
- UniFi: Java 进程， `/usr/lib/unifi/`
- MongoDB: 2.4.10 @ 27117，数据库 `ace`
- API: `https://<internal IP redacted>:8443/api/login`
- 2FA 登录格式: `密码|验证码`（不适用于 `/api/auth/login`）
- 固件缓存: `/usr/lib/unifi/data/firmware.json`

## 拓扑关系（LLDP 发现）

```
USG-3P (WAN) → US16P150 (<internal IP redacted>) → 各 AP
  Port 6 → 主卧 AP (<internal IP redacted>) → PoE Out → 可乐罐 (<internal IP redacted>)
  Port ? → 客厅 AP (<internal IP redacted>)
  Port ? → 起居室 (<internal IP redacted>)
  Port ? → 客卧 (<internal IP redacted>)
  Port ? → 次卧 (<internal IP redacted>)
```

## 刷新设备清单

```bash
# 从 MongoDB 刷新
sshpass -p '<password redacted>' ssh root@<internal IP redacted> \
  'mongo --port 27117 ace --quiet --eval "print(JSON.stringify(db.device.find({},{name:1,model:1,ip:1,mac:1,version:1,type:1}).toArray()))"'
```
