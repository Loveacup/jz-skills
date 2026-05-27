# Calendar account migration notes

## Current account rule

The active family/work calendars have migrated from the previous iCloud account to the iCloud account:

```text
<email redacted>
```

All Calendar.app operations should target calendars under this account. Alex confirmed the foxmail iCloud calendars are the display-name set with suffix `1`: `个人1`, `工作1`, `Naomi1`, `Zelda1`.

## Why this matters

After migration, Calendar.app may expose duplicate or near-duplicate calendar names, for example:

- `个人` and `个人1`
- `工作` and `工作1`
- `Naomi` and `Naomi1`
- `Zelda` and `Zelda1`

Do not infer the correct target only from the display name. The account/source is more important than the calendar name.

## Safe workflow

1. Use the confirmed foxmail iCloud calendars by default:
   - Personal → `个人1`
   - Work → `工作1`
   - Naomi → `Naomi1`
   - Zelda → `Zelda1`
2. Never write new events to the old non-`1` calendars (`个人`, `工作`, `Naomi`, `Zelda`) unless Alex explicitly asks for old-calendar maintenance.
3. Never write new events to local `On My Mac` calendars when duplicates exist.

## Current known duplicate set observed in Calendar.app

A previous check showed these names present simultaneously:

```text
个人, 工作, Naomi, Zelda, Naomi1, 工作1, 个人1, Zelda1
```

This confirms the active foxmail iCloud set is `个人1`, `工作1`, `Naomi1`, `Zelda1`. Treat the non-`1` names as old calendars unless Alex explicitly says otherwise.
