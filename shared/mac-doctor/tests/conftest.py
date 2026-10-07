"""把无扩展名、带连字符的可执行 `scripts/mac-doctor` 作为模块 `mac_doctor` 载入。"""
import importlib.util
import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))
_PATH = _SKILL_ROOT / "scripts" / "mac-doctor"
_loader = SourceFileLoader("mac_doctor", str(_PATH))
_spec = importlib.util.spec_from_loader("mac_doctor", _loader)
mac_doctor = importlib.util.module_from_spec(_spec)
sys.modules["mac_doctor"] = mac_doctor
_loader.exec_module(mac_doctor)  # __name__ == "mac_doctor" → 不触发 __main__


import pytest


@pytest.fixture(autouse=True)
def _no_real_typesafe_key(monkeypatch, tmp_path_factory):
    """Never let tests read the user's real TypeSafe key file or env."""
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    missing = tmp_path_factory.mktemp("typesafe") / "absent-key"
    monkeypatch.setenv("TYPESAFE_API_KEY_FILE", os.fspath(missing))
