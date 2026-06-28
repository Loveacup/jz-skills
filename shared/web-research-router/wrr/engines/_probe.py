"""命令探测工具（P1）。

提供 `probe_command()` 异步探测本地 CLI 工具可用性、版本、健康状况。
用于 doctor 深度检查（P1），避免在 health_check 内重复造轮子。
"""
import asyncio
import shutil
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class CommandProbeResult:
    """命令探测结果。"""
    command: str
    status: str  # ok | missing | broken | timeout | error
    path: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "status": self.status,
            "path": self.path,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
        }


async def probe_command(
    cmd: str,
    args: Tuple[str, ...] = ("--version",),
    timeout: float = 5.0,
) -> CommandProbeResult:
    """异步探测命令是否可用。

    Args:
        cmd: 命令名（不含路径）
        args: 传递给命令的参数（默认 --version）
        timeout: 超时时间（秒）

    Returns:
        CommandProbeResult:
            - status="missing": 命令不在 PATH
            - status="ok": 命令执行成功（exit code 0）
            - status="broken": 命令执行失败（exit code != 0）
            - status="timeout": 命令超时被杀
            - status="error": 其他错误（OSError, FileNotFoundError 等）

    Examples:
        >>> result = await probe_command("opencli", ("--version",))
        >>> assert result.status == "ok"
        >>> assert "/opencli" in result.path
    """
    # Step 1: 检查命令是否在 PATH
    cmd_path = shutil.which(cmd)
    if not cmd_path:
        return CommandProbeResult(
            command=cmd,
            status="missing",
            error=f"{cmd} not found in PATH",
        )

    # Step 2: 执行命令
    try:
        proc = await asyncio.create_subprocess_exec(
            cmd_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 等待完成，带超时
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
            exit_code = proc.returncode
        except asyncio.TimeoutError:
            # 超时：杀进程
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return CommandProbeResult(
                command=cmd,
                status="timeout",
                path=cmd_path,
                error=f"Command timed out after {timeout}s",
            )

        # Step 3: 解码输出（限制长度，避免巨大输出）
        stdout = stdout_bytes.decode("utf-8", errors="replace")[:500]
        stderr = stderr_bytes.decode("utf-8", errors="replace")[:500]

        # Step 4: 判断状态
        if exit_code == 0:
            return CommandProbeResult(
                command=cmd,
                status="ok",
                path=cmd_path,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
            )
        else:
            return CommandProbeResult(
                command=cmd,
                status="broken",
                path=cmd_path,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                error=f"Command exited with code {exit_code}",
            )

    except (OSError, FileNotFoundError) as e:
        # 命令存在但无法执行（权限问题等）
        return CommandProbeResult(
            command=cmd,
            status="error",
            path=cmd_path,
            error=f"{type(e).__name__}: {e}",
        )
    except Exception as e:
        # 其他未预期错误
        return CommandProbeResult(
            command=cmd,
            status="error",
            path=cmd_path,
            error=f"{type(e).__name__}: {e}",
        )
