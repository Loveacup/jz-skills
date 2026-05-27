# README Writing Guide

Write GitHub READMEs that convert visitors into users and contributors. Based on 50+ starred READMEs from [awesome-readme](https://github.com/matiassingers/awesome-readme) plus the user's own repos.

> **Golden rule:** README is the project's front door — not documentation, not a spec sheet. Make it clear, scannable, and actionable.

---

## 🔀 Decision Tree: Which Sections Matter

```
Project type?
├─ Library / SDK → API quick example above the fold is essential
├─ CLI tool → terminal GIF + one-liner install + usage example
├─ Web app / GUI → screenshot above the fold + live demo link
├─ AI agent skill → architecture diagram + sync/deploy commands
├─ Configuration / dotfiles → what it looks like (screenshot) + how to apply
├─ Translation / localization → before/after screenshots + coverage stats
└─ Documentation / guide → clean TOC + searchable headings
```

---

## 📋 Section Guide

### 1. Title + One-Liner

**Above the fold.** Visitor decides in 3 seconds whether to stay.

```markdown
# 🏛️ Project Name

> One sentence that says WHAT it does, WHO it's for, and WHY it exists.
```

✅ Good: "jz-skills · AI Agent Skills Hub — one repo, four layers, three platforms."
❌ Bad: "A collection of skills for various AI agents."

**Bilingual pattern (if targeting CN + EN audience):**
```markdown
# 🏛️ jz-skills · AI Agent Skills Hub

> 🤖 **AI agent skills for Hermes, Claude Code, and pi — one repo, four layers, three platforms.**
>
> 🏯 **服务于 Hermes、Claude Code 和 pi 的 AI 技能仓库 — 一库四层，三端同步。**
```

### 2. Badges

Keep to 3-5 essential badges. Shield format:
```markdown
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green)]()
[![Stars](https://img.shields.io/github/stars/user/repo?style=social)]()
```

Essential: license, version, CI status (if CI exists). Nice-to-have: downloads, coverage, language.

### 3. Table of Contents

Include if README > 2 screens (~50 lines). Use anchors:
```markdown
## 📖 目录

- [🚀 快速开始](#-快速开始)
- [📐 架构](#-架构)
- [🤝 贡献](#-贡献)
```

### 4. About / Features

**Not a feature list — a value proposition.** Answer: what problem does this solve? Why should I use this instead of alternatives?

For feature lists, use checkmarks + emoji categories:
```markdown
## ✨ Features

| Category | What you get |
|----------|-------------|
| 🔍 Search | Semantic search across 100K+ documents in <100ms |
| 🔄 Sync | Bidirectional sync with auto-sanitization |
| 🏯 Multi-profile | 15-profile governance with task routing |
```

### 5. Quick Start / Installation

**Must be copy-paste ready.** One command to get running:
```markdown
## 🚀 Quick Start

```bash
git clone https://github.com/user/repo.git && cd repo && ./install.sh
```

> **Prerequisites:** Python 3.10+, 4GB RAM
```

If installation has steps, number them. Show expected output.

### 6. Usage

Show the most common use case FIRST. Then advanced ones.

For CLI tools: terminal recording (GIF or asciinema).
For libraries: code snippet that demonstrates the core value.
For GUI apps: screenshot of the main interface.

```markdown
## 📖 Usage

```bash
# Basic usage
tool --input data.csv --output report.pdf

# With options
tool --input data.csv --format json --verbose
```

![demo](docs/demo.gif)
```

### 7. Architecture / Project Structure

Skip for tiny projects. Essential for anything with >5 files.

**Text tree pattern (works everywhere, no image needed):**
```
project/
├── src/           # Core source code
│   ├── core/      # Business logic
│   └── api/       # REST endpoints
├── tests/         # Test suite
├── docs/          # Documentation
└── scripts/       # Build/deploy scripts
```

**Architecture diagram pattern (text-based):**
```
🌐 Layer 1: shared/          Cross-platform
⚙️ Layer 2: hermes/          Platform-specific
🏯 Layer 3: profiles/        Per-profile
```

### 8. Roadmap / What's Next

Shows the project is alive. Use task list format:
```markdown
## 🗺️ Roadmap

- [x] Core search engine
- [x] REST API
- [ ] Web UI
- [ ] Plugin system
```

Link to GitHub Issues for full list.

### 9. Contributing

Standard template:
```markdown
## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feat/amazing-feature`
3. Commit: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feat/amazing-feature`
5. Open a PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
```

### 10. License + Acknowledgements

```markdown
## 📄 License

MIT — see [LICENSE](LICENSE).

## 🙏 Acknowledgements

- [Library X](https://github.com/x) — for the parsing engine
- [@contributor](https://github.com/contributor) — for the CI pipeline
```

---

## 🎯 Special Patterns

### AI Agent Skill README

Requirements beyond standard README:
```markdown
## 📦 Skill Format

skill-name/
├── SKILL.md          ← YAML frontmatter + markdown body
├── references/        ← Progressive disclosure docs
└── scripts/           ← Runnable helpers

## 🔄 Sync Workflow

# Push: local → GitHub (auto-sanitized)
./deploy/sync-back.sh

# Pull: GitHub → local
git pull && ./deploy/sync-all.sh
```

### Bilingual README (EN + ZH)

Pattern from jz-skills / iTerm2-zh-CN:
```markdown
# 🇨🇳 Project Name · 项目名

> 🇺🇸 English one-liner.
>
> 🇨🇳 中文一句话。

## 📖 目录

- [Quick Start · 快速开始](#quick-start)

## 🚀 Quick Start · 快速开始

```bash
git clone ... && ./install.sh
```
```

Key rules:
- Primary language first in section headings (EN · ZH or ZH · EN — pick one)
- Code blocks are language-agnostic
- Long descriptions: alternate paragraphs (one EN, one ZH)

---

## 🚫 Anti-Patterns

| Don't | Do instead |
|-------|-----------|
| "This is a project that does stuff" | "Process 10K images/minute with GPU acceleration" |
| 500-word backstory before any code | One-liner → quick start → then context |
| 15 badges, half broken | 3-5 essential badges, all verified |
| "Just clone and run it" (no deps listed) | Prerequisites section + tested install steps |
| Screenshot from 3 versions ago | Current screenshot, update on major releases |
| README > 500 lines with no TOC | Add TOC for anything > 2 screens |
| Every section is mandatory | Skip sections that don't add value for your project type |
| Copy-pasting API docs into README | Link to docs site; keep README to "why" + "how to start" |

---

## ✅ README Review Checklist

Use this when writing or reviewing a README:

- [ ] Can a new visitor understand what this does in 5 seconds?
- [ ] Is the install command copy-paste ready (one block)?
- [ ] Is there a usage example that shows the core value?
- [ ] Are badges up to date (license, version, CI)?
- [ ] Is there a TOC if the README is > 2 screens?
- [ ] Are screenshots/GIFs from the current version?
- [ ] Is there a license section?
- [ ] Is there a "how to contribute" section?
- [ ] For bilingual: is the language consistent (same primary-first order)?
- [ ] Does it pass the "bus factor" test — can a stranger get running in <5 min?

---

## 📚 Reference Examples

| Repo | Strength |
|------|----------|
| [jz-skills](https://github.com/Loveacup/jz-skills) | Bilingual + multi-layer architecture + sync workflow |
| [iTerm2-zh-CN](https://github.com/Loveacup/iTerm2-zh-CN) | Clean bilingual + AI deployment guide + collapsible FAQ |
| [Best-README-Template](https://github.com/othneildrew/Best-README-Template) | Comprehensive section template with badge variables |
| [awesome-readme](https://github.com/matiassingers/awesome-readme) | 100+ curated examples by pattern type |
| [fiber](https://github.com/gofiber/fiber) | Excellent library README: benchmarks + quickstart + API |
| [lobe-chat](https://github.com/lobehub/lobe-chat) | Modern design: feature graphics + ecosystem map |

---

## 🔧 Tools

- [shields.io](https://shields.io) — badge generator
- [readme.so](https://readme.so) — visual README editor
- [vhs](https://github.com/charmbracelet/vhs) — terminal GIF generator
- [carbon.now.sh](https://carbon.now.sh) — code screenshot beautifier
