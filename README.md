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

## Daily Workflow

1. Edit skills in `shared/` or `hermes/` / `cc/` / `pi/`
2. `git commit && git push`
3. On each machine: `git pull && ./deploy/sync-all.sh all`

## Skill Format

All skills follow the [Agent Skills standard](https://skills.sh):
- `SKILL.md` with YAML frontmatter
- Optional `references/` for progressive disclosure
- Optional `scripts/` for runnable helpers

## License

MIT
