# Bookmark timeline & usage ranking design notes

Use when the user asks for 按年份归档、书签考古、书签时光机、常用书签、点击排序、usage ranking, or history-based sorting.

> Status (2026-06-11): P1 `timeline` is **implemented** in `bookmark-cli.py` (year archive,
> URL dedupe with earliest add_date, import-batch detection ≥30/min, `--stats-json` for the
> P3 strata narrative). P2 `usage` / `render --sort usage` remains **unimplemented and
> deferred** pending explicit History permission and a main-device History export.

## Session-derived facts to preserve

- `bookmark-cli.py render` groups only by category → subcategory; the year archive lives in the separate `timeline` subcommand. Usage sorting is still unimplemented.
- Parser already preserves bookmark timestamps:
  - Chrome JSON `date_added` is WebKit/Chrome 1601-epoch microseconds and is converted to Unix seconds.
  - Netscape HTML `ADD_DATE` is carried through.
  - Render writes `ADD_DATE` back to HTML.
- Bookmark export formats (Netscape HTML / Chrome Bookmarks JSON) do **not** contain click counts, visit counts, or “frequently used” signals.

## Year archive / “bookmark time machine” design

Correct time-line口径:
1. Exclude built-in buckets (`browser-internal`, `bookmarklet`) unless the user explicitly wants them.
2. Deduplicate by URL and take the **earliest** `add_date` per URL as `first_added_at`.
3. Derive `year` from `first_added_at`.
4. Detect import/sync batches: many items added in the same minute/day (e.g. ≥30/minute) should be marked `import_batch`; their timestamp is only a lower bound, not necessarily the true first discovery time.
5. Put missing/impossible dates (`<2000`, future) into an “年份未知” bucket.

Recommended outputs:
- `书签时光机_<source>_YYYYMMDD.md` in Obsidian `00-Inbox/`: frontmatter, stats callout, migration-batch caveat, sections by year, each year summarizing top categories/domains and representative bookmarks.
- Optional HTML timeline folder only when the user explicitly opts in, because importing it can duplicate bookmarks.
- Optional analytics view: category × year matrix and era labels.

Suggested optional schema fields:
- `first_added_at`, `year`, `import_batch`, `era`
- Keep them optional and backward-compatible. Prefer a read-only derived timeline unless the user asks to annotate `classified.json`.

## Usage / click ranking design

Data source:
- Local Chromium History SQLite, e.g. Chrome `~/Library/Application Support/Google/Chrome/<Profile>/History` or Edge equivalent.
- Relevant fields: `urls.visit_count`, `urls.typed_count`, `urls.last_visit_time`, `urls.hidden`, plus `visits`/`visit_source` when deeper filtering is needed.

Privacy and safety gate:
1. Ask explicit permission before reading History; do not treat bookmark permission as History permission.
2. Copy the DB to a temp snapshot and query the copy only.
3. Never write to the browser DB.
4. Drop non-bookmark history rows after aggregation; do not persist unrelated browsing history.
5. Delete the temp snapshot after use.
6. Report coverage honestly.

Join strategy:
1. Exact URL match.
2. Canonicalized URL match: remove fragment, common `utm_*`, normalize trailing slash and http/https where safe.
3. Domain-level fallback with low confidence, used only as a weak within-category hint.
4. Filter out ghost rows: `hidden=1` or `visit_count=0` should not count as real usage. A local test showed many apparent bookmark/history matches were ghost rows.

Scoring:
- Avoid claiming “all-time most used”: Chromium history is commonly time-limited and device-local.
- Prefer buckets over false precision: 🔥 高频 / ⭐ 常用 / 偶用 / 无记录.
- Example: `usage_score = visit_count + 3 * typed_count`, optionally with recency decay from `last_visit_time` (e.g. 30-day half-life).

Failure modes to mention to the user:
- History may only cover recent months.
- The current machine may not be the primary browsing/bookmarking machine.
- Private/incognito browsing is absent.
- Synced history and bookmarks can diverge.
- Running browser may lock the DB, so use snapshot copy.

## Recommended implementation phases

- P1 Timeline — **DONE** (2026-06-11): `timeline` subcommand reads classified data and emits Markdown + `--stats-json`. No new permission required.
- P2 Usage — deferred: add a `usage` subcommand that ingests an explicitly approved History snapshot, joins/scores bookmarks, and allows `render --sort usage`. Local-machine coverage was only ≈2.2% (45/2002 URLs), so run against a main-device History export.
- P3 Archaeology narrative — **DONE** (2026-06-11, agent-side): era summaries written by the agent from `timeline --stats-json` output; every number must come from the stats JSON.
