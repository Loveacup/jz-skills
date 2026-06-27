# CC + taste-skill Mobile Prototype Workflow

> 2026-05-31 · Session: 银杏汇小程序原型图生成

## When to use

When the user wants to quickly generate mobile app / mini-program prototype screenshots (discussion version) from a design document.

## Pattern

### Step 1: Prepare context file

Write to `/tmp/cc-{task}-prototype.md`. Must contain:
- Source document path (the plan/spec)
- Key pages to prototype with content description
- Design constraints (viewport size, language, aesthetic direction)
- Output paths for screenshots

### Step 2: Launch CC with high effort

```bash
claude --model claude-opus-4-8 --effort xhigh
```

taste-skill Design Read benefits significantly from higher effort.

### Step 3: CC workflow

1. `git clone https://github.com/Leonxlnx/taste-skill /tmp/taste-skill`
2. Read taste-skill SKILL.md for design principles
3. Output a **one-line Design Read** before any code:
   - Page kind (community app, dashboard, etc.)
   - Audience (mixed-age residents, elderly-friendly)
   - Vibe language (trust-first, calm, practical)
   - Aesthetic family (white cards + single accent color + minimal motion)
   - Dials: VARIANCE / MOTION / DENSITY
4. Write shared `app.css` + one HTML per page
5. Start local HTTP server on port 8765 (Playwright needs http:// not file://)
6. Screenshot each page at target viewport (375×812 for WeChat mini-program)
7. Generate combined overview image

### Step 4: Preserve sources

Copy all HTML/CSS source files from `/tmp/yinxinghui/` to the Obsidian vault alongside the plan document. Add a README.md with:
- File inventory
- Preview instructions (`python3 -m http.server 8765`)
- Links to related plan/review documents

## Cost profile (from 2026-05-31 session)

- 4 mobile tab pages (home, services, finance, profile) + combined overview
- 1518 lines of HTML/CSS total (app.css: 242, tab1-4: 306-347 each, all.html: 165)
- CC time: ~15 minutes
- Tokens: ~50k
- Model: Opus 4.8 with effort levels available

## Pitfalls

- **Playwright blocks file:// protocol** — CC must start `python3 -m http.server` on a port before screenshots
- **Effort matters** — `xhigh` or `max` produces noticeably better Design Read and layout quality
- **Preserve sources** — `/tmp/` gets cleaned; copy output files to vault before session ends
- **Source docs in Chinese** — specify output language explicitly in context file
