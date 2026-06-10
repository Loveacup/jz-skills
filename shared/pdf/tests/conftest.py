"""Pytest configuration for the pdf skill tests.

Ensures the `scripts/` directory is importable regardless of pytest's CWD so
that `import md2pdf_chrome` and `from themes import ...` resolve, and registers
the `integration` marker.
"""

import sys
from pathlib import Path

# tests/ lives next to scripts/ under the skill root.
SCRIPTS_DIR = (Path(__file__).resolve().parent.parent / "scripts").resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that launch Chromium (slower)",
    )
