# Screenshot-to-calendar extraction patterns

Use this when the user sends a screenshot of a booking, ticket, medical appointment, school notice, travel itinerary, or similar and implies it should become calendar context.

## General workflow

1. Extract structured fields from the screenshot: title/event type, person, date/time, location, ticket/order number, seat/queue, status, special instructions.
2. Infer calendar ownership using the normal rules, but write to the confirmed foxmail calendars:
   - Naomi / 蔡懿涵 / 懿涵 → `Naomi1`
   - Zelda / 蔡若涵 / 若涵 / 妹妹 → `Zelda1`
   - Alex personal → `个人1`
   - Work → `工作1`
3. Before writing, query the target calendar for the relevant day to avoid duplicates and conflicts.
4. If the screenshot lacks date/time but the user gives context like “今晚”, use the current date and retrieve/verify public event time if available. If uncertainty remains, make the ambiguity explicit in notes and choose the best-supported time rather than blocking on low-risk details.
5. Write concise, operational notes: identifiers, seat/queue, entry requirements, what to bring, and any warning text. Do not expose full ID numbers; preserve masked forms only.
6. Use reminders appropriate to the event type. For time-sensitive child outings, use at least 1-hour reminder; add an earlier reminder if travel/preparation matters.
7. Verify the event after creation with a read-back query.

## Medical appointment screenshot pattern

Extract:

- Patient / 就诊人
- Department / 科室
- Campus and specific building/floor/location
- Appointment time
- Registration status
- Outpatient number / 门诊号
- Queue/sequence / 就诊序号
- Fee
- QR/check-in number if visible

Default handling:

- Calendar: child’s calendar (`Naomi1` or `Zelda1`).
- Title: `🏥 脱敏注射-Naomi` or equivalent medical title.
- For 脱敏注射, use the established 3-hour block even if the appointment slot is 30 minutes.
- Location: full hospital campus + building/floor/area.
- Notes: include appointment slot, status, queue, fee, and “携带就诊卡 / 电子医保码；到院后签到，等待叫号”.
- Reminders: at least 60 min and 15 min if same-day; otherwise default medical 1 day can also apply.

## Concert / performance ticket screenshot pattern

Extract:

- Performance name if visible or user-provided
- City/venue clues
- Attendee / masked identity only
- Seat section/row/seat
- Ticket number (`T.N` etc.)
- Entry instructions and prohibited items
- Ticket validity (“一次入场有效”)

Default handling:

- Calendar: child’s calendar if the user says Naomi/Zelda is going.
- Title: `🎵 <artist/event>-Naomi` or similar.
- Location: venue if visible or verified from public listing.
- Notes: include attendee, companion, seat, ticket number, ID-entry rule, one-entry validity, and prohibited-item warning.
- If public listings disagree on showtime, pick the official/best-supported time, mention the discrepancy in notes, and recommend early arrival.
- Reminders: 3 hours and 1 hour before for concerts/large venues.

## Privacy notes

- Never write full ID numbers from screenshots into calendar notes.
- Keep ticket/QR/order numbers only when operationally useful for check-in or support.
- Mention “请勿截图转发给陌生人” style warnings in notes if present.
