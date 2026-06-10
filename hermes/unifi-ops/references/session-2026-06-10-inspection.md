# 2026-06-10 全设备巡检记录

## 巡检概况
- 时间：2026-06-10 16:57
- 方式：SSH 直连 + mca-dump + MongoDB
- 耗时：16s 并行扫描
- 结果：7/7 在线

## 发现的异常

### 1. 主卧 AP — satisfaction=-1，SSID 异常
- **症状**：satisfaction=-1，VAP 只有 `element-cace8a1835b8551c` 和 `vwire`
- **根因**：Controller WLAN 配置中包含 element-... 这个独立 SSID，主卧 AP 被分配了它而非 `1201-ubnt`
- **修复尝试**：
  1. MongoDB 禁用 element WLAN → **无效**（AP 不接收更改）
  2. 重启 Controller + 重启 AP → **无效**（配置未推送）
  3. API force-provision → **部分成功**（element 被清除，但 1201-ubnt 未补上）
  4. 需要在 Controller Web UI 中重新分配 WLAN → **待办**
- **教训**：MongoDB 直改不触发 Controller provision。AP WLAN 分配必须通过 API/Web UI。

### 2. 可乐罐固件落后
- **症状**：v6.7.17 vs 其他 AP v6.7.41
- **修复**：`selfupgrade` 自动下载 v6.7.41 (10.7MB)，reboot 后生效（待验证）
- **发现**：firmware.json 在 Controller `/usr/lib/unifi/data/firmware.json`，FW URL 在 `fw-download.ubnt.com`

### 3. 物理拓扑发现
- LLDP 发现主卧 AP 连交换机 Port 6
- 可乐罐通过主卧 AP PoE 输出口供电（菊花链）

## 关键技术发现

### API 2FA 登录公式
```
密码|验证码  (pipe 分隔)
```
例：`<password redacted>|809822`
- 端点：`POST /api/login`（非 `/api/auth/login`）
- 必须 `--http1.1`，HTTP/2 有协议错误

### 固件升级命令变迁
- 旧 AP：`upgrade <url>`
- 新 AP (v6.7+)：`selfupgrade`（自动拉取）或 `fwupdate`（手动）

### MongoDB 修改限制
- 直接改 `ace` 数据库不触发 AP 配置推送
- 需通过 API `force-provision` 或重启 Controller + AP

### 设备 SSH 凭据
- 全部设备：admin/<password redacted>（与 Controller 密码相同）
- Controller：root/<password redacted>

### Controller 进程
- Debian 8 (jessie)
- UniFi Java + MongoDB 2.4.10
- 重启：`/etc/init.d/unifi restart`
- 启动约 45-60 秒
