# Single-Agent Literary Rewrite Pattern

Use when the user asks CC to rewrite an existing article/document for better prose quality — not restructuring, not summarization, but **literary improvement**.

## Session Pattern (2026-05-28)

The user had an 8000-word technical reference article on Harness Engineering that needed to be rewritten as a literary essay in the style of Paul Graham — first-person, warm, with concrete human stories, no AI-slop markers.

### What worked

**Single-agent tmux, no team.** For literary rewrites where tone and narrative coherence matter, a single agent with the whole file in context produces more cohesive prose than split-team approaches.

**Stylistic guidance in the prompt:**
- "像 Paul Graham 随笔那样——有观点、有温度、有具体的人，不堆砌术语"
- "消除 AI 写作痕迹：去掉'值得注意的是''首先/其次/最后''综上所述'这类链条式连接词"
- "第一人称视角"
- "加入 PG 式自我修正" (e.g., "这个数字我没找到 primary source，可能是有人为了好记而四舍五入了")

**Structural technique that worked:**
- Take a character from a later section (in this case, "客服经理 L" from §8) and move them to the opening as a narrative hook
- Close by returning to that character — bookend structure
- Use "我认识..." / "我反复想起..." / "读到这句话的时候我突然意识到..." as transitions between technical sections

**Timing expectation:** A ~7000-character Chinese literary rewrite took ~7 minutes of thinking + writing (single Opus-class model in tmux). The thinking phase for multi-section rewrites can take 4-6 minutes before any output appears — don't interrupt.

### What to avoid

- Don't ask CC to "do one chapter and wait for feedback" — literary tone needs cross-chapter coherence. Tell it to write all chapters in one pass.
- Don't use agent team for literary rewrites — the split-context approach breaks narrative flow.
- Don't use print mode for literary rewrites — the multi-turn read→think→write pattern benefits from tmux's persistent context.

### Key metrics from this session

- Input: 16800 bytes, ~8000 chars Chinese technical article
- Output: 30470 bytes, 398 lines, 7035 Chinese characters (within 7000-9000 target)
- All 13 reference links preserved
- All core data points retained (OpenAI 5-month/0-code, Anthropic 2%→12%, Terminal Bench 13.7pp, etc.)
- 4 markdown tables converted to bullet lists
- AI chain words eliminated throughout
