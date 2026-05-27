# Plugin Import Fix — 2026-05-20

## Problem

The `kanban-gate` plugin's `__init__.py` used a relative import:

```python
from .gate_core import kanban_gate_pre_tool_call, check_critical_tool_confirm
```

When Hermes loads plugins, it uses `exec()` or dynamic module loading without setting `__package__`. This causes:

```
ModuleNotFoundError: No module named 'kanban_gate'
```

The gateway crashes on startup, repeatedly restarting and eventually receiving SIGTERM from systemd/launchd.

## Root Cause

Hermes plugin loading mechanism does not establish a proper package context for relative imports. The `__file__` variable may also be undefined in some load paths (e.g., `exec(open('__init__.py').read())`).

## Fix

Replace relative import with `importlib.util` absolute path loading:

```python
import importlib.util
import os
import sys
from pathlib import Path

try:
    _PLUGIN_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # __file__ undefined when loaded via exec()
    _PLUGIN_DIR = Path(os.getcwd())

_GATE_CORE_PATH = _PLUGIN_DIR / "gate_core.py"

_spec = importlib.util.spec_from_file_location(
    "kanban_gate_gate_core", _GATE_CORE_PATH
)
_gate_core = importlib.util.module_from_spec(_spec)
sys.modules["kanban_gate_gate_core"] = _gate_core
_spec.loader.exec_module(_gate_core)

kanban_gate_pre_tool_call = _gate_core.kanban_gate_pre_tool_call
check_critical_tool_confirm = _gate_core.check_critical_tool_confirm
```

## Verification

Test both load paths:

```bash
# Simulate exec() loading
cd ~/.hermes/profiles/regent/plugins/kanban-gate
python3 -c "exec(open('__init__.py').read()); print('OK')"

# Simulate module import
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('kanban_gate', '__init__.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('OK')
"
```

## Prevention

All Hermes profile plugins that split logic across multiple files must use absolute path loading via `importlib.util`. Never use relative imports in plugin `__init__.py`.
