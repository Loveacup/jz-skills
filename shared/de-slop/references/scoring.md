# 5-Dimension Scoring System

Rate the final text on each dimension, 1-10. Total 50. **Below 35: revise.**

---

## Scoring Rubric

### Directness
*Statements or announcements?*

| Score | Description |
|:---:|------|
| 1-3 | Heavy throat-clearing. Multiple "Here's what...", "Let me be clear...", signposting before every point. Reader waits for the actual content. |
| 4-6 | Some announcements, but mostly direct. Occasional "It's worth noting..." or "The real question is..." |
| 7-9 | Nearly all direct statements. Minimal setup. Point arrives immediately. |
| 10 | Every sentence earns its place. No throat-clearing anywhere. Reading feels like skipping stones, not wading. |

### Rhythm
*Varied or metronomic?*

| Score | Description |
|:---:|------|
| 1-3 | Every sentence the same length. Predictable cadence. Three-item lists everywhere. Paragraphs all end punchily. |
| 4-6 | Some variation, but still patterns. Two-three sentences that match in length. |
| 7-9 | Natural variation. Short sentences. Then longer ones that breathe. No detectable template. |
| 10 | Rhythm feels organic — you can hear a person speaking. Sentence lengths fluctuate like conversation. |

### Trust
*Respects reader intelligence?*

| Score | Description |
|:---:|------|
| 1-3 | Over-explains everything. Repeated points in different words. "This matters because..." hand-holding. Permission-granting ("And that's okay."). |
| 4-6 | Mostly trusts readers but still over-explains key points. Some redundancy. |
| 7-9 | Leaves space for reader to think. Points made once, cleanly. Context enough to follow, not drown. |
| 10 | Reads like a conversation between equals. No hand-holding. Every sentence assumes you're keeping up. |

### Authenticity
*Sounds human?*

| Score | Description |
|:---:|------|
| 1-3 | Plastic. Template feel. Sycophantic tone. No opinions. No edge. Reads like corporate press release or Wikipedia article. |
| 4-6 | Functional but flat. Technically correct, emotionally absent. |
| 7-9 | Has a voice. Opinions present. Some personality. Occasional messiness that feels real. |
| 10 | Feels like a specific person wrote it. Has quirks, opinions, contradictions. You could pick this author out of a lineup. |

### Density
*Anything cuttable?*

| Score | Description |
|:---:|------|
| 1-3 | Bloated. Every sentence has filler. Adverbs everywhere. "In order to" instead of "to." Half the words are scaffolding. |
| 4-6 | Mostly tight but still carries dead weight. A few phrases that add nothing. |
| 7-9 | Lean. Every word pulls weight. No obvious cuts without losing meaning. |
| 10 | Austere. Cannot remove a single word without changing meaning. Like a haiku in prose. |

---

## Scoring Examples

### Example 1: Obvious AI Slop

> Great question! Here's an overview of the topic. I hope this helps! Let me know if you'd like me to expand.
>
> This groundbreaking innovation serves as an enduring testament to human creativity, marking a pivotal moment in the evolving landscape of technology. At its core, what really matters is the intricate interplay between automation and human judgment, showcasing how these tools can foster collaboration while underscoring their vital role in modern workflows.
>
> Industry observers have noted that adoption has accelerated. The future looks bright. Exciting times lie ahead.

| Dimension | Score | Notes |
|-----------|:---:|------|
| Directness | **2** | "Great question!" "I hope this helps!" "Here's an overview" — throat-clearing overload |
| Rhythm | **3** | Chaining -ing phrases, rule of three, generic conclusion |
| Trust | **2** | Over-explains, hand-holds, asks if reader wants more |
| Authenticity | **1** | "groundbreaking" "enduring testament" "pivotal moment" — pure template |
| Density | **2** | Half the text is filler. Core message could be one sentence. |
| **Total** | **10/50** | ❌ Must rewrite |

### Example 2: Clean but Soulless

> AI coding assistants speed up some tasks. A 2024 study found developers using Codex completed simple functions 55% faster. The tools are good at boilerplate. They are bad at knowing when they are wrong. The productivity claims are hard to verify. Acceptance is not correctness, and correctness is not value.

| Dimension | Score | Notes |
|-----------|:---:|------|
| Directness | **8** | Clean, no throat-clearing |
| Rhythm | **4** | Functional but flat — every sentence similar length and structure |
| Trust | **8** | Trusts reader to follow |
| Authenticity | **4** | No voice, no opinion, reads like a neutral report |
| Density | **7** | Reasonably tight |
| **Total** | **31/50** | ⚠️ Borderline — needs voice injection (Personality & Soul) |

### Example 3: Human Voice

> AI coding assistants can make you faster at the boring parts. Not everything. Definitely not architecture.
>
> They're great at boilerplate: config files, test scaffolding, repetitive refactors. They're also great at sounding right while being wrong. I've accepted suggestions that compiled, passed lint, and still missed the point because I stopped paying attention.
>
> People I talk to tend to land in two camps. Some use it like autocomplete for chores and review every line. Others disable it after it keeps suggesting patterns they don't want. Both feel reasonable.
>
> The productivity metrics are slippery. GitHub says Copilot users "accept 30% of suggestions," but acceptance isn't correctness, and correctness isn't value. If you don't have tests, you're basically guessing.

| Dimension | Score | Notes |
|-----------|:---:|------|
| Directness | **9** | Opens with the point. No setup. |
| Rhythm | **8** | Short ("Not everything. Definitely not architecture.") → long → short. Natural breathing. |
| Trust | **9** | Assumes intelligence. Leaves conclusions implicit. |
| Authenticity | **8** | First person. Specific experience. Opinionated. |
| Density | **8** | Lean. Could trim slightly but already tight. |
| **Total** | **42/50** | ✅ Strong |

---

## Scoring Thresholds

| Score Range | Action |
|:---:|------|
| 40-50 | ✅ Excellent. Ship it. |
| 35-39 | ⚠️ Acceptable. Minor tweaks if time. |
| 25-34 | 🔄 Borderline. Revise targeted sections. |
| Below 25 | ❌ Heavy AI signal. Full rewrite needed. |
