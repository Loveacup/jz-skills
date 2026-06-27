# Kanban Swarm Profile Setup

2026-06-04: Verified creating 6 swarm profiles for morning-news-briefing parallel pipeline.

## Profile Creation

```bash
# Create profiles cloned from default (copies config.yaml, .env, SOUL.md, skills)
hermes profile create --clone --description "zh news search worker" lane-zh
hermes profile create --clone --description "en news search worker" lane-en
# ... etc
```

## Required Configuration Per Profile

After cloning, each profile must be reconfigured to avoid conflicts:

### 1. Unique API server port

Cloned profiles inherit `platforms.api_server.extra.port: 8460` which conflicts with the default gateway. Assign unique ports:

```bash
hermes --profile lane-zh config set platforms.api_server.extra.port 8660
hermes --profile lane-en config set platforms.api_server.extra.port 8661
# ... sequential unique ports
```

### 2. Disable Telegram (worker profiles)

Worker profiles only need API server — Telegram conflicts with the main gateway:

```bash
hermes --profile lane-zh config set platforms.telegram.enabled false
# ... apply to all worker profiles
```

### 3. Model assignment

Workers → cheap model (flash), verifier/synthesizer → quality (pro):

```bash
hermes --profile lane-zh config set model deepseek-v4-flash
hermes --profile lane-zh config set provider deepseek

hermes --profile auditor config set model deepseek-v4-pro
hermes --profile auditor config set provider deepseek
```

### 4. Skills symlinks

Workers need at minimum `web-research-router` + the task-specific skill. Set up symlinks to the shared skill pool:

```bash
ln -s ~/.hermes/skills/productivity/morning-news-briefing \
      ~/.hermes/profiles/lane-zh/skills/productivity/morning-news-briefing
ln -s ~/.hermes/skills/web-research-router \
      ~/.hermes/profiles/lane-zh/skills/web-research-router
```

Or if using `--clone` (not `--no-skills`), the full skill set is copied but can be pruned.

## Gateway Startup

After configuration, start gateways (one per profile):

```bash
hermes --profile lane-zh gateway run --replace
```

Verify with: `ps aux | grep 'hermes.*gateway' | grep 'lane-zh'`

## Swarm Command Syntax

```bash
hermes kanban swarm \
  --worker "PROFILE:TITLE:SKILL,SKILL" \   # --worker is repeatable
  --verifier VERIFIER_PROFILE \
  --synthesizer SYNTHESIZER_PROFILE \
  "goal text"    # GOAL IS POSITIONAL, not --goal flag
```

Key: `--worker` format includes skills as comma-separated list after the second colon.

## Dispatch

After swarm creation, dispatch the task cards:

```bash
hermes kanban dispatch --max N   # N = number of workers
```

The dispatcher spawns standalone agent processes per task. Each worker profile needs its gateway running on a unique port.

## Pitfalls

- **`platforms.api_server.extra.port` is the port that matters** — `api_server.port` at the top level is not used by gateways. Always set `platforms.api_server.extra.port`.
- **Goal is positional** — not `--goal "..."` but just the last positional argument.
- **Publisher/synthesizer may crash-loop** if its gateway port conflicts. Check PID files and gateway logs.
- **Skills format in --worker**: `PROFILE:TITLE:SKILL,SKILL` with colons separating profile, title, and skills. Skills are comma-separated.
- **All profile gateways must be running before swarm dispatch.** `hermes kanban swarm` creates the task graph but does not start gateways. If worker/verifier/synthesizer gateways are stopped, tasks sit in `running` with no actual agent process. Run `hermes profile list` to check gateway status; `hermes gateway start --profile <name>` for each stopped profile.
- **Publisher/synthesizer profile may have zero skill symlinks.** A cloned profile might copy `config.yaml` + `.env` but not the skills directory. Always verify with `hermes profile show <name>` — if `Skills: 0`, manually create symlinks to the shared pool. For morning-news-briefing: `morning-news-briefing`, `news-assembly`, `de-slop`, `tts-manager`.
- **Skill names in kanban tasks must use full categorized paths.** `morning-news-briefing` (short name) fails resolution in kanban worker context; use `productivity/morning-news-briefing` (full path). Same for `creative/de-slop`, `hermes/tts-manager`, etc.
- **Swarm router may assign wrong skills to publisher.** The auto-router picks skills from the task description, which can map to non-existent names like `avoid-ai-writing`. Check the spawned tasks with `hermes kanban show <id>` and verify `skills:` field. If wrong, archive the task and recreate with explicit `--skill` flags.
- **`dispatch_in_gateway` may be `false`.** If `dispatch_in_gateway=false` in the profile's `config.yaml`, tasks won't be picked up automatically. Either run `hermes kanban dispatch` manually, or set `kanban.dispatch_in_gateway: true` and restart the gateway.
