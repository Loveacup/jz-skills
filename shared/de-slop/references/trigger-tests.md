# Trigger Test Cases

当修改 `SKILL.md` 的 description/triggers 时，跑此表验证不会意外破坏触发率。

---

## Should Trigger ✅

| # | 场景 | 语言 | 应触发？ | 命中词 |
|---|------|:--:|:--:|------|
| 1 | "humanize this paragraph: The groundbreaking innovation..." | EN | ✅ | `humanize` |
| 2 | "de-slop this text" | EN | ✅ | `de-slop` |
| 3 | "rewrite this to sound more natural, it reads like ChatGPT" | EN | ✅ | `rewrite` |
| 4 | "check this article for AI tells before I publish" | EN | ✅ | `check for AI tells` |
| 5 | "edit this draft, it sounds like an AI wrote it" | EN | ✅ | `edit draft` |
| 6 | "帮我去AI味：值得注意的是，在当今数字化背景下..." | ZH | ✅ | `去AI味` |
| 7 | "说人话：随着人工智能技术的不断发展，企业办公模式..." | ZH | ✅ | `说人话` |
| 8 | "这段太AI了，改一下：[text]" | ZH | ✅ | 隐式触发（`太AI了`） |
| 9 | "润色一下让它更自然，别像模板：[text]" | ZH | ✅ | `改得自然一点`/`别像模板` |
| 10 | "polish this prose and remove the AI slop" | EN | ✅ | `polish prose` |

---

## Should NOT Trigger ❌

| # | 场景 | 语言 | 应触发？ | 原因 |
|---|------|:--:|:--:|------|
| 1 | "fix the grammar in this paragraph" | EN | ❌ | Grammar-only fix, not AI detection |
| 2 | "translate this to Chinese" | EN | ❌ | Translation task |
| 3 | "review this code for bugs" | EN | ❌ | Code review → DO NOT use |
| 4 | "write a blog post about AI and remote work" | EN | ❌ | Generation, not editing |
| 5 | "帮我翻译这段英文：[text]" | ZH | ❌ | 翻译任务 |
| 6 | "这段代码有什么问题：[code]" | ZH | ❌ | Code review |
| 7 | "写一篇文章关于远程办公的利弊" | ZH | ❌ | 生成，不是改写 |
| 8 | "format this document with proper headings" | EN | ❌ | Technical formatting → DO NOT use |
| 9 | "summarize this article in 3 bullet points" | EN | ❌ | Summarization, not humanizing |
| 10 | "帮我改一下这篇文章的错别字" | ZH | ❌ | 语法/拼写修正 Only |

---

## Edge Cases ⚠️

| # | 场景 | 预期行为 |
|---|------|---------|
| 1 | "polish this technical documentation" | ✅ Trigger (polish) but skip Personality → Clean Mode |
| 2 | "帮我把这段学术论文改得更自然" | ✅ Trigger but 语体识别 → 学术档，仅改 D/I 类 |
