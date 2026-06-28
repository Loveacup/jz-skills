"""测试 _probe.py 命令探测工具。"""
import asyncio
import shutil
from unittest.mock import patch, MagicMock

from wrr.engines._probe import probe_command, CommandProbeResult


def run(coro):
    """同步运行协程。"""
    return asyncio.run(coro)


# ── probe_command 测试 ──────────────────────────────────────────────
def test_probe_command_missing():
    """命令不存在 → status="missing"。"""
    with patch("shutil.which", return_value=None):
        result = run(probe_command("nonexistent"))
    assert result.status == "missing"
    assert result.command == "nonexistent"
    assert result.path is None
    assert "not found" in result.error.lower()


def test_probe_command_ok():
    """命令执行成功 → status="ok"。"""
    async def mock_create_subprocess(*args, **kwargs):
        proc = MagicMock()

        async def mock_communicate():
            return (b"version 1.0\n", b"")

        proc.communicate = mock_communicate
        proc.returncode = 0
        return proc

    with patch("shutil.which", return_value="/usr/bin/echo"):
        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            result = run(probe_command("echo", ("--version",)))

    assert result.status == "ok"
    assert result.exit_code == 0
    assert result.path == "/usr/bin/echo"
    assert "version" in result.stdout.lower()


def test_probe_command_nonzero_exit():
    """命令返回非零退出码 → status="broken"。"""
    async def mock_create_subprocess(*args, **kwargs):
        proc = MagicMock()

        async def mock_communicate():
            return (b"", b"error: invalid option\n")

        proc.communicate = mock_communicate
        proc.returncode = 1
        return proc

    with patch("shutil.which", return_value="/usr/bin/false"):
        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            result = run(probe_command("false"))

    assert result.status == "broken"
    assert result.exit_code == 1
    assert "exited with code 1" in result.error


def test_probe_command_timeout():
    """命令超时 → status="timeout"，进程被杀。"""
    async def mock_create_subprocess(*args, **kwargs):
        proc = MagicMock()

        async def hang_forever():
            await asyncio.sleep(10)  # 远超 timeout
            return (b"", b"")

        async def mock_wait():
            pass

        proc.communicate = hang_forever
        proc.kill = MagicMock()
        proc.wait = mock_wait
        return proc

    with patch("shutil.which", return_value="/usr/bin/sleep"):
        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            result = run(probe_command("sleep", ("10",), timeout=0.1))

    assert result.status == "timeout"
    assert "timed out" in result.error.lower()


def test_probe_command_os_error():
    """命令存在但执行失败（OSError）→ status="error"。"""
    async def mock_create_subprocess(*args, **kwargs):
        raise OSError("Permission denied")

    with patch("shutil.which", return_value="/usr/bin/restricted"):
        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            result = run(probe_command("restricted"))

    assert result.status == "error"
    assert "OSError" in result.error
    assert "Permission denied" in result.error


def test_probe_command_output_truncation():
    """输出超过 500 字符会被截断。"""
    async def mock_create_subprocess(*args, **kwargs):
        proc = MagicMock()
        long_output = b"x" * 1000

        async def mock_communicate():
            return (long_output, b"")

        proc.communicate = mock_communicate
        proc.returncode = 0
        return proc

    with patch("shutil.which", return_value="/usr/bin/spam"):
        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            result = run(probe_command("spam"))

    assert result.status == "ok"
    assert len(result.stdout) == 500
    assert result.stdout == "x" * 500


def test_command_probe_result_to_dict():
    """CommandProbeResult.to_dict() 返回完整字段。"""
    result = CommandProbeResult(
        command="test",
        status="ok",
        path="/usr/bin/test",
        exit_code=0,
        stdout="output",
        stderr="",
        error="",
    )
    d = result.to_dict()
    assert d["command"] == "test"
    assert d["status"] == "ok"
    assert d["path"] == "/usr/bin/test"
    assert d["exit_code"] == 0
    assert d["stdout"] == "output"
