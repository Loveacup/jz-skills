# 日历归档功能

## 概述

Naomi/Zelda 日历事件过多会导致 AppleScript 不稳定，因此每季度自动归档超过 90 天的历史事件。

## 工作原理

- **频率**：每季度执行一次（1/4/7/10 月 1 号凌晨 2 点）
- **目标**：归档超过 90 天的事件
- **源日历**：Naomi1、Zelda1（`<email redacted>` iCloud 账户）
- **归档目标**：History Archive 日历（自动创建）

## 手动执行

```bash
# 归档 Naomi1（默认 90 天）
bash ~/.hermes/skills/calendar-manager/scripts/archive-calendar.sh Naomi1

# 归档 Zelda1（自定义 60 天）
bash ~/.hermes/skills/calendar-manager/scripts/archive-calendar.sh Zelda1 60

# Python 直接执行
python3 ~/.hermes/skills/calendar-manager/scripts/archive_old_events.py 90 Naomi1
```

## 归档规则

1. **只归档历史事件**：开始时间早于 90 天前
2. **保留原信息**：归档后标题添加 `[from:源日历]` 标记
3. **安全限量**：每次最多处理 300 个事件
4. **自动创建目标**：History Archive 日历不存在时自动创建

## 自动化

Cron job `季度日历归档`：每年 1/4/7/10 月 1 号 02:00 自动执行，归档 Naomi1 + Zelda1，完成后发送 Telegram 报告。

## 注意事项

- 归档前自动激活 Calendar.app
- 损坏的事件自动跳过
- 建议每季度检查归档结果
