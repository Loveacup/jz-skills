# Regent Self-Test Template

Use this template for comprehensive governance health checks.

## 1. Infrastructure Health
- [ ] Gateway running (`hermes -p regent gateway status`, check PID, Telegram connected)
- [ ] Plugins loaded without errors (grep gateway.log for `ModuleNotFoundError`, import errors)
- [ ] Last startup timestamp

## 2. Plugin Gate Regression
- [ ] Read-only tools pass: cronjob `list`, memory `recall`/`reflect`, send_message no-target
- [ ] Write tools blocked: cronjob `create`/`update`, memory `add`/`remove`, send_message with target
- [ ] Control-plane paths blocked: write_file/patch/terminal → config.yaml, SOUL.md, plugins/, cron/, memories/, .env
- [ ] `confirmed_by_user: true` bypass works for all gated tools that support it
- [ ] Normal tools not intercepted: delegate_task, skill_view, read_file, web_search, kanban_show

## 3. Constitution Acceptance Tests
- [ ] Hermes questions → hermes-agent skill loaded (check SOUL.md boot rule #2)
- [ ] Config questions → actual profile checked via tools, not default assumption
- [ ] Cron jobs are silent/low-frequency only
- [ ] Read/verification/orchestration paths unblocked after any gate change

## 4. Memory Isolation
- [ ] No default references in regent MEMORY.md
- [ ] Pool within budget (MEMORY + USER ≤ 2,200 chars, or justified overage)
- [ ] No task progress / PR numbers / commit SHAs / one-off outcomes in memory

## 5. SOUL.md Integrity
- [ ] Core sections present: identity, ceremony, governance flow, phase boundaries, boot iron laws, notification discipline
- [ ] Long-form sections actually removed (not just annotated as "已移入")
- [ ] No orphaned claims (grep for each removed section header)

## 6. Hindsight Health
- [ ] No duplicate near-identical entries (check with `hindsight_recall` on key topics)
- [ ] Only stable facts stored (corrections, decisions, conventions), no session progress
