#!/usr/bin/env python3
"""
Calendar Archiver - Archive old events from macOS Calendar.app
Moves events older than N days to a history/archive calendar
"""

import subprocess
import sys
from datetime import datetime, timedelta

def run_applescript(script):
    """Execute AppleScript and return result"""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def ensure_archive_calendar_exists():
    """Create archive calendar if it doesn't exist"""
    script = '''
    tell application "Calendar"
        activate
        try
            calendar "History Archive"
            return "exists"
        on error
            make new calendar with properties {name:"History Archive"}
            return "created"
        end try
    end tell
    '''
    return run_applescript(script)

def count_events(calendar_name):
    """Count events in a calendar"""
    script = f'''
    tell application "Calendar"
        tell calendar "{calendar_name}"
            return count of events
        end tell
    end tell
    '''
    out, err, code = run_applescript(script)
    try:
        return int(out) if code == 0 else 0
    except:
        return 0

def archive_old_events(source_cal="Naomi", days_back=90, dry_run=False):
    """Archive events older than days_back days"""
    
    # Ensure archive calendar exists
    ensure_archive_calendar_exists()
    
    # Calculate cutoff date
    cutoff = datetime.now() - timedelta(days=days_back)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Archiving events from '{source_cal}' older than {cutoff_str}")
    
    # Get old events (limited to first 300 to avoid timeout)
    get_script = f'''
    tell application "Calendar"
        tell calendar "{source_cal}"
            set now to current date
            set cutoffDate to now - ({days_back} * days)
            set oldEvents to {{}}
            
            repeat with evt in events 1 thru 300
                try
                    if (start date of evt) < cutoffDate then
                        set eventInfo to {{
                            summary:summary of evt,
                            startDate:start date of evt,
                            endDate:end date of evt
                        }}
                        set end of oldEvents to eventInfo
                    end if
                end try
            end repeat
            
            return oldEvents
        end tell
    end tell
    '''
    
    out, err, code = run_applescript(get_script)
    
    if code != 0:
        print(f"Error finding events: {err}")
        return 0
    
    # Count how many events were found (rough parsing)
    event_count = out.count('summary:') if out else 0
    print(f"Found approximately {event_count} events to archive")
    
    if dry_run:
        print("DRY RUN - no changes made")
        return 0
    
    # Archive and delete each old event
    archive_script = f'''
    tell application "Calendar"
        tell calendar "{source_cal}"
            set targetCal to calendar "History Archive"
            set now to current date
            set cutoffDate to now - ({days_back} * days)
            set archivedCount to 0
            
            repeat with evt in events 1 thru 300
                try
                    if (start date of evt) < cutoffDate then
                        tell targetCal
                            make new event with properties {{
                                summary:(summary of evt) & " [from:{source_cal}]",
                                start date:(start date of evt),
                                end date:(end date of evt)
                            }}
                        end tell
                        delete evt
                        set archivedCount to archivedCount + 1
                    end if
                end try
            end repeat
            
            return archivedCount
        end tell
    end tell
    '''
    
    out, err, code = run_applescript(archive_script)
    
    if code == 0:
        try:
            count = int(out)
            print(f"Archived {count} events successfully")
            return count
        except:
            print(f"Result: {out}")
            return 0
    else:
        print(f"Error during archive: {err}")
        return 0

if __name__ == "__main__":
    # Parse arguments
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    source = sys.argv[2] if len(sys.argv) > 2 else "Naomi"
    dry = sys.argv[3] == "--dry-run" if len(sys.argv) > 3 else False
    
    # Show current counts
    print(f"Current events in {source}: {count_events(source)}")
    print(f"Current events in History Archive: {count_events('History Archive')}")
    print()
    
    # Run archive
    archive_old_events(source, days, dry)
    
    # Show updated counts
    print()
    print(f"After archive:")
    print(f"Events in {source}: {count_events(source)}")
    print(f"Events in History Archive: {count_events('History Archive')}")
