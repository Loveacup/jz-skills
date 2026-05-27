#!/bin/bash
# Calendar Archive Wrapper - 季度归档入口脚本
# Usage: ./archive-calendar.sh [calendar_name] [days]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALENDAR_NAME="${1:-Naomi}"
DAYS_BACK="${2:-90}"

echo "🗓️  Calendar Archive Tool"
echo "========================"
echo "Source: $CALENDAR_NAME"
echo "Archive events older than: $DAYS_BACK days"
echo ""

# Activate Calendar.app first
open -a Calendar
sleep 2

# Run archive
python3 "$SCRIPT_DIR/archive_old_events.py" "$DAYS_BACK" "$CALENDAR_NAME"

echo ""
echo "Done!"
