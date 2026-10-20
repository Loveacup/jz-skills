"""XHS-Downloader 后端胶水层（主力路径）。

职责：把规范化后的 URL 交给跑在独立 Python 3.12 venv 里的 runner 子进程，
解析其 JSON 输出，按六种情形分类，成功时经 xhs_adapter 产出报告输入契约。

设计要点：
- **子进程边界 = Python 版本隔离 + 测试 mock 缝**。单元测试注入 runner_fn 即可
  完全避开真实子进程/网络。
- **cookie 策略上提到本层**：runner 是哑的，build_command 永远显式带 cookie（默认 ""），
  这样「免登录传空字符串」成为本层可测契约（见 references/xhs-downloader-integration.md）。
- 目标 Python 3.9（Hermes 部署默认）→ from __future__ import annotations。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from parse_xhs_url import prepare_url
from xhs_adapter import adapt_to_report_input

# ---- 路径：bootstrap clone 与 runner（单元测试经 runner_fn 注入，不依赖这些）----
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.dirname(_SCRIPTS_DIR)
XHS_DL_DIR = os.path.join(_SKILL_DIR, ".xhs-downloader")
PYTHON_BIN = os.path.join(XHS_DL_DIR, ".venv", "bin", "python")
RUNNER_PATH = os.path.join(_SCRIPTS_DIR, "xhs_downloader_runner.py")

DEFAULT_TIMEOUT = 60

# IP 风控标记：任一出现即立即止损（见 SKILL.md Q7 / 错误码 300012）
_IP_RISK_MARKERS = ("300012", "ip at risk", "风控")


def build_command(
    url: str,
    *,
    cookie: str = "",
    python_bin: str = PYTHON_BIN,
    runner: str = RUNNER_PATH,
) -> list:
    """组装子进程 argv：[venv-python, runner, url, cookie]。

    cookie 永远作为独立 argv 元素传入，默认空字符串（免登录关键）。
    """
    return [python_bin, runner, url, cookie]


def _is_ip_risk(text: str) -> bool:
    low = (text or "").lower()
    return any(marker in low for marker in _IP_RISK_MARKERS)


def _parse_payload(stdout: str):
    """只认 stdout 的最后一行 JSON。

    XHS-Downloader 库会把进度信息打到 stdout，排在 runner 的 JSON 之前；
    runner 已重定向库的 stdout 到 stderr，这里再取末行 JSON 作为双保险。
    """
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except (ValueError, TypeError):
            return None
    return None


def classify(returncode: int, stdout: str, stderr: str) -> dict:
    """纯分类：子进程输出 → {status, data, message, stop_loss}。

    status ∈ {ok, failed, ip_risk, error}。timeout / invalid_url 在 fetch_note 处理。
    """
    combined = "%s\n%s" % (stdout or "", stderr or "")
    # IP 风控优先判断（通常伴随非零退出）→ 立即止损
    if _is_ip_risk(combined):
        return {
            "status": "ip_risk",
            "data": None,
            "message": "IP 风控（300012），立即止损，不要轮换方案",
            "stop_loss": True,
        }
    if returncode != 0:
        return {
            "status": "error",
            "data": None,
            "message": "runner 子进程异常退出: %s" % (stderr or "").strip()[:500],
            "stop_loss": False,
        }
    payload = _parse_payload(stdout)
    if payload is None:
        return {
            "status": "error",
            "data": None,
            "message": "runner 输出不是合法 JSON",
            "stop_loss": False,
        }
    if payload.get("ok") and payload.get("data"):
        return {
            "status": "ok",
            "data": payload["data"],
            "message": "获取小红书作品数据成功",
            "stop_loss": False,
        }
    return {
        "status": "failed",
        "data": None,
        "message": "XHS-Downloader 未能提取作品数据",
        "stop_loss": False,
    }


def _default_runner_fn(cmd: list, timeout: int):
    """真实子进程调用。cwd/PYTHONPATH 指向 bootstrap clone 以便 `from source import XHS`。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = XHS_DL_DIR
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=XHS_DL_DIR,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def fetch_note(
    raw_url: str,
    *,
    cookie: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    runner_fn=None,
) -> dict:
    """高层入口：原始输入 → 报告输入契约（或结构化错误）。

    返回:
        {
          "status": ok|failed|ip_risk|timeout|error|invalid_url,
          "report_input": dict|None,   # 仅 ok 时有
          "message": str,
          "stop_loss": bool,           # 仅 ip_risk 为 True
          "url": str,                  # 规范化后的链接（invalid_url 时为原始输入）
        }
    """
    url = prepare_url(raw_url)
    if not url:
        return {
            "status": "invalid_url",
            "report_input": None,
            "message": "无法识别为小红书作品链接",
            "stop_loss": False,
            "url": raw_url,
        }

    cmd = build_command(url, cookie=cookie)
    runner_fn = runner_fn or _default_runner_fn

    try:
        returncode, stdout, stderr = runner_fn(cmd, timeout)
    except (TimeoutError, subprocess.TimeoutExpired):
        return {
            "status": "timeout",
            "report_input": None,
            "message": "runner 子进程超时（%ss）" % timeout,
            "stop_loss": False,
            "url": url,
        }

    result = classify(returncode, stdout, stderr)
    report_input = None
    if result["status"] == "ok":
        report_input = adapt_to_report_input(result["data"], url=url)
    return {
        "status": result["status"],
        "report_input": report_input,
        "message": result["message"],
        "stop_loss": result["stop_loss"],
        "url": url,
    }


def main(argv: list) -> int:
    """CLI：python xhs_backend.py <url> [cookie] → 打印报告输入契约 JSON。"""
    if len(argv) < 2:
        print("用法: python xhs_backend.py <小红书链接> [cookie]", file=sys.stderr)
        return 2
    cookie = argv[2] if len(argv) > 2 else ""
    out = fetch_note(argv[1], cookie=cookie)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
