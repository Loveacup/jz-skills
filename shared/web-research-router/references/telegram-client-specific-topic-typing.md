# Telegram topic typing indicators: client-specific rendering

Use when debugging Telegram Bot API `sendChatAction` / typing indicators in forum topics, private DM topics, or channel direct-message topics.

## Session lesson

A user observed:

- Telegram Desktop/PC shows the bot's native `typing…` indicator in the topic.
- Telegram iOS does not show the same indicator.
- A visible `...` fallback was sent as an ordinary chat message, which is undesirable unless explicitly opted in.

This changes the diagnosis: when one client renders the native indicator and another does not, the backend/API path is probably functioning. The remaining problem is likely Telegram client rendering or mobile topic metadata behavior, not a Hermes `sendChatAction` routing failure.

## Decision pattern

- If Desktop/PC shows native typing: do not claim the backend failed.
- If iOS alone does not show it: classify as client-specific rendering limitation unless raw API logs show `BadRequest` or missing topic id.
- Keep native `sendChatAction` as the default behavior.
- Do not enable visible placeholder fallbacks by default. If offered, require opt-in and deletion guarantees.

## No-restart debugging protocol

When investigating gateway typing/status indicators from an active Telegram conversation:

1. **Do not restart the gateway as a diagnostic step.** Restarting kills the in-flight agent loop, tool state, and any CC/tmux monitoring context; session resume only preserves transcript, not live execution state.
2. **Separate API correctness from client rendering.** First verify that `sendChatAction` reaches Telegram and returns success for the exact `chat_id` + topic metadata. Only then reason about Desktop vs iOS rendering.
3. **Use bounded live probes, not gateway restarts.** A 15–25 second loop that sends native typing every ~4 seconds is enough to test visibility without changing runtime code.
4. **Before any code edit that may require restart, write a handoff.** Include current session key, files touched, test command, live probe result, and rollback command.
5. **If the user says to stop / leave it /先不管, immediately stop investigation and roll back uncommitted experiment diffs for this issue.** Confirm with `git diff -- <files>` before reporting completion.

## Concrete live probe pattern

Run from the Hermes checkout with the runtime venv. Load tokens from the active profile `.env`, but never print them.

```bash
cd ~/.hermes/hermes-agent
venv/bin/python - <<'PY'
import asyncio, os, sys, time
from pathlib import Path
sys.path.insert(0, '.')
for env_path in [Path('~/.hermes/profiles/regent/.env').expanduser(), Path('~/.hermes/.env').expanduser()]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from telegram import Bot

async def main():
    bot = Bot(os.environ['TELEGRAM_BOT_TOKEN'])
    chat_id = int(os.environ.get('PROBE_TELEGRAM_CHAT_ID', '7931997806'))
    thread_id = int(os.environ.get('PROBE_TELEGRAM_THREAD_ID', '38893'))
    start = time.monotonic()
    oks = 0
    for i in range(5):
        ok = await bot.send_chat_action(chat_id=chat_id, action='typing', message_thread_id=thread_id)
        print(f'tick {i+1}: message_thread_id OK={ok}')
        oks += bool(ok)
        await asyncio.sleep(4)
    print('summary', {'ticks': oks, 'seconds': round(time.monotonic() - start, 1)})

asyncio.run(main())
PY
```

Interpretation:

- `OK=True` for the target topic + Desktop visible but iOS invisible ⇒ likely Telegram iOS rendering limitation.
- `BadRequest` or no topic id in raw call ⇒ backend routing issue; inspect metadata extraction and `_message_thread_id_for_typing`.
- Both `message_thread_id` and `api_kwargs.direct_messages_topic_id` may return `OK=True`; prefer the parameter that matches Telegram's documented chat/topic type and the runtime library signature.

## Rollback discipline for aborted typing experiments

If the user decides not to continue, revert only the files touched for the experiment; do not disturb unrelated worktree changes.

```bash
cd ~/.hermes/hermes-agent
git checkout -- gateway/platforms/telegram.py tests/gateway/test_telegram_thread_fallback.py
git diff -- gateway/platforms/telegram.py tests/gateway/test_telegram_thread_fallback.py --stat
git status --short
```

Report explicitly whether the typing diff is empty and list unrelated modified files as left untouched.

## Search pattern

Search with client-qualified queries, not just Bot API terms:

- `Telegram iOS sendChatAction message_thread_id topic typing indicator`
- `Telegram Desktop iOS private chat topics bot message_thread_id missing`
- `Telegram direct_messages_topic_id sendChatAction iOS`

Cross-check:

- Official Bot API changelog for `message_thread_id` / `direct_messages_topic_id` support.
- Telegram bug tracker for mobile/iOS topic metadata omissions.
- GitHub issues in Hermes/OpenClaw/telegram-bot-api for observed client differences.

## Visible fallback guardrails

If a fallback marker such as `...` or `正在处理…` is ever implemented:

1. Default off.
2. Per-chat or per-profile opt-in only.
3. Send as a tracked temporary message with message id persisted for cleanup.
4. Delete in `finally` after the final assistant reply.
5. If deletion fails, log clearly and never retry in a loop.
6. Never use fallback marker to mask a known client limitation without telling the user.
