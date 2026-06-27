# Agent SkillHub Context Map

Use this reference for centralized SkillHub tasks. It prevents agents from reading the full Obsidian governance project when a small, task-specific context set is enough.

## Rule

Default context is:

1. `/Users/alexcai/.agents/config/agent-skills/paths.yml`
2. `/Users/alexcai/.agents/config/agent-skills/docs.yml`
3. `/Users/alexcai/.agents/config/agent-skills/governance-policy.yml`
4. `/Users/alexcai/.agents/config/agent-skills/source-taxonomy.yml`
5. `/Users/alexcai/.agents/config/agent-skills/secrets-policy.yml`
6. `/Users/alexcai/.agents/skill-sources.md`
7. `/Users/alexcai/.agents/.skill-lock.json`
8. `/Users/alexcai/.agents/skill-function-tags.tsv`

Do not read `/Users/alexcai/Documents/Obsidian/AlexCai/20-Areas/20_技术项目/Agent Skills 中心化治理/` recursively. Read only the specific target document named by `docs.yml`.

## Task Routing

| Task | Read |
|---|---|
| Write a new skill | This skill, `agent-skillhub-workflow.md`, target pool directory, related existing skills |
| Import GitHub skills | `.skill-lock.json`, `skill-sources.md`, `source-taxonomy.yml`, `secrets-policy.yml`, target pool, upstream repo |
| Modify an existing skill | Active canonical skill, source repo copy if present, `skill-sources.md`, dirty-gate policy |
| Promote to pool | `governance-policy.yml`, source path, active runtime exposure, dirty source gate |
| Repoint runtime | `runtime-cli-registry.json`, `governance-policy.yml`, active symlink audit |
| Update tags | `skill-function-tags.tsv`, `source-taxonomy.yml`, skill `SKILL.md`; do not use script output as final authority |
| Write back Obsidian | `docs.yml` plus only the specific `monitor_log`, `evidence_index`, `architecture_changelog`, or `function_tags_index` |

## When Full Obsidian Reading Is Allowed

Only read the broader Obsidian project when:

- changing governance architecture,
- resolving an L3 Alex decision,
- reconciling contradictory historical evidence,
- preparing a project-level migration,
- or explicitly asked by Alex.

## Minimal Evidence To Record

Every SkillHub state change should record:

- changed paths,
- source and canonical relation,
- dirty-gate result when relevant,
- runtime exposure change or `none`,
- validation commands,
- writeback targets.
