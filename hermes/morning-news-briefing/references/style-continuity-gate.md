# Style Continuity Gate — Mobile PDF

Use this reference when a user complains that today's mobile PDF "looks different from yesterday" or "the style changed."

## Root cause pattern

The worker fixing visual defects regenerated the HTML/CSS from scratch instead of reusing the previously accepted template. This produces a style drift even when structural checks pass.

## Prevention

1. **Before creating any mobile PDF repair/rebuild task**, locate the most recent accepted mobile PDF and its HTML source:
   - Search `~/.hermes/workspaces/morning-news-YYYYMMDD/` or `~/.hermes/kanban/workspaces/` for `*-mobile-editorial*.pdf/html`.
   - Use the latest one with a `done` auditor card and no user complaints.

2. **Reference the baseline in the repair task body**:
   - Include the absolute path of the accepted HTML/PDF.
   - Explicitly instruct: "Reuse the CSS color palette and layout from this baseline; do not invent a new style."

3. **Audit must include a style-continuity dimension**:
   - Compare dark-pixel ratio (should match baseline, e.g. ~0.5–0.7% for light themes).
   - Verify palette: paper `#fffdf8` or `#fffdf9`, ink `#202124` or `#1b1a17`, accent `#b47a32` (gold/brown).
   - Confirm newsletter elements: pill labels, reading nav, masthead.
   - Reject if the PDF switches to a dark/financial-terminal theme.

## Recovery when drift is detected

1. Do not argue from page count or file size.
2. Create a new Kanban card: `mn-YYYYMMDD-mobile-vN-light-match-baseline`.
3. Body must contain:
   - Path to today's clean Markdown input.
   - Path to yesterday's accepted HTML baseline.
   - Explicit style constraints (copy the palette and layout rules from the baseline).
4. Dependent audit card must check style continuity plus the usual structural/visual gates.
5. Only deliver after the audit passes the style-continuity dimension.

## Accepted mobile palette (as of 2026-05-21)

| Token | Value | Usage |
|-------|-------|-------|
| `--paper` | `#fffdf9` | Page background |
| `--ink` | `#202124` | Primary body text |
| `--gold` | `#b47a32` | Accent / highlights / borders |
| `--soft` | `#fff8ed` | Card backgrounds |
| `--wash` | `#f7f0e6` | Subtle section backgrounds |

Dark-pixel ratio target: < 1% (light theme).

## Anti-pattern

- ❌ "Fix the visual issues" without referencing a baseline → worker invents a new style.
- ❌ Auditing only structure (div balance, U+FFFD) and ignoring color palette → passes a visually wrong PDF.
- ❌ Delivering a dark-theme PDF when the user has accepted a light newsletter theme.
