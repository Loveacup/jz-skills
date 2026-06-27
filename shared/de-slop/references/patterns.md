# AI Writing Patterns — Complete Reference

30+ patterns organized by category. Each includes: problem explanation, trigger words/phrases, and before/after examples.

---

## CONTENT PATTERNS

### 1. Significance Inflation

**Words to watch:** stands/serves as, testament, pivotal moment, underscores/highlights importance, reflects broader, symbolizing its ongoing/enduring, marking/shaping the, key turning point, evolving landscape, indelible mark

**Problem:** LLMs puff up ordinary facts into grand historical significance.

**Before:** The Statistical Institute of Catalonia was established in 1989, marking a pivotal moment in the evolution of regional statistics.

**After:** The Statistical Institute of Catalonia was established in 1989 to collect regional statistics.

### 2. Notability Overemphasis

**Words to watch:** independent coverage, local/regional/national media outlets, active social media presence, written by a leading expert

**Problem:** Hammering claims of importance instead of providing context.

**Before:** Her views have been cited in The New York Times, BBC, and Financial Times. She maintains an active social media presence with over 500,000 followers.

**After:** In a 2024 New York Times interview, she argued that AI regulation should focus on outcomes rather than methods.

### 3. -ing Phrase Padding

**Words to watch:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., fostering..., showcasing...

**Problem:** Tacking -ing clauses onto sentence ends to manufacture depth.

**Before:** The temple's color palette resonates with the region's beauty, symbolizing Texas bluebonnets, reflecting the community's connection to the land.

**After:** The temple uses blue, green, and gold. The architect said these reference local bluebonnets.

### 4. Promotional / Advertisement Language

**Words to watch:** boasts a, vibrant, rich (figurative), profound, nestled, in the heart of, groundbreaking (figurative), renowned, breathtaking, must-visit, stunning

**Problem:** AI can't keep a neutral tone, especially for "cultural heritage" topics.

**Before:** Nestled within the breathtaking region of Gonder, Alamata stands as a vibrant town with rich cultural heritage and stunning natural beauty.

**After:** Alamata Raya Kobo is a town in the Gonder region, known for its weekly market.

### 5. Vague Attributions

**Words to watch:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications

**Problem:** Attributing opinions to unnamed authorities without sources.

**Before:** Experts believe it plays a crucial role in the regional ecosystem.

**After:** The river supports several endemic fish species, according to a 2019 Chinese Academy of Sciences survey.

### 6. Formulaic "Challenges" Sections

**Words to watch:** Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook

**Problem:** Every AI article ends with a templated "challenges and future" section.

**Before:** Despite its prosperity, Korattur faces challenges including traffic. Despite these challenges, it continues to thrive.

**After:** Traffic increased after 2015 when three IT parks opened. The municipality began a drainage project in 2022.

---

## LANGUAGE & GRAMMAR PATTERNS

### 7. AI Vocabulary Words

**High-frequency AI words:** Actually, additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant

**Problem:** These words appear far more frequently in post-2023 text. They often co-occur.

**Before:** An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape, showcasing integration into the traditional diet.

**After:** Pasta dishes, introduced during Italian colonization, remain common in the south.

### 8. Copula Avoidance

**Words to watch:** serves as/stands as/marks/represents [a], boasts/features/offers [a]

**Problem:** LLMs substitute elaborate constructions for simple "is"/"are"/"has".

**Before:** Gallery 825 serves as LAAA's exhibition space. The gallery features four spaces and boasts over 3,000 square feet.

**After:** Gallery 825 is LAAA's exhibition space. The gallery has four rooms totaling 3,000 square feet.

### 9. Negative Parallelisms & Tailing Negations

**Problem:** "Not only...but..." / "It's not just X, it's Y" / clipped negations like "no guessing."

**Before:** It's not just about the beat; it's part of the aggression. The options come from the selected item, no guessing.

**After:** The heavy beat adds to the aggressive tone. The options come from the selected item without forcing the user to guess.

### 10. Rule of Three Overuse

**Problem:** AI forces ideas into groups of three for false comprehensiveness.

**Before:** The event features keynotes, panels, and networking. Innovation, inspiration, and industry insights.

**After:** The event includes talks and panels. Time for informal networking between sessions.

### 11. Elegant Variation (Synonym Cycling)

**Problem:** AI's repetition-penalty causes excessive synonym substitution.

**Before:** The protagonist faces challenges. The main character overcomes obstacles. The central figure triumphs. The hero returns.

**After:** The protagonist faces many challenges but eventually triumphs and returns home.

### 12. False Ranges

**Problem:** "From X to Y" where X and Y aren't on a meaningful scale.

**Before:** From the singularity of the Big Bang to the grand cosmic web, from the birth of stars to the dance of dark matter.

**After:** The book covers the Big Bang, star formation, and dark matter theories.

### 13. Passive Voice & Subjectless Fragments

**Problem:** Hiding the actor or dropping the subject entirely.

**Before:** No configuration file needed. The results are preserved automatically.

**After:** You do not need a configuration file. The system preserves the results automatically.

---

## STYLE PATTERNS

### 14. Em Dashes (Hard Constraint)

**Rule:** Final rewrite contains ZERO em dashes (—) or en dashes (–). Replace with: period, comma, colon, parentheses, or restructure. Also catch spaced dashes (` — `) and double hyphens (`--`).

**Before:** The term is promoted by Dutch institutions—not by the people themselves—yet this continues.

**After:** The term is promoted by Dutch institutions, not by the people themselves. Yet this mislabeling continues.

### 15. Boldface Overuse

**Problem:** AI emphasizes phrases in bold mechanically.

**Before:** It blends **OKRs**, **KPIs**, and the **Business Model Canvas**.

**After:** It blends OKRs, KPIs, and the Business Model Canvas.

### 16. Inline-Header Vertical Lists

**Problem:** AI lists where each item starts with bolded header + colon.

**Before:** - **User Experience:** The UX has been improved. - **Performance:** Speed enhanced. - **Security:** Encryption added.

**After:** The update improves the interface, speeds up load times, and adds end-to-end encryption.

### 17. Title Case in Headings

**Problem:** AI capitalizes all main words in headings.

**Before:** ## Strategic Negotiations And Global Partnerships

**After:** ## Strategic negotiations and global partnerships

### 18. Emojis

**Problem:** AI decorates headings/bullets with emojis.

**Before:** 🚀 **Launch Phase:** Product launches Q3. ✅ **Next Steps:** Schedule meeting.

**After:** The product launches in Q3. Next step: schedule a follow-up.

### 19. Curly Quotation Marks

**Problem:** ChatGPT uses curly quotes ("...") instead of straight quotes ("...").

**Before:** He said "the project is on track."

**After:** He said "the project is on track."

---

## COMMUNICATION PATTERNS

### 20. Chatbot Artifacts

**Words to watch:** I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., let me know

**Problem:** Conversation correspondence pasted as content.

**Before:** Here is an overview of the French Revolution. I hope this helps! Let me know if you'd like me to expand.

**After:** The French Revolution began in 1789 when financial crisis led to widespread unrest.

### 21. Knowledge-Cutoff Disclaimers & Speculative Gap-Filling

**Words to watch:** as of [date], up to my last training update, While specific details are limited, based on available information, maintains a low profile, keeps personal details private, likely grew up/studied

**Problem:** (a) Cutoff disclaimers left in. (b) When info is unavailable, AI invents plausible filler instead of saying "unknown."

**Before (gap-fill):** Information about her early life is not publicly available, suggesting she maintains a low profile. She likely grew up in a middle-class household.

**After:** Her early life is not documented in the available sources. (Or omit the section entirely.)

### 22. Sycophantic / Servile Tone

**Problem:** Overly positive, people-pleasing language.

**Before:** Great question! You're absolutely right that this is complex. That's an excellent point.

**After:** The economic factors you mentioned are relevant here.

---

## FILLER & HEDGING

### 23. Filler Phrases

**Before → After:**
- "In order to achieve this goal" → "To achieve this"
- "Due to the fact that" → "Because"
- "At this point in time" → "Now"
- "In the event that" → "If"
- "has the ability to" → "can"
- "It is important to note that" → (delete, state directly)

### 24. Excessive Hedging

**Before:** It could potentially possibly be argued that the policy might have some effect.

**After:** The policy may affect outcomes.

### 25. Generic Positive Conclusions

**Before:** The future looks bright. Exciting times lie ahead as they continue their journey toward excellence.

**After:** The company plans to open two more locations next year.

### 26. Hyphenated Word Pair Overuse

**Words affected:** third-party, cross-functional, client-facing, data-driven, decision-making, well-known, high-quality, real-time, long-term

**Rule:** Keep hyphens when attributive (before noun: "a high-quality report"). Drop when predicate (after noun: "the report is high quality").

**Before:** The cross-functional team delivered a high-quality report. The team is cross-functional, and the report is high-quality.

**After:** The cross-functional team delivered a high-quality report. The team is cross functional, and the report is high quality.

### 27. Persuasive Authority Tropes

**Phrases:** The real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter

**Before:** The real question is whether teams can adapt. At its core, what really matters is readiness.

**After:** The question is whether teams can adapt. That mostly depends on whether the organization is ready to change.

### 28. Signposting & Announcements

**Phrases:** Let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado

**Before:** Let's dive into how caching works in Next.js. Here's what you need to know.

**After:** Next.js caches data at multiple layers: request memoization, the data cache, and the router cache.

### 29. Fragmented Headers

**Problem:** Heading followed by one-line paragraph that restates the heading.

**Before:**
> ## Performance
> Speed matters.
> When users hit a slow page, they leave.

**After:**
> ## Performance
> When users hit a slow page, they leave.

### 30. Diff-Anchored Writing

**Problem:** Documentation written as narrating a change, not describing the thing as it is.

**Before:** This function was added to replace the previous approach, which caused O(n²) performance.

**After:** This function uses a hash map for O(1) lookups, avoiding the O(n²) cost of naive iteration.

---

## STRUCTURAL ANTI-PATTERNS (from stop-slop)

### 31. Binary Contrasts

False drama through negation-then-assertion.

| Pattern | Fix |
|---------|-----|
| "Not because X. Because Y." | State Y directly |
| "[X] isn't the problem. [Y] is." | "The problem is Y" |
| "It feels like X. It's actually Y." | Drop the setup |
| "The question isn't X. It's Y." | Ask Y directly |
| "doesn't mean X, but actually Y" | State Y |

### 32. Negative Listing

Listing what something is NOT before revealing what it IS. A rhetorical striptease.

**Before:** Not a framework. Not a platform. Not a library. A new way to build.

**After:** A new build system.

### 33. Dramatic Fragmentation

Sentence fragments for emphasis read as manufactured profundity.

| Pattern | Problem |
|---------|---------|
| "[Noun]. That's it. That's the [thing]." | Performative simplicity |
| "X. And Y. And Z." | Staccato drama |

**Before:** Speed. Quality. Cost. You can only pick two. That's it. That's the tradeoff.

**After:** Speed, quality, cost—pick two.

### 34. False Agency

Giving inanimate things human verbs. Complaints don't "become" fixes. Bets don't "live or die." Decisions don't "emerge." **Name the human.**

| Pattern | Fix |
|---------|-----|
| "a complaint becomes a fix" | Someone fixed it |
| "the decision emerges" | Someone decided |
| "the culture shifts" | People changed behavior |
| "the data tells us" | Someone read the data |
| "the market rewards" | Buyers paid for things |

### 35. Narrator-from-a-Distance

Floating above the scene instead of putting the reader in it.

| Pattern | Fix |
|---------|-----|
| "Nobody designed this." | "You don't sit down one day and decide to..." |
| "This happens because..." | Put reader in the scene |
| "People tend to..." | "You probably..." |

### 36. Rhetorical Setups

Announcing insight rather than delivering it.

| Pattern | Fix |
|---------|-----|
| "What if [reframe]?" | Make the claim |
| "Here's what I mean:" | Delete, restate |
| "Think about it:" | Delete |
| "And that's okay." | Delete |

### 37. Wh- Sentence Starters

Sentences starting with What, When, Where, Which, Who, Why, How → Restructure. Lead with subject or verb.

**Before:** What makes this hard is the constraint on memory.

**After:** The 16GB memory constraint makes this hard.

### 38. Lazy Extremes

Words: every, always, never, everyone, everybody, nobody → use specifics instead.

**Before:** Everyone knows this approach fails. It always breaks in production.

**After:** Three teams reported failures with this approach in production last quarter.

---

## ADDITIONAL PATTERNS

### Throat-Clearing Openers (stop-slop extended list)

Remove these and state the content directly:

"Here's the thing:", "Here's what [X]", "It turns out", "The uncomfortable truth is", "Let me be clear", "I'll say it again:", "I'm going to be honest", "Can we talk about", "The real [X] is"

### Emphasis Crutches (stop-slop)

Delete. They add zero meaning:

"Full stop." / "Period.", "Let that sink in.", "This matters because", "Make no mistake"

### Business Jargon (stop-slop)

| Avoid | Use instead |
|-------|-------------|
| Navigate (challenges) | Handle |
| Unpack (analysis) | Explain |
| Lean into | Accept |
| Landscape (context) | Situation |
| Game-changer | Significant |
| Double down | Commit |
| Deep dive | Analysis |
| Circle back | Return to |
| On the same page | Aligned |

### Meta-Commentary (stop-slop)

Remove self-referential asides:

"Hint:", "Plot twist:", "You already know this, but", "But that's another post", "X is a feature, not a bug", "The rest of this essay...", "Let me walk you through...", "As we'll see..."

### Vague Declaratives (stop-slop)

Sentences that announce importance without naming specifics:

"The reasons are structural", "The implications are significant", "This is the deepest problem", "The stakes are high", "The consequences are real"

→ Either name the specific thing or delete the sentence.

### Adverbs (stop-slop)

Kill all -ly words and softeners: really, just, literally, genuinely, honestly, simply, actually, deeply, truly, fundamentally, inherently, inevitably, interestingly, importantly, crucially
