# CC Agent Team Cross-Project Analysis with OB Verification

> Pattern discovered 2026-06-08: AstrBot vs 艾大力 comparison. Hermes does the initial research (web-research-router + GitHub code exploration), then CC agent team does multi-lens parallel analysis with Obsidian vault source verification, producing a structured document to OB Inbox.

## When to Use

When the user asks to:
- Compare an external project/technology with an internal product/project
- Produce "借鉴分析" / "对比分析" / "深度分析" documents for Obsidian
- Analyze what an internal project can learn from an external one

## 🚨 Mandatory Philosophy Pre-Check (RUN BEFORE WRITING CONTEXT)

**Users often have core product philosophies that are NOT reflected in existing documents.** Failing to surface and respect these philosophies leads to entire rounds of analysis being off-target and needing complete rewrites.

Before writing the CC context file, explicitly ask the user (or recall from memory):

> "What is your core product philosophy? Specifically: does AI touch patients directly, or only empower staff? What's the AI's role boundary?"

**Real case (2026-06-08):** The initial AstrBot-vs-艾大力 analysis assumed AstrBot's "AI chatbot talks to users" model was applicable. User corrected mid-session: "AI不直接触达C端患者，AI是给医护人员赋能" — a fundamental philosophy shift that required v3 complete rewrite. The correction was NOT in any existing document or BP.

**Checklist before writing context:**
- [ ] Read ALL existing product docs AND meeting minutes — don't rely on polished BP alone
- [ ] Explicitly surface the user's philosophy about AI role boundaries
- [ ] Verify whether the external project's model aligns with the user's philosophy
- [ ] If there's a mismatch, flag it in the context file intro: "注意：用户哲学是 X，外部项目做法是 Y，分析需要翻译而非照搬"

## Prerequisites

- Hermes has completed initial research (source code cloned, key files read, architecture understood)
- Hermes has identified OB vault paths for the internal project's files
- Context file prepared at `/tmp/cc-context-{task}.md`

## Context File Template

```markdown
# {Task Title}

## 核心哲学（如适用）
**用户的产品哲学：{state explicitly}**
这决定了分析的"翻译方向"——外部项目的哪些做法可以直接借鉴，哪些需要翻译成用户哲学的等价物。

## 任务
N Lens 并行审查，输出结构化文档到 OB 收件箱

## 已知事实（Hermes 侧记忆）
{key facts about both projects}

## {External Project} 概要（Hermes 已完成分析）
{architecture summary, key source code references, findings}

## {Internal Project} 现有产品架构
{from Hermes' understanding of OB files}

## 分析任务：N Lens 并行

### Lens 1: {name}
### Lens 2: {name}
### Lens 3: {name}

## 输出要求
1. 输出文件：`{OB inbox path}`
2. 格式：Markdown + YAML frontmatter
3. 每个 Lens 一个章节 + 综合优先级行动建议
4. 中文为主
5. 用 agent-direct-output 模式

## Worker 规则
- timeout 10min per worker
- 假死先 ls -la 查磁盘
- 直接写文件到 /tmp/，leader 合并到最终路径
```

## Critical: OB Source Verification

**User will correct you if workers only read the context summary and not the actual OB files.** Always include in the context:

> 所有 worker 必须先去 OB 读 {project_path}/ 下的所有 .md 文件核实产品现状，不要只靠 context 摘要。

This often requires **two rounds** of worker spawning:
1. Round 1: workers analyze based on context file → return preliminary results
2. Round 2 (after user correction): workers re-read OB files → produce verified analysis

## Multi-Round Flow

```
Hermes research → write context file → launch CC
  ↓
Round 1: CC spawns workers → workers analyze (may miss OB verification)
  ↓
User: "要对着 ob 库进行核实"
  ↓
Hermes → send-keys supplement instruction
  ↓
Round 2: workers read OB files → produce verified analysis
  ↓
Leader merges → patches → outputs final doc
```

## Thinking Loop Recovery

In xhigh effort cross-project analysis, CC often enters thinking loops (token frozen >3min). Recovery:

```bash
# 1. Ctrl+C to interrupt
tmux send-keys -t <session> C-c
# 2. Single-line push command (≤120 chars, Chinese works)
tmux send-keys -t <session> "直接写文件，不要过度思考。" Enter
# 3. If OB verification was missed, send supplement
tmux send-keys -t <session> "补充：也要读 {ob_path} 下相关文件。" Enter
```

## Verified Output Format

This format was validated in the AstrBot-艾大力 session (2026-06-08):

```
---
status: 树苗
type: 分析
tags: [domain1, domain2, 架构]
created: YYYY-MM-DD
source: {external project} v{version} 源码分析
project: "[[internal project doc]]"
---

# {Title}

> 分析对象 / 分析目标 / 方法

## 导读：一句话结论

{3-5 line executive summary with key red lines}

---

## Lens 1: {name}
{detailed analysis with real code references (file:line)}

---

## Lens 2: {name}
{detailed analysis}

---

## Lens 3: {name}
{detailed analysis}

---

## 优先级行动建议

### 🔴 高优先级（P0 · 0–3 个月）
### 🟡 中优先级（P1 · 3–6 个月）
### 🟢 低优先级（P2 · 6–18 个月）

### 一页纸落地顺序
{ASCII timeline diagram}

---

## 附：跨 Lens 关键交叉点
{cross-cutting insights connecting all lenses}
```

## Pitfalls

1. **Workers trust context summary over source**: Always supplement with OB read instruction. Users expect OB files as ground truth. This often requires **two rounds** of worker spawning — round 1 produces preliminary results, round 2 (after user says "核实OB") produces verified analysis.
2. **Multi-line send-keys queue pollution**: During thinking loops, keep supplements to single-line (≤120 chars). Multi-line commands queue up and don't execute (pitfall #33).
3. **Token freeze ≠ worker stall**: xhigh effort workers can show same tool count for minutes but still be computing. Check disk output before declaring stall.
4. **Meeting minutes / supplementary files**: Users often mention additional OB directories mid-analysis (e.g. "也要看会议纪要"). Meeting minutes contain operational reality that polished BP documents omit. Be ready to send quick supplement instructions to CC.
5. **External project is just ONE reference**: User may initially accept a single-project comparison (\"分析 AstrBot\"), then later demand broader research (\"还有别的项目可以引用的\"). Be ready to scale the reference set from 1→N. Context v4 for this pattern successfully used 12 projects across 3 categories.
6. **CC fails 3+ times to spawn agents → switch to delegate_task**: When CC repeatedly enters thinking loops without spawning workers (Burrowing/Brewing/Hyperspacing with token freeze), use Hermes' `delegate_task` with 3 parallel subagents as fallback. Each subagent writes a file to `/tmp/`, then Hermes merges. See `references/delegate-task-cc-fallback.md`.
7. **Multi-round correction cycle**: Expect 3-4 rounds for complex analysis: (1) initial analysis → (2) user demands OB verification → (3) user corrects philosophy → (4) user demands broader references. Each round may need CC context rewrite + fresh session.
