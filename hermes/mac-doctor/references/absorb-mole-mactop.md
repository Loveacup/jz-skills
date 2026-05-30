# 吸收方案：tw93/mole + metaspartan/mactop

> CC 写作，2026-05-30。13 项吸收方案，按 P0-P3 分级。

## 七个盲区

| 盲区 | 现状 | 缺什么 | 来源 |
|---|---|---|---|
| 健康分是阶梯静态扣分 | Critical -15、Warning -4 | 渐变扣分（线性插值） | mole |
| 告警是瞬时超阈值 | CPU >80% 就 🔴 | 持续时长窗口（≥N 分钟） | mole |
| 硬件缺功耗维度 | 只看电池/SMART | SoC/CPU/GPU/ANE/DRAM 瓦数、带宽、风扇 RPM | mactop |
| 热分级用 pmset -g therm | 只看节流 | NSProcessInfo.thermalState 四档 | mactop |
| Wi-Fi 只到 RSSI/TX Rate | 有 RSSI/Noise | PHY Mode → Wi-Fi 6/7 映射、Thunderbolt 拓扑 | mactop |
| Dev 审计只扫 ~/.cache | 看用户级缓存 | 项目 build artifacts 残留（node_modules/target/venv 等） | mole |
| 清理无安全闸 | 直接 rm | dry-run + whitelist + operation log | mole |

## 优先级

| 优先级 | 项 | 工作量 |
|:---:|---|:---:|
| P0 | A3 单行诊断 + E1 窗口告警 + D2 dry-run 安全闸 | 中 |
| P1 | A1 渐变扣分 + D1 build artifacts + B1 功耗 | 中 |
| P2 | A2 uptime + B3 thermalState + C1 Wi-Fi gen + F1 count/interval | 小 |
| P3 | B2 风扇 + B4 DRAM + C2 TB + D3 installer + F2/F3 schema | 中 |

## 不吸收

- mole TUI 菜单、Shell completion
- mactop Fan Control（写 SMC 越界）、Prometheus、Menubar、Party Mode
- mole Visual disk analyzer（Tier 2a 已有 du -sh）

## 落地后

- 更新版本 2.1.0 → 2.2.0
- 新建 `references/tier2c-power-fan.md`（B1+B2+B4）
- 新建 `references/tier3-cleanup-safety.md`（D2）
