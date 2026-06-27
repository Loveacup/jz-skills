# Gateway Restart Context Preservation

Use when a Hermes agent is debugging gateway behavior while a CC/tmux investigation is active.

## Learning

Restarting the Hermes gateway during an active Telegram/CC debugging turn can preserve the persisted session key/transcript, but it does **not** preserve the live in-flight agent loop:

- active tool-call state is interrupted;
- temporary reasoning/work variables are lost;
- CC monitoring cadence is broken;
- queued user replies may restart into a new turn that only sees transcript, not the live work plan;
- the user experiences this as "you restarted gateway and lost context".

This is especially harmful when the user is giving rapid correction during a gateway bug investigation.

## Rule

Do **not** use gateway restart as a casual probe while debugging Telegram typing, delivery, streaming, topic, or session behavior.

Before any gateway restart during a CC-assisted task:

1. Write a handoff file under `/tmp/` or the project workspace containing:
   - current hypothesis;
   - files changed;
   - commands/tests already run;
   - CC session name and current status;
   - exact next verification step after restart.
2. Send a visible progress block to the user saying restart is about to happen and what state has been persisted.
3. If CC is involved, capture the pane and include the latest CC status in the handoff.
4. Restart once, not repeatedly. After restart, read the handoff before answering or continuing.
5. If the task can be verified without restart, prefer live probes/log inspection over restart.

## Anti-pattern

Repeatedly editing/restarting the gateway to test `sendChatAction` / Telegram typing behavior while CC is mid-discussion. Even if session persistence works, the live monitoring loop is broken and the user loses trust.

## Minimal handoff template

```md
# Gateway restart handoff

Task:
Current user complaint:
Hypothesis:
Changed files:
Tests/log probes already run:
CC session:
Latest CC status:
Next step after restart:
Do not do:
```
