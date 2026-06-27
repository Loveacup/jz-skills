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

## 移动事件（改日期）

### ⚠️ 直接修改 `start date` / `end date` 不可靠

即使新日期计算正确（newStart < newEnd 验证通过），直接设置 `start date` / `end date` 可能报错：

```
Failed to save event [...], with error [{
    NSLocalizedDescription = "开始日期必须早于结束日期。";
}] (-10025)
```

此错误发生在部分事件上（可能与会话状态、alarms、或其他内部约束有关），日期计算本身无误。

### ✅ 可靠方案：delete + recreate

```applescript
tell application "Calendar"
  -- 1. 跨日历搜索找到目标事件
  set theEvent to missing value
  set theCal to missing value
  repeat with cal in calendars
    try
      repeat with ev in (every event of cal)
        try
          if (summary of ev) contains "关键词" then
            -- 可选：进一步按日期筛选
            set theEvent to ev
            set theCal to cal
            exit repeat
          end if
        end try
      end repeat
    end try
    if theEvent is not missing value then exit repeat
  end repeat
  
  if theEvent is not missing value then
    -- 2. 保存属性
    set evSummary to summary of theEvent
    set evNotes to description of theEvent
    set evLocation to location of theEvent
    
    -- 3. 构造新日期
    set newStart to current date
    set month of newStart to June
    set day of newStart to 5
    set year of newStart to 2026
    set hours of newStart to 9
    set minutes of newStart to 0
    set seconds of newStart to 0
    
    set newEnd to current date
    set month of newEnd to June
    set day of newEnd to 5
    set year of newEnd to 2026
    set hours of newEnd to 12
    set minutes of newEnd to 0
    set seconds of newEnd to 0
    
    -- 4. 在新日历创建事件
    tell calendar "个人1"
      set newEv to make new event with properties {¬
        summary:evSummary, ¬
        start date:newStart, ¬
        end date:newEnd, ¬
        description:evNotes, ¬
        location:evLocation}
      -- 重新添加提醒
      make new display alarm at newEv with properties {trigger interval:-1440}
    end tell
    
    -- 5. 删除旧事件
    delete theEvent
  end if
end tell
```

### 按 UID 跨日历搜索

当已知事件 UID 时：

```applescript
set theEvent to missing value
repeat with cal in calendars
  try
    set ev to event id "49E51DD0-..." of cal
    set theEvent to ev
    exit repeat
  end try
end repeat
```

### 去重清理

delete + recreate 多次尝试可能导致重复事件。用全量扫描+计数清理：

```applescript
tell application "Calendar"
  set personalCal to calendar "个人1"
  set evs to (every event of personalCal)
  set found to 0
  repeat with ev in evs
    try
      if (summary of ev) contains "关键词" then
        if found = 0 then
          set found to 1  -- 保留第一个
        else
          delete ev  -- 删除其余重复
        end if
      end if
    end try
  end repeat
end tell
```
