"""pytest 引导：把连字符文件名 mac-doctor-triage.py 注册为可 import 的 mac_doctor_triage。

cron 入口须保持连字符命名（与 Cron 注册表一致），但 Python import 不支持连字符，
故用 importlib 在测试期把它加载进 sys.modules。
"""
import importlib.util
import sys
from pathlib import Path

_TRIAGE_PATH = Path(__file__).parent / "mac-doctor-triage.py"
if _TRIAGE_PATH.exists() and "mac_doctor_triage" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("mac_doctor_triage", _TRIAGE_PATH)
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["mac_doctor_triage"] = _module
    _spec.loader.exec_module(_module)
