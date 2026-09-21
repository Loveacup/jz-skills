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
import os
import select
import signal
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
        nonlocal resource_status, reason
        resource_status = status
        reason = rsn
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
    while resource_status is None:
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
    # ── P2B S1B · opt-in verdict_v1 capture ──
    p.add_argument("--capture-mode", choices=["legacy", "verdict_v1"],
                   default="legacy",
                   help="legacy（默认）：stdout 直连 raw；verdict_v1：管道分帧+分类落规范 verdict")
    p.add_argument("--ingress-cap", type=int, default=DEFAULT_INGRESS_CAP,
                   help="verdict_v1：从 stdout 管道实际读入的物理字节上限（默认 128 MiB）")
    p.add_argument("--verdict-cap", type=int, default=DEFAULT_VERDICT_CAP,
                   help="verdict_v1：规范 verdict raw 落盘上限（默认 1 MiB）")
    p.add_argument("--diagnostic-cap", type=int, default=DEFAULT_DIAGNOSTIC_CAP,
                   help="verdict_v1：.diag.jsonl 落盘上限（默认 512 KiB；触顶只截断）")
    p.add_argument("--classifier-module", default=None,
                   help="test-only：从此路径加载 classify_jsonl_line（生产接线绝不传）")
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
    if capture:
        # 正的、带默认值的上限校验；仅 verdict_v1 生效。diagnostic 路径固定派生自
        # raw_output，无 override flag 可注入（契约要求拒绝任何 override）。
        for name, val in (("--ingress-cap", args.ingress_cap),
                          ("--verdict-cap", args.verdict_cap),
                          ("--diagnostic-cap", args.diagnostic_cap)):
            if val <= 0:
                print(f"supervisor: {name} must be positive", file=sys.stderr)
                return 3
        args.diagnostic_output = args.raw_output + ".diag.jsonl"

    args.argv = list(argv)
    started_at = now_iso()
    os.makedirs(os.path.dirname(args.state_file) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.pid_store) or ".", exist_ok=True)

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
