"""bootstrap 纯助手与状态检查（不联网、无副作用）。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from xhs_bootstrap import (  # noqa: E402
    REPO_URL,
    clone_command,
    doctor,
    sync_command,
    venv_python,
)


def test_clone_command_shape():
    cmd = clone_command("/tmp/xhs-dl")
    assert cmd[:4] == ["git", "clone", "--depth", "1"]
    assert REPO_URL in cmd
    assert cmd[-1] == "/tmp/xhs-dl"


def test_sync_command_shape():
    assert sync_command() == ["uv", "sync", "--no-dev"]


def test_venv_python_path():
    p = venv_python("/tmp/xhs-dl")
    assert p == os.path.join("/tmp/xhs-dl", ".venv", "bin", "python")


def test_doctor_on_missing_dir_not_ready(tmp_path):
    status = doctor(str(tmp_path))
    assert status["ready"] is False
    assert status["clone_exists"] is False
    assert status["venv_exists"] is False
