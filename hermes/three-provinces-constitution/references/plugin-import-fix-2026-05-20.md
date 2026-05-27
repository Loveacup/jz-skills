# Hermes Plugin Import Safety Pattern

**Date**: 2026-05-20
**Trigger**: kanban-gate plugin crashed regent gateway with `ModuleNotFoundError: No module named 'kanban_gate'`

## Root Cause

Hermes loads profile plugins via `exec()` or dynamic module loading. In neither case is `__package__` set, so relative imports (`from .gate_core import ...`) fail. Error surfaces at gateway startup, not install time.

## Fix Pattern

```python
import importlib.util, os, sys
from pathlib import Path

try:
    _DIR = Path(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    _DIR = Path(os.getcwd())

_spec = importlib.util.spec_from_file_location("mod", _DIR / "module.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["mod"] = _mod
_spec.loader.exec_module(_mod)
func = _mod.func
```

`try/except NameError` handles `exec()` mode where `__file__` is undefined.

## Verification

```bash
python3 -c "exec(open('__init__.py').read()); print('OK')"
```
