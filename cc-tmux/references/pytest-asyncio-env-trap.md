# pytest-asyncio 环境陷阱

> 2026-06-28 实发：WRR GitHub 引擎集成测试。`pytest` 命令调用的是系统 Python 3.9 的 pytest，而项目 venv 是 Python 3.11，导致 `pytest-asyncio` 插件在系统环境中未安装，async 测试全部失败。

## 症状

```
async def functions are not natively supported.
You need to install a suitable plugin for your framework, for example:
  - pytest-asyncio
  - pytest-tornasync
  - pytest-trio
  - pytest-twisted
```

但 `pip install pytest-asyncio` 报错 PEP 668（系统包保护），venv 的 pip 安装后仍无效。

## 根因

- `pytest` 命令解析到 `/Library/Python/3.9/bin/pytest`（系统 Python）
- 项目 venv 在 `~/.hermes/hermes-agent/venv/bin/python3`（Python 3.11）
- 两者环境隔离，系统 pytest 看不到 venv 的 `pytest-asyncio`

## 诊断

```bash
# 检查 pytest 实际路径
which pytest
# → /Library/Python/3.9/bin/pytest

# 检查项目 Python
python3 -c "import sys; print(sys.executable)"
# → /Users/alexcai/.hermes/hermes-agent/venv/bin/python3

# 检查 pytest 版本（系统 vs venv）
pytest --version          # 系统
python3 -m pytest --version  # venv（通过 python3 -m 调用）
```

## 修复

**正确做法**：用 venv 的 Python 调用 pytest

```bash
# 方法 1：python3 -m pytest（推荐）
cd ~/.hermes/plugins/wrr-hermes
python3 -m pytest tests/ -v

# 方法 2：绝对路径
~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -v

# 方法 3：激活 venv（如果已激活）
source ~/.hermes/hermes-agent/venv/bin/activate
pytest tests/ -v
```

**错误做法**：
- ❌ `pip install pytest-asyncio`（系统 pip，装到错误环境）
- ❌ `pytest tests/`（调用系统 pytest，看不到 venv 插件）

## 预防

1. **项目目录下优先用 `python3 -m pytest`**，不直接用 `pytest`
2. **CI/脚本中显式指定 Python 路径**：`python3 -m pytest` 而非 `pytest`
3. **检查 pytest 插件是否安装**：`python3 -m pytest --version` 应显示插件列表

## 相关 Pitfall

- cc-tmux Pitfall #35：CC 自报 "8/8 passed" 但产物不可信——CC 可能用系统 pytest 跑过，未验证真实环境
