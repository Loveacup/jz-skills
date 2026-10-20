# Real Bilibili video fallback and publish gate

## When this applies

A user sends a Bilibili URL and expects the normal single formal `B站笔记_*.md` artifact, but the browser-backed platform adapter cannot read the page during this run.

## Reliable recovery path

1. Treat the platform adapter's doctor result as a **preflight snapshot**, not proof that a browser call will succeed.
2. If the first read command returns a browser-connection/session error, do **not** retry video/subtitle/comments in a loop. Fall back to the analyzer's API/ASR pipeline:
   ```bash
   cd ~/code/jz-skills/shared/bilibili-video-analyzer
   PYTHONPATH=scripts /usr/bin/python3 scripts/fetch_all.py <BVID>
   ```
   This run successfully fetched 167 danmaku, 259 comments, and a chunked H200 ASR transcript for an ~83-minute video.
3. `fetch_all.py` is positional, not argparse-driven: do not use `--help` as a capability probe; it is interpreted as the BVID. Read the script or use a real BVID.
4. If `fetch_all.py` prints `RESULT_JSON` but does not persist a combined `*_fetch_all.json`, use the supported reconstruction route:
   ```bash
   PYTHONPATH=scripts /usr/bin/python3 scripts/generate_report.py --bvid <BVID> ...
   ```
   Then inspect the resulting frontmatter and content before treating it as publishable.

## Publish-quality lesson

A successful writer run is not a successful note. In this case the first generated report had a blank title, a `_骨架占位`, malformed timestamp handling, and claim-first gates G5/G9/G10 failures. It was kept out of the vault.

Before saving or promoting any formal note:

- run `verify_publishable_report.py`;
- manually inspect title/frontmatter, source counts, timestamp links, skeleton residue, and whether audience reactions were actually present in danmaku/comments rather than invented by the writer;
- when necessary, write a bounded evidence-led note from transcript + comments + danmaku, explicitly labeling interview/product assertions as claims rather than independently verified facts;
- preserve exactly one user-facing `B站笔记_*.md` in the vault; temporary ASR/data/report artifacts remain in `/tmp`.

## Obsidian governance route

Use the vault lifecycle rather than writing a core page directly:

1. write the finished note as `lifecycle_state: candidate` in `01-Staging/`;
2. run the report publishability gate;
3. run `vault-keeper/engine/gate.py` against `30-Resources/60_视频笔记`;
4. only if eligible, promote with `promote.py`, then refresh qmd index/embeddings.

This video passed the publishability gate and was promoted R1 with confidence 0.62.
