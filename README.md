# jz-skills

AI agent skills for Hermes (三省六部), Claude Code, and pi — one repo, three platforms.

## Structure

```
jz-skills/
├── shared/              ← Cross-platform skills (same for all agents)
│   ├── web-research-router/    检索总控：Exa/Tavily/Brave/arXiv 路由
│   ├── github-code-explorer/   GitHub 源码四层探索 (L1→L4)
│   ├── grill-with-docs/        设计审查：对照 CONTEXT.md + ADR
│   └── skill-authoring/        Skill 合规增强层
│
├── hermes/              ← Hermes-specific skills
│   ├── financial-research-agents/  三省六部金融研究
│   ├── tradingagents/              A股交易分析
│   ├── llm-wiki/                   LLM 知识库
│   └── arxiv/                      学术论文检索
│
├── cc/                  ← Claude Code specific (WIP)
├── pi/                  ← pi specific (WIP)
│
└── deploy/
    └── sync-all.sh      ← Deploy to Hermes / CC / pi
```

## Quick Start

```bash
# Clone
git clone git@github.com:Loveacup/jz-skills.git ~/jz-skills

# Deploy to all platforms
cd ~/jz-skills && ./deploy/sync-all.sh all

# Or deploy to one platform
./deploy/sync-all.sh hermes
./deploy/sync-all.sh cc
./deploy/sync-all.sh pi
```

## Sync Workflow

jz-skills supports **bidirectional sync** between GitHub and your local agents.

```
 ┌─────────────────────────────────────┐
 │        GitHub (source of truth)     │
 │    github.com/Loveacup/jz-skills    │
 └──────────┬──────────────┬───────────┘
            │ git pull     │ git pull
            ▼              ▼
     ┌──────────┐   ┌──────────┐
     │ Mac mini │   │  MacBook │
     │          │   │          │
     │ Hermes   │   │ CC       │
     │ sync-all │   │ sync-all │
     └──────────┘   └──────────┘
```

### Local Agent → GitHub (push changes up)

When you modify a skill directly in `~/.hermes/skills/` (via agent or manual edit):

```bash
./deploy/sync-back.sh --dry-run   # preview what changed
./deploy/sync-back.sh              # apply (Hermes → repo)
git diff                           # review
git commit -am "描述改动"
git push
```

### GitHub → Local Agent (pull changes down)

When another machine pushed updates, or you edited directly in the repo:

```bash
git pull
./deploy/sync-all.sh hermes   # or: cc / pi / all
```

### One-Line Daily

```bash
# Before work: pull latest
git pull && ./deploy/sync-all.sh hermes

# After work: push changes
./deploy/sync-back.sh && git commit -am "daily sync" && git push
```

## Skill Format

All skills follow the [Agent Skills standard](https://skills.sh):
- `SKILL.md` with YAML frontmatter
- Optional `references/` for progressive disclosure
- Optional `scripts/` for runnable helpers

## License

MIT
