# AppleScript Calendar Operations

## 日期创建陷阱

`date "Thursday, June 4, 2026 at 9:00:00 AM"` 这种自然语言日期格式在 osascript 中**不稳定**，经常报 `-30720` 语法错误。

### 推荐方式：current date + 属性设置

```applescript
set startDate to current date
set month of startDate to June
set day of startDate to 4
set year of startDate to 2026
set hours of startDate to 9
set minutes of startDate to 0
set seconds of startDate to 0

set endDate to startDate + (3 * hours)
```

### 创建事件（完整模板）

```applescript
tell application "Calendar"
  tell calendar "个人1"
    set startDate to current date
    set month of startDate to June
    set day of startDate to 4
    set year of startDate to 2026
    set hours of startDate to 9
    set minutes of startDate to 0
    set seconds of startDate to 0
    
    set endDate to startDate + (3 * hours)
    
    set theEvent to make new event with properties {¬
      summary:"🏥 事件标题", ¬
      start date:startDate, ¬
      end date:endDate, ¬
      location:"地点", ¬
      description:"备注内容"}
    
    -- 添加提醒（秒为单位，负数为提前）
    make new display alarm at theEvent with properties {trigger interval:-1440} -- 1天前
  end tell
end tell
```

### 常用 reminder 秒数

| 提前量 | trigger interval |
|--------|:-----------------|
| 1 天 | -86400 |
| 1 小时 | -3600 |
| 30 分钟 | -1800 |
| 15 分钟 | -900 |
| 事件开始时 | 0 |
