# Browser / Agent Tool Viability Assessment

Use this note when evaluating products like browser gateways, scraping helpers, Chrome extensions, MCP servers, or CLI tools that give AI agents access to web pages.

## Evidence to gather

- Official site: positioning, install path, docs, pricing, privacy, terms, support/contact.
- Distribution channels: Chrome Web Store listing, npm/PyPI/Homebrew package, GitHub repos, release cadence.
- Adoption signals: users/downloads/ratings/stars/issues, but label vendor-reported numbers separately from independent signals.
- Code/package signals: license, package size, dependency count, source availability, binaries vs readable code, telemetry/update behavior.
- Security boundary: required browser permissions, local vs remote mode, API keys, encryption claims, logging/storage, ability to disable telemetry, whether payment/CAPTCHA/sensitive pages are excluded.
- Fit for user's stack: overlap with existing tools, unique capability, setup burden, failure modes, and whether it should be a skill/MCP/tool integration.

## Output shape

1. Verdict first: real/not real, usable/not usable, trial recommendation.
2. What it does in plain language.
3. Positive evidence with sources.
4. Early-stage / maturity warnings.
5. Privacy and security risk assessment.
6. Suggested staged trial plan.
7. Red lines: what not to connect or automate until trust improves.

## Risk heuristics

- Treat high-permission browser extensions and remote browser-control services as high trust requirements even if the product is legitimate.
- Local-only/read-only modes are usually a safer first trial than remote/full-control modes.
- Do not equate vendor claims of E2E encryption or privacy with independent verification; mark them as self-reported unless audited.
- Prefer isolated browser profiles for first tests, especially when the extension requests `all_urls`, `debugger`, `scripting`, `nativeMessaging`, or similar permissions.

## Tool-selection pattern for web/social extraction

When comparing browser-agent/scraping products against existing skills, do not treat generic tools as replacements for platform-specific skills. Use this selection hierarchy:

1. **Platform-specific skill first** when available. It encodes selectors, auth quirks, output schema, OCR/reporting, and fallback logic. Examples: `xhs-crawler` for 小红书, `xurl` for X/Twitter, `forum-content-extraction` for NGA/BBS, `youtube-content` for YouTube.
2. **Crawl/extract engine second** for public webpages and batch reading. Crawl4AI-style tools are best for public pages, JS-rendered articles, Reddit/Zhihu public pages, ordinary forums, docs, blogs, and URL-to-Markdown pipelines.
3. **Real-browser automation fallback** for logged-in/dynamic pages. agent-browser/Playwright MCP/BrowserMCP-style tools are best for click/scroll/expand, screenshots, login-state reading, and diagnosing why a platform-specific extractor failed.
4. **API/CLI route before scraping** when a reliable authenticated API skill exists. For X/Twitter, prefer `xurl` or official/API-backed routes over browser scraping.

Site notes from prior assessment:
- 小红书: generic crawlers are weak; use `xhs-crawler`; browser automation is a diagnostic/fallback layer.
- Reddit: public extraction is feasible with Crawl4AI-style tools; use browser automation for deep single-thread/comment expansion.
- X/Twitter: generic crawling is poor; prefer API/`xurl`; browser automation only for small read/screenshot fallbacks.
- NGA/BBS: public pages can be crawled; login/permission threads need the forum extraction fallback chain and possibly a logged-in isolated browser profile.
- 知乎: public answers/articles can often be extracted; full answers/comments/login walls often need browser automation.
