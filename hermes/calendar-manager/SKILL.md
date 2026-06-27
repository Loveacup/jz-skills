---

name: calendar-manager
description: |
type: routine
  管理 macOS Calendar.app 和 Apple Reminders 的智能助手。自动识别重复日程、智能判断日历归属（个人/工作/Naomi/Zelda）、医疗类日程特殊处理、网球课地点自动匹配、待办事项自动分流。
  
  触发场景：添加日历、日程、网球课、脱敏治疗、删除日程、改时间、这周安排、Naomi、Zelda
  DO NOT use for: 查询天气、设置闹钟、纯文档编辑、非日历类查询

---

# Calendar Manager - 智能日历管理

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "加个日历而已，直接 AppleScript 就行" | 跳过 7 步流水线 = 丢失去重、归属判断、emoji 模板、地点匹配 |
| "用户只说加日程，没说是哪个日历" | skill 有完整归属关键词规则，不该额外问用户 |
| "用 AppleScript 查就行" | icalBuddy 推荐（无权限弹窗），AppleScript 是备用方案 |
| "提醒写 Reminders 里就行" | 孩子医疗/教育类提醒必须写入对应孩子日历（Naomi1/Zelda1），不要拆到 Reminders |
| "网球课地点用户又没明确说" | 默认冠享网球俱乐部，"水印城/钱江湾"→乐不思，skill 已规定 |

## 概述

核心：**7 步流水线**处理每个日程请求。所有日历操作默认针对 `<email redacted>` iCloud 账户下的 `个人1 / 工作1 / Naomi1 / Zelda1`。**不要写入不带 `1` 的旧日历。**

## 日历结构

| 优先级 | 日历 | 实际名称 | 用途 |
|-------|------|---------|------|
| 1 | 个人 | 个人1 | Alex 个人事务 |
| 2 | 工作 | 工作1 | 工作会议、商务 |
| 3 | Naomi | Naomi1 | Naomi（懿涵）所有日程 |
| 4 | Zelda | Zelda1 | Zelda（若涵）所有日程 |

## 核心处理流程

```
用户输入
    ↓
[1. 解析意图] → 提取标题、时间、地点、备注
    ↓
[2. 类型判断] → 日历事件 or 待办事项？
    ├─→ 待办 → 转 Reminders
    └─→ 日历事件 → 继续
    ↓
[3. 日历归属] → 关键词匹配
    ├─→ 含 "Naomi/懿涵" → Naomi1
    ├─→ 含 "Zelda/若涵/妹妹" → Zelda1
    ├─→ 含 "会议/工作" → 工作1
    └─→ 默认 → 个人1
    ↓
[4. 重复检测] → icalBuddy 查目标日历当日
    ├─→ 精确重复（标题+时间+地点）→ 自动合并
    ├─→ 时间冲突 → 询问用户（替换/保留/合并）
    └─→ 无重复 → 创建
    ↓
[5. 智能增强] → 应用场景规则（详见 rules.md）
    ├─→ 🏥 医疗 → 3h 时长 + 就诊卡 + 1天前提醒
    ├─→ 🏃 网球课 → 自动匹配地点
    └─→ 🎓 教育 → 关联备注
    ↓
[6. 格式化] → 加 emoji + 结构化备注
    ↓
[7. 确认执行] → 展示结果，等用户确认
```

## 工具选型

**查询：优先 icalBuddy**（无权限弹窗）。AppleScript 备用 → `references/applescript-operations.md`。

```bash
# 今日所有日历
icalBuddy eventsToday

# 指定日历+日期范围
icalBuddy -ic "个人1,工作1,Naomi1,Zelda1" eventsFrom:2026-02-13 to:2026-02-14

# 关键词过滤
icalBuddy -ic "Naomi1,Zelda1" eventsToday | grep "网球"
```

**写入/修改/删除：AppleScript osascript。** 详见 `references/applescript-operations.md`。

⚠️ **AppleScript 日期陷阱**：`date "Thursday, June 4, 2026 at 9:00:00 AM"` 格式在 osascript 中会报 `-30720` 语法错误。不要用字符串日期，改用 `current date` + 逐属性设置：

```applescript
set startDate to current date
set month of startDate to June
set day of startDate to 4
set year of startDate to 2026
set hours of startDate to 9
set minutes of startDate to 0
set seconds of startDate to 0
set endDate to startDate + (3 * hours)  -- 3h 医疗默认
```

## 智能询问规则

以下情况暂停并询问用户。**询问必须用 `clarify` + `choices`（最多 4 选项）。**

| 场景 | 内容 |
|------|------|
| 日期模糊 | 22:00~06:00 "今晚/明早" 歧义 |
| 信息不完整 | 仅活动名无时间 |
| 时间冲突 | 同时段有不同活动 |
| 归属不明 | 无法判断是孩子还是个人 |
| 地点模糊 | "老地方"等 |

## 关键规则速查

### 标题 emoji

| 类型 | emoji | 触发词 |
|------|-------|-------|
| 医疗 | 🏥 | 脱敏、门诊、牙医、眼科 |
| 网球 | 🎾 | 网球课、打网球 |
| 教育 | 🎓 | 合唱、课程、考试、开学 |
| 运动 | 🏃 | 游泳、跑步、健身 |
| 社交 | 🍽️ | 聚餐、宴请、约会 |
| 旅行 | ✈️ | 出差、旅游、航班 |
| 工作 | 💼 | 会议、面试、汇报 |

### 提醒默认值

| 类型 | 默认提前 |
|------|---------|
| 🏥 医疗 | 1 天 |
| 💼 工作/会议 | 30 分钟 |
| 🎓 教育/课程 | 1 小时 |
| 🍽️ 社交 | 1 小时 |
| ✈️ 旅行 | 1 天 |

### 全天 vs 时间事件

| 输入特征 | 判定 |
|---------|------|
| 含具体时间 | ⏰ 时间事件 |
| "全天/一整天" | 📅 全天事件 |
| 节假日 | 📅 全天事件 |
| 仅日期无时间 | ⚠️ 询问 |

**临时占位规则**：即使"先排时间占位"，也必须创建**带预估时间段的时间事件**（晚饭默认 18:00-20:00，午饭 12:00-13:30），备注写「临时预估，待更新」。不要创建全天事件。

### 孩子医疗提醒归属

Naomi/Zelda 的医疗预约/随访提醒**必须写入对应孩子日历**（Naomi1/Zelda1），不要拆到 Apple Reminders。

## 详细规则参考

| 文件 | 何时读取 |
|------|---------|
| `references/rules.md` | 医疗规则、网球课地点、emoji 完整映射、日期歧义、冲突处理、合并/拆分 |
| `references/examples.md` | 常见场景输入输出 |
| `references/workflows.md` | CRUD/去重/重复事件流程图 |
| `references/screenshots-to-calendar.md` | 截图转日历（医院预约、演出票等）|
| `references/applescript-operations.md` | AppleScript 备用代码（CRUD、去重查询、Reminders）|
| `references/archiving.md` | 季度归档功能 |
| `references/calendar-account-migration.md` | 账户迁移细节 |

## 🚫 禁止操作

| 禁止 | 原因 | 替代 |
|------|------|------|
| **删除日历** | 数据丢失 + iCloud 同步问题 | 归档旧事件 |
| **重建日历** | 可能创建本地日历（非 iCloud）| 修改现有事件 |
| **批量移动事件至其他账户** | 重复 + 同步冲突 | 手动逐个确认 |

---

## ✅ 执行验证清单

- [ ] 是否用 icalBuddy 做了重复检测？
- [ ] 归属日历是否正确（Naomi1/Zelda1/工作1/个人1 带 `1`）？
- [ ] 标题是否加了对应 emoji？
- [ ] 医疗类是否标注 3h 时长 + 携带就诊卡？
- [ ] 网球课是否匹配了正确地点（默认冠享，水印城/钱江湾→乐不思）？
- [ ] 孩子医疗提醒是否写入对应孩子日历而非 Reminders？
- [ ] 是否向用户展示了结果并等待确认？

## ⚠️ 已记录陷阱

### AppleScript 日期格式不可靠

`date "Thursday, June 4, 2026 at 9:00:00 AM"` 这种字符串格式在部分 macOS 语言/区域设置下会报 `无效的日期与时间` 错误（-30720）。

**可靠替代**：用 `current date` + 逐属性设置。

```applescript
-- ❌ 不可靠
set startDate to date "Thursday, June 4, 2026 at 9:00:00 AM"

-- ✅ 可靠
set startDate to current date
set month of startDate to June
set day of startDate to 4
set year of startDate to 2026
set hours of startDate to 9
set minutes of startDate to 0
set seconds of startDate to 0
set endDate to startDate + (3 * hours)
```

> 2026-06-01 实测：`date "Thursday, June 4, 2026 at 9:00:00 AM"` 在 macOS 26.2 (zh-CN) 下失败，程序化方式成功。

### 移动事件：不要直接修改 start/end date

直接 `set start date of ev to newStart` + `set end date of ev to newEnd` 会报 `-10025` 错误（"开始日期必须早于结束日期"），即使 newStart 确实早于 newEnd。

**可靠替代**：delete + recreate（详见 `references/applescript-operations.md` 的「移动事件」章节）。

> 2026-06-04 实测：移「🏥 省口腔·张睿（检查）」从 6/4 到 6/5，直接改日期连续失败 4 次，delete+recreate 一次成功。
