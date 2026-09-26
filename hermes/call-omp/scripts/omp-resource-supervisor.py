#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────
# omp-resource-supervisor.py —— call-omp 资源监督器（P0A slice 1）
#
# 职责：把一个 OMP 进程跑在独立 process group / session 里，
#   流式把 stdout 写到指定 raw 文件，硬性执行 raw_bytes ≤ --raw-cap
#   （默认 20 MiB）。超出时立刻停止整个 PGID，记录 bounded forensic
#   状态到 --state-file（status=resource_rejected），并把 PGID/PID
#   身份保留以便外部 monitor 通过同一份身份核对（PID 重用场景）。
#
# 不解析 stdout 语义、不做协议判断；只做"流 + 字节 + 进程组 + 鉴权"。
#
# 用法：
#   python3 omp-resource-supervisor.py \
#     --state-file /tmp/omp-supervisor-foo.json \
#     --raw-output /tmp/omp-raw-foo.json \
#     --raw-cap 20971520 \
#     --pid-store /tmp/omp-supervisor-foo.pids \
#     -- <omp-cmd...>
#
# 退出码：
#   0  子进程 exit_code=0 且未触发熔断
#   2  资源熔断（raw_cap / rate_fuse），已在 state-file 落 resource_rejected
#   3  参数错误 / 子进程启动失败
#   4  子进程非零退出（state-file.run.exit_code / .run.resource_status）
# ─────────────────────────────────────────────────────────────────
from __future__ import annotations
import argparse
import errno
import hashlib
import importlib.util
import json
import math
import os
import select
import signal
import stat
import subprocess
import sys
import time
import uuid

DEFAULT_RAW_CAP = 20 * 1024 * 1024
TAIL_CAP = 8192

# ── P2B S1B · opt-in verdict_v1 capture caps ──
# 仅 --capture-mode verdict_v1 使用；legacy 路径完全不受影响。
DEFAULT_INGRESS_CAP = 128 * 1024 * 1024   # 从 stdout 管道实际读入的物理字节上限
DEFAULT_VERDICT_CAP = 1 * 1024 * 1024     # 规范 verdict raw 落盘上限
DEFAULT_DIAGNOSTIC_CAP = 512 * 1024       # .diag.jsonl 落盘上限（触顶只截断，不熔断）
# 单条 JSONL 记录（含末尾换行）硬上限，1 MiB 包含边界；与分类器 MAX_INPUT_BYTES 对齐。
MAX_INPUT_BYTES = 1024 * 1024
READ_CHUNK = 1 << 16

try:
    # POSIX-only. Absence means we CANNOT enforce a kernel-level hard cap
    # across escaped (setsid) descendants, so the supervisor fails closed
    # rather than silently claiming a hard cap it cannot deliver.
    import resource as _resource
except ImportError:  # pragma: no cover - non-POSIX platform
    _resource = None


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def atomic_write_json(path: str, payload: dict) -> None:
    tmp = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def own_pgid(child_pid: int, child_pgid: int) -> bool:
    # Returns True if the supervisor owns the child's PGID and is therefore
    # safe to kill it. We require:
    #  * the recorded PGID is non-zero and matches the recorded PID
    #    (the child was started with start_new_session=True so its PGID
    #    equals its PID by construction),
    #  * the child's PGID differs from the supervisor's own PGID (we never
    #    want to killpg ourselves).
    if child_pgid <= 0 or child_pid <= 0:
        return False
    if child_pgid != child_pid:
        # Popen with start_new_session=True always creates a new session
        # whose leader's PGID equals its PID. If that invariant is broken
        # we cannot be sure the recorded PGID still maps to *this* child.
        return False
    try:
        current = os.getpgrp()
    except OSError:
        return False
    return current != child_pgid


def terminate_owned_pg(child_pgid: int, child_pid: int, *, grace: float = 1.0) -> bool:
    """Send TERM to the owned PGID; if still alive after grace, KILL.
    Returns True if the group is verifiably gone, False if we cannot
    confirm — caller MUST NOT touch arbitrary PIDs in that case.

    macOS quirk: killpg(child_pgid, 0) can return EPERM if the supervisor's
    session/UID no longer matches the child's (typically because the child
    reparented to launchd after start_new_session). On Linux the same check
    returns ESRCH for a dead group. We treat EPERM as inconclusive-but-not-
    necessarily-fatal and rely on waitpid/WIFEXITED on the Popen object as
    the authoritative death signal.
    """
    if not own_pgid(child_pid, child_pgid):
        return False
    try:
        os.killpg(child_pgid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    deadline = time.time() + grace
    while time.time() < deadline:
        try:
            os.killpg(child_pgid, 0)
            time.sleep(0.05)
            continue
        except ProcessLookupError:
            return True
        except OSError:
            # EPERM on macOS: child exists but we cannot signal it from our
            # session. Authoritative death signal is child.wait() in the
            # caller; treat this loop as inconclusive and rely on the
            # caller-side wait to confirm.
            time.sleep(0.05)
            continue
    # After grace, escalate to KILL.
    if not own_pgid(child_pid, child_pgid):
        return False
    try:
        os.killpg(child_pgid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    # Final verification.
    try:
        os.killpg(child_pgid, 0)
        return False
    except ProcessLookupError:
        return True
    except OSError:
        return False


def child_rlimit_preexec(raw_cap: int):
    """Return a preexec callable that pins RLIMIT_FSIZE to raw_cap in the child.

    RLIMIT_FSIZE is enforced by the kernel at write() time and is INHERITED by
    every descendant of the OMP child — including any that detach via setsid.
    A write that would extend a regular file past raw_cap fails with EFBIG and
    raises SIGXFSZ, so no escaped descendant can push the raw output beyond the
    cap regardless of supervisor polling. Both soft and hard limits are set to
    raw_cap so a descendant cannot raise the limit back up. The supervisor's own
    process limits are untouched (this runs only in the forked child)."""
    def _apply() -> None:  # runs post-fork, pre-exec, in the child
        _resource.setrlimit(_resource.RLIMIT_FSIZE, (raw_cap, raw_cap))
    return _apply


def containment_reason(reason: str, *, reaped: bool) -> str:
    """Append a truthful containment marker when the direct child could not be
    reaped by deadline. Never implies clean containment on an unconfirmed reap.

    Kept as a tiny pure function so the (rarely reachable) unreaped branch can
    be proven deterministically without racing a real unkillable process."""
    if reaped:
        return reason
    marker = "containment_failure:child_not_reaped"
    if marker in reason:
        return reason
    return f"{reason}; {marker}" if reason else marker


def resource_trip_shutdown(child: subprocess.Popen, child_pgid: int,
                           child_pid: int, *, grace: float) -> int | None:
    """Single safe shutdown path for ANY resource trip (raw_cap OR rate_fuse).

    Containment invariant shared by both fuses:
      * TERM then KILL the owned process group — but ONLY after own_pgid()
        validation, which is enforced inside terminate_owned_pg(). We never
        signal a group we do not own.
      * child.wait() is the authoritative death signal on macOS, where
        killpg(pgid, 0) may return EPERM for a live-but-unsignalable child.

    Returns the child's return code once reaped, or None if it could not be
    confirmed dead within the grace-derived deadline. Callers treat a live
    child as a containment failure and must not proceed as if it were gone.
    """
    terminate_owned_pg(child_pgid, child_pid, grace=grace)
    try:
        child.wait(timeout=max(2.0, grace + 1.0))
    except subprocess.TimeoutExpired:
        pass
    return child.returncode


def owned_group_members(child_pgid: int, exclude_pid: int) -> list[int] | None:
    """Live (non-zombie) members of the owned process group other than
    exclude_pid, from a `ps` census. None means the census failed; callers
    treat that as unknown and never as an empty group."""
    try:
        out = subprocess.run(["ps", "-A", "-o", "pid=,pgid=,stat="], capture_output=True,
                             text=True, timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    members = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            pid, pgid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if pgid == child_pgid and pid != exclude_pid and not parts[2].startswith("Z"):
            members.append(pid)
    return members


def wait_leader_exit(child: subprocess.Popen, timeout: float) -> bool:
    """Wait up to timeout for the leader to exit, leaving it unreaped so its PID
    keeps the owned group identity and the group can still be signalled safely.
    Uses os.waitid(WNOWAIT) when available, otherwise polls `ps` for the zombie
    state; neither path reaps."""
    end = time.monotonic() + timeout
    while True:
        if child.returncode is not None:
            return True
        if hasattr(os, "waitid"):
            if execute_child_exited_unreaped(child):
                return True
        else:
            try:
                st = subprocess.run(["ps", "-o", "stat=", "-p", str(child.pid)], capture_output=True,
                                    text=True, timeout=5).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                st = ""
            if st.startswith("Z"):
                return True
        if time.monotonic() >= end:
            return False
        time.sleep(0.05 if hasattr(os, "waitid") else 0.2)


def build_state_payload(args: argparse.Namespace, *, status: str,
                       exit_code: int | None, started_at: str,
                       ended_at: str, raw_bytes: int, raw_lines: int,
                       digest: str, tail_bytes: int, reason: str,
                       rate_fuse: dict | None, capture: dict | None = None) -> dict:
    payload = {
        "schema": "call-omp-resource-supervisor.v1",
        "task_id": args.task_id,
        "task_id_source": args.task_id_source,
        "state_file": args.state_file,
        "raw_output": args.raw_output,
        "raw_cap": args.raw_cap,
        "raw_bytes": raw_bytes,
        "raw_lines": raw_lines,
        "raw_sha256": digest,
        "raw_tail_bytes": tail_bytes,
        "rate_fuse": rate_fuse or {"enabled": False},
        "status": status,
        "reason": reason,
        "run": {
            "started_at": started_at,
            "ended_at": ended_at,
            "exit_code": exit_code,
            "pid_store": args.pid_store,
        },
        "child_identity": {
            "pid": getattr(args, "recorded_pid", None),
            "pgid": getattr(args, "recorded_pgid", None),
            "session_id": getattr(args, "recorded_sid", None),
            "argv": list(getattr(args, "argv", [])),
        },
    }
    # Additive capture fields ONLY in verdict_v1. Legacy invocations pass
    # capture=None and the state schema is byte-for-byte unchanged.
    if capture is not None:
        payload.update(capture)
    return payload


def canonical_jsonl(obj) -> bytes:
    """确定性规范 JSONL（键排序 + 紧凑分隔符 + ASCII-safe + 末尾换行）。

    与分类器 _canonical 同形；用于把 diagnostic_record（仅固定安全键、无 canary）
    落到 .diag.jsonl。ensure_ascii=True 保证任何已解析对象都可编码，不会抛异常。"""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text.encode("utf-8") + b"\n"


def capture_fields(args: argparse.Namespace, *, ingress_bytes: int,
                   ingress_lines: int, ingress_sha256: str, verdict_bytes: int,
                   verdict_lines: int, verdict_sha256: str, diagnostic_bytes: int,
                   diagnostic_lines: int, diagnostic_sha256: str,
                   diagnostic_truncated: bool, preserved: int, denied: int,
                   unknown_ct: int, tc_unknown: int) -> dict:
    """verdict_v1 的附加 capture 字段块（全部为 additive）。"""
    return {
        "capture_mode": "verdict_v1",
        "diagnostic_output": args.diagnostic_output,
        "ingress_bytes": ingress_bytes,
        "ingress_lines": ingress_lines,
        "ingress_sha256": ingress_sha256,
        "verdict_bytes": verdict_bytes,
        "verdict_lines": verdict_lines,
        "verdict_sha256": verdict_sha256,
        "diagnostic_bytes": diagnostic_bytes,
        "diagnostic_lines": diagnostic_lines,
        "diagnostic_sha256": diagnostic_sha256,
        "diagnostic_truncated": diagnostic_truncated,
        "preserved_count": preserved,
        "denied_count": denied,
        "unknown_count": unknown_ct,
        "terminal_capable_unknown_count": tc_unknown,
    }


def zero_capture(args: argparse.Namespace) -> dict:
    return capture_fields(args, ingress_bytes=0, ingress_lines=0,
                          ingress_sha256="", verdict_bytes=0, verdict_lines=0,
                          verdict_sha256="", diagnostic_bytes=0,
                          diagnostic_lines=0, diagnostic_sha256="",
                          diagnostic_truncated=False, preserved=0, denied=0,
                          unknown_ct=0, tc_unknown=0)


def load_classifier(module_path: str | None):
    """加载 classify_jsonl_line。默认用与本脚本同目录的 omp_stream_classifier.py；

    --classifier-module 是 test-only 注入点（如注入会抛异常的 classifier 以验证
    fail-closed 路径），send 生产接线永不传它。"""
    if module_path:
        path = module_path
        modname = "omp_injected_classifier"
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, "omp_stream_classifier.py")
        modname = "omp_stream_classifier"
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.classify_jsonl_line


def hash_file(path: str):
    """(size, sha256_hex, line_count)；文件缺失记 (0, '', 0)。"""
    h = hashlib.sha256()
    size = 0
    lines = 0
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
                size += len(chunk)
                lines += chunk.count(b"\n")
    except FileNotFoundError:
        return 0, "", 0
    return size, h.hexdigest(), lines


def run_verdict_capture(args: argparse.Namespace, argv: list, started_at: str,
                        classify) -> int:
    """verdict_v1 opt-in capture path.

    子进程 stdout 走 PIPE（不再直连 raw 文件）；监督器用可 select 的非阻塞管道 +
    有界增量分帧器逐行读取，每条完整行交给 classify_jsonl_line：
      * preserve → 只把 verdict_line 追加进规范 raw_output（verdict_* 计量）；
      * deny/unknown → 绝不把源正文写进 raw；
      * diagnostic_record 规范 JSONL 追加进 .diag.jsonl（触顶只截断、保聚合计数）。

    ingress 计量所有从管道实际读入的物理字节，独立于 verdict/diagnostic 上限。任何
    分类异常 / 写错误 / verdict 触顶 / ingress 触顶 / 超长行 → resource_rejected。
    terminal_capable 的 unknown 不可信：drain 到 EOF 后最终仍 resource_rejected。

    【RLIMIT 真话】preexec 仍把子进程 RLIMIT_FSIZE 钉在 raw_cap——它保护子孙进程写
    *普通文件* 的大小，由内核在 write() 时强制并被 setsid 逃逸的子孙继承；但它 **不是**
    stdout 管道的 ingress 上限（管道非普通文件，RLIMIT_FSIZE 不作用于它）。stdout 管道
    的有界性完全由本函数的 ingress 计量 + close/teardown 提供，两者互不替代。
    """
    args.diagnostic_output = args.raw_output + ".diag.jsonl"
    diag_path = args.diagnostic_output

    def preflight_reject(reason: str) -> None:
        atomic_write_json(args.state_file, build_state_payload(
            args, status="rejected", exit_code=None, started_at=started_at,
            ended_at=now_iso(), raw_bytes=0, raw_lines=0, digest="",
            tail_bytes=0, reason=reason, rate_fuse=None,
            capture=zero_capture(args)))

    try:
        raw_fh = open(args.raw_output, "wb", buffering=0)
    except OSError as exc:
        preflight_reject(f"raw_open_failed:{exc.errno or -1}")
        return 3
    try:
        diag_fh = open(diag_path, "wb", buffering=0)
    except OSError as exc:
        try:
            raw_fh.close()
        except OSError:
            pass
        preflight_reject(f"diag_open_failed:{exc.errno or -1}")
        return 3

    try:
        # stdout=PIPE：由监督器读取分帧；RLIMIT_FSIZE 仍在子进程侧安装（见 docstring）。
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True,
                                 preexec_fn=child_rlimit_preexec(args.raw_cap))
    except (FileNotFoundError, PermissionError, OSError,
            subprocess.SubprocessError) as exc:
        for fh in (raw_fh, diag_fh):
            try:
                fh.close()
            except OSError:
                pass
        preflight_reject(f"exec_failed:{type(exc).__name__}")
        return 3

    args.recorded_pid = child.pid
    try:
        args.recorded_pgid = os.getpgid(child.pid)
    except OSError:
        args.recorded_pgid = os.getpgrp()
    try:
        args.recorded_sid = os.getsid(child.pid)
    except OSError:
        args.recorded_sid = args.recorded_pgid

    with open(args.pid_store, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "pid": args.recorded_pid,
            "pgid": args.recorded_pgid,
            "session_id": args.recorded_sid,
            "argv": list(argv),
            "expected_pgid": args.expected_pgid,
            "capture_mode": "verdict_v1",
        }, sort_keys=True))

    # ── streaming accounting ──
    ingress_bytes = 0
    ingress_lines = 0
    ingress_hash = hashlib.sha256()
    verdict_bytes = 0
    verdict_lines = 0
    diag_bytes = 0
    diag_lines = 0
    diag_truncated = False
    preserved = denied = unknown_ct = tc_unknown = 0
    seq = 0
    buffer = bytearray()
    resource_status: str | None = None
    reason = ""
    untrusted = False
    tripped = False  # set once the owned group went through resource_trip_shutdown

    # ── P0 rate fuse, applied to PHYSICAL ingress byte deltas (not raw-file
    # polling). Same options/semantics as legacy: 滑动时间窗内累计 ingress ≥
    # window_bytes，连续 N 个评估 tick 越限即熔断。禁用时 window_bytes<=0。──
    rate_enabled = args.rate_window_bytes > 0
    rate_fuse_state = {
        "enabled": rate_enabled,
        "window_bytes": args.rate_window_bytes,
        "window_seconds": args.rate_window_seconds,
        "fuse_windows": args.rate_fuse_windows,
        "consecutive_over": 0,
    }
    rate_ring: list = []  # list[(ts, ingress_byte_delta)]
    # 评估 tick：与 legacy 一致用 0.1s 轮询节律（禁用则同样用 0.1s 唤醒读取）。
    poll_timeout = 0.1

    stdout_fd = child.stdout.fileno()
    os.set_blocking(stdout_fd, False)

    def close_reader() -> None:
        try:
            child.stdout.close()
        except OSError:
            pass

    def do_trip(status: str, rsn: str) -> None:
        nonlocal resource_status, reason, tripped
        resource_status = status
        reason = rsn
        tripped = True
        close_reader()
        resource_trip_shutdown(child, args.recorded_pgid, args.recorded_pid,
                               grace=args.grace_seconds)

    def handle_record(record: bytes):
        """处理一条完整（含 \\n）记录；返回 (status, reason) 表示应熔断，否则 None。"""
        nonlocal seq, verdict_bytes, verdict_lines, diag_bytes, diag_lines
        nonlocal diag_truncated, preserved, denied, unknown_ct, tc_unknown, untrusted
        seq += 1
        if len(record) > MAX_INPUT_BYTES:
            return ("overlong", f"resource_rejected:overlong_line:{len(record)}")
        try:
            result = classify(record, seq)
        except Exception as exc:  # 分类器永不该抛；抛即 fail-closed
            return ("classifier_exception",
                    f"resource_rejected:classifier_exception:{type(exc).__name__}")

        decision = result.decision
        if decision == "preserve":
            preserved += 1
        elif decision == "deny":
            denied += 1
        else:
            unknown_ct += 1
            if result.terminal_capable:
                tc_unknown += 1
                untrusted = True  # 不可信：最终态强制 resource_rejected

        if decision == "preserve" and result.verdict_line:
            vl = result.verdict_line
            if verdict_bytes + len(vl) > args.verdict_cap:
                return ("verdict_cap",
                        f"resource_rejected:verdict_cap_exceeded:"
                        f"{verdict_bytes + len(vl)}>{args.verdict_cap}")
            try:
                raw_fh.write(vl)
            except OSError as exc:
                return ("verdict_write_error",
                        f"resource_rejected:verdict_write_error:{exc.errno or -1}")
            verdict_bytes += len(vl)
            verdict_lines += 1

        # diagnostic：触顶只截断（保聚合计数并继续 drain），真实写错误才熔断。
        diag_line = canonical_jsonl(result.diagnostic_record)
        if not diag_truncated:
            if diag_bytes + len(diag_line) <= args.diagnostic_cap:
                try:
                    diag_fh.write(diag_line)
                except OSError as exc:
                    return ("diagnostic_write_error",
                            f"resource_rejected:diagnostic_write_error:{exc.errno or -1}")
                diag_bytes += len(diag_line)
                diag_lines += 1
            else:
                diag_truncated = True
        return None

    def process_chunk(chunk: bytes):
        """把一段读入字节计量、分帧、分类；返回 (status, reason) 需熔断，否则 None。"""
        nonlocal ingress_bytes, ingress_lines, buffer
        ingress_bytes += len(chunk)
        ingress_hash.update(chunk)
        ingress_lines += chunk.count(b"\n")
        # ingress 触顶：独立于 verdict/diagnostic/rate。
        if ingress_bytes > args.ingress_cap:
            return ("ingress_cap",
                    f"resource_rejected:ingress_cap_exceeded:"
                    f"{ingress_bytes}>{args.ingress_cap}")
        buffer += chunk
        while True:
            nl = buffer.find(b"\n")
            if nl == -1:
                if len(buffer) > MAX_INPUT_BYTES:
                    return ("overlong",
                            f"resource_rejected:overlong_line_unterminated:{len(buffer)}")
                break
            record = bytes(buffer[:nl + 1])
            del buffer[:nl + 1]
            action = handle_record(record)
            if action is not None:
                return action
        return None

    # ── read/frame/classify loop（tick 化：每个 tick 先排空当前可读数据，再做一次
    #    rate 评估）。select/read 故障一律 fail-closed（capture_io_error），绝不当
    #    成 EOF 静默上报成功。──
    # Hard wall-clock deadline (optional; SEND passes max_time + 30). OMP's own
    # --max-time is not trusted to bound the child: a rejected-but-running audit
    # would outlive its verdict.
    deadline = (time.monotonic() + args.max_seconds) if args.max_seconds is not None else None
    while resource_status is None:
        if deadline is not None and time.monotonic() >= deadline:
            do_trip("deadline_exceeded",
                    f"resource_rejected:deadline_exceeded:{args.max_seconds:g}s")
            break
        try:
            rlist, _, _ = select.select([stdout_fd], [], [], poll_timeout)
        except (OSError, ValueError) as exc:
            # 无效 fd / 内核错误：不可信，熔断而非静默成功。
            do_trip("capture_io_error",
                    f"resource_rejected:capture_io_error:select:{type(exc).__name__}")
            break

        delta_tick = 0
        eof = False
        io_action = None
        # 排空本 tick 当前所有可读数据（非阻塞）；避免单 tick 多次 read 令
        # consecutive_over 失真。
        if rlist:
            while True:
                try:
                    chunk = os.read(stdout_fd, READ_CHUNK)
                except (BlockingIOError, InterruptedError):
                    break  # EAGAIN：本 tick 数据已排空
                except OSError as exc:
                    io_action = ("capture_io_error",
                                 f"resource_rejected:capture_io_error:read:"
                                 f"{exc.errno if exc.errno is not None else type(exc).__name__}")
                    break
                if chunk == b"":
                    eof = True
                    break
                delta_tick += len(chunk)
                action = process_chunk(chunk)
                if action is not None:
                    do_trip(action[0], action[1])
                    break
            if resource_status is not None:
                break
        if io_action is not None:
            do_trip(io_action[0], io_action[1])
            break

        # ── rate fuse：对 physical ingress delta 做滑动窗口评估（每 tick 一次）──
        if rate_enabled:
            now = time.time()
            rate_ring.append((now, delta_tick))
            cutoff = now - rate_fuse_state["window_seconds"]
            while rate_ring and rate_ring[0][0] < cutoff:
                rate_ring.pop(0)
            window_bytes = sum(d for _, d in rate_ring)
            if window_bytes >= rate_fuse_state["window_bytes"]:
                rate_fuse_state["consecutive_over"] += 1
            else:
                rate_fuse_state["consecutive_over"] = 0
            if rate_fuse_state["consecutive_over"] >= rate_fuse_state["fuse_windows"]:
                do_trip("rate_fuse",
                        f"resource_rejected:rate_fuse:{window_bytes}B/"
                        f"{rate_fuse_state['window_bytes']}B over "
                        f"{rate_fuse_state['fuse_windows']} windows")
                break

        if eof:
            break  # EOF：write 端全部关闭（仅在无前置熔断时为正常）

    # EOF 到达且无硬熔断：任何非空、无末尾换行的残留尾片都是 framing 破坏。
    # 契约（S1B/EOF-framing 修复，L2 found EOF-terminal-unknown bypass）：verdict_v1
    # 是 newline-delimited JSONL——一条记录只有带末尾换行才算完整。绝不把尾片交给
    # 分类器：即便它是语法合法但缺末尾换行的 terminal-shaped JSON（如 turn_end），也
    # 一律按 framing-invalid fail closed，不做 partial JSON parse、不做 terminal 能力
    # 推断。fail closed：不 preserve、不写 raw/diag、尾片正文绝不进入 raw/diag/state；
    # 走与其它熔断相同的 close reader + owned-PGID 安全 shutdown/reap 路径。reason 只带
    # 字节计数、不含任何尾片正文。
    if resource_status is None and buffer:
        n = len(buffer)
        buffer = bytearray()
        do_trip("incomplete_final_record",
                f"resource_rejected:incomplete_final_record:{n}")

    # terminal_capable 的 unknown：即使有后续合法 end 事件，最终仍 resource_rejected。
    if resource_status is None and untrusted:
        resource_status = "classification_untrusted"
        reason = "resource_rejected:classification_untrusted"

    # EOF does not mean the child exited: a child may close stdout and keep running.
    # Wait for it only until the deadline (or the grace period without one); a child
    # still alive then is stopped through the owned-group trip path and is never
    # recorded as normal_completion. An already-rejected run (classification_untrusted)
    # keeps its reason but its live child is stopped the same way.
    if not tripped:
        wait_s = max(2.0, args.grace_seconds + 1.0)
        if deadline is not None:
            wait_s = max(0.0, deadline - time.monotonic())
        if not wait_leader_exit(child, wait_s):
            if resource_status is not None:
                prior_status, prior_reason = resource_status, reason
                do_trip(prior_status, prior_reason)
            elif deadline is not None:
                do_trip("deadline_exceeded",
                        f"resource_rejected:deadline_exceeded:{args.max_seconds:g}s")
            else:
                do_trip("child_alive_after_eof", "resource_rejected:child_alive_after_eof")

    # A leader exit must not leave same-group survivors behind the receipt. While
    # the leader is still unreaped (waitid path) the group identity is retained and
    # the survivors are stopped; after a reap it is only observed, never signalled.
    if not tripped:
        survivors = owned_group_members(args.recorded_pgid, args.recorded_pid)
        if survivors is None or survivors:
            marker = ("owned_group_state_unknown" if survivors is None
                      else "owned_group_alive_after_exit")
            if resource_status is None:
                resource_status, reason = marker, f"resource_rejected:{marker}"
            else:
                reason = f"{reason}; {marker}"
            if child.returncode is None:
                terminate_owned_pg(args.recorded_pgid, args.recorded_pid,
                                   grace=args.grace_seconds)
            else:
                reason = f"{reason}; containment_failure:group_not_signalled_after_reap"
            try:
                child.wait(timeout=max(2.0, args.grace_seconds + 1.0))
            except subprocess.TimeoutExpired:
                pass
            left = owned_group_members(args.recorded_pgid, args.recorded_pid)
            if left is None or left:
                reason = f"{reason}; containment_failure:owned_group_alive"

    # ── finalize：关我方句柄，reap 子进程，用磁盘文件作为权威 digest 源 ──
    close_reader()
    for fh in (raw_fh, diag_fh):
        try:
            fh.flush()
            fh.close()
        except OSError:
            pass

    try:
        child.wait(timeout=max(2.0, args.grace_seconds + 1.0))
    except subprocess.TimeoutExpired:
        pass
    rc = child.returncode
    if resource_status is not None:
        reason = containment_reason(reason, reaped=rc is not None)

    ended_at = now_iso()
    v_size, v_sha, v_lines = hash_file(args.raw_output)
    d_size, d_sha, d_lines = hash_file(diag_path)
    try:
        tail_bytes = len(open(args.raw_output, "rb").read()[-args.tail_cap:])
    except FileNotFoundError:
        tail_bytes = 0

    cap = capture_fields(
        args, ingress_bytes=ingress_bytes, ingress_lines=ingress_lines,
        ingress_sha256=ingress_hash.hexdigest() if ingress_bytes else "",
        verdict_bytes=v_size, verdict_lines=v_lines, verdict_sha256=v_sha,
        diagnostic_bytes=d_size, diagnostic_lines=d_lines, diagnostic_sha256=d_sha,
        diagnostic_truncated=diag_truncated, preserved=preserved, denied=denied,
        unknown_ct=unknown_ct, tc_unknown=tc_unknown)

    # 持久化真实 rate_fuse 结构（含最终 consecutive_over）；禁用时才落 {enabled:false}，
    # 绝不用 {enabled:false} 覆盖 enabled=true。
    rate_fuse_final = rate_fuse_state if rate_enabled else None

    if resource_status is not None:
        payload = build_state_payload(
            args, status="resource_rejected",
            exit_code=rc if rc is not None else 124,
            started_at=started_at, ended_at=ended_at,
            raw_bytes=v_size, raw_lines=v_lines, digest=v_sha,
            tail_bytes=tail_bytes, reason=reason, rate_fuse=rate_fuse_final,
            capture=cap)
        atomic_write_json(args.state_file, payload)
        return 2

    payload = build_state_payload(
        args, status="reported", exit_code=rc if rc is not None else 0,
        started_at=started_at, ended_at=ended_at,
        raw_bytes=v_size, raw_lines=v_lines, digest=v_sha,
        tail_bytes=tail_bytes, reason="normal_completion",
        rate_fuse=rate_fuse_final, capture=cap)
    atomic_write_json(args.state_file, payload)
    return 0 if rc == 0 else 4


class ExecuteControlError(Exception):
    """The execute_v1 cancellation channel cannot be trusted."""


def _validate_private_regular(
        path: str, *, allow_missing: bool) -> os.stat_result | None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise ExecuteControlError(f"not_private_regular:{path}")
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o077:
        raise ExecuteControlError(f"not_private_owned:{path}")
    return st


def atomic_write_private_json(path: str, payload: dict) -> None:
    """Atomic 0600 JSON publication used only by execute_v1."""
    _validate_private_regular(path, allow_missing=True)
    tmp = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = -1
    committed = False
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            json.dump(payload, fh, sort_keys=True, separators=(",", ":"))
            fh.write("\n")
            os.fchmod(fh.fileno(), 0o600)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        committed = True
    finally:
        if fd >= 0:
            os.close(fd)
        # Once replace commits, no fallible housekeeping may invert the
        # caller's exact publication result. Clean the temp only pre-commit.
        if not committed:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def open_private_output(path: str):
    existing = _validate_private_regular(path, allow_missing=True)
    flags = os.O_WRONLY
    if existing is None:
        flags |= os.O_CREAT | os.O_EXCL
    if not hasattr(os, "O_NOFOLLOW"):
        raise ExecuteControlError("nofollow_unsupported")
    flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
                or stat.S_IMODE(st.st_mode) & 0o077
                or (existing is not None
                    and (st.st_dev, st.st_ino) !=
                    (existing.st_dev, existing.st_ino))):
            raise ExecuteControlError(f"unsafe_output:{path}")
        os.fchmod(fd, 0o600)
        os.ftruncate(fd, 0)
        fh = os.fdopen(fd, "wb", buffering=0)
        fd = -1
        return fh
    finally:
        if fd >= 0:
            os.close(fd)


def read_execute_cancel(args: argparse.Namespace) -> str | None:
    """Read one atomic request without following a symlink.

    A well-formed request for another attempt is stale and ignored. Malformed
    channel data or any control I/O fault is fail-closed because it makes
    authenticated cancellation unavailable for the current attempt.
    """
    path = args.control_file
    try:
        lst = os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ExecuteControlError(
            f"control_lstat:{exc.errno or -1}") from exc
    if stat.S_ISLNK(lst.st_mode) or not stat.S_ISREG(lst.st_mode):
        raise ExecuteControlError("control_not_regular")
    if not hasattr(os, "O_NOFOLLOW"):
        raise ExecuteControlError("control_nofollow_unsupported")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = -1
    io_error: ExecuteControlError | None = None
    try:
        fd = os.open(path, flags)
        st = os.fstat(fd)
        if ((st.st_dev, st.st_ino) != (lst.st_dev, lst.st_ino)):
            raise ExecuteControlError("control_replaced")
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
                or stat.S_IMODE(st.st_mode) & 0o077):
            raise ExecuteControlError("control_not_private")
        if st.st_size > 4096:
            raise ExecuteControlError("control_too_large")
        data = os.read(fd, 4097)
    except ExecuteControlError as exc:
        io_error = exc
    except OSError as exc:
        io_error = ExecuteControlError(f"control_io:{exc.errno or -1}")
    if fd >= 0:
        try:
            os.close(fd)
        except OSError as exc:
            if io_error is None:
                io_error = ExecuteControlError(
                    f"control_close:{exc.errno or -1}")
    if io_error is not None:
        raise io_error
    if len(data) > 4096:
        raise ExecuteControlError("control_too_large")
    try:
        request = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecuteControlError("control_invalid_json") from exc
    required = {
        "schema", "task_id", "attempt_id", "launch_fingerprint", "reason",
    }
    if not isinstance(request, dict) or set(request) != required:
        raise ExecuteControlError("control_invalid_shape")
    if request.get("schema") != "call-omp-cancel.v1":
        raise ExecuteControlError("control_invalid_schema")
    if not all(isinstance(request.get(key), str) for key in required):
        raise ExecuteControlError("control_invalid_types")
    reason = request["reason"]
    if not reason or len(reason) > 512 or any(ord(ch) < 0x20 for ch in reason):
        raise ExecuteControlError("control_invalid_reason")
    if (request["task_id"] != args.task_id
            or request["attempt_id"] != args.attempt_id
            or request["launch_fingerprint"] != args.launch_fingerprint):
        return None
    return reason


def execute_child_identity(args: argparse.Namespace) -> dict:
    return {
        "pid": getattr(args, "recorded_pid", None),
        "pgid": getattr(args, "recorded_pgid", None),
        "session_id": getattr(args, "recorded_sid", None),
        "supervisor_pid": os.getpid(),
        "identity_observed": getattr(args, "identity_observed", False),
    }


def execute_receipt(args: argparse.Namespace, *, status: str,
                    started_at: str, ended_at: str | None,
                    worker_exit_code: int | None,
                    supervisor_exit_code: int | None,
                    terminal_reason: str, cleanup_confirmed: bool,
                    stdout_bytes: int, stdout_lines: int, stdout_sha256: str,
                    stderr_bytes: int, stderr_lines: int, stderr_sha256: str,
                    stdout_truncated: bool, stderr_truncated: bool,
                    escaped_evidence: bool) -> dict:
    return {
        "schema": "call-omp-resource-supervisor.v2",
        "capture_mode": "execute_v1",
        "task_id": args.task_id,
        "task_id_source": args.task_id_source,
        "attempt_id": args.attempt_id,
        "launch_fingerprint": args.launch_fingerprint,
        "state_file": args.state_file,
        "raw_output": args.raw_output,
        "pid_store": args.pid_store,
        "stderr_output": args.stderr_output,
        "raw_cap": args.raw_cap,
        "control_file": args.control_file,
        "max_seconds": args.max_seconds,
        "status": status,
        "reason": terminal_reason,
        "terminal_reason": terminal_reason,
        "cleanup_confirmed": cleanup_confirmed,
        # cleanup_confirmed covers only the observed start_new_session process
        # group and direct child. It never asserts containment of an unobserved
        # setsid/double-fork descendant.
        "process_identity_guard": "unreaped_leader_until_last_group_signal",
        "cleanup_scope": "observed_process_group",
        "terminal_decision_cutoff":
            "post_cleanup_signal_block_then_control_read",
        "escaped_descendant_evidence": escaped_evidence,
        "worker_exit_code": worker_exit_code,
        "worker_signal": -worker_exit_code if (
            isinstance(worker_exit_code, int) and worker_exit_code < 0) else None,
        "exit_code": worker_exit_code,
        "supervisor_exit_code": supervisor_exit_code,
        "raw_bytes": stdout_bytes,
        "raw_lines": stdout_lines,
        "raw_sha256": stdout_sha256,
        "stdout_truncated": stdout_truncated,
        "stderr_bytes": stderr_bytes,
        "stderr_lines": stderr_lines,
        "stderr_sha256": stderr_sha256,
        "stderr_truncated": stderr_truncated,
        "run": {
            "started_at": started_at,
            "ended_at": ended_at,
            "exit_code": worker_exit_code,
            "worker_exit_code": worker_exit_code,
            "supervisor_exit_code": supervisor_exit_code,
            "pid_store": args.pid_store,
        },
        "child_identity": execute_child_identity(args),
    }


def execute_identity_payload(args: argparse.Namespace, *, status: str,
                             cleanup_confirmed: bool) -> dict:
    child_identity = execute_child_identity(args)
    return {
        "schema": "call-omp-execute-identity.v1",
        "capture_mode": "execute_v1",
        "task_id": args.task_id,
        "attempt_id": args.attempt_id,
        "launch_fingerprint": args.launch_fingerprint,
        "state_file": args.state_file,
        "raw_output": args.raw_output,
        "control_file": args.control_file,
        "pid_store": args.pid_store,
        "status": status,
        "cleanup_confirmed": cleanup_confirmed,
        "process_identity_guard": "unreaped_leader_until_last_group_signal",
        # Keep the legacy top-level identity shape for authenticated readers
        # while also publishing the explicit v1 nested identity.
        "pid": child_identity["pid"],
        "pgid": child_identity["pgid"],
        "session_id": child_identity["session_id"],
        "supervisor_pid": child_identity["supervisor_pid"],
        "child_identity": child_identity,
    }


def execute_child_exited_unreaped(child: subprocess.Popen) -> bool:
    """Observe leader exit without releasing its PID/process-group identity."""
    result = os.waitid(
        os.P_PID, child.pid,
        os.WEXITED | os.WNOHANG | os.WNOWAIT)
    return result is not None and getattr(result, "si_pid", 0) == child.pid


def execute_group_state(child_pid: int, child_pgid: int) -> str:
    """Return alive, gone, or unknown for the retained owned group."""
    if not own_pgid(child_pid, child_pgid):
        return "unknown"
    try:
        os.killpg(child_pgid, 0)
        return "alive"
    except ProcessLookupError:
        return "gone"
    except OSError:
        return "unknown"


def cleanup_execute_group(child: subprocess.Popen, child_pid: int,
                          child_pgid: int, *, grace: float) -> tuple[bool, bool]:
    """Stop and verify only the group created by this live Popen owner."""
    group_state = execute_group_state(child_pid, child_pgid)
    if child.returncode is not None or not own_pgid(child_pid, child_pgid):
        # A retained, unreaped Popen authenticates its direct child. Stop only
        # that child when the group identity is mismatched; never signal an
        # unknown group. A non-None returncode means somebody already reaped
        # the leader, so the numeric PGID is no longer safe for signalling.
        if child.returncode is None:
            try:
                child.terminate()
                child.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                try:
                    child.kill()
                    child.wait(timeout=max(1.0, grace))
                except (OSError, subprocess.TimeoutExpired):
                    pass
            except OSError:
                pass
        return False, child.returncode is not None
    if group_state != "gone":
        try:
            os.killpg(child_pgid, signal.SIGTERM)
        except ProcessLookupError:
            group_state = "gone"
        except OSError:
            group_state = "unknown"
        deadline = time.monotonic() + grace
        while group_state != "gone" and time.monotonic() < deadline:
            time.sleep(0.025)
            group_state = execute_group_state(child_pid, child_pgid)
        if group_state != "gone":
            try:
                os.killpg(child_pgid, signal.SIGKILL)
            except ProcessLookupError:
                group_state = "gone"
            except OSError:
                group_state = "unknown"

    try:
        child.wait(timeout=max(1.0, grace + 0.5))
    except subprocess.TimeoutExpired:
        pass
    child_reaped = child.returncode is not None

    # No group signal occurs after child.wait(): reaping releases the numeric
    # identity, so the remaining killpg(..., 0) calls are observation-only. A
    # coincidental reuse can make cleanup conservatively false but cannot cause
    # this supervisor to signal the replacement group.
    verify_deadline = time.monotonic() + max(1.0, grace)
    while time.monotonic() < verify_deadline:
        group_state = execute_group_state(child_pid, child_pgid)
        if group_state == "gone":
            break
        time.sleep(0.025)
    return group_state == "gone", child_reaped

def emergency_cleanup_execute(args: argparse.Namespace) -> None:
    """Bounded fail-safe for exceptions escaping execute_v1 after spawn."""
    child = getattr(args, "_execute_child", None)
    if child is None or child.returncode is not None:
        return
    child_pgid = getattr(args, "recorded_pgid", None)
    if not isinstance(child_pgid, int):
        # The unreaped Popen identity prevents PID reuse; start_new_session
        # establishes PID == PGID before exec even if observation raised.
        child_pgid = child.pid
    try:
        cleanup_execute_group(
            child, child.pid, child_pgid, grace=args.grace_seconds)
    except Exception as exc:
        # Never convert an unverified emergency cleanup into a clean receipt.
        print(f"supervisor: emergency cleanup failed: {type(exc).__name__}",
              file=sys.stderr)


def run_execute_capture(args: argparse.Namespace, argv: list,
                        started_at: str) -> int:
    """execute_v1: bounded raw pipes plus authenticated owned-group control."""
    args.stderr_output = args.raw_output + ".err"
    args.recorded_pid = None
    args.recorded_pgid = None
    args.recorded_sid = None
    args.identity_observed = False
    args._execute_child = None

    stdout_bytes = 0
    stdout_lines = 0
    stdout_hash = hashlib.sha256()
    stderr_bytes = 0
    stderr_lines = 0
    stderr_hash = hashlib.sha256()
    stdout_truncated = False
    stderr_truncated = False
    escaped_evidence = False
    child = None
    stdout_fh = None
    stderr_fh = None
    started_mono = time.monotonic()
    signal_seen = {"number": None}
    termination_signals = {signal.SIGTERM, signal.SIGINT}
    if hasattr(signal, "SIGHUP"):
        termination_signals.add(signal.SIGHUP)

    def on_signal(signum, _frame) -> None:
        signal_seen["number"] = signum

    for signum in termination_signals:
        signal.signal(signum, on_signal)

    def receipt(status: str, worker_rc: int | None, supervisor_rc: int | None,
                terminal_reason: str, cleanup: bool,
                ended_at: str | None = None) -> dict:
        return execute_receipt(
            args, status=status, started_at=started_at, ended_at=ended_at,
            worker_exit_code=worker_rc, supervisor_exit_code=supervisor_rc,
            terminal_reason=terminal_reason, cleanup_confirmed=cleanup,
            stdout_bytes=stdout_bytes, stdout_lines=stdout_lines,
            stdout_sha256=stdout_hash.hexdigest() if stdout_bytes else "",
            stderr_bytes=stderr_bytes, stderr_lines=stderr_lines,
            stderr_sha256=stderr_hash.hexdigest() if stderr_bytes else "",
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            escaped_evidence=escaped_evidence)

    def publish_terminal_without_child(reason: str, supervisor_rc: int) -> int:
        payload = receipt("rejected", None, supervisor_rc, reason, True,
                          now_iso())
        try:
            atomic_write_private_json(
                args.pid_store,
                execute_identity_payload(args, status="rejected",
                                         cleanup_confirmed=True))
        except (OSError, ExecuteControlError):
            pass
        try:
            atomic_write_private_json(args.state_file, payload)
        except (OSError, ExecuteControlError) as exc:
            print(f"supervisor: terminal receipt write failed: {type(exc).__name__}",
                  file=sys.stderr)
            return 3
        return supervisor_rc

    starting = receipt("starting", None, None, "starting", False)
    try:
        atomic_write_private_json(args.state_file, starting)
        atomic_write_private_json(
            args.pid_store,
            execute_identity_payload(args, status="starting",
                                     cleanup_confirmed=False))
    except (OSError, ExecuteControlError) as exc:
        return publish_terminal_without_child(
            f"identity_starting_publish_failed:{type(exc).__name__}", 3)

    waitid_api = ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")
    signal_fence_api = ("pthread_sigmask", "sigpending", "SIG_BLOCK")
    if (not all(hasattr(os, name) for name in waitid_api)
            or not all(hasattr(signal, name) for name in signal_fence_api)):
        return publish_terminal_without_child(
            "unreaped_exit_or_signal_fence_unsupported", 3)

    try:
        pre_cancel = read_execute_cancel(args)
    except ExecuteControlError as exc:
        return publish_terminal_without_child(
            f"control_invalid:{exc}", 3)
    if pre_cancel is not None:
        return publish_terminal_without_child(f"cancelled:{pre_cancel}", 2)
    if signal_seen["number"] is not None:
        return publish_terminal_without_child(
            f"supervisor_signal:{signal_seen['number']}", 2)

    try:
        stdout_fh = open_private_output(args.raw_output)
        stderr_fh = open_private_output(args.stderr_output)
    except (OSError, ExecuteControlError) as exc:
        for fh in (stdout_fh, stderr_fh):
            if fh is not None:
                fh.close()
        return publish_terminal_without_child(
            f"capture_open_failed:{type(exc).__name__}", 3)

    depth_text = os.environ.get("CALL_OMP_DEPTH", "0")
    if (not depth_text.isdigit() or len(depth_text) > 9):
        stdout_fh.close()
        stderr_fh.close()
        return publish_terminal_without_child("invalid_call_omp_depth", 3)
    child_env = os.environ.copy()
    child_env["CALL_OMP_DEPTH"] = str(int(depth_text) + 1)

    try:
        child = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True, env=child_env,
            bufsize=0)
    except (FileNotFoundError, PermissionError, OSError,
            subprocess.SubprocessError) as exc:
        stdout_fh.close()
        stderr_fh.close()
        return publish_terminal_without_child(
            f"exec_failed:{type(exc).__name__}", 3)
    args._execute_child = child

    args.recorded_pid = child.pid
    try:
        observed_pgid = os.getpgid(child.pid)
        observed_sid = os.getsid(child.pid)
        args.recorded_pgid = observed_pgid
        args.recorded_sid = observed_sid
        args.identity_observed = (
            observed_pgid == child.pid and observed_sid == child.pid)
    except ProcessLookupError:
        # start_new_session establishes both identities before exec. A child
        # may finish before observation; retain the construction identity but
        # record that it was not observed live.
        args.recorded_pgid = child.pid
        args.recorded_sid = child.pid
        args.identity_observed = False
    except OSError:
        args.recorded_pgid = child.pid
        args.recorded_sid = child.pid
        args.identity_observed = False

    trigger = None
    internal_failure = False
    if (args.recorded_pgid != child.pid
            or args.recorded_sid != child.pid):
        trigger = "child_identity_mismatch"
        internal_failure = True

    try:
        atomic_write_private_json(
            args.pid_store,
            execute_identity_payload(args, status="running",
                                     cleanup_confirmed=False))
        atomic_write_private_json(
            args.state_file,
            receipt("running", None, None, "running", False))
    except (OSError, ExecuteControlError) as exc:
        trigger = f"identity_publish_failed:{type(exc).__name__}"
        internal_failure = True

    active: dict[int, str] = {}
    try:
        if child.stdout is not None:
            os.set_blocking(child.stdout.fileno(), False)
            active[child.stdout.fileno()] = "stdout"
        if child.stderr is not None:
            os.set_blocking(child.stderr.fileno(), False)
            active[child.stderr.fileno()] = "stderr"
    except OSError as exc:
        if trigger is None:
            trigger = f"capture_nonblocking_failed:{exc.errno or -1}"
            internal_failure = True

    def consume_ready(timeout: float) -> str | None:
        nonlocal stdout_bytes, stdout_lines, stderr_bytes, stderr_lines
        nonlocal stdout_truncated, stderr_truncated
        if not active:
            if timeout > 0:
                time.sleep(timeout)
            return None
        try:
            ready, _, _ = select.select(list(active), [], [], timeout)
        except (OSError, ValueError) as exc:
            return f"capture_select_failed:{type(exc).__name__}"
        for fd in ready:
            stream = active.get(fd)
            if stream is None:
                continue
            try:
                chunk = os.read(fd, READ_CHUNK)
            except BlockingIOError:
                continue
            except OSError as exc:
                return f"capture_read_failed:{exc.errno or -1}"
            if not chunk:
                active.pop(fd, None)
                continue
            if stream == "stdout":
                remaining = max(0, args.raw_cap - stdout_bytes)
                kept = chunk[:remaining]
                view = memoryview(kept)
                while view:
                    try:
                        written = os.write(stdout_fh.fileno(), view)
                    except OSError as exc:
                        return f"stdout_write_failed:{exc.errno or -1}"
                    if written <= 0:
                        return "stdout_write_failed:short"
                    persisted = view[:written]
                    stdout_bytes += written
                    stdout_lines += persisted.tobytes().count(b"\n")
                    stdout_hash.update(persisted)
                    view = view[written:]
                if len(kept) != len(chunk):
                    stdout_truncated = True
                    return "stdout_cap_exceeded"
            else:
                remaining = max(0, args.raw_cap - stderr_bytes)
                kept = chunk[:remaining]
                view = memoryview(kept)
                while view:
                    try:
                        written = os.write(stderr_fh.fileno(), view)
                    except OSError as exc:
                        return f"stderr_write_failed:{exc.errno or -1}"
                    if written <= 0:
                        return "stderr_write_failed:short"
                    persisted = view[:written]
                    stderr_bytes += written
                    stderr_lines += persisted.tobytes().count(b"\n")
                    stderr_hash.update(persisted)
                    view = view[written:]
                if len(kept) != len(chunk):
                    stderr_truncated = True
                    return "stderr_cap_exceeded"
        return None

    cancel_reason = None
    while trigger is None:
        try:
            cancel_reason = read_execute_cancel(args)
        except ExecuteControlError as exc:
            trigger = f"control_invalid:{exc}"
            internal_failure = True
            break
        if cancel_reason is not None:
            trigger = f"cancelled:{cancel_reason}"
            break
        if signal_seen["number"] is not None:
            trigger = f"supervisor_signal:{signal_seen['number']}"
            break
        if time.monotonic() - started_mono >= args.max_seconds:
            trigger = "deadline_exceeded"
            break
        try:
            leader_exited = execute_child_exited_unreaped(child)
        except (ChildProcessError, OSError) as exc:
            trigger = f"child_exit_observation_failed:{type(exc).__name__}"
            internal_failure = True
            break
        if leader_exited:
            trigger = "worker_exited"
            break
        capture_error = consume_ready(0.05)
        if capture_error is not None:
            trigger = capture_error
            internal_failure = not capture_error.endswith("_cap_exceeded")
            break

    group_gone, child_reaped = cleanup_execute_group(
        child, args.recorded_pid, args.recorded_pgid,
        grace=args.grace_seconds)

    # Drain data already committed to the pipes after group cleanup. If a pipe
    # remains open after the observed group is gone, an escaped descendant is
    # evidenced; it is not safe to claim cleanup.
    drain_deadline = time.monotonic() + max(0.5, args.grace_seconds)
    while active and time.monotonic() < drain_deadline:
        capture_error = consume_ready(0.05)
        if capture_error is not None:
            if capture_error == "stdout_cap_exceeded":
                stdout_truncated = True
                if trigger == "worker_exited":
                    trigger = capture_error
            elif capture_error == "stderr_cap_exceeded":
                stderr_truncated = True
                if trigger == "worker_exited":
                    trigger = capture_error
            elif trigger == "worker_exited":
                trigger = capture_error
                internal_failure = True
    if active and group_gone:
        escaped_evidence = True
    for pipe in (child.stdout, child.stderr):
        if pipe is not None:
            try:
                pipe.close()
            except OSError:
                pass

    try:
        child.wait(timeout=0)
    except subprocess.TimeoutExpired:
        pass
    worker_rc = child.returncode

    for fh in (stdout_fh, stderr_fh):
        try:
            fh.flush()
            os.fsync(fh.fileno())
            fh.close()
        except OSError:
            if trigger == "worker_exited":
                trigger = "capture_finalize_failed"
                internal_failure = True

    # Terminal-decision linearization: after owned cleanup, block all handled
    # termination signals and include signals delivered or already pending at
    # the cutoff. The mask intentionally remains in force through process exit.
    # Signals arriving after this completed cutoff do not undo an already-clean
    # decision; this does not claim that every pre-receipt signal wins.
    pending_signals: set[int] = set()
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, termination_signals)
        pending_signals = set(signal.sigpending()).intersection(
            termination_signals)
    except (OSError, ValueError) as exc:
        trigger = f"terminal_signal_fence_failed:{type(exc).__name__}"
        internal_failure = True

    terminal_signal = signal_seen["number"]
    if terminal_signal is None and pending_signals:
        terminal_signal = min(pending_signals)
    if terminal_signal is not None and cancel_reason is None:
        trigger = f"supervisor_signal:{terminal_signal}"

    # The final authenticated control observation is the second half of the
    # terminal-decision cutoff. Later stop requests are resolved by the public
    # cancel_requested/identity fence rather than rewriting this receipt.
    try:
        final_cancel = read_execute_cancel(args)
    except ExecuteControlError as exc:
        final_cancel = None
        if cancel_reason is None:
            trigger = f"control_invalid:{exc}"
            internal_failure = True
    if final_cancel is not None:
        cancel_reason = final_cancel
        trigger = f"cancelled:{final_cancel}"

    cleanup_confirmed = (
        group_gone and child_reaped and not escaped_evidence)
    if not cleanup_confirmed:
        trigger = f"{trigger};containment_unknown"

    if trigger == "worker_exited" and worker_rc == 0 and cleanup_confirmed:
        status = "reported"
        supervisor_rc = 0
        terminal_reason = "normal_completion"
    else:
        status = "rejected"
        terminal_reason = trigger
        if internal_failure:
            supervisor_rc = 3
        elif trigger == "worker_exited":
            supervisor_rc = 4
            terminal_reason = (
                "worker_exit_nonzero" if worker_rc is not None
                else "worker_exit_unknown")
        elif not cleanup_confirmed:
            supervisor_rc = 4
        else:
            supervisor_rc = 2

    ended_at = now_iso()
    terminal_identity = execute_identity_payload(
        args, status=status, cleanup_confirmed=cleanup_confirmed)
    try:
        atomic_write_private_json(args.pid_store, terminal_identity)
    except (OSError, ExecuteControlError) as exc:
        status = "rejected"
        supervisor_rc = 3
        terminal_reason = (
            f"{terminal_reason};identity_terminal_publish_failed:"
            f"{type(exc).__name__}")

    terminal_receipt = receipt(
        status, worker_rc, supervisor_rc, terminal_reason,
        cleanup_confirmed, ended_at)
    try:
        atomic_write_private_json(args.state_file, terminal_receipt)
    except (OSError, ExecuteControlError) as exc:
        # The identity was published first so a failed receipt cannot leave a
        # durable successful identity. Preserve the real cleanup result while
        # marking publication failure; never synthesize cleanup success.
        try:
            atomic_write_private_json(
                args.pid_store,
                execute_identity_payload(
                    args, status="rejected",
                    cleanup_confirmed=cleanup_confirmed))
        except (OSError, ExecuteControlError):
            pass
        print(f"supervisor: terminal receipt write failed: {type(exc).__name__}",
              file=sys.stderr)
        return 3
    return supervisor_rc


def main() -> int:
    p = argparse.ArgumentParser(prog="omp-resource-supervisor.py",
                                description="call-omp P0A resource supervisor")
    p.add_argument("--state-file", required=True)
    p.add_argument("--raw-output", required=True)
    p.add_argument("--raw-cap", type=int, default=DEFAULT_RAW_CAP)
    p.add_argument("--pid-store", required=True)
    p.add_argument("--task-id", required=True)
    p.add_argument("--task-id-source", default="unknown")
    p.add_argument("--tail-cap", type=int, default=TAIL_CAP)
    # Optional rate fuse: sliding window bytes/sec; disabled by default.
    p.add_argument("--rate-window-bytes", type=int, default=0,
                   help="Window size in bytes; 0 disables the rate fuse")
    p.add_argument("--rate-window-seconds", type=float, default=1.0)
    p.add_argument("--rate-fuse-windows", type=int, default=3,
                   help="Trigger kill only after N consecutive windows exceed the cap")
    p.add_argument("--grace-seconds", type=float, default=1.0,
                   help="TERM→KILL grace period before escalating to KILL")
    p.add_argument("--expected-pgid", type=int, default=None,
                   help="If set, supervisor refuses to terminate any group not equal to this")
    # Additive capture modes. execute_v1 deliberately bypasses the legacy
    # RLIMIT_FSIZE path and owns bounded stdout/stderr pipes itself.
    p.add_argument("--capture-mode",
                   choices=["legacy", "verdict_v1", "execute_v1"],
                   default="legacy",
                   help="legacy（默认）/ verdict_v1 / execute_v1")
    p.add_argument("--ingress-cap", type=int, default=DEFAULT_INGRESS_CAP,
                   help="verdict_v1：从 stdout 管道实际读入的物理字节上限（默认 128 MiB）")
    p.add_argument("--verdict-cap", type=int, default=DEFAULT_VERDICT_CAP,
                   help="verdict_v1：规范 verdict raw 落盘上限（默认 1 MiB）")
    p.add_argument("--diagnostic-cap", type=int, default=DEFAULT_DIAGNOSTIC_CAP,
                   help="verdict_v1：.diag.jsonl 落盘上限（默认 512 KiB；触顶只截断）")
    p.add_argument("--classifier-module", default=None,
                   help="test-only：从此路径加载 classify_jsonl_line（生产接线绝不传）")
    p.add_argument("--attempt-id", default=None,
                   help="execute_v1：不可复用的 UUID attempt identity")
    p.add_argument("--launch-fingerprint", default=None,
                   help="execute_v1：64 位 SHA-256 launch fingerprint")
    p.add_argument("--control-file", default=None,
                   help="execute_v1：私有原子 cancel request 路径")
    p.add_argument("--max-seconds", type=float, default=None,
                   help="execute_v1：监督器自持的正数硬截止时间")
    # The child command is everything after `--` (or after a literal `--`
    # token if `argparse` did not consume it via the nargs handling below).
    p.add_argument("child_argv", nargs=argparse.REMAINDER,
                   help="Command to run, after `--`. Example: -- /bin/cmd arg1")
    args = p.parse_args()
    argv = list(args.child_argv)
    # argparse's REMAINDER includes the literal `--` token as the first element.
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        argv = []

    if args.raw_cap <= 0:
        print("supervisor: --raw-cap must be positive", file=sys.stderr)
        return 3
    if not argv:
        print("supervisor: missing child command after `--`", file=sys.stderr)
        return 3

    capture = args.capture_mode == "verdict_v1"
    execute_capture = args.capture_mode == "execute_v1"
    if capture:
        # 正的、带默认值的上限校验；仅 verdict_v1 生效。diagnostic 路径固定派生自
        # raw_output，无 override flag 可注入（契约要求拒绝任何 override）。
        for name, val in (("--ingress-cap", args.ingress_cap),
                          ("--verdict-cap", args.verdict_cap),
                          ("--diagnostic-cap", args.diagnostic_cap)):
            if val <= 0:
                print(f"supervisor: {name} must be positive", file=sys.stderr)
                return 3
        if args.max_seconds is not None and (not math.isfinite(args.max_seconds)
                                             or args.max_seconds <= 0):
            print("supervisor: verdict_v1 --max-seconds must be positive", file=sys.stderr)
            return 3
        args.diagnostic_output = args.raw_output + ".diag.jsonl"
    if execute_capture:
        try:
            parsed_attempt = uuid.UUID(args.attempt_id or "")
        except (ValueError, AttributeError):
            print("supervisor: execute_v1 --attempt-id must be a UUID",
                  file=sys.stderr)
            return 3
        args.attempt_id = str(parsed_attempt)
        fingerprint = (args.launch_fingerprint or "").lower()
        if (len(fingerprint) != 64
                or any(ch not in "0123456789abcdef" for ch in fingerprint)):
            print("supervisor: execute_v1 --launch-fingerprint must be SHA-256",
                  file=sys.stderr)
            return 3
        args.launch_fingerprint = fingerprint
        if (args.max_seconds is None or not math.isfinite(args.max_seconds)
                or args.max_seconds <= 0):
            print("supervisor: execute_v1 --max-seconds must be positive",
                  file=sys.stderr)
            return 3
        if (not math.isfinite(args.grace_seconds)
                or args.grace_seconds <= 0):
            print("supervisor: execute_v1 --grace-seconds must be positive",
                  file=sys.stderr)
            return 3
        if not args.control_file or not os.path.isabs(args.control_file):
            print("supervisor: execute_v1 --control-file must be absolute",
                  file=sys.stderr)
            return 3
        protected = [
            args.state_file, args.pid_store, args.raw_output,
            args.raw_output + ".err", args.control_file,
        ]
        if len(set(map(os.path.realpath, protected))) != len(protected):
            print("supervisor: execute_v1 paths must be distinct",
                  file=sys.stderr)
            return 3

    args.argv = list(argv)
    started_at = now_iso()
    os.makedirs(os.path.dirname(args.state_file) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.pid_store) or ".", exist_ok=True)

    if execute_capture:
        os.makedirs(os.path.dirname(args.raw_output) or ".", exist_ok=True)
        try:
            return run_execute_capture(args, argv, started_at)
        finally:
            # This is the outermost post-spawn safety net. Any unexpected
            # exception, including a publication bug, still gets a bounded
            # attempt to stop/reap the retained owned child and group.
            emergency_cleanup_execute(args)

    cap0 = zero_capture(args) if capture else None

    # Seed initial state so monitor can always read identity before exec.
    initial = build_state_payload(args, status="starting", exit_code=None,
                                  started_at=started_at, ended_at=started_at,
                                  raw_bytes=0, raw_lines=0, digest="",
                                  tail_bytes=0, reason="init",
                                  rate_fuse={
                                      "enabled": args.rate_window_bytes > 0,
                                      "window_bytes": args.rate_window_bytes,
                                      "window_seconds": args.rate_window_seconds,
                                      "fuse_windows": args.rate_fuse_windows,
                                  },
                                  capture=cap0)
    initial["child_identity"]["pid"] = None
    initial["child_identity"]["pgid"] = None
    atomic_write_json(args.state_file, initial)

    # Fail closed: without RLIMIT_FSIZE the hard, kernel-level raw cap that
    # survives setsid escape is impossible. Refuse to run rather than pretend.
    if _resource is None:
        atomic_write_json(args.state_file, build_state_payload(
            args, status="rejected", exit_code=None, started_at=started_at,
            ended_at=now_iso(), raw_bytes=0, raw_lines=0, digest="",
            tail_bytes=0, reason=f"hard_cap_unsupported:{sys.platform}",
            rate_fuse=None, capture=cap0))
        return 3

    if capture:
        try:
            classify = load_classifier(args.classifier_module)
        except Exception as exc:
            atomic_write_json(args.state_file, build_state_payload(
                args, status="rejected", exit_code=None, started_at=started_at,
                ended_at=now_iso(), raw_bytes=0, raw_lines=0, digest="",
                tail_bytes=0, reason=f"classifier_load_failed:{type(exc).__name__}",
                rate_fuse=None, capture=cap0))
            return 3
        return run_verdict_capture(args, argv, started_at, classify)

    try:
        raw_fh = open(args.raw_output, "wb", buffering=0)
    except OSError as exc:
        atomic_write_json(args.state_file, build_state_payload(
            args, status="rejected", exit_code=None, started_at=started_at,
            ended_at=now_iso(), raw_bytes=0, raw_lines=0, digest="",
            tail_bytes=0, reason=f"raw_open_failed:{exc.errno or -1}",
            rate_fuse=None))
        return 3

    try:
        # preexec_fn installs the kernel hard cap in the child BEFORE exec; a
        # failure there raises SubprocessError in the parent → fail closed.
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                 stdout=raw_fh, stderr=subprocess.PIPE,
                                 start_new_session=True,
                                 preexec_fn=child_rlimit_preexec(args.raw_cap))
    except (FileNotFoundError, PermissionError, OSError,
            subprocess.SubprocessError) as exc:
        try:
            raw_fh.close()
        except OSError:
            pass
        atomic_write_json(args.state_file, build_state_payload(
            args, status="rejected", exit_code=None, started_at=started_at,
            ended_at=now_iso(), raw_bytes=0, raw_lines=0, digest="",
            tail_bytes=0, reason=f"exec_failed:{type(exc).__name__}",
            rate_fuse=None))
        return 3

    args.recorded_pid = child.pid
    try:
        args.recorded_pgid = os.getpgid(child.pid)
    except OSError:
        args.recorded_pgid = os.getpgrp()
    try:
        args.recorded_sid = os.getsid(child.pid)
    except OSError:
        args.recorded_sid = args.recorded_pgid

    with open(args.pid_store, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "pid": args.recorded_pid,
            "pgid": args.recorded_pgid,
            "session_id": args.recorded_sid,
            "argv": list(argv),
            "expected_pgid": args.expected_pgid,
        }, sort_keys=True))

    rate_fuse_state = {
        "enabled": args.rate_window_bytes > 0,
        "window_bytes": args.rate_window_bytes,
        "window_seconds": args.rate_window_seconds,
        "fuse_windows": args.rate_fuse_windows,
        "consecutive_over": 0,
    }
    ring = []  # list[(ts, byte_delta)]
    total = 0
    digest = hashlib.sha256()
    raw_lines = 0
    last_newline_at = 0
    reason = ""
    rate_recent_over = False
    rate_recent = False
    raw_fh_closed = False

    # The supervisor controls lifecycle via waitpid only — it never touches
    # raw bytes; the kernel pipes the child's stdout to raw_fh.
    rc = None
    resource_status = None
    fuse_deadline = None
    while True:
        try:
            rc = child.wait(timeout=0.1)
            break
        except subprocess.TimeoutExpired:
            try:
                cur = os.fstat(raw_fh.fileno()).st_size
            except OSError:
                cur = total
            delta = cur - total
            if delta < 0:
                delta = 0
            total = cur
            digest = hashlib.sha256()  # rehash from disk; cheap for tests
            try:
                with open(args.raw_output, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        digest.update(chunk)
            except FileNotFoundError:
                pass

            if total >= args.raw_cap:
                resource_status = "raw_cap"
                reason = f"raw_cap_exceeded:{total}>{args.raw_cap}"
                # Trip the resource fuse via the shared shutdown path: stop the
                # child process group FIRST (so its stdout pipe drains and
                # closes), reap it, then truncate the on-disk file to exactly
                # raw_cap. This guarantees the file never exceeds the cap
                # regardless of bytes already buffered in the kernel pipe.
                rc = resource_trip_shutdown(child, args.recorded_pgid,
                                            args.recorded_pid,
                                            grace=args.grace_seconds)
                # Close the supervisor's read end of the pipe.
                try:
                    raw_fh.close()
                except OSError:
                    pass
                raw_fh = None
                raw_fh_closed = True
                # Truncate to raw_cap. The file size on disk at this point
                # reflects everything the kernel had buffered; cap it now.
                try:
                    with open(args.raw_output, "r+b") as fh:
                        fh.truncate(args.raw_cap)
                        fh.flush()
                        os.fsync(fh.fileno())
                except OSError:
                    pass
                break

            if rate_fuse_state["enabled"]:
                now = time.time()
                ring.append((now, delta))
                cutoff = now - rate_fuse_state["window_seconds"]
                while ring and ring[0][0] < cutoff:
                    ring.pop(0)
                window_bytes = sum(d for _, d in ring)
                if window_bytes >= rate_fuse_state["window_bytes"]:
                    rate_fuse_state["consecutive_over"] += 1
                else:
                    rate_fuse_state["consecutive_over"] = 0
                if rate_fuse_state["consecutive_over"] >= rate_fuse_state["fuse_windows"]:
                    resource_status = "rate_fuse"
                    reason = (f"rate_fuse:{window_bytes}B/"
                              f"{rate_fuse_state['window_bytes']}B "
                              f"over {rate_fuse_state['fuse_windows']} windows")
                    # Containment: the rate fuse MUST tear the child down on the
                    # same safe path as raw_cap. Previously this branch only set
                    # the status and broke, so it could report resource_rejected
                    # while the child was still alive and writing. No raw_cap
                    # truncation here — rate-fuse trips while raw_bytes < raw_cap,
                    # so truncate(raw_cap) would wrongly *extend* the file.
                    rc = resource_trip_shutdown(child, args.recorded_pgid,
                                                args.recorded_pid,
                                                grace=args.grace_seconds)
                    try:
                        raw_fh.close()
                    except OSError:
                        pass
                    raw_fh = None
                    raw_fh_closed = True
                    break

    # ── Finalize: close our end, then make the ON-DISK file authoritative ──
    # Close first so no supervisor-side write is in flight while we truncate
    # and re-stat. From here on, every reported field is derived from the file
    # that actually persisted after all control actions.
    if raw_fh is not None:
        try:
            raw_fh.flush()
            raw_fh.close()
        except OSError:
            pass
        raw_fh = None

    # Observe the actual persisted size BEFORE any defensive action.
    try:
        pre_size = os.stat(args.raw_output).st_size
    except FileNotFoundError:
        pre_size = 0

    # Defensive hard-cap guard behind the kernel RLIMIT_FSIZE: if anything —
    # including an escaped setsid descendant that briefly held the fd — left
    # the file above raw_cap, shrink it back to exactly raw_cap. CONDITIONAL on
    # strictly-greater so the rate fuse (which trips while the file is BELOW
    # cap) can never expand a smaller file.
    over_cap = pre_size > args.raw_cap
    if over_cap:
        try:
            with open(args.raw_output, "r+b") as fh:
                fh.truncate(args.raw_cap)
                fh.flush()
                os.fsync(fh.fileno())
        except OSError:
            pass

    # Re-sample the final, authoritative size AFTER all control actions.
    try:
        total = os.stat(args.raw_output).st_size
    except FileNotFoundError:
        total = 0

    # Natural-exit-over/at-cap detection (child self-exited at/over the cap).
    if resource_status is None and total >= args.raw_cap:
        resource_status = "raw_cap"
        reason = f"raw_cap_exceeded:{total}>{args.raw_cap}"
    elif resource_status is not None and resource_status != "raw_cap" and over_cap:
        # A non-cap fuse (rate_fuse) fired first but the file was ALSO driven
        # over cap. Carry BOTH facts truthfully rather than hide the breach.
        reason = f"{reason}; raw_cap_exceeded:{pre_size}>{args.raw_cap}"

    if resource_status is not None:
        # We already attempted a clean TERM/KILL via terminate_owned_pg (gated
        # by own_pgid). Confirm the DIRECT child was reaped; if it was not, the
        # state must say so instead of implying clean containment.
        try:
            child.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass
        rc = child.returncode
        reason = containment_reason(reason, reaped=child.returncode is not None)

    ended_at = now_iso()
    # Re-hash the final on-disk file so the digest ALWAYS matches raw_bytes.
    final_digest = hashlib.sha256()
    raw_lines = 0
    try:
        with open(args.raw_output, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                final_digest.update(chunk)
                raw_lines += chunk.count(b"\n")
    except FileNotFoundError:
        pass

    try:
        tail = open(args.raw_output, "rb").read()[-args.tail_cap:]
        tail_bytes = len(tail)
    except FileNotFoundError:
        tail_bytes = 0

    if resource_status is not None:
        status = "resource_rejected"
        exit_code = rc if rc is not None else 124
        rate_fuse_final = rate_fuse_state if rate_fuse_state["enabled"] else None
        payload = build_state_payload(
            args, status=status, exit_code=exit_code,
            started_at=started_at, ended_at=ended_at,
            raw_bytes=total, raw_lines=raw_lines, digest=final_digest.hexdigest(),
            tail_bytes=tail_bytes, reason=reason,
            rate_fuse=rate_fuse_final)
        atomic_write_json(args.state_file, payload)
        return 2

    payload = build_state_payload(
        args, status="reported", exit_code=rc if rc is not None else 0,
        started_at=started_at, ended_at=ended_at,
        raw_bytes=total, raw_lines=raw_lines, digest=final_digest.hexdigest(),
        tail_bytes=tail_bytes, reason="normal_completion",
        rate_fuse=rate_fuse_state if rate_fuse_state["enabled"] else None)
    atomic_write_json(args.state_file, payload)

    return 0 if rc == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
