import sys
import subprocess
from pathlib import Path

def get_weather():
    print("Test weather...")
    try:
        subprocess.run(["curl", "-s", "-m", "5", "wttr.in"], timeout=7)
        print("Weather done")
    except:
        print("Weather failed/timed out")

def get_calendar():
    print("Test calendar...")
    try:
        subprocess.run(["osascript", "-e", "tell application \"Calendar\" to count calendars"], timeout=5)
        print("Calendar done")
    except:
        print("Calendar failed/timed out")

def get_ai():
    print("Test AI logs...")
    sys.path.append('~/clawd/scripts')
    try:
        from extract_ai_conversations_summary import extract_claude_summary
        extract_claude_summary('2026-02-13')
        print("AI done")
    except:
        print("AI failed")

get_weather()
get_ai()
get_calendar()
print("All done")
