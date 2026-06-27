#!/usr/bin/env python3
"""
Deduplicate and rank multi-engine search results with URL normalization + RRF.

Input: JSON array or object containing result items. Accepted shapes:
  [ {"url": "...", "title": "...", "snippet": "...", "provider": "exa", "rank": 1}, ... ]
  {"results": [...]}
  {"exa": [...], "brave": [...], "tavily": [...]}

Output: JSON object with:
  - results: merged ranked results
  - provider_counts
  - duplicate_count
  - gaps

Usage:
  python scripts/dedup_rrf.py results.json
  cat results.json | python scripts/dedup_rrf.py
  # Weighted RRF: per-provider or per-source_tier weights (see source-map-schema.md SOURCE_QUALITY)
  python scripts/dedup_rrf.py results.json --weights exa=1.0,brave=0.9,social=0.5
  python scripts/dedup_rrf.py results.json --weights '{"exa":1.0,"social":0.5,"*":0.7}'
  # Per-item override: add a numeric "weight" field to any input item (per-subquery weighting).
  # No --weights and no "weight" fields → unweighted RRF, byte-identical to the legacy path.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {
    "fbclid", "gclid", "dclid", "mc_cid", "mc_eid", "igshid", "ref", "ref_src",
    "spm", "campaign", "source", "feature", "si"
}
DEFAULT_K = 60
DEFAULT_WEIGHT = 1.0


def parse_weights(spec: str | None) -> dict[str, float]:
    """Parse a weight spec into a {key: weight} map.

    Accepts either JSON (`{"exa":1.0,"social":0.5}`) or a compact
    comma list (`exa=1.0,brave=0.9,social=0.5`). Keys are matched
    case-insensitively against each item's provider, then its
    source_tier (so the source-map-schema SOURCE_QUALITY table —
    keyed by source_tier — can be passed verbatim). Key `*` sets a
    default for everything else.
    """
    if not spec:
        return {}
    spec = spec.strip()
    if spec.startswith("{"):
        raw = json.loads(spec)
        return {str(k).lower().strip(): float(v) for k, v in raw.items()}
    weights: dict[str, float] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"bad --weights entry (need key=value): {pair!r}")
        key, value = pair.split("=", 1)
        weights[key.lower().strip()] = float(value.strip())
    return weights


def resolve_weight(item: dict[str, Any], provider: str, weights: dict[str, float]) -> float:
    """Pick the weight for one item.

    Precedence: explicit item-level `weight` field (per-subquery) >
    weights[provider] > weights[source_tier] > weights['*'] > 1.0.
    Backward-compatible: empty weights + no `weight` field → 1.0,
    so RRF scoring is byte-identical to the unweighted path.
    """
    if "weight" in item:
        try:
            return float(item["weight"])
        except (TypeError, ValueError):
            pass
    if not weights:
        return DEFAULT_WEIGHT
    if provider in weights:
        return weights[provider]
    tier = str(item.get("source_tier") or "").lower().strip()
    if tier and tier in weights:
        return weights[tier]
    return weights.get("*", DEFAULT_WEIGHT)


def normalize_url(url: str) -> str:
    """Normalize URLs enough for source dedup without destroying semantics."""
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/+$", "", parts.path or "/")
    if path == "/":
        path = ""
    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lk = key.lower()
        if lk in TRACKING_KEYS or any(lk.startswith(prefix) for prefix in TRACKING_PREFIXES):
            continue
        query_pairs.append((key, value))
    query = urlencode(sorted(query_pairs), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def canonical_provider(item: dict[str, Any], fallback: str = "unknown") -> str:
    provider = item.get("provider") or item.get("engine") or item.get("source") or fallback
    return str(provider).lower().strip() or "unknown"


def extract_items(payload: Any) -> list[dict[str, Any]]:
    """Flatten common search output shapes into result dicts."""
    items: list[dict[str, Any]] = []

    def add(item: Any, provider_hint: str = "unknown", rank_hint: int | None = None) -> None:
        if not isinstance(item, dict):
            return
        url = item.get("url") or item.get("link") or item.get("href")
        if not url:
            return
        out = dict(item)
        out["url"] = url
        out.setdefault("provider", canonical_provider(item, provider_hint))
        if rank_hint is not None:
            out.setdefault("rank", rank_hint)
        items.append(out)

    if isinstance(payload, list):
        for idx, item in enumerate(payload, 1):
            add(item, rank_hint=idx)
    elif isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            for idx, item in enumerate(payload["results"], 1):
                add(item, rank_hint=idx)
        elif isinstance(payload.get("content"), list):
            for idx, item in enumerate(payload["content"], 1):
                add(item, rank_hint=idx)
        else:
            for key, value in payload.items():
                if isinstance(value, list):
                    for idx, item in enumerate(value, 1):
                        add(item, provider_hint=key, rank_hint=idx)
    return items


@dataclass
class MergedResult:
    normalized_url: str
    url: str
    title: str = ""
    snippet: str = ""
    rrf_score: float = 0.0
    providers: set[str] = field(default_factory=set)
    source_ranks: dict[str, int] = field(default_factory=dict)
    duplicates: list[dict[str, Any]] = field(default_factory=list)


def merge_rrf(items: list[dict[str, Any]], k: int = DEFAULT_K,
              weights: dict[str, float] | None = None) -> dict[str, Any]:
    weights = weights or {}
    groups: dict[str, MergedResult] = {}
    provider_seen_rank: dict[str, int] = defaultdict(int)
    provider_counts = Counter()

    for item in items:
        provider = canonical_provider(item)
        provider_counts[provider] += 1
        provider_seen_rank[provider] += 1
        rank = int(item.get("rank") or provider_seen_rank[provider])
        norm = normalize_url(str(item.get("url", "")))
        if not norm:
            continue
        score = resolve_weight(item, provider, weights) / (k + rank)
        if norm not in groups:
            groups[norm] = MergedResult(
                normalized_url=norm,
                url=str(item.get("url")),
                title=str(item.get("title") or item.get("name") or ""),
                snippet=str(item.get("snippet") or item.get("description") or item.get("highlights") or ""),
            )
        group = groups[norm]
        group.rrf_score += score
        group.providers.add(provider)
        group.source_ranks[provider] = min(rank, group.source_ranks.get(provider, 10**9))
        group.duplicates.append({
            "provider": provider,
            "rank": rank,
            "url": item.get("url"),
            "title": item.get("title") or item.get("name"),
        })
        if not group.title and (item.get("title") or item.get("name")):
            group.title = str(item.get("title") or item.get("name"))
        if not group.snippet and (item.get("snippet") or item.get("description")):
            group.snippet = str(item.get("snippet") or item.get("description"))

    merged = sorted(groups.values(), key=lambda r: (r.rrf_score, len(r.providers)), reverse=True)
    duplicate_count = len(items) - len(groups)
    provider_set = set(provider_counts)
    gaps = []
    if len(provider_set) <= 1:
        gaps.append("Only one provider present; RRF is acting as dedup/rank normalization, not cross-engine consensus.")
    if duplicate_count == 0 and len(provider_set) > 1:
        gaps.append("No cross-provider URL overlap; inspect source quality manually before treating results as confirmed.")

    out = {
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "normalized_url": r.normalized_url,
                "snippet": r.snippet,
                "rrf_score": round(r.rrf_score, 6),
                "providers": sorted(r.providers),
                "source_ranks": dict(sorted(r.source_ranks.items())),
                "duplicates": r.duplicates,
            }
            for r in merged
        ],
        "provider_counts": dict(sorted(provider_counts.items())),
        "input_count": len(items),
        "unique_count": len(groups),
        "duplicate_count": duplicate_count,
        "gaps": gaps,
    }
    # Only surface weights when non-default → unweighted output stays byte-identical.
    if weights:
        out["weights_applied"] = dict(sorted(weights.items()))
    return out


def main() -> int:
    # Manual parse keeps the legacy positional-file / stdin contract intact
    # while adding an optional `--weights` flag (anywhere in argv).
    weights_spec: str | None = None
    positional: list[str] = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--weights":
            i += 1
            weights_spec = argv[i] if i < len(argv) else None
        elif arg.startswith("--weights="):
            weights_spec = arg.split("=", 1)[1]
        else:
            positional.append(arg)
        i += 1

    weights = parse_weights(weights_spec)

    src = positional[0] if positional and positional[0] not in {"-", "--"} else None
    raw = open(src, "r", encoding="utf-8").read() if src else sys.stdin.read()
    if not raw.strip():
        print(json.dumps({"results": [], "provider_counts": {}, "input_count": 0, "unique_count": 0, "duplicate_count": 0, "gaps": ["No input provided."]}, ensure_ascii=False, indent=2))
        return 0
    payload = json.loads(raw)
    items = extract_items(payload)
    print(json.dumps(merge_rrf(items, weights=weights), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
