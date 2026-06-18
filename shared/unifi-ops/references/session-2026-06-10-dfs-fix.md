# DFS 信道迁移 + 全线巡检实录

**日期**: 2026-06-10
**异常**: 全线 5GHz RadarDetected 告警 ×5，全部 AP 挤 ch36；Port 13 100M 未知设备
**结果**: ✅ 信道分散到 ch149-161，DFS 告警已归档

---

## DFS Radar 根因

- 全部 6 台 AP 配置在 ch36 (5180MHz, DFS 信道)
- 4 台 AP 在不同日期检测到雷达信号
- 同频干扰加剧——6 台共享同一信道

## 解决方案

### 信道分频表

| AP | 原信道 | 新信道 | 频段 |
|----|--------|--------|------|
| 客厅 | 36 | 149 | UNII-3（非 DFS）|
| 起居室 | 36 | 153 | UNII-3 |
| 客卧 | 36 | 157 | UNII-3 |
| 主卧 | 36 | 161 | UNII-3 |
| 次卧 | 36 | 149 | UNII-3 |
| 可乐罐 | 36 | 153 | UNII-3 |

### 执行步骤

1. MongoDB `radio_table.channel` 更新（6 台）
2. AP 本地 `sed` 改 `radio.2.channel` → `cfgmtd -w` → sysrq 重启
3. 分两批重启：客厅/客卧/次卧 → 起居室/主卧/可乐罐
4. 主卧重启后补 bridge+hostapd
5. MCA dump 验证信道 + satisfaction
6. 归档 RadarDetected 告警

### 踩坑

- **可乐罐 cfgmtd 静默失败**：第一次 sed+cfgmtd+重启后仍 ch36。原因：cfgmtd -w 输出显示成功但未实际持久化。解决：改前 grep 确认，改后 grep 验证，再次 cfmtd -w + reboot → 成功。

## 全线巡检结果（信道调整后）

| AP | 5GHz 信道 | 满意度 |
|----|----------|--------|
| 客厅 | ch149 | 98 |
| 起居室 | ch153 | 98 |
| 客卧 | ch157 | 96 |
| 主卧 | ch161 | 99 |
| 次卧 | ch149 | 98 |
| 可乐罐 | ch153 | 96 |

---

## Port 13 100M 设备排查

交换机 US-16-150W ASIC 芯片不暴露 MAC/FDB 表，无法通过 SSH 确定端口-设备映射。

**排除已知端口后候选**（有线智能家居设备）：

| 设备 | MAC | 可疑度 |
|------|-----|--------|
| terncy-99008fe | 1c:82:59:90:08:fe | ⭐⭐⭐ |
| smarthomefansbox-super | 02:00:00:23:1e:01 | ⭐⭐ |
| houzzkit | 3a:87:9f:0d:75:9f | ⭐⭐ |
| IP3-Century ×2 | 84:47:09:12:b7:5b/.5c | ⭐⭐ |

**结论**：100M 非故障（IoT 设备无需千兆），搁置待 Controller Web UI 查。
