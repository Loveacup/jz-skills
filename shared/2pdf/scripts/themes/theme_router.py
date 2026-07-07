"""Content-aware palette/theme router for md2pdf_chrome.py.

The router inspects the Markdown source and picks one of the built-in palettes
or legacy themes. It is deterministic, dependency-free, and unit-testable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

BUILTIN_PALETTES = [
    "blue",
    "sepia",
    "nord",
    "gruvbox-dark",
    "gruvbox-light",
    "solarized-light",
    "solarized-dark",
    "dracula",
]

TECH_WORDS = {
    "python", "javascript", "rust", "go", "golang", "api", "database", "docker",
    "kubernetes", "k8s", "server", "cloud", "aws", "cli", "git", "github",
    "code", "programming", "developer", "software", "algorithm", "function",
    "class", "module", "ml", "ai", "data", "prompt", "llm", "model",
}

ACADEMIC_WORDS = {
    "paper", "research", "study", "abstract", "introduction", "methodology",
    "conclusion", "references", "university", "professor", "thesis", "journal",
    "academic", "hypothesis", "experiment", "survey", "theory",
}

BUSINESS_WORDS = {
    "quarter", "revenue", "profit", "market", "strategy", "stakeholder",
    "customer", "product", "okr", "kpi", "meeting", "proposal", "deck",
    "company", "business", "sales", "marketing", "roi", "growth",
}

CREATIVE_WORDS = {
    "design", "portfolio", "art", "illustration", "photography", "story",
    "novel", "poem", "music", "film", "creative", "brand", "ux", "ui",
}

LIFESTYLE_WORDS = {
    "recipe", "travel", "fitness", "health", "meditation", "daily", "habit",
    "journal", "review", "life", "family", "food", "coffee", "tea",
}

NIGHT_WORDS = {"night", "dark", "crypto", "terminal", "cli", "ops", "hack"}
WARM_WORDS = {"warm", "paper", "journal", "reading", "book", "history"}
COLD_WORDS = {"cold", "ice", "arctic", "nordic", "minimal", "scandinavian"}
RETRO_WORDS = {"retro", "vintage", "gaming", "terminal"}


def _extract_frontmatter(md_text: str) -> tuple[str, dict[str, Any]]:
    """Return (body_without_frontmatter, frontmatter_dict)."""
    if not md_text.startswith("---"):
        return md_text, {}
    try:
        end = md_text.find("\n---", 3)
        if end == -1:
            return md_text, {}
        fm_block = md_text[3:end].strip()
        body = md_text[end + 4:].strip()
        fm: dict[str, Any] = {}
        for line in fm_block.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
        return body, fm
    except Exception:
        return md_text, {}


def _domain_guess(text: str) -> str | None:
    text_lower = text.lower()
    counts = {
        "tech": sum(1 for w in TECH_WORDS if w in text_lower),
        "academic": sum(1 for w in ACADEMIC_WORDS if w in text_lower),
        "business": sum(1 for w in BUSINESS_WORDS if w in text_lower),
        "creative": sum(1 for w in CREATIVE_WORDS if w in text_lower),
        "lifestyle": sum(1 for w in LIFESTYLE_WORDS if w in text_lower),
    }
    best = max(counts, key=counts.get)
    return best if counts[best] > 2 else None


def _code_ratio(text: str) -> float:
    fence_chars = 0
    for match in re.findall(r"```[\s\S]*?```", text):
        fence_chars += len(match)
    inline_chars = len(re.findall(r"`[^`]+`", text)) * 8
    total = max(len(text), 1)
    return (fence_chars + inline_chars) / total


def _has_mermaid(text: str) -> bool:
    return "```mermaid" in text.lower()


def _has_math(text: str) -> bool:
    return bool(re.search(r"(?<!\\)\$\$[\s\S]*?\$\$", text)) or bool(
        re.search(r"(?<!\\)\$[^$\s][^$]*?[^\\\s$]\$", text)
    )


def _emoji_counts(text: str) -> dict[str, int]:
    # Simple Unicode emoji regex (covers most common emojis)
    emojis = re.findall(
        r"[\U0001F300-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]", text
    )
    counts: dict[str, int] = {}
    for e in emojis:
        counts[e] = counts.get(e, 0) + 1
    return counts


def _hour_bucket(hour: int | None) -> str | None:
    if hour is None:
        return None
    if 0 <= hour <= 5:
        return "night"
    if 6 <= hour <= 17:
        return "day"
    return "evening"


def _contains_any(text: str, words: set[str]) -> bool:
    text_lower = text.lower()
    return any(w in text_lower for w in words)


def route(md_text: str, page_size: str = "A4", hour: int | None = None) -> str:
    """Pick a palette/theme name for the given Markdown text.

    Returns a legacy theme name if explicitly requested in frontmatter, otherwise
    one of the built-in palettes.
    """
    body, fm = _extract_frontmatter(md_text)
    text = body.lower()

    # Explicit frontmatter theme hint wins immediately (legacy or palette).
    fm_theme = fm.get("theme")
    if fm_theme and isinstance(fm_theme, str):
        return fm_theme.strip()

    word_count = len(text.split())
    code_ratio = _code_ratio(md_text)
    domain = _domain_guess(text)
    has_mermaid = _has_mermaid(md_text)
    has_math = _has_math(md_text)
    emojis = _emoji_counts(md_text)
    bucket = _hour_bucket(hour)
    is_mobile = page_size != "A4"

    # Base scores; default blue gets a small head start.
    scores: dict[str, int] = {p: 0 for p in BUILTIN_PALETTES}
    scores["blue"] += 10

    # Domain signals
    if domain == "tech":
        scores["nord"] += 15
        scores["gruvbox-dark"] += 10
        scores["solarized-dark"] += 10
        scores["dracula"] += 10
        scores["solarized-light"] += 10
    elif domain == "academic":
        scores["sepia"] += 15
        scores["solarized-light"] += 10
        scores["blue"] += 5
    elif domain == "creative":
        scores["gruvbox-light"] += 10
        scores["sepia"] += 10
        scores["blue"] += 5
    elif domain == "business":
        scores["blue"] += 10
        scores["solarized-light"] += 5

    # Code-heavy
    if code_ratio > 0.15:
        scores["gruvbox-dark"] += 20
        scores["nord"] += 15
        scores["solarized-dark"] += 20
        scores["dracula"] += 10
        scores["gruvbox-light"] += 10
        scores["solarized-light"] += 10

    if has_mermaid or has_math:
        scores["nord"] += 10
        scores["gruvbox-dark"] += 10
        scores["solarized-dark"] += 10

    # Length
    if word_count > 2500:
        scores["sepia"] += 10
        scores["solarized-light"] += 5
    elif word_count < 600:
        scores["dracula"] += 10
        scores["nord"] += 5
        scores["gruvbox-dark"] += 5

    # Keyword vibes
    if _contains_any(text, NIGHT_WORDS):
        scores["gruvbox-dark"] += 30
        scores["solarized-dark"] += 30
        scores["dracula"] += 30
    if _contains_any(text, WARM_WORDS):
        scores["sepia"] += 30
        scores["gruvbox-light"] += 15
    if _contains_any(text, COLD_WORDS):
        scores["nord"] += 30
    if _contains_any(text, RETRO_WORDS):
        scores["gruvbox-dark"] += 30
        scores["gruvbox-light"] += 30

    # Emoji
    energy_emojis = {"🔥", "⚡", "🚀", "💥", "💡"}
    calm_emojis = {"📚", "☕", "🍵", "🌿"}
    if any(emojis.get(e, 0) for e in energy_emojis):
        scores["dracula"] += 5
        scores["gruvbox-dark"] += 5
    if any(emojis.get(e, 0) for e in calm_emojis):
        scores["sepia"] += 10

    # Time of day
    if bucket == "night":
        scores["gruvbox-dark"] += 15
        scores["solarized-dark"] += 15
        scores["dracula"] += 15
    elif bucket == "day":
        scores["blue"] += 10
        scores["sepia"] += 10
        scores["solarized-light"] += 10
        scores["gruvbox-light"] += 10
    elif bucket == "evening":
        scores["gruvbox-dark"] += 10
        scores["solarized-dark"] += 10

    # Mobile tie-breaker toward higher contrast dark palettes
    if is_mobile:
        if max(scores, key=scores.get) in {"gruvbox-dark", "solarized-dark", "dracula"}:
            scores["gruvbox-dark"] += 5
            scores["solarized-dark"] += 5
            scores["dracula"] += 5

    # Fallback tie-breaker order (blue first, then calm, then dark).
    tie_order = [
        "blue", "nord", "sepia", "solarized-light",
        "gruvbox-light", "gruvbox-dark", "solarized-dark", "dracula",
    ]
    best_score = max(scores.values())
    candidates = [p for p in scores if scores[p] == best_score]
    if len(candidates) == 1:
        return candidates[0]
    for p in tie_order:
        if p in candidates:
            return p
    return "blue"


def list_palettes() -> list[str]:
    return list(BUILTIN_PALETTES)


def is_palette(name: str) -> bool:
    return name in BUILTIN_PALETTES


def is_legacy_theme(name: str) -> bool:
    # Avoid importing to keep dependency-free; check filesystem directly.
    themes_dir = Path(__file__).parent
    return (themes_dir / f"{name}.css").exists()
