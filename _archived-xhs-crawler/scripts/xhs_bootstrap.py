"""XHS-Downloader bootstrap —— 幂等地把 3.12 后端备好。

把 JoeanAmier/XHS-Downloader clone 到 skill 本地的 gitignored 目录 `.xhs-downloader/`，
并用 uv 同步出一个 Python 3.12 的 `.venv`（含全部依赖）。skill 胶水层（3.9）调用
xhs_backend → runner 时就用这个 venv 的解释器。

设计：
- 纯命令构造（clone_command / sync_command）与状态检查（doctor）可单元测试，不联网。
- ensure() 是幂等副作用入口：缺则补，已就绪则跳过。
- 目标 Python 3.9（Hermes 部署默认）→ from __future__ import annotations。

CLI:
    python xhs_bootstrap.py          # ensure（幂等准备）
    python xhs_bootstrap.py doctor   # 打印就绪状态
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

REPO_URL = "https://github.com/JoeanAmier/XHS-Downloader.git"

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.dirname(_SCRIPTS_DIR)
XHS_DL_DIR = os.path.join(_SKILL_DIR, ".xhs-downloader")


def clone_command(dest: str = XHS_DL_DIR, repo: str = REPO_URL) -> list:
    return ["git", "clone", "--depth", "1", repo, dest]


def sync_command(uv_bin: str = "uv") -> list:
    # 仓库 .python-version 固定 3.12；uv sync 会据此取/建解释器
    return [uv_bin, "sync", "--no-dev"]


def venv_python(dl_dir: str = XHS_DL_DIR) -> str:
    return os.path.join(dl_dir, ".venv", "bin", "python")


def doctor(dl_dir: str = XHS_DL_DIR) -> dict:
    """返回就绪状态（纯检查，不联网、无副作用）。"""
    vpy = venv_python(dl_dir)
    clone_exists = os.path.isdir(os.path.join(dl_dir, "source"))
    venv_exists = os.path.isfile(vpy)
    return {
        "dl_dir": dl_dir,
        "clone_exists": clone_exists,
        "venv_exists": venv_exists,
        "venv_python": vpy,
        "ready": clone_exists and venv_exists,
    }


def _run(cmd: list, cwd: str = None) -> None:
    print("▶ %s" % " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure(dl_dir: str = XHS_DL_DIR) -> dict:
    """幂等准备后端；返回最终 doctor 状态。"""
    status = doctor(dl_dir)
    if status["ready"]:
        print("✅ XHS-Downloader 后端已就绪：%s" % status["venv_python"])
        return status

    if not status["clone_exists"]:
        print("📥 clone XHS-Downloader → %s" % dl_dir)
        _run(clone_command(dl_dir))

    print("📦 uv sync（Python 3.12 + 依赖）...")
    _run(sync_command(), cwd=dl_dir)

    status = doctor(dl_dir)
    if not status["ready"]:
        raise RuntimeError(
            "bootstrap 失败：venv 未生成，检查 uv 是否安装（brew install uv）"
        )
    print("✅ 完成：%s" % status["venv_python"])
    return status


def main(argv: list) -> int:
    if len(argv) > 1 and argv[1] == "doctor":
        print(json.dumps(doctor(), ensure_ascii=False, indent=2))
        return 0 if doctor()["ready"] else 1
    try:
        ensure()
        return 0
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print("❌ %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
