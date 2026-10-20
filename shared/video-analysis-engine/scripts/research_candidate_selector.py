"""S9-4 plan-global research candidate selector (standalone, pure).

This module owns a single decision: given a *plan snapshot* — an ordered list of
research queries, each carrying discovery candidates plus a plan-global source /
fetch budget — decide which unique source URLs to fetch and prove that every
required (P0/P1) claim binding is covered.

It is deliberately hermetic:

* No transport / adapter / WRR / Hermes import. It never performs I/O. Every
  answer is a deterministic function of ``input_mapping`` alone.
* URL canonicalization is a pure, self-contained reimplementation of the same
  safe normalization the research contract applies (lower-case host, drop
  default ports, strip tracking params, reject credentials / signed tokens).
  A candidate whose URL is empty or unsafe is simply unselectable.

The only public entry point is :func:`select_plan_candidates`.

Vocabulary
----------
binding
    A unit of required coverage. Each P0/P1 query contributes one binding per
    ``claim_uid``; a P0/P1 query with no claim contributes the single synthetic
    binding ``"<query_uid>:<none>"``. P2 queries contribute no required binding.
unique URL slot
    Candidates that canonicalize to the same URL collapse into one slot. The
    slot keeps *all* contributor candidates and their query/claim/binding
    provenance, but counts once against ``max_sources`` / ``max_fetches``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

__all__ = ["select_plan_candidates"]

# Reason codes are a closed, public vocabulary — callers switch on these.
REASON_MISSING_REQUIRED_CANDIDATE = "MISSING_REQUIRED_CANDIDATE"
REASON_MAX_SOURCES_INSUFFICIENT = "MAX_SOURCES_INSUFFICIENT"
REASON_MAX_FETCHES_INSUFFICIENT = "MAX_FETCHES_INSUFFICIENT"

_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}
_REQUIRED_PRIORITIES = frozenset({"P0", "P1"})
_NONE_CLAIM = "<none>"

# Query-parameter markers that indicate a credential / signed token; a URL that
# carries any of these is treated as unsafe and therefore unselectable.
_SIGNED_MARKERS = (
    "token", "signature", "credential", "authorization", "apikey", "api_key",
    "signed", "x_amz_", "x_goog_", "sig", "session", "cookie", "password",
    "secret",
)
# Tracking parameters that carry no identity and are dropped during canonicalization.
_TRACKING_KEYS = frozenset({"fbclid", "gclid", "ref", "ref_src"})


def _canonical_url(candidate: Mapping) -> Optional[str]:
    """Return the safe canonical URL for a candidate, or ``None`` if unselectable.

    ``canonical_url`` wins over ``url`` when present; an empty/whitespace value on
    the preferred field falls through to the other. The normalization mirrors the
    research contract's public-URL rules so selection stays consistent with the
    downstream source identity model.
    """
    raw = candidate.get("canonical_url")
    if raw is None or not str(raw).strip():
        raw = candidate.get("url")
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = urlsplit(text)
        _ = parsed.port  # forces a ValueError on a malformed port
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    port = parsed.port
    default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    host = parsed.hostname.lower()
    netloc = host if port is None or default_port else f"{host}:{port}"
    query = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower().replace("-", "_")
        if any(marker in lowered for marker in _SIGNED_MARKERS):
            return None
        if lowered.startswith("utm_") or lowered in _TRACKING_KEYS:
            continue
        query.append((key, val))
    query.sort()
    return urlunsplit((scheme, netloc, parsed.path or "/", urlencode(query), ""))


def _as_sequence(value) -> tuple:
    if isinstance(value, (str, bytes)) or isinstance(value, Mapping):
        return ()
    if isinstance(value, Sequence):
        return tuple(value)
    return ()


class _CandidateRecord:
    """One valid (selectable) candidate, tagged with its stable sort key."""

    __slots__ = ("uid", "url", "query_uid", "stable_key", "raw")

    def __init__(self, uid, url, query_uid, stable_key, raw):
        self.uid = uid
        self.url = url
        self.query_uid = query_uid
        self.stable_key = stable_key
        self.raw = raw


def select_plan_candidates(input_mapping: Mapping) -> dict:
    """Select plan-global unique source URLs and prove required coverage.

    See the module docstring for the full contract. The return value is a plain
    ``dict`` with keys ``selected_raw_candidates``, ``selected_urls``,
    ``diagnostics`` and ``feasible``. The input is never mutated and repeated
    calls are deep-equal.
    """
    if not isinstance(input_mapping, Mapping):
        raise TypeError("input_mapping must be a mapping")

    queries = _as_sequence(input_mapping.get("queries"))
    max_sources = int(input_mapping.get("max_sources") or 0)
    max_fetches = int(input_mapping.get("max_fetches") or 0)

    # --- Pass 0: flatten queries into valid candidate records + bindings ----- #
    records: list[_CandidateRecord] = []
    # ordered required bindings: (binding_id, query_uid, claim_uid_or_None)
    required_bindings: list[tuple[str, str, Optional[str]]] = []
    # per-query first valid candidate (lowest stable key) — every binding of a
    # query is covered by that query's first selectable candidate.
    query_first: dict[str, _CandidateRecord] = {}

    order = 0
    for query in queries:
        if not isinstance(query, Mapping):
            continue
        query_uid = query.get("query_uid")
        priority = query.get("priority")
        priority_rank = _PRIORITY_RANK.get(priority, 3)
        try:
            plan_index = int(query.get("plan_index") or 0)
        except (TypeError, ValueError):
            plan_index = 0
        claim_uids = _as_sequence(query.get("claim_uids"))

        if priority in _REQUIRED_PRIORITIES:
            if claim_uids:
                for claim_uid in claim_uids:
                    required_bindings.append(
                        (f"{query_uid}:{claim_uid}", query_uid, claim_uid)
                    )
            else:
                required_bindings.append(
                    (f"{query_uid}:{_NONE_CLAIM}", query_uid, None)
                )

        for candidate in _as_sequence(query.get("candidates")):
            if not isinstance(candidate, Mapping):
                order += 1
                continue
            url = _canonical_url(candidate)
            try:
                discovery_rank = int(candidate.get("discovery_rank") or 0)
            except (TypeError, ValueError):
                discovery_rank = 0
            candidate_uid = candidate.get("candidate_uid")
            stable_key = (
                priority_rank,
                plan_index,
                discovery_rank,
                str(candidate_uid),
                order,
            )
            order += 1
            if url is None:
                continue
            record = _CandidateRecord(candidate_uid, url, query_uid, stable_key, candidate)
            records.append(record)
            prior = query_first.get(query_uid)
            if prior is None or stable_key < prior.stable_key:
                query_first[query_uid] = record

    # --- URL groups: canonical_url -> stable-sorted contributor records ------ #
    groups: dict[str, list[_CandidateRecord]] = {}
    for record in records:
        groups.setdefault(record.url, []).append(record)
    for url in groups:
        groups[url].sort(key=lambda r: r.stable_key)

    # --- Pass 1: cover every required binding with its query's first URL ----- #
    # url -> ordered, de-duplicated list of covered binding rows
    required_url_bindings: dict[str, list[tuple[str, str, Optional[str]]]] = {}
    uncovered_binding_ids: list[str] = []
    covered_binding_count = 0
    for binding_id, query_uid, claim_uid in required_bindings:
        first = query_first.get(query_uid)
        if first is None:
            uncovered_binding_ids.append(binding_id)
            continue
        covered_binding_count += 1
        required_url_bindings.setdefault(first.url, []).append(
            (binding_id, query_uid, claim_uid)
        )

    required_urls = list(required_url_bindings)
    required_unique_count = len(required_urls)

    # --- Feasibility ---------------------------------------------------------- #
    reasons: list[str] = []
    if uncovered_binding_ids:
        reasons.append(REASON_MISSING_REQUIRED_CANDIDATE)
    if required_unique_count > max_sources:
        reasons.append(REASON_MAX_SOURCES_INSUFFICIENT)
    if required_unique_count > max_fetches:
        reasons.append(REASON_MAX_FETCHES_INSUFFICIENT)
    feasible = not reasons

    # --- Build the selected URL order ---------------------------------------- #
    # Required URLs are never dropped for budget (diagnostic honesty). They are
    # emitted in stable representative order.
    selected_urls_ordered = sorted(required_urls, key=lambda u: groups[u][0].stable_key)

    # Pass 2: iff required first-pass unique count fits max_sources, top up with
    # the remaining unique URLs in stable order, bounded by BOTH budgets so we
    # never schedule more fetches than allowed.
    if required_unique_count <= max_sources:
        cap = min(max_sources, max_fetches)
        remaining = sorted(
            (u for u in groups if u not in required_url_bindings),
            key=lambda u: groups[u][0].stable_key,
        )
        for url in remaining:
            if len(selected_urls_ordered) >= cap:
                break
            selected_urls_ordered.append(url)

    # --- Materialize selected_urls + selected_raw_candidates ------------------ #
    selected_urls: list[dict] = []
    selected_raw_candidates: list[dict] = []
    for url in selected_urls_ordered:
        contributors = groups[url]
        binding_rows = required_url_bindings.get(url, [])
        binding_ids = [row[0] for row in binding_rows]
        claim_uids = sorted(
            {row[2] for row in binding_rows if row[2] is not None}
        )
        query_uids = sorted({r.query_uid for r in contributors})
        representative = contributors[0]
        selected_urls.append(
            {
                "canonical_url": url,
                "representative_candidate_uid": representative.uid,
                "contributor_candidate_uids": [r.uid for r in contributors],
                "binding_ids": binding_ids,
                "query_uids": query_uids,
                "claim_uids": claim_uids,
            }
        )
        raw_copy = dict(representative.raw)  # shallow copy; input stays pristine
        raw_copy["matched_binding_ids"] = binding_ids
        selected_raw_candidates.append(raw_copy)

    diagnostics = {
        "required_p01_binding_count": len(required_bindings),
        "covered_p01_binding_count": covered_binding_count,
        "required_p01_unique_url_count": required_unique_count,
        "selected_unique_url_count": len(selected_urls),
        "max_sources": max_sources,
        "max_fetches": max_fetches,
        "uncovered_binding_ids": uncovered_binding_ids,
        "reasons": reasons,
    }

    return {
        "selected_raw_candidates": selected_raw_candidates,
        "selected_urls": selected_urls,
        "diagnostics": diagnostics,
        "feasible": feasible,
    }
