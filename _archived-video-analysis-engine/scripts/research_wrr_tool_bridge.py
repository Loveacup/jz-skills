#!/usr/bin/env python3
"""S9-1 injectable WRR tool bridge: dispatcher seam, raw/untrusted output only.

Wraps an injected :class:`SyncToolDispatcher` so it can serve as the query
executor for :class:`research_wrr_adapter.HermesWRRAdapter`. The bridge:

* invokes the dispatcher *exactly once* per query with ``name='web_search'`` and
  a bounded arg mapping (query text, route mode, ``max_results``) — it never
  forces a provider/engine, reads env/credentials, opens a socket, or retries;
* accepts only a JSON string or a mapping response, rejecting an over-bound
  string *before* parsing so an oversized blob can never reach ``json.loads``;
* parses the ``success``/``details.results`` envelope and normalizes each result
  down to the adapter's raw discovery keys, dropping unknown keys and skipping
  any non-mapping / malformed entry — an empty result set is valid;
* fabricates no quote/snapshot/evidence on the search path — S5's validator owns
  every promotion.

S9-3 adds an explicit, opt-in :meth:`HermesWRRToolExecutor.enrich_selected_candidates`
seam: given externally-selected discovery candidates it dispatches ``web_fetch``
once per deduplicated, capped URL and returns a fresh enriched mapping carrying
the fetched ``content``, a ``content_sha256`` over that text, a ``full`` snapshot,
and ``quote_candidates`` built only from *exact* highlight substrings. The search
``__call__`` path never fetches; enrichment happens only when this method is
called.

Every failure surfaces a stable, public :class:`ResearchExecutorError` code and
never reflects the raw response, a secret, or a provider internal. The private
cause is severed with ``from None`` so no traceback can leak it.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Protocol, runtime_checkable

from research_transport import ResearchExecutorError


@runtime_checkable
class SyncToolDispatcher(Protocol):
    """Injected synchronous tool seam: dispatch a named tool call to raw output.

    ``dispatch`` receives a stable tool ``name`` and a plain ``args`` mapping and
    returns either a JSON string or a mapping. It owns transport, retries, and
    engine selection; the bridge calls it once per query and trusts nothing it
    returns.
    """

    def dispatch(self, name: str, args: dict) -> "str | dict":
        ...


# Raw discovery metadata only — the S5 validator/adjudicator owns every
# evidence/quote/source promotion downstream. Route/provider metadata is passed
# through when the tool supplies it; nothing here is fabricated.
_DISCOVERY_KEYS = (
    "url",
    "canonical_url",
    "title",
    "snippet",
    "content",
    "published_at",
    "source_kind",
    "authority_relation",
    "publisher",
    "publisher_group",
    "route",
    "provider",
    "provider_confidence",
)

# Stable, public failure codes. None reflects the raw response or a secret.
_ERR_DISPATCH_FAILED = "tool_dispatch_failed"
_ERR_RESPONSE_TYPE = "tool_response_type_invalid"
_ERR_RESPONSE_TOO_LARGE = "tool_response_too_large"
_ERR_RESPONSE_UNPARSEABLE = "tool_response_unparseable"
_ERR_RESPONSE_UNSUCCESSFUL = "tool_response_unsuccessful"
_ERR_RESPONSE_MALFORMED = "tool_response_malformed"

# S9-3 fetch-enrichment codes — same discipline: a failed candidate yields only
# one of these stable strings, never a URL / text / secret / raw response.
_ERR_FETCH_DISPATCH_FAILED = "fetch_dispatch_failed"
_ERR_FETCH_RESPONSE_TYPE = "fetch_response_type_invalid"
_ERR_FETCH_RESPONSE_TOO_LARGE = "fetch_response_too_large"
_ERR_FETCH_RESPONSE_UNPARSEABLE = "fetch_response_unparseable"
_ERR_FETCH_RESPONSE_UNSUCCESSFUL = "fetch_response_unsuccessful"
_ERR_FETCH_RESPONSE_MALFORMED = "fetch_response_malformed"
_ERR_FETCH_URL_MISMATCH = "fetch_url_mismatch"
_ERR_FETCH_TEXT_INVALID = "fetch_text_invalid"
_ERR_FETCH_CHARS_MISMATCH = "fetch_chars_mismatch"
_ERR_FETCH_HIGHLIGHTS_INVALID = "fetch_highlights_invalid"


class HermesWRRToolExecutor:
    """Adapt a :class:`SyncToolDispatcher` into a WRR-adapter query executor."""

    def __init__(
        self,
        dispatcher: SyncToolDispatcher,
        *,
        max_results: int = 10,
        max_response_chars: int = 65536,
        max_fetches: int = 3,
        max_fetch_chars: int = 20000,
    ) -> None:
        self._dispatcher = dispatcher
        self._max_results = max(0, int(max_results))
        self._max_response_chars = max(0, int(max_response_chars))
        # Enrichment budget: at most ``max_fetches`` retained URLs, each fetched
        # once with a bounded ``max_characters`` request. Both stay positive.
        self._max_fetches = max(0, int(max_fetches))
        self._max_fetch_chars = max(1, int(max_fetch_chars))

    def __call__(self, query: Mapping[str, object]) -> Mapping[str, object]:
        args = {
            "query": query["query"],
            "mode": query.get("mode"),
            "max_results": self._max_results,
        }
        try:
            response = self._dispatcher.dispatch("web_search", args)
        except Exception:
            # WRR owns retries; the private cause is dropped, never reflected.
            raise ResearchExecutorError(_ERR_DISPATCH_FAILED) from None

        envelope = self._parse_envelope(response)
        results = self._extract_results(envelope)
        return {"results": tuple(self._normalize_results(results))}

    def _parse_envelope(self, response: object) -> Mapping[str, object]:
        if isinstance(response, str):
            # Size-gate the raw string *before* parsing so an oversized blob can
            # never reach ``json.loads`` (and can never be reflected on failure).
            if len(response) > self._max_response_chars:
                raise ResearchExecutorError(_ERR_RESPONSE_TOO_LARGE) from None
            try:
                parsed = json.loads(response)
            except Exception:
                raise ResearchExecutorError(_ERR_RESPONSE_UNPARSEABLE) from None
            if not isinstance(parsed, Mapping):
                raise ResearchExecutorError(_ERR_RESPONSE_MALFORMED) from None
            return parsed
        if isinstance(response, Mapping):
            return response
        raise ResearchExecutorError(_ERR_RESPONSE_TYPE) from None

    @staticmethod
    def _extract_results(envelope: Mapping[str, object]) -> list:
        if envelope.get("success") is not True:
            raise ResearchExecutorError(_ERR_RESPONSE_UNSUCCESSFUL) from None
        details = envelope.get("details")
        if not isinstance(details, Mapping):
            raise ResearchExecutorError(_ERR_RESPONSE_MALFORMED) from None
        results = details.get("results")
        # A list/tuple is required; a bare string is iterable but not a result
        # list, so reject anything that is not an actual sequence of records.
        if not isinstance(results, (list, tuple)):
            raise ResearchExecutorError(_ERR_RESPONSE_MALFORMED) from None
        return list(results)

    def _normalize_results(self, results: list) -> list:
        normalized: list = []
        for raw in results:
            if len(normalized) >= self._max_results:
                break
            if not isinstance(raw, Mapping):
                # Malformed / non-mapping records are skipped, never raised.
                continue
            item = {key: raw[key] for key in _DISCOVERY_KEYS if key in raw}
            normalized.append(item)
        return normalized

    # ------------------------------------------------------------------
    # S9-3: explicit, opt-in fetch enrichment.
    #
    # ``enrich_selected_candidates`` is the *only* path that dispatches
    # ``web_fetch``; ``__call__`` (search) never does. The caller supplies
    # already-selected discovery candidate mappings; this method deduplicates by
    # first-seen valid string URL, fetches at most ``max_fetches`` of them once
    # each, and returns a fresh enriched mapping per success — the input is never
    # mutated in place. A candidate that fails validation produces no output and
    # contributes one stable public error code (never a URL / text / secret /
    # raw response / exception); one failure never affects the others.
    # ------------------------------------------------------------------
    def enrich_selected_candidates(
        self, candidates
    ) -> Mapping[str, object]:
        enriched: list = []
        errors: list = []
        seen: set = set()
        fetched = 0
        for candidate in candidates:
            if fetched >= self._max_fetches:
                break
            url = self._selected_url(candidate)
            if url is None or url in seen:
                # No valid URL, or a repeat of an already-retained one: skip
                # without consuming fetch budget and without an error code.
                continue
            seen.add(url)
            fetched += 1
            try:
                enriched.append(self._enrich_candidate(candidate, url))
            except ResearchExecutorError as err:
                # Isolated, redacted: only the stable code survives.
                errors.append(err.code)
        return {"enriched": tuple(enriched), "errors": tuple(errors)}

    @staticmethod
    def _selected_url(candidate: object) -> "str | None":
        if not isinstance(candidate, Mapping):
            return None
        url = candidate.get("url")
        if not isinstance(url, str) or not url:
            return None
        # Canonical absolute http(s) only. ``urllib`` is a red-lined import, so
        # the ``urlsplit`` semantics are enforced by hand: an ``http``/``https``
        # scheme, a non-empty netloc, and no whitespace/control characters
        # anywhere. Anything else (blank, ``ftp``, relative, bare host) is
        # skipped — no fetch, no error, no budget spent.
        if any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in url):
            return None
        lowered = url.lower()
        for scheme in ("http://", "https://"):
            if lowered.startswith(scheme):
                rest = url[len(scheme):]
                # netloc is the authority up to the first path/query/fragment.
                netloc = rest
                for delimiter in ("/", "?", "#"):
                    idx = netloc.find(delimiter)
                    if idx != -1:
                        netloc = netloc[:idx]
                return url if netloc else None
        return None

    def _enrich_candidate(
        self, candidate: Mapping[str, object], url: str
    ) -> Mapping[str, object]:
        try:
            response = self._dispatcher.dispatch(
                "web_fetch", {"url": url, "max_characters": self._max_fetch_chars}
            )
        except Exception:
            # WRR owns retries; the private cause is dropped, never reflected.
            raise ResearchExecutorError(_ERR_FETCH_DISPATCH_FAILED) from None

        envelope = self._parse_fetch_envelope(response)
        text, highlights = self._fetch_details(envelope, url)
        return self._build_enriched(candidate, text, highlights)

    def _parse_fetch_envelope(self, response: object) -> Mapping[str, object]:
        if isinstance(response, str):
            # Size-gate before parsing so an oversized blob never reaches
            # ``json.loads`` and can never be reflected on failure.
            if len(response) > self._max_response_chars:
                raise ResearchExecutorError(_ERR_FETCH_RESPONSE_TOO_LARGE) from None
            try:
                parsed = json.loads(response)
            except Exception:
                raise ResearchExecutorError(_ERR_FETCH_RESPONSE_UNPARSEABLE) from None
            if not isinstance(parsed, Mapping):
                raise ResearchExecutorError(_ERR_FETCH_RESPONSE_MALFORMED) from None
            return parsed
        if isinstance(response, Mapping):
            return response
        raise ResearchExecutorError(_ERR_FETCH_RESPONSE_TYPE) from None

    @staticmethod
    def _fetch_details(envelope: Mapping[str, object], url: str):
        if envelope.get("success") is not True:
            raise ResearchExecutorError(_ERR_FETCH_RESPONSE_UNSUCCESSFUL) from None
        details = envelope.get("details")
        if not isinstance(details, Mapping):
            raise ResearchExecutorError(_ERR_FETCH_RESPONSE_MALFORMED) from None
        # The fetched snapshot must be exactly the URL we requested.
        if details.get("url") != url:
            raise ResearchExecutorError(_ERR_FETCH_URL_MISMATCH) from None
        text = details.get("text")
        if not isinstance(text, str) or not text:
            raise ResearchExecutorError(_ERR_FETCH_TEXT_INVALID) from None
        chars = details.get("chars")
        if not isinstance(chars, int) or isinstance(chars, bool) or chars != len(text):
            raise ResearchExecutorError(_ERR_FETCH_CHARS_MISMATCH) from None
        highlights = details.get("highlights")
        if not isinstance(highlights, (list, tuple)):
            raise ResearchExecutorError(_ERR_FETCH_HIGHLIGHTS_INVALID) from None
        return text, highlights

    def _build_enriched(
        self, candidate: Mapping[str, object], text: str, highlights
    ) -> Mapping[str, object]:
        content_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # Carry only the original discovery allowlist forward; drop everything
        # else the input may have carried (raw html, cursors, secrets...).
        enriched = {key: candidate[key] for key in _DISCOVERY_KEYS if key in candidate}
        enriched["content"] = text
        enriched["content_sha256"] = content_sha256
        enriched["snapshot"] = {
            "content": text,
            "content_sha256": content_sha256,
            "mode": "full",
        }
        enriched["quote_candidates"] = self._quote_candidates(text, highlights)
        return enriched

    @staticmethod
    def _quote_candidates(text: str, highlights) -> tuple:
        # Only non-empty string highlights that are *exact* substrings of the
        # fetched text are promoted — using the first deterministic offset,
        # deduplicated, upstream order preserved. A snippet / non-exact
        # highlight is never upgraded into a quote candidate.
        candidates: list = []
        seen: set = set()
        for highlight in highlights:
            if not isinstance(highlight, str) or not highlight or highlight in seen:
                continue
            start = text.find(highlight)
            if start < 0:
                continue
            seen.add(highlight)
            candidates.append(
                {
                    "quote_text": highlight,
                    "start": start,
                    "end": start + len(highlight),
                }
            )
        return tuple(candidates)


__all__ = ["SyncToolDispatcher", "HermesWRRToolExecutor"]
