"""Conservative, receipt-backed cleanup plans."""
from __future__ import annotations

import datetime as dt
import fnmatch
import glob
import hashlib
import json
import os
import plistlib
import re
import errno
import stat
import fcntl
import ctypes
import subprocess
import time
from pathlib import Path

from . import paths

CATALOGUE = Path(__file__).with_name("targets.json")
PLAN_TTL = dt.timedelta(hours=1)
COMMAND_TIMEOUT = 15
# CAUTION (move-to-Trash) execution is off by design (decision 2026-10-04): macOS
# can only rename by directory fd + name, so the move cannot be bound to the
# approved inode (5 independent review rounds). CAUTION items are review-only;
# apply refuses them with a receipt and the user moves them in Finder.
CAUTION_APPLY_ENABLED = False


def _run(argv, *, timeout=COMMAND_TIMEOUT, **kwargs):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, **kwargs)


def load_targets():
    return json.loads(CATALOGUE.read_text())


def _home():
    return paths.account_home().expanduser().absolute()


def _render(template, extra=None):
    vals = {"home": str(_home())}
    vals.update(extra or {})
    try:
        return template.format(**vals)
    except (KeyError, ValueError):
        return template


def _excluded_paths(target):
    return {Path(_render(template)).absolute() for template in target.get("exclude_paths", [])}


def _path_candidates(target):
    candidates = []
    excluded = _excluded_paths(target)
    for template in target["paths"]:
        rendered = _render(template)
        matches = glob.glob(rendered) if "*" in rendered else [rendered]
        for candidate in matches:
            path = Path(candidate)
            if path.absolute() in excluded:
                continue
            try:
                path.stat()
            except FileNotFoundError:
                continue
            except OSError:
                # An unreadable declared path is not evidence that it is absent.
                pass
            candidates.append(path)
    return list(dict.fromkeys(candidates))


def _size(path, timeout=COMMAND_TIMEOUT, runner=None):
    try:
        result = (runner or _run)(["du", "-sk", str(path)], timeout=timeout)
        if result.returncode:
            return "unknown"
        return int(result.stdout.split()[0]) * 1024
    except (OSError, subprocess.TimeoutExpired, TimeoutError, ValueError, IndexError):
        return "unknown"


def _snapshot_report(runner, timeout):
    try:
        result = runner(["tmutil", "listlocalsnapshots", "/"], timeout=timeout)
        if result.returncode:
            raise OSError(result.stderr or "tmutil unavailable")
        dates = sorted(set(re.findall(r"(\d{4}-\d{2}-\d{2}-\d{6})", result.stdout)))
        return {"target": "tm-local-snapshot", "title": "Time Machine local snapshots",
                "class": "REPORT", "action": "report", "count": len(dates), "dates": dates,
                "estimated_purgeable_bytes": "unknown",
                "manual_commands": [f"tmutil deletelocalsnapshots {date}" for date in dates],
                "status": "ok"}
    except (OSError, subprocess.TimeoutExpired, TimeoutError) as exc:
        return {"target": "tm-local-snapshot", "title": "Time Machine local snapshots",
                "class": "REPORT", "action": "report", "count": "unknown", "dates": [],
                "estimated_purgeable_bytes": "unknown", "manual_commands": [],
                "status": f"unknown: {exc}"}


def _brew_report(target, runner, timeout):
    cache_path = None
    cache_size = "unknown"
    dry_run_output = ""
    try:
        resolved = runner(["brew", "--cache"], timeout=timeout)
        if resolved.returncode == 0 and resolved.stdout.strip():
            cache_path = str(Path(resolved.stdout.strip()).expanduser())
            cache_size = _size(Path(cache_path), timeout, runner)
    except (OSError, subprocess.TimeoutExpired, TimeoutError):
        pass
    try:
        result = runner(target["dry_run_cmd"], timeout=timeout)
        dry_run_output = (result.stdout or "") + (result.stderr or "")
        status = "ok" if result.returncode == 0 else f"unknown: brew cleanup dry-run exit {result.returncode}"
    except (OSError, subprocess.TimeoutExpired, TimeoutError) as exc:
        status = f"unknown: {exc}"
    item_count = sum(bool(re.match(r"\s*Would\s+(remove|delete|unlink)\b", line, re.IGNORECASE))
                     for line in dry_run_output.splitlines())
    units = {"b": 1, "byte": 1, "bytes": 1, "k": 1024, "kb": 1024, "kib": 1024,
             "m": 1024 ** 2, "mb": 1024 ** 2, "mib": 1024 ** 2,
             "g": 1024 ** 3, "gb": 1024 ** 3, "gib": 1024 ** 3,
             "t": 1024 ** 4, "tb": 1024 ** 4, "tib": 1024 ** 4}
    parsed_sizes = []
    for value, unit in re.findall(r"(?i)(\d+(?:\.\d+)?)\s*(bytes?|b|k|kb|kib|m|mb|mib|g|gb|gib|t|tb|tib)\b", dry_run_output):
        parsed_sizes.append(int(float(value) * units[unit.lower()]))
    return {"target": target["id"], "title": target["title"], "path": cache_path or "unknown",
            "size_bytes": cache_size, "class": "REPORT", "action": "report",
            "dry_run_command": list(target["dry_run_cmd"]), "dry_run_output": dry_run_output,
            "dry_run_item_count": item_count if dry_run_output else "unknown",
            "dry_run_size_bytes": sum(parsed_sizes) if parsed_sizes else "unknown",
            "manual_command": target["manual_command"], "status": status}


def scan(targets=None, *, timeout=COMMAND_TIMEOUT, runner=None):
    """Read-only size inventory; unreadable, timed-out sizes stay explicitly unknown."""
    chosen = targets if targets is not None else load_targets()
    run = runner or _run
    records = []
    for target in chosen:
        if target.get("class") == "NEVER":
            continue
        if target.get("class") == "REPORT":
            records.append(_snapshot_report(run, timeout) if target["id"] == "tm-local-snapshot"
                           else _brew_report(target, run, timeout) if target["id"] == "brew-cache" else {})
            continue
        for path in _path_candidates(target):
            try:
                st = path.lstat()
                age = max(0, (time.time() - st.st_mtime) / 86400)
                if age < target.get("min_age_days", 0):
                    continue
                size = _size(path, timeout, run)
                records.append({"target": target["id"], "title": target["title"], "path": str(path),
                                "size_bytes": size, "class": target["class"], "action": target["action"],
                                "mtime": st.st_mtime, "age_days": round(age, 1)})
            except FileNotFoundError:
                continue
            except OSError as exc:
                records.append({"target": target["id"], "title": target["title"], "path": str(path),
                                "size_bytes": "unknown", "class": target["class"], "action": target["action"],
                                "mtime": None, "age_days": "unknown", "status": f"unknown: {exc}"})
    return records

def _native_environment(target, scope):
    env = os.environ.copy()
    env["HOME"] = str(_home())
    for key, value in target.get("native_env", {}).items():
        env[key] = value.format(scope=scope)
    return env


def _effective_native_scope(target, scope, runner, timeout):
    command = target.get("resolve_cmd")
    if not command:
        return None, "native cache resolver is missing"
    try:
        result = runner(command, timeout=timeout, env=_native_environment(target, scope))
        if result.returncode:
            return None, result.stderr.strip() or "native cache resolver failed"
        observed = Path(result.stdout.strip()).expanduser().resolve(strict=False)
        expected = Path(scope).expanduser().resolve(strict=False)
        if observed != expected:
            return None, f"native cache path mismatch: resolved {observed}, expected {expected}"
        return str(expected), ""
    except (OSError, subprocess.TimeoutExpired, TimeoutError, ValueError) as exc:
        return None, f"native cache resolver failed: {exc}"


def _native_argv(target, scope):
    return [arg.format(scope=scope) for arg in target["native_cmd"]]


def _native_action_env(target, scope):
    return _native_environment(target, scope)


def _roots(target):
    return [Path(_render(template)).absolute() for template in target["paths"]]


def _pattern_matches(path, pattern):
    path_parts = Path(path).parts
    pattern_parts = pattern.parts
    return len(path_parts) == len(pattern_parts) and all(
        fnmatch.fnmatchcase(actual, expected) for actual, expected in zip(path_parts, pattern_parts))


def _under(path, roots, excluded=()):
    try:
        lexical = Path(path).absolute()
        real = Path(path).resolve(strict=True)
    except OSError:
        return False
    return (real == lexical and lexical not in excluded
            and any(_pattern_matches(lexical, root) for root in roots))


def _hard_denied(path):
    try:
        p = Path(path).resolve(strict=True)
        home = _home().resolve(strict=False)
    except OSError:
        return True
    denied = [(Path("/"), False), (home, False), (Path("/System"), True), (Path("/Library"), True),
              (Path("/Applications"), True), (home / "Library", False),
              (home / "Documents", True), (home / "Desktop", True),
              (home / "Library/Mobile Documents", True), (home / "Library/Keychains", True)]
    for d, deny_descendants in denied:
        try:
            dr = d.resolve(strict=False)
            if p == dr or (deny_descendants and dr in p.parents):
                return True
        except OSError:
            return True
    protected = [home / ".cache/huggingface", home / ".cache/qmd", home / "Library/Containers",
                 home / "Library/Group Containers", home / "Library/Application Support/MobileSync/Backup",
                 home / ".docker/volumes", home / "Library/Mail", home / "Pictures/Photos Library.photoslibrary"]
    for d in protected:
        dr = d.resolve(strict=False)
        if p == dr or dr in p.parents:
            return True
    return False


def _plan_path(plan_id):
    if not plan_id or Path(plan_id).name != plan_id or not all(c.isalnum() or c in "-_" for c in plan_id):
        raise ValueError("invalid plan id")
    return paths.plans_dir() / f"{plan_id}.json"


def make_plan(target_ids=None, *, include_caution=False, runner=None):
    targets = load_targets()
    allowed = {t["id"]: t for t in targets if t["class"] in {"SAFE", "CAUTION"}}
    selected = set(target_ids) if target_ids is not None else set(allowed)
    unknown = selected - allowed.keys()
    if unknown:
        raise ValueError("unknown or report-only target id: " + ", ".join(sorted(unknown)))
    chosen = [t for t in targets if t["id"] in selected
              and (t["class"] == "SAFE" or (include_caution and t["class"] == "CAUTION"))]
    run = runner or _run
    raw = scan(chosen, runner=run)
    items = []
    by_id = {t["id"]: t for t in chosen}
    for record in raw:
        p = Path(record["path"])
        try:
            st = p.lstat()
        except OSError:
            continue
        t = by_id[record["target"]]
        native_scope = None
        if t["action"] == "native":
            native_scope_template = t.get("scope_path")
            if not native_scope_template:
                raise ValueError(f"{t['id']} has no declared native scope")
            expected_scope = _render(native_scope_template)
            native_scope, error = _effective_native_scope(t, expected_scope, run, COMMAND_TIMEOUT)
            if native_scope is None:
                raise ValueError(f"{t['id']} native scope refused: {error}")
        file_type = ("directory" if stat.S_ISDIR(st.st_mode) else
                     "file" if stat.S_ISREG(st.st_mode) else "other")
        items.append({"target": t["id"], "path": str(p), "size_bytes": record["size_bytes"],
                      "dev": st.st_dev, "inode": st.st_ino, "mtime": st.st_mtime,
                      "file_type": file_type,
                      "class": t["class"], "action": t["action"], "native_cmd": t.get("native_cmd"),
                      "native_env": t.get("native_env", {}), "native_scope": native_scope,
                      "inuse_check": t["inuse_check"], "min_age_days": t.get("min_age_days", 0),
                      "rebuildable": t["rebuildable"]})
    created = dt.datetime.now(dt.timezone.utc)
    expires = created + PLAN_TTL
    seed = json.dumps([(i["target"], i["path"], i["dev"], i["inode"], i["mtime"]) for i in items], sort_keys=True)
    plan_id = created.strftime("%Y%m%dT%H%M%SZ") + "-" + hashlib.sha256(seed.encode()).hexdigest()[:10]
    plan = {"plan_id": plan_id, "host": os.uname().nodename, "created_at": created.isoformat(),
            "expires_at": expires.isoformat(), "items": items}
    dest = _plan_path(plan_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    base = plan_id
    suffix = 0
    while True:
        try:
            with dest.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(plan, indent=2) + "\n")
            break
        except FileExistsError:
            suffix += 1
            plan_id = f"{base}-{suffix}"
            plan["plan_id"] = plan_id
            dest = _plan_path(plan_id)
    return plan


def _receipt(item, plan_id, action, method, result, reason, size, phase="outcome", trash_path=None,
             **extra):
    return {"ts": dt.datetime.now(dt.timezone.utc).isoformat(), "plan_id": plan_id,
            "item": item.get("path"), "action": action, "method": method, "phase": phase,
            "result": result, "reason": reason, "size_bytes": size, "trash_path": trash_path,
            **extra}


def _append_receipt(receipt):
    f = paths.receipts_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _in_use(path, timeout, runner):
    if not Path(path).exists():
        return None
    try:
        result = runner(["lsof", "+D", path], timeout=timeout)
    except (OSError, subprocess.TimeoutExpired, TimeoutError):
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 1 and not (result.stderr or "").strip() and Path(path).exists():
        return False
    return None

def _free_bytes(runner):
    try:
        result = runner(["diskutil", "info", "-plist", "/"], timeout=COMMAND_TIMEOUT)
        if result.returncode:
            return None
        data = plistlib.loads(result.stdout.encode() if isinstance(result.stdout, str) else result.stdout)
        for key in ("APFSContainerFree", "Container Free Space"):
            if key in data:
                return int(data[key])
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        pass
    return None


def _open_directory_chain(path, hook=None):
    path = Path(path)
    if not path.is_absolute() or path.anchor != "/":
        raise OSError("path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fds = []
    try:
        fd = os.open("/", flags)
        fds.append(fd)
        current = Path("/")
        for index, component in enumerate(path.parts[1:], start=1):
            fd = os.open(component, flags, dir_fd=fds[-1])
            fds.append(fd)
            current /= component
            if hook is not None:
                hook(index, current)
        return fds, [os.fstat(fd) for fd in fds]
    except BaseException:
        for fd in reversed(fds):
            os.close(fd)
        raise


def _close_fds(fds):
    for fd in reversed(fds):
        try:
            os.close(fd)
        except OSError:
            pass


def _fd_identity(path):
    try:
        fds, stats = _open_directory_chain(path)
    except OSError:
        return None
    try:
        st = stats[-1]
        return st.st_dev, st.st_ino
    finally:
        _close_fds(fds)


def _fd_ancestry_safe(path, parent_fds, parent_stats, item_stat):
    parent_ids = {(st.st_dev, st.st_ino) for st in parent_stats}
    home = paths.account_home()
    subtree_denies = [
        Path("/System"), Path("/Library"), Path("/Applications"),
        home / "Documents", home / "Desktop", home / "Library/Mobile Documents",
        home / "Library/Keychains", home / ".cache/huggingface", home / ".cache/qmd",
        home / "Library/Containers", home / "Library/Group Containers",
        home / "Library/Application Support/MobileSync/Backup", home / ".docker/volumes",
        home / "Library/Mail", home / "Pictures/Photos Library.photoslibrary",
    ]
    for denied in subtree_denies:
        identity = _fd_identity(denied)
        if identity is not None and identity in parent_ids:
            return False
        if identity is not None and identity == (item_stat.st_dev, item_stat.st_ino):
            return False
    exact_denies = [Path("/"), home, home / "Library"]
    if any(_fd_identity(denied) == (item_stat.st_dev, item_stat.st_ino) for denied in exact_denies):
        return False
    # Reopen the lexical ancestry from / and require every component still be
    # the directory object pinned by the original walk.
    try:
        current_fds, current_stats = _open_directory_chain(Path(path).parent)
    except OSError:
        return False
    try:
        current_ids = [(st.st_dev, st.st_ino) for st in current_stats]
        opened_ids = [(st.st_dev, st.st_ino) for st in parent_stats]
        return current_ids == opened_ids
    finally:
        _close_fds(current_fds)


def _renameatx_exclusive(source_fd, source_name, destination_fd, destination_name):
    try:
        renameatx_np = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True).renameatx_np
    except (AttributeError, OSError) as exc:
        raise OSError(errno.ENOSYS, f"exclusive rename is unavailable: {exc}") from exc
    renameatx_np.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                             ctypes.c_uint)
    renameatx_np.restype = ctypes.c_int
    result = renameatx_np(source_fd, os.fsencode(source_name), destination_fd,
                          os.fsencode(destination_name), 0x4)  # RENAME_EXCL
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), source_name, destination_name)


def _fd_path(fd):
    raw = fcntl.fcntl(fd, 50, b"\0" * 1024)  # macOS F_GETPATH, MAXPATHLEN
    return os.fsdecode(raw.split(b"\0", 1)[0])


def _trash_binding_matches(trash_fd):
    home_fds = []
    try:
        home_fds, _ = _open_directory_chain(paths.account_home())
        home_fd = home_fds[-1]
        trash_stat = os.stat(".Trash", dir_fd=home_fd, follow_symlinks=False)
        opened_stat = os.fstat(trash_fd)
        return (stat.S_ISDIR(trash_stat.st_mode)
                and (trash_stat.st_dev, trash_stat.st_ino) ==
                (opened_stat.st_dev, opened_stat.st_ino))
    except OSError:
        return False
    finally:
        _close_fds(home_fds)


def _trash(path, item, plan_id, walk_hook=None):
    source = Path(path).absolute()
    parent_fds = []
    trash_fds = []
    source_fd = None
    moved = False
    destination_name = None

    def recovery_details(reason):
        try:
            actual = str(Path(_fd_path(trash_fd)) / destination_name)
        except OSError as exc:
            actual = None
            reason = f"{reason}; actual Trash path unavailable: {exc}"
        try:
            approved = _fd_path(source_fd)
        except OSError as exc:
            approved = None
            reason = f"{reason}; approved object path unavailable: {exc}"
        return reason, {"actual_location": actual, "approved_object_location": approved,
                        "manual_recovery": True}

    try:
        parent_fds, parent_stats = _open_directory_chain(source.parent, walk_hook)
        parent_fd = parent_fds[-1]
        source_fd = os.open(source.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                            | getattr(os, "O_NONBLOCK", 0), dir_fd=parent_fd)
        source_stat = os.fstat(source_fd)
        expected = (item.get("dev"), item.get("inode"), item.get("mtime"))
        actual_type = ("directory" if stat.S_ISDIR(source_stat.st_mode) else
                       "file" if stat.S_ISREG(source_stat.st_mode) else "other")
        if actual_type != item.get("file_type") or actual_type == "other":
            return "trash", "refused", "source type does not match planned file_type", None, False, {}
        if (source_stat.st_dev, source_stat.st_ino, source_stat.st_mtime) != expected:
            return "trash", "refused", "path fingerprint changed during fd walk", None, False, {}
        if not _fd_ancestry_safe(source, parent_fds, parent_stats, source_stat):
            return "trash", "refused", "symlink or hard-denied ancestry changed during fd walk", None, False, {}

        trash_dir = paths.account_home() / ".Trash"
        trash_fds, trash_stats = _open_directory_chain(trash_dir)
        trash_fd = trash_fds[-1]
        if trash_stats[-1].st_dev != source_stat.st_dev:
            return "trash", "refused", "cross-volume Trash move refused", None, False, {}
        try:
            trash_base = _fd_path(trash_fd)
        except OSError as exc:
            return "trash", "refused", f"Trash path lookup failed before move: {exc}", None, False, {}
        if not _trash_binding_matches(trash_fd):
            return "trash", "refused", "Trash directory binding changed before move", None, False, {}
        if not _fd_ancestry_safe(source, parent_fds, parent_stats, source_stat):
            return "trash", "refused", "source ancestry changed before Trash move", None, False, {}

        short_id = plan_id[:8]
        for index in range(1, 10000):
            destination_name = f"{source.name} mac-doctor {short_id} {index}"
            if walk_hook is not None:
                walk_hook("before-rename", destination_name)
            try:
                _renameatx_exclusive(parent_fd, source.name, trash_fd, destination_name)
                moved = True
                break
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    continue
                raise
        else:
            return "trash", "refused", "unique Trash name allocation exhausted", None, False, {}

        if walk_hook is not None:
            walk_hook("after-rename", destination_name)
        checks = []
        try:
            moved_stat = os.stat(destination_name, dir_fd=trash_fd, follow_symlinks=False)
            pinned_stat = os.fstat(source_fd)
            if (moved_stat.st_dev, moved_stat.st_ino) != (pinned_stat.st_dev, pinned_stat.st_ino):
                checks.append("destination dev/inode differs from pinned source")
        except OSError as exc:
            checks.append(f"destination stat failed: {exc}")
            pinned_stat = os.fstat(source_fd)
        if pinned_stat.st_mtime != item.get("mtime"):
            checks.append("pinned source mtime changed")
        if not _trash_binding_matches(trash_fd):
            checks.append("Trash binding changed")
        if not _fd_ancestry_safe(source, parent_fds, parent_stats, pinned_stat):
            checks.append("source parent binding changed")
        if checks:
            reason, extra = recovery_details("; ".join(checks))
            return "trash", "failed", reason, extra["actual_location"], True, extra
        destination = str(Path(_fd_path(trash_fd)) / destination_name)
        return "trash", "done", "moved to .Trash; restore manually (Finder Put Back is unavailable)", destination, False, {}
    except OSError as exc:
        if moved and destination_name is not None:
            reason, extra = recovery_details(f"post-move verification failed: {exc}")
            return "trash", "failed", reason, extra["actual_location"], True, extra
        if exc.errno == errno.EXDEV:
            return "trash", "refused", "cross-volume Trash move refused", None, False, {}
        if exc.errno in {errno.ELOOP, errno.ENOENT, errno.ENOTDIR}:
            return "trash", "refused", f"symlink or missing directory refused: {exc}", None, False, {}
        if exc.errno == errno.ENOSYS:
            return "trash", "refused", f"fd-anchored Trash move refused: {exc}", None, False, {}
        return "trash", "failed", f"fd-anchored Trash move failed: {exc}", None, False, {}
    finally:
        if source_fd is not None:
            os.close(source_fd)
        _close_fds(trash_fds)
        _close_fds(parent_fds)

def _fingerprint_matches(path, item):
    try:
        st = Path(path).lstat()
    except OSError:
        return False
    return (st.st_dev, st.st_ino, st.st_mtime) == (item.get("dev"), item.get("inode"), item.get("mtime"))


def _validate_current_path(path, target, item):
    if _hard_denied(path) or not _under(path, _roots(target), _excluded_paths(target)):
        return None, "hard-denied path, path outside catalogue pattern, or symlink escape"
    if not _fingerprint_matches(path, item):
        return None, "path fingerprint changed"
    try:
        real = Path(path).resolve(strict=True)
    except OSError as exc:
        return None, f"path no longer exists: {exc}"
    if _hard_denied(real) or not _under(real, _roots(target), _excluded_paths(target)):
        return None, "canonical path failed hard-deny or catalogue-pattern validation"
    return str(real), ""


def _policy_matches(item, target):
    return (item.get("class") == target["class"]
            and item.get("action") == target["action"]
            and item.get("native_cmd") == target.get("native_cmd")
            and item.get("native_env", {}) == target.get("native_env", {})
            and item.get("inuse_check") == target["inuse_check"]
            and item.get("min_age_days") == target.get("min_age_days", 0)
            and item.get("rebuildable") == target["rebuildable"])


def _manifest_matches_plan_id(plan, plan_id):
    try:
        created = dt.datetime.fromisoformat(plan["created_at"])
        seed = json.dumps([(item["target"], item["path"], item["dev"], item["inode"], item["mtime"])
                           for item in plan["items"]], sort_keys=True)
    except (KeyError, TypeError, ValueError):
        return False
    base_id = created.strftime("%Y%m%dT%H%M%SZ") + "-" + hashlib.sha256(seed.encode()).hexdigest()[:10]
    suffix = plan_id[len(base_id) + 1:] if plan_id.startswith(base_id + "-") else ""
    return (plan.get("plan_id") == plan_id
            and (plan_id == base_id or (suffix.isdigit() and bool(suffix))))


def apply(plan_id, allow_caution=False, yes=False, *, renew_if_unchanged=False, runner=None,
          timeout=COMMAND_TIMEOUT, trash_walk_hook=None):
    if not yes:
        return {"plan_id": plan_id, "refused": True, "reason": "--yes is required", "items": [],
                "free_bytes_before": None, "free_bytes_after": None, "free_bytes_delta": None,
                "note": "Trash does not free disk space until emptied."}
    run = runner or _run
    planfile = _plan_path(plan_id)
    plan = json.loads(planfile.read_text())
    now = dt.datetime.now(dt.timezone.utc)
    renewal_metadata = {}
    if now >= dt.datetime.fromisoformat(plan["expires_at"]):
        if not renew_if_unchanged:
            return {"plan_id": plan_id, "refused": True, "reason": "plan expired", "items": [],
                    "free_bytes_before": None, "free_bytes_after": None, "free_bytes_delta": None,
                    "note": "Trash does not free disk space until emptied."}
        items = plan.get("items")
        host = os.uname().nodename
        if (not isinstance(items, list) or not items
                or plan.get("host") != host
                or any(not isinstance(item, dict) or item.get("class") != "SAFE"
                       or item.get("action") != "native" for item in items)):
            return {"plan_id": plan_id, "refused": True,
                    "reason": "expired plan is not eligible for unchanged SAFE/native renewal",
                    "items": [], "free_bytes_before": None, "free_bytes_after": None,
                    "free_bytes_delta": None,
                    "note": "Trash does not free disk space until emptied."}
        if any(type(item.get("size_bytes")) is not int or item["size_bytes"] < 0 for item in items):
            return {"plan_id": plan_id, "refused": True,
                    "reason": "approved scan size is unknown or invalid; renewal refused",
                    "items": [], "free_bytes_before": None, "free_bytes_after": None,
                    "free_bytes_delta": None, "note": "Trash does not free disk space until emptied."}
        target_ids = [item.get("target") for item in items]
        if (any(not isinstance(target_id, str) or not target_id for target_id in target_ids)
                or len(set(target_ids)) != len(target_ids)):
            return {"plan_id": plan_id, "refused": True,
                    "reason": "expired plan has invalid or duplicate target IDs", "items": [],
                    "free_bytes_before": None, "free_bytes_after": None, "free_bytes_delta": None,
                    "note": "Trash does not free disk space until emptied."}
        if not _manifest_matches_plan_id(plan, plan_id):
            return {"plan_id": plan_id, "refused": True,
                    "reason": "expired plan manifest changed or does not match plan ID; renewal refused",
                    "items": [], "free_bytes_before": None, "free_bytes_after": None,
                    "free_bytes_delta": None, "note": "Trash does not free disk space until emptied."}
        try:
            renewed = make_plan(target_ids, runner=run)
        except (OSError, ValueError, subprocess.TimeoutExpired, TimeoutError) as exc:
            return {"plan_id": plan_id, "refused": True,
                    "reason": f"renewal planning failed: {exc}", "items": [],
                    "free_bytes_before": None, "free_bytes_after": None, "free_bytes_delta": None,
                    "note": "Trash does not free disk space until emptied."}
        if any(type(item.get("size_bytes")) is not int or item["size_bytes"] < 0
               for item in renewed["items"]):
            return {"plan_id": plan_id, "refused": True,
                    "reason": "fresh scan size is unknown or invalid; renewal refused",
                    "items": [], "free_bytes_before": None, "free_bytes_after": None,
                    "free_bytes_delta": None, "note": "Trash does not free disk space until emptied."}
        if renewed.get("host") != host or renewed.get("items") != items:
            return {"plan_id": plan_id, "refused": True,
                    "reason": "expired plan manifest changed; renewal refused", "items": [],
                    "free_bytes_before": None, "free_bytes_after": None, "free_bytes_delta": None,
                    "note": "Trash does not free disk space until emptied."}
        approved_plan_id = plan_id
        plan_id = renewed["plan_id"]
        plan = renewed
        renewal_metadata = {"approved_plan_id": approved_plan_id, "renewed_from": approved_plan_id}
    receipt_file = paths.receipts_file()
    try:
        receipt_file.parent.mkdir(parents=True, exist_ok=True)
        with receipt_file.open("a", encoding="utf-8"):
            pass
    except OSError as exc:
        return {"plan_id": plan_id, **renewal_metadata, "refused": True,
                "reason": f"receipt log is not writable: {exc}",
                "items": [], "free_bytes_before": None, "free_bytes_after": None,
                "free_bytes_delta": None, "note": "Trash does not free disk space until emptied."}
    before = _free_bytes(run)
    results = []
    catalog = {t["id"]: t for t in load_targets()}

    def outcome(item, action, method, result, reason, trash_path=None, **extra):
        row = _receipt(item, plan_id, action, method, result, reason,
                       item.get("size_bytes", "unknown"), phase="outcome",
                       trash_path=trash_path, **renewal_metadata, **extra)
        _append_receipt(row)
        results.append(row)

    for item in plan.get("items", []):
        path = item.get("path", "")
        action = item.get("action", "")
        method, refusal = "none", ""
        target = catalog.get(item.get("target"))
        if not target or target["class"] not in {"SAFE", "CAUTION"} or action not in {"native", "trash"}:
            refusal = "unknown, protected, or report-only target/action"
        elif _hard_denied(path):
            refusal = "hard-denied path"
        elif not _under(path, _roots(target), _excluded_paths(target)):
            refusal = "path outside exact declared target pattern or symlink escape"
        elif not _fingerprint_matches(path, item):
            refusal = "path fingerprint changed"
        elif not _policy_matches(item, target):
            refusal = "plan policy does not match catalogue"
        elif target["class"] == "CAUTION" and not CAUTION_APPLY_ENABLED:
            refusal = "CAUTION items are review-only by design; move them manually in Finder"
        elif target["class"] == "CAUTION" and not allow_caution:
            refusal = "class not allowed"
        elif target["class"] == "SAFE" and (target["action"] != "native" or not target.get("native_cmd")):
            refusal = "SAFE target requires its native cleanup command"
        elif target["class"] == "CAUTION" and target["action"] != "trash":
            refusal = "CAUTION targets may only move to Trash"
        else:
            try:
                current_age = (time.time() - Path(path).lstat().st_mtime) / 86400
                if current_age < target.get("min_age_days", 0):
                    refusal = "minimum age condition no longer holds"
            except OSError as exc:
                refusal = f"path validation failed: {exc}"

        if not refusal and target["inuse_check"]:
            busy = _in_use(path, timeout, run)
            if busy is not False:
                refusal = "in-use check detected use or returned unknown"
        real_path = None
        if not refusal:
            real_path, refusal = _validate_current_path(path, target, item)

        scope = None
        argv = None
        env = None
        if not refusal and target["action"] == "native":
            scope_template = target.get("scope_path")
            scope = _render(scope_template) if scope_template else ""
            if not scope or item.get("native_scope") != str(Path(scope).resolve(strict=False)):
                refusal = "planned native scope does not match catalogue"
            else:
                effective, error = _effective_native_scope(target, scope, run, timeout)
                if effective is None or effective != item["native_scope"]:
                    refusal = error or "effective native scope changed"
                else:
                    argv = _native_argv(target, scope)
                    env = _native_action_env(target, scope)
            if not refusal:
                real_path, refusal = _validate_current_path(path, target, item)

        if refusal:
            outcome(item, action, method, "refused", refusal)
            continue

        method = "native" if target["action"] == "native" else "trash"
        attempt = _receipt(item, plan_id, action, method, "attempt",
                           "durable authorization record written before mutation",
                           item.get("size_bytes", "unknown"), phase="attempt", **renewal_metadata)
        try:
            _append_receipt(attempt)
            results.append(attempt)
        except OSError as exc:
            return {"plan_id": plan_id, **renewal_metadata, "refused": True,
                    "reason": f"attempt receipt could not be durably written; run aborted: {exc}",
                    "items": results, "free_bytes_before": before, "free_bytes_after": None,
                    "free_bytes_delta": None, "note": "No action was dispatched for this item."}

        # The durable log write itself can take time; validate the path identity once more.
        real_path, stale_reason = _validate_current_path(path, target, item)
        if stale_reason:
            outcome(item, action, method, "refused", stale_reason)
            continue
        trash_path = None
        stop_run = False
        receipt_extra = {}
        try:
            if method == "native":
                proc = run(argv, timeout=timeout, env=env)
                result = "done" if proc.returncode == 0 else "failed"
                reason = "completed" if proc.returncode == 0 else (proc.stderr.strip() or "native command failed")
            else:
                method, result, reason, trash_path, stop_run, receipt_extra = _trash(
                    path, item, plan_id, trash_walk_hook)
        except (OSError, subprocess.TimeoutExpired, TimeoutError) as exc:
            result, reason, receipt_extra = "failed", str(exc), {}
        try:
            outcome(item, action, method, result, reason, trash_path, **receipt_extra)
        except OSError as exc:
            return {"plan_id": plan_id, **renewal_metadata, "refused": True,
                    "reason": f"outcome receipt failed after attempt: {exc}",
                    "items": results, "free_bytes_before": before, "free_bytes_after": None,
                    "free_bytes_delta": None, "note": "Attempt receipt is durable; inspect outcome manually."}
        if method == "trash" and stop_run:
            return {"plan_id": plan_id, **renewal_metadata, "refused": True,
                    "reason": "Trash move verification failed; run stopped; manual recovery required",
                    "items": results, "free_bytes_before": before, "free_bytes_after": None,
                    "free_bytes_delta": None, "note": "Use the recorded actual_location and approved_object_location."}

    after = _free_bytes(run)
    delta = after - before if after is not None and before is not None else None
    refused = any(row["phase"] == "outcome" and row["result"] == "refused" for row in results)
    return {"plan_id": plan_id, **renewal_metadata, "refused": refused, "items": results,
            "free_bytes_before": before, "free_bytes_after": after, "free_bytes_delta": delta,
            "nominal_size_bytes": sum(i["size_bytes"] for i in results
                                      if i["phase"] == "outcome" and isinstance(i["size_bytes"], int)),
            "note": "Trash does not free disk space until emptied; free-byte delta is measured separately."}


def receipts(last=50):
    p = paths.receipts_file()
    if not p.exists():
        return []
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    return rows[-max(0, last):]
