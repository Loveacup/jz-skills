# AI Model Comparison Verification Notes

Use this when comparing frontier/API models for agent, coding, context, pricing, or Hermes model-routing decisions.

## Source priority

1. Official provider model/release pages for benchmark tables and capability claims.
2. Official API pricing docs for token prices, cache read/write prices, context length, output limits, and compatibility notes.
3. Hugging Face model cards / evalResults for open-weight models, especially when official pages are marketing-heavy.
4. Third-party leaderboards only as secondary evidence; label them as such.

## What to extract

- Model identifier and exact variant (e.g. standard vs highspeed/turbo/pro, thinking vs non-thinking).
- Context window and max output length; do not conflate them.
- Pricing per 1M input/output tokens; separately record cache read/write and promotional discounts.
- Agent/coding benchmarks: Terminal-Bench, SWE-Bench Pro, SWE-Bench Verified, Toolathlon, Claw/MMClaw, VIBE-Pro when available.
- Reasoning/knowledge benchmarks: GPQA Diamond, HLE with/without tools, AIME/HMMT/IMO-style math where relevant.
- Multimodal support and benchmark conditions if vision/video is part of the comparison.

## Comparison discipline

- Separate “main model suitability” from raw benchmark rank. For Hermes-style main models, terminal/tool long-run stability matters more than generic chat quality.
- Mark benchmark condition differences: tool-augmented vs no-tools, thinking effort, in-house harness, averaged runs, re-evaluated scores, context-management tricks, and max-token settings.
- Do not compare a provider’s current model to another provider’s older model without labeling the mismatch.
- Treat “open-weight” and “official hosted API” as separate deployment questions; latency, throughput, and tool-call formatting may differ.
- For cost, calculate at least one blended workload cost, commonly 70% input / 30% output, and show ratios to the baseline model. Use an actual calculator/tool, not mental math.

## Recent provider quirks captured from research

- Kimi K2.6: official docs/model card report 256K/262,144-token context, native text/image/video, thinking/non-thinking modes, and strong SWE-Bench Pro/SWE-Bench Verified. Some benchmark comparisons are against GPT-5.4 rather than GPT-5.5; label that.
- MiniMax M2.7: official docs report 204,800-token context, standard and highspeed variants with same benchmark claims but different price/speed. MiniMax recommends the Anthropic-compatible endpoint for thinking/interleaved-thinking support. It is text-generation oriented; do not assume it replaces a vision model.
- DeepSeek V4 Pro: strong fit for 1M-context and low-cost compression/long-context work; distinguish list price from temporary promotional pricing.

## Suggested output shape

- Start with the recommendation in one or two lines.
- Then group by: role/positioning, coding-agent data, reasoning data, context, price, recommended routing.
- Avoid wide markdown tables on Telegram; use compact bullet lists instead.
