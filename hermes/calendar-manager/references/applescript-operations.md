# AppleScript 备用操作

当 icalBuddy 不可用时使用 AppleScript 备用方案。

## 注意事项

首次使用需授权：**系统设置 → 隐私与安全性 → 自动化**。

## Calendar 自动启动

```bash
pgrep -x "Calendar" > /dev/null || open -a Calendar
sleep 3
```

## Calendar.app CRUD

### 获取事件列表

```bash
osascript -e '
tell application "Calendar"
    tell calendar "个人1"
        events of today
    end tell
end tell'
```

### 创建事件

```bash
osascript -e '
tell application "Calendar"
    tell calendar "Naomi1"
        make new event with properties {summary:"🎾 网球课", start date:current date, end date:(current date + 3600)}
    end tell
end tell'
```

### 删除事件

```bash
osascript -e '
tell application "Calendar"
    delete (first event of calendar "工作1" whose summary contains "会议")
end tell'
```

### 修改事件

```bash
osascript -e '
tell application "Calendar"
    tell calendar "Naomi1"
        set summary of first event where summary contains "网球课" to "🎾 网球课-乐不思"
    end tell
end tell'
```

### 批量删除

```bash
osascript -e '
tell application "Calendar"
    tell calendar "Naomi1"
        delete (every event whose summary contains "网球课")
    end tell
end tell'
```

## 重复检测查询（AppleScript）

```bash
osascript << 'EOF'
tell application "Calendar"
    set targetDate to current date
    set year of targetDate to 2026
    set month of targetDate to 2
    set day of targetDate to 13
    set time of targetDate to 0

    set endDate to targetDate + 1 * days

    tell calendar "Naomi1"
        set todayEvents to every event whose start date ≥ targetDate and start date < endDate
        set eventList to {}
        repeat with evt in todayEvents
            set end of eventList to (summary of evt)
        end repeat
        return eventList
    end tell
end tell
EOF
```

## Apple Reminders 操作

### 获取提醒列表

```bash
osascript -e '
tell application "Reminders"
    get name of every reminder in list "家庭"
end tell'
```

### 创建提醒

```bash
osascript -e '
tell application "Reminders"
    tell list "家庭"
        make new reminder with properties {name:"买牛奶", due date:(current date)}
    end tell
end tell'
```
