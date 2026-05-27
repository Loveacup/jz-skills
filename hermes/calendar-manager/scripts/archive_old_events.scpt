on run argv
    set daysBack to 90
    set sourceCalName to "Naomi"
    set targetCalName to "History Archive"
    
    if (count of argv) > 0 then set daysBack to (item 1 of argv as integer)
    if (count of argv) > 1 then set sourceCalName to (item 2 of argv)
    if (count of argv) > 2 then set targetCalName to (item 3 of argv)
    
    tell application "Calendar"
        activate
        try
            set targetCal to calendar targetCalName
        on error
            set targetCal to make new calendar with properties {name:targetCalName}
        end try
        
        set cutoffDate to (current date) - (daysBack * days)
        set archivedCount to 0
        set errorCount to 0
        
        try
            tell calendar sourceCalName
                set eventsToArchive to {}
                set eventList to events 1 thru 200
                
                repeat with evt in eventList
                    try
                        if (start date of evt) < cutoffDate then
                            set end of eventsToArchive to evt
                        end if
                    end try
                end repeat
                
                repeat with evt in eventsToArchive
                    try
                        set evtSummary to summary of evt
                        set evtStart to start date of evt
                        set evtEnd to end date of evt
                        tell targetCal
                            make new event with properties {summary:evtSummary & " [from:" & sourceCalName & "]", start date:evtStart, end date:evtEnd}
                        end tell
                        delete evt
                        set archivedCount to archivedCount + 1
                    on error
                        set errorCount to errorCount + 1
                    end try
                end repeat
            end tell
        on error errMsg
            return "Error: " & errMsg
        end try
        
        return "Archive complete: " & archivedCount & " events archived, " & errorCount & " failed"
    end tell
end run
