# Cross-platform Bilibili + YouTube full Obsidian report workflow (2026-07-05)

## Trigger

User provides both a Bilibili URL and a YouTube URL, and asks for a full Obsidian note / 落库 / 跑质量门. Typical case: Bilibili is a Chinese mirror or trimmed/translated version whose description points to the YouTube original.

## Durable workflow

1. **Confirm relationship with lightweight metadata first**
   - Bilibili: use `x/web-interface/view` to inspect title, description, duration, pages, cid, stats.
   - YouTube: use `fetch_youtube.py` or yt-dlp metadata.
   - If Bilibili description points to the same YouTube URL, treat it as one cross-platform artifact, not two independent notes.

2. **Collect both evidence streams**
   - Bilibili: `fetch_all.py <BV> --report` to collect danmaku, comments, subtitle/ASR, and cross-platform YouTube comments if detected.
   - YouTube: `fetch_youtube.py '<url>' --limit 50` for metadata, transcript, comments.
   - For a hand-written full report, also fetch a clean timestamped transcript via `media/youtube-content/scripts/fetch_transcript.py '<url>' --timestamps` and use it as the primary source when the YouTube video is the original.

3. **Do not publish engine skeletons**
   - `/tmp/<video_id>_youtube_report.md` and `/tmp/<BV>_report.md` are useful evidence/scaffolding only.
   - Hand-write the full `## 0.`–`## 8.` report from the transcript and comments.
   - Include a title/description vs transcript alignment check when the Bilibili title/intro repackages the original.

4. **Cross-check external factual claims**
   - Mode: WRR `grounding`.
   - Engines: Exa + Brave when available; if one times out, keep the successful source and explicitly note the fallback.
   - High-value sources for LLM Wiki-style videos: Karpathy LLM Wiki gist, Claude Code MCP docs, Zapier MCP official page, Obsidian Web Clipper docs.
   - Use official/primary sources for product capability claims; do not treat creator narration or comments as final truth.

5. **Save correctly**
   - Draft to `/tmp/B站笔记_<主题>_<YYYYMMDD>.md`.
   - Run `verify_report.py` before saving.
   - Save via terminal `cp`, not `write_file`, into the vault's current video note directory (`30-Resources/60_视频笔记/` in AlexCai vault v2).
   - After `cp`, run `chmod 644 <final.md>` if the file lands as `600`, then `ls -la` and `wc -c`.

6. **Verify the final saved artifact**
   - Re-run `verify_report.py <final.md>` on the saved Obsidian path.
   - Run a human-readable publish QA: no `骨架占位`/Skeleton residue, no >1000 char raw transcript lines, §1 has table + Mermaid, §3/§4/§7 are prose analysis, §5 quotes are curated and short, source map exists.
   - Update search index: `qmd update`; if it reports new hashes needing vectors, run `qmd embed`.

## Pattern from the 2026-07-05 sample

- Bilibili `BV1VQ7561ErK`: P1 Chinese processed version + P2 English original, zero danmaku, three low-signal comments.
- YouTube `0-QDPnEIkvw`: original source; transcript-api produced 394 segments; comments gave better implementation feedback.
- Full report passed `verify_report.py` only after expanding §4 Deep Dive beyond the minimum; initial failure was `G4 min 377 words`.
- Useful content stance: absorb the LLM Wiki pattern into Alex's existing OB lifecycle; do not recommend a permanent nightly cron. Prefer phase-based / cumulative-trigger automation with explicit retirement conditions.
