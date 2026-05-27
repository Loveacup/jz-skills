"""Theme loader for md2pdf converters.

Auto-discovers CSS theme files from the themes/ directory.
Each .css file contains TOML-style metadata in a block comment header.
"""

import re
from pathlib import Path
from dataclasses import dataclass

THEMES_DIR = Path(__file__).parent

# Cache: theme name -> Theme object
_cache: dict[str, "Theme"] = {}


@dataclass(frozen=True)
class Theme:
    name: str
    description: str
    css: str
    hljs_theme: str


def _parse_theme(css_path: Path) -> Theme:
    """Parse a theme CSS file with TOML-style metadata header."""
    text = css_path.read_text(encoding="utf-8")

    # Extract metadata from /* [theme] ... */ block
    meta_match = re.search(
        r"/\*\s*\[theme\]\s*\n(.*?)\*/", text, re.DOTALL
    )
    meta = {}
    if meta_match:
        for line in meta_match.group(1).strip().splitlines():
            line = line.strip()
            if "=" in line:
                key, _, val = line.partition("=")
                meta[key.strip()] = val.strip()

    # CSS is everything after the metadata block comment
    css = ""
    if meta_match:
        css = text[meta_match.end():].strip()
    else:
        css = text.strip()

    return Theme(
        name=meta.get("name", css_path.stem),
        description=meta.get("description", ""),
        css=css,
        hljs_theme=meta.get("hljs_theme", "atom-one-dark"),
    )


def load_theme(name: str) -> Theme:
    """Load a theme by name. Raises ValueError if not found."""
    if name in _cache:
        return _cache[name]

    css_path = THEMES_DIR / f"{name}.css"
    if not css_path.exists():
        available = ", ".join(list_themes())
        raise ValueError(f"Unknown theme '{name}'. Available: {available}")

    theme = _parse_theme(css_path)
    _cache[name] = theme
    return theme


def list_themes() -> list[str]:
    """Return sorted list of available theme names."""
    return sorted(p.stem for p in THEMES_DIR.glob("*.css"))
