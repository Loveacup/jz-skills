#!/usr/bin/env python3
"""mac-doctor unified watchdog — 每 2 小时巡检，只在需人工处理时输出。

六检：CPU+内存+磁盘+Swap / Kanban 完整性 / 僵尸进程 / MCP 孤儿检查。
MCP 默认只报告；显式开启清理偏好并登记具体目标后，才允许对确认的孤儿发送 SIGTERM。
P2：集成 preferences 操作偏好（白名单过滤 + signature 抑制 + triage 触发）。
"""

import importlib.util
import json, os, re, shlex, signal, stat, subprocess, sys, time
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from macdoctor import jev
from macdoctor.paths import data_dir, hermes_home, config_file

HERMES_HOME = hermes_home()
COLLECTOR = SCRIPTS_DIR / "collector-daemon.py"
PREFERENCES_MODULE = SCRIPTS_DIR / "preferences.py"
ZOMBIE_KILLER_MODULE = SCRIPTS_DIR / "zombie_killer.py"
STATE_FILE = ((HERMES_HOME / "profiles" / "cron-worker" / "state" / "mac-doctor-watchdog-state.json")
              if HERMES_HOME else data_dir() / "mac-doctor-watchdog-state.json")
KANBAN_DB = (HERMES_HOME / "kanban.db") if HERMES_HOME else data_dir() / "kanban.db"
ZOMBIE_MAX = 4
MCP_IDENTIFIERS = ("searxng", "tavily", "exa", "brave-search", "codegraph", "context7", "chroma", "modelcontextprotocol")
RUNTIME_IDENTIFIERS = {"claude", "claude-code", "claude_code", "codex", "omp", "opencode"}
GENERIC_CLEANUP_TARGETS = {"mcp", "mcp-server", "server", "node", "nodejs", "python", "python2", "python3", "python3.12", "python3.13", "npm", "npx", "pnpm", "bun", "uv", "uvx", "pipx", "sh", "bash", "zsh", "brave", "playwright", "chrome", "chromium", "modelcontextprotocol", "hermes", "tmux"}
COOLDOWN_HOURS = 3
DISK_CHANGE_THRESHOLD_GB = 1.0  # 磁盘变化超过此值才重新报告
SUPPRESSION_TTL_HOURS = 3
_seen_counts = {}  # signature 出现计数只在内存维护，绝不写回 preferences.json（避免污染 schema）


def _load_preferences_module():
    """动态加载 P1 preferences.py（cron-worker profile 下无法直接 import）。"""
    spec = importlib.util.spec_from_file_location("mac_doctor_preferences", PREFERENCES_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_prefs():
    """加载操作偏好；任何异常 fail-soft 回退最小默认，不让看门狗 crash。"""
    try:
        return _load_preferences_module().load_preferences(PREFERENCES_FILE)
    except Exception as e:
        print(f"preferences load failed: {e}", file=sys.stderr)
        return {"facts": {"known_short_running_tools": []}, "interpretations": [], "suppressions": []}


_INSPECTION_DIR = _load_preferences_module().inspection_dir()
PREFERENCES_FILE = _INSPECTION_DIR / "preferences.json"
TRIAGE_TRIGGER_FILE = _INSPECTION_DIR / ".triage-trigger"
ZOMBIE_KILL_MARKER = _INSPECTION_DIR / ".known-zombie-killed.json"
MCP_CLEANUP_AUDIT_FILE = _INSPECTION_DIR / "mcp-cleanup-audit.jsonl"


def save_prefs(prefs):
    """原子写回偏好（委托 P1 save_preferences）。"""
    _load_preferences_module().save_preferences(PREFERENCES_FILE, prefs)


def is_known_short_running_tool(name, prefs):
    """name 是否在 facts.known_short_running_tools 白名单内（大小写无关）。"""
    tools = prefs.get("facts", {}).get("known_short_running_tools", [])
    return str(name).lower() in {str(t).lower() for t in tools}


def _alert_text(alert):
    return alert.get("text", str(alert)) if isinstance(alert, dict) else str(alert)


def _extract_process_name(alert):
    text = _alert_text(alert)
    m = re.search(r"(?:Process|process)\s+([^\s:]+)", text)
    if m:
        return Path(m.group(1)).name
    for token in re.findall(r"[A-Za-z0-9_.+-]+", text):
        if token not in {"CPU", "cpu", "sustained", "Process", "process"}:
            return Path(token).name
    return ""


def filter_known_short_running_alerts(alerts, prefs):
    """剔除已知短跑工具的 CPU 100% 告警（如 ccusage 跑满瞬时 CPU）。"""
    kept = []
    for alert in alerts:
        proc = _extract_process_name(alert)
        if "cpu" in _alert_text(alert).lower() and proc and is_known_short_running_tool(proc, prefs):
            continue
        kept.append(alert)
    return kept


def add_suppression(signature, prefs, now=None):
    """写入/刷新 prefs.suppressions（last_seen/count/ttl）并原子写回。"""
    now = time.time() if now is None else now
    items = prefs.setdefault("suppressions", [])
    for item in items:
        if item.get("signature") == signature:
            item["last_seen"] = now
            item["count"] = int(item.get("count", 1)) + 1
            item["ttl_hours"] = SUPPRESSION_TTL_HOURS
            save_prefs(prefs)
            return
    items.append({"signature": signature, "first_seen": now, "last_seen": now,
                  "count": 2, "ttl_hours": SUPPRESSION_TTL_HOURS})
    save_prefs(prefs)


def is_signature_suppressed(signature, prefs, now=None):
    """内存级快速判断 signature 是否在活跃抑制窗口内（看门狗本轮去重用）。

    与 P1 preferences.is_suppressed(path, sig, now) 分工：P1 读文件并清理过期项，
    供 triage 等文件级 TTL 检查（deprecated 但保留兼容）；本函数零 IO 读内存 prefs。
    """
    now = time.time() if now is None else now
    for item in prefs.get("suppressions", []):
        if item.get("signature") != signature:
            continue
        if item.get("last_seen", 0) + item.get("ttl_hours", SUPPRESSION_TTL_HOURS) * 3600 > now:
            return True
    return False


def record_signature_seen(signature, prefs, now=None):
    """记录 signature 出现次数；连续第 2 次写 suppression 并返回 True。计数仅存内存。"""
    now = time.time() if now is None else now
    count = int(_seen_counts.get(signature, 0)) + 1
    _seen_counts[signature] = count
    if count >= 2:
        add_suppression(signature, prefs, now=now)
        return True
    return False


def issue_signature(check_name, data):
    """把一条 issue 归一化成稳定 signature 字符串。"""
    if check_name == "zombie":
        return f"zombie:{normalize_zombie_set(data)}"
    return f"{check_name}:{str(data)[:160]}"


def trigger_triage(reason):
    """有异常时落 .triage-trigger 供 triage 流程拾取；写失败只警告不 crash。"""
    try:
        TRIAGE_TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"created_at": datetime.now().isoformat(), "reason": reason, "source": "mac-doctor-watchdog"}
        TRIAGE_TRIGGER_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"triage trigger failed: {e}", file=sys.stderr)


def check_kanban():
    """Kanban 数据库完整性检查。"""
    if not KANBAN_DB.exists():
        return ("warn", f"{KANBAN_DB.name} 文件不存在")
    try:
        r = subprocess.run(["sqlite3", str(KANBAN_DB), "PRAGMA integrity_check"],
                           capture_output=True, text=True, timeout=10)
        result = r.stdout.strip()
        if result != "ok":
            return ("fail", f"{KANBAN_DB.name}: {result[:200]}")
        return ("ok", None)
    except Exception as e:
        return ("error", f"Kanban 检查失败: {e}")


def check_zombies():
    """Detect zombies and attach observed parent identity for guarded cleanup."""
    try:
        r = subprocess.run(["ps", "axo", "pid,ppid,stat,args"], capture_output=True, text=True, timeout=10)
        id_proc = subprocess.run(["ps", "-axo", "pid=,ppid=,lstart=,args="],
                                 capture_output=True, text=True, timeout=10)
        if r.returncode or id_proc.returncode:
            return ("error", "ps failed while observing zombie identities")
        identities = {}
        for line in id_proc.stdout.splitlines():
            fields = line.split(None, 7)
            if len(fields) == 8:
                identities[fields[0]] = tuple(fields[:7]) + (fields[7],)
        zombies = []
        for line in r.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4 and "Z" in parts[2]:
                zombies.append({"pid": parts[0], "ppid": parts[1], "cmd": parts[3][:80],
                                "parent_identity": identities.get(parts[1])})
        return ("ok", None) if len(zombies) <= ZOMBIE_MAX else ("warn", zombies)
    except Exception as e:
        return ("error", str(e))


def _load_zombie_killer_module():
    """动态加载 zombie_killer.py（同 PREFERENCES_MODULE 模式）。"""
    if not ZOMBIE_KILLER_MODULE.exists():
        # 子 agent D 坑: 部署漂移时无感; 启动期 fail-loud 一次性 stderr
        print(f"watchdog: zombie_killer 模块丢失 ({ZOMBIE_KILLER_MODULE}), L2 kill 钩子失效", file=sys.stderr)
    spec = importlib.util.spec_from_file_location("mac_doctor_zombie_killer", ZOMBIE_KILLER_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
_EMPTY_KILL_ACTION = {"killed": [], "skipped": {"cooldown": [], "not_found": [], "permission_denied": [], "error": []}, "gated": False, "reason": None}


def _process_identity_tokens(command):
    """Parse only executable/package identities; ps args is not shell-quoted."""
    try:
        argv = shlex.split(command)
    except ValueError:
        argv = command.split()
    if not argv:
        return [], []
    prefix = command.split(" --", 1)[0].lower()
    if ".app/contents/macos/" in prefix:
        return argv, []
    executable = argv[0].rsplit("/", 1)[-1].lower()
    identities = [argv[0]]
    if executable in {"sh", "bash", "zsh"}:
        option_index = next((i for i, arg in enumerate(argv[1:], 1)
                             if arg.startswith("-") and "c" in arg[1:]), None)
        if option_index is not None:
            nested = []
            for item in argv[option_index + 1:option_index + 3]:
                try:
                    nested.extend(shlex.split(item) if " " in item else [item])
                except ValueError:
                    nested.extend(item.split())
            identities.extend(nested[:2])
    elif executable in {"python", "python2", "python3", "python3.12", "python3.13"}:
        if len(argv) > 2 and argv[1] == "-m":
            identities.append(argv[2])
        elif len(argv) > 1 and not argv[1].startswith("-"):
            identities.append(argv[1])
    elif executable in {"npm", "npx", "pnpm", "bun", "uv", "uvx", "pipx"}:
        identities.extend(argv[1:7])
    elif executable in {"node", "nodejs"} and len(argv) > 1 and not argv[1].startswith("-"):
        identities.append(argv[1])
    return argv, identities


def _normalized_identity_tokens(command):
    _, identities = _process_identity_tokens(command)
    result = set()
    for token in identities:
        token = token.strip().strip("'\"").lower().rstrip("/;,)")
        if not token or token.startswith("-"):
            continue
        result.add(token)
        base = token.rsplit("/", 1)[-1]
        if base.startswith("@") and "/" in base:
            base = base.split("/", 1)[-1]
        base = re.sub(r"@[^@/]+$", "", base)
        base = re.sub(r"\.(?:js|cjs|mjs|py)$", "", base)
        if base:
            result.add(base)
    return result


def _is_mcp_process(command):
    """Match MCP server identities, not unrelated args, URLs, or browser bundles."""
    argv, identities = _process_identity_tokens(command)
    if not argv:
        return False
    if any(arg.lower() in {"--mcp", "--mcp-server"} for arg in argv[1:]):
        return True
    for token in identities:
        lower = token.lower()
        if re.search(r"(?:^|[/@._-])mcp(?:$|[/._-])", lower):
            return True
        if any(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", lower)
               for word in MCP_IDENTIFIERS):
            return True
    return False


def _is_runtime_anchor(command):
    """Recognize known interactive runtimes and wrapped CLI executables."""
    argv, identities = _process_identity_tokens(command)
    if not argv:
        return False
    executable = argv[0].rsplit("/", 1)[-1].lower()
    if executable in RUNTIME_IDENTIFIERS | {"tmux"}:
        return True
    if executable == "hermes" and argv[1:2] == ["chat"]:
        return True
    if executable == "hermes" and argv[1:3] == ["gateway", "run"]:
        return True
    if any(argv[i:i + 4] == ["-m", "hermes_cli.main", "gateway", "run"]
           for i in range(max(0, len(argv) - 3))):
        return True
    lowered = command.lower().lstrip()
    if lowered.startswith(("/applications/cursor.app/contents/macos/cursor",
                           "/applications/visual studio code.app/contents/macos/code")):
        return True
    return any(re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", token.lower())
               for token in identities[1:] for name in RUNTIME_IDENTIFIERS)


def _parse_process_row(line):
    parts = line.strip().split(None, 7)
    if len(parts) < 8 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return parts[0], parts[1], " ".join(parts[2:7]), parts[7]


def _append_mcp_cleanup_audit(pid, identity, result):
    """Append a minimal, private audit record without capturing full argv."""
    try:
        MCP_CLEANUP_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(str(MCP_CLEANUP_AUDIT_FILE), flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return False
            os.fchmod(fd, 0o600)
            record = {"timestamp": datetime.now().astimezone().isoformat(),
                      "pid": int(pid), "identity": identity, "result": result}
            data = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            return os.write(fd, data) == len(data)
        finally:
            os.close(fd)
    except Exception:
        return False


def check_mcp_cleanup(prefs=None):
    """Detect MCP orphans; only narrowly authorized, revalidated PID 1 orphans get SIGTERM."""
    try:
        r = subprocess.run(["ps", "-axo", "pid,ppid,lstart,args"], capture_output=True,
                           text=True, timeout=10)
        if r.returncode != 0:
            return ("error", f"ps failed (exit {r.returncode})")
        rows = {}
        for line in r.stdout.splitlines()[1:]:
            parsed = _parse_process_row(line)
            if parsed:
                pid, ppid, started, command = parsed
                rows[pid] = (ppid, started, command)
        if not rows:
            return ("error", "ps returned no process rows")
        mcp_pids = {pid for pid, (_, _, cmd) in rows.items() if _is_mcp_process(cmd)}
        if not mcp_pids:
            return ("ok", None)
        anchor_pids = {pid for pid, (_, _, cmd) in rows.items() if _is_runtime_anchor(cmd)}
        if not anchor_pids:
            return ("warn", f"发现 {len(mcp_pids)} 个 MCP 进程；未找到可信运行时 anchor，未清理")
        valid = set(anchor_pids)
        changed = True
        while changed:
            changed = False
            for pid, (ppid, _, _) in rows.items():
                if ppid in valid and pid not in valid:
                    valid.add(pid)
                    changed = True
        orphans = sorted(mcp_pids - valid, key=int)
        if not orphans:
            return ("ok", None)
        auto_cleanup = (prefs or {}).get("facts", {}).get("user_preferences", {}).get(
            "auto_kill_mcp_orphans", False) is True
        targets = (prefs or {}).get("facts", {}).get("known_mcp_cleanup_targets", [])
        if not auto_cleanup or not targets:
            return ("warn", f"发现 {len(orphans)} 个孤儿 MCP 进程；需显式开启自动清理并登记目标，未执行清理")
        if not isinstance(targets, list) or any(not isinstance(t, str) or not t.strip() for t in targets):
            return ("warn", "known_mcp_cleanup_targets 必须是非空字符串列表；未执行清理")
        allowed = [t.strip().lower() for t in targets]
        if any(t in GENERIC_CLEANUP_TARGETS or len(t) < 3 for t in allowed):
            return ("warn", "known_mcp_cleanup_targets 含过于宽泛目标；未执行清理")
        candidates = []
        for pid in orphans:
            ppid, started, command = rows[pid]
            if ppid != "1":
                continue
            identities = _normalized_identity_tokens(command)
            match = next((target for target in allowed if target in identities), None)
            if match:
                candidates.append((pid, ppid, started, command, match))
        if not candidates:
            return ("warn", f"发现 {len(orphans)} 个孤儿 MCP 进程，但未找到可安全清理的已登记目标")
        killed, failed, audit_failed = [], [], []
        for pid, ppid, started, command, identity in candidates:
            try:
                verify = subprocess.run(["ps", "-p", pid, "-o", "pid=,ppid=,lstart=,args="],
                                        capture_output=True, text=True, timeout=5)
                current = _parse_process_row(verify.stdout) if verify.returncode == 0 else None
                if not current or current != (pid, ppid, started, command):
                    _append_mcp_cleanup_audit(pid, identity, "skipped_changed")
                    failed.append(pid)
                    continue
                if not _append_mcp_cleanup_audit(pid, identity, "signal_attempt"):
                    failed.append(pid)
                    audit_failed.append(pid)
                    continue
                os.kill(int(pid), signal.SIGTERM)
                killed.append(pid)
                if not _append_mcp_cleanup_audit(pid, identity, "signaled"):
                    audit_failed.append(pid)
            except Exception:
                failed.append(pid)
                _append_mcp_cleanup_audit(pid, identity, "failed")
        if not killed:
            suffix = "；审计日志不可写" if audit_failed else ""
            return ("warn", f"发现 {len(orphans)} 个孤儿 MCP 进程；安全复核后未清理 {len(failed)} 个{suffix}")
        msg = f"清理了 {len(killed)} 个孤儿 MCP 进程"
        if failed or audit_failed:
            msg += f"（{len(failed)} 个未清理，{len(audit_failed)} 个审计记录异常）"
        return ("cleaned", msg)
    except Exception as e:
        return ("error", str(e))


def load_state():
    """加载上次报告状态。"""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {}


def save_state(state):
    """保存当前报告状态。"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))
    except Exception:
        pass


def save_report_state(diagnosis, snap, issues):
    """封装状态写回：保留 zombie_sig / mcp_cleaned_msg 供下次去重。"""
    zombie_issues = [i[1] for i in issues if i[0] == "zombie"]
    mcp_issues = [i[1] for i in issues if i[0] == "mcp"]
    save_state({
        "last_report_ts": datetime.now().isoformat(),
        "diagnosis": diagnosis,
        "disk_free_gb": snap.get("disk_free_gb"),
        "zombie_sig": normalize_zombie_set(zombie_issues[0]) if zombie_issues else "",
        "mcp_cleaned_msg": mcp_issues[0] if mcp_issues else "",
    })


def normalize_zombie_set(zombies):
    """标准化僵尸进程集合为可比较的签名。"""
    if not zombies:
        return ""
    return ",".join(sorted(str(z.get("pid") if isinstance(z, dict) else z) for z in zombies))


def is_duplicate_disk_alert(diagnosis, disk_free_gb, prev_state):
    """磁盘告警去重：同 diagnosis + 变化 < 阈值 + 冷却期内 → 跳过。"""
    if not prev_state:
        return False
    if "Disk low" not in diagnosis or "Disk low" not in prev_state.get("diagnosis", ""):
        return False
    prev_disk = prev_state.get("disk_free_gb")
    if prev_disk is None or disk_free_gb is None:
        return False
    if abs(disk_free_gb - prev_disk) >= DISK_CHANGE_THRESHOLD_GB:
        return False  # 磁盘变化足够大，需要报告
    try:
        last_ts = datetime.fromisoformat(prev_state.get("last_report_ts", ""))
        if (datetime.now() - last_ts).total_seconds() / 3600 >= COOLDOWN_HOURS:
            return False  # 冷却时间已过
    except (ValueError, TypeError):
        return False
    return True


def is_duplicate_zombie_alert(zombies, prev_state):
    """僵尸去重：相同 PID 集合在冷却期内不重报（僵尸是父进程的债，子进程端无解）。"""
    if not prev_state or not zombies:
        return False
    if normalize_zombie_set(zombies) != prev_state.get("zombie_sig", ""):
        return False  # 集合变了，必须报
    try:
        last_ts = datetime.fromisoformat(prev_state.get("last_report_ts", ""))
        if (datetime.now() - last_ts).total_seconds() / 3600 >= COOLDOWN_HOURS:
            return False  # 冷却期已过，重新报一次
    except (ValueError, TypeError):
        return False
    return True


def is_duplicate_mcp_cleaned(prev_state):
    """MCP cleaned 去重：清理是良性副作用，冷却期内不重复推送「清理了 N 个」。"""
    if not prev_state:
        return False
    try:
        last_ts = datetime.fromisoformat(prev_state.get("last_report_ts", ""))
        if (datetime.now() - last_ts).total_seconds() / 3600 >= COOLDOWN_HOURS:
            return False
    except (ValueError, TypeError):
        return False
    return bool(prev_state.get("mcp_cleaned_msg"))


def main():
    checks = {}
    issues = []
    snap, alerts, diagnosis = {}, [], ""
    # 1. Collector 快照
    try:
        r = subprocess.run(["python3", str(COLLECTOR), "--json"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            snap = data.get("snapshot", {})
            alerts = data.get("alerts", [])
            diagnosis = data.get("diagnosis", "")
        else:
            issues.append(("collector", f"collector-daemon 失败 (exit {r.returncode})"))
    except Exception as e:
        issues.append(("collector", f"collector 异常: {e}"))
    # 阈值告警（排除纯异常）+ 操作偏好白名单过滤（prefs 复用到后续 signature 去重）
    threshold_alerts = [a for a in alerts if not a.get("is_anomaly", False)]
    prefs = load_prefs()
    threshold_alerts = filter_known_short_running_alerts(threshold_alerts, prefs)
    # 2. Kanban + 3. Zombie + L2 kill hook
    status, data = check_kanban()
    checks["kanban"] = status
    if status != "ok":
        issues.append(("kanban", data))
    # 3. Zombie + L2 kill hook（同 PID 集合 + 冷却期内 → 静默，僵尸是父进程的债子进程端无解）
    status, data = check_zombies()
    checks["zombie"] = status
    zombie_kill_action = _EMPTY_KILL_ACTION
    if status == "warn" and isinstance(data, list):
        try:
            zk = _load_zombie_killer_module()
            zombie_kill_action = zk.kill_known_zombies(data, prefs, marker_path=ZOMBIE_KILL_MARKER)
            if zombie_kill_action["killed"] or zombie_kill_action["skipped"]["not_found"]:
                time.sleep(1)  # 给 SIGCHLD 一帧传 init
                status, data = check_zombies()
                checks["zombie"] = status
        except Exception as e:
            print(f"zombie_killer 加载/调用失败: {e}", file=sys.stderr)
    if status == "warn":
        if is_duplicate_zombie_alert(data, load_state()):
            checks["zombie"] = "ok_silent"
        else:
            issues.append(("zombie", data))
    # 4. MCP：成功自动清理是维护动作而非人工告警，保持 stdout 静默。
    # 清理失败仍进入 issues，供 Telegram/triage 处理。
    status, data = check_mcp_cleanup(prefs)
    checks["mcp"] = status
    if status == "cleaned":
        checks["mcp"] = "ok_silent"
    elif status != "ok":
        issues.append(("mcp", data))
    # 操作偏好 signature 去重：活跃抑制内的 issue 静默，连续 2 次自动写抑制
    kept = []
    for name, data in issues:
        sig = issue_signature(name, data)
        if is_signature_suppressed(sig, prefs):
            continue
        record_signature_seen(sig, prefs)
        kept.append((name, data))
    issues = kept
    # 判断是否静默
    collector_ok = not threshold_alerts and diagnosis == "All clear" and not any(
        i[0] == "collector" for i in issues)
    other_ok = all(i[0] != "kanban" and i[0] != "zombie" for i in issues)
    if collector_ok and other_ok and not issues:
        sys.exit(0)
    # 去重：纯磁盘告警在冷却期内不重复推送
    only_disk_issue = not any(i[0] != "collector" for i in issues) and diagnosis.startswith("Disk low")
    if only_disk_issue and is_duplicate_disk_alert(diagnosis, snap.get("disk_free_gb"), load_state()):
        sys.exit(0)  # 静默：与上次相同的磁盘告警
    jev_result = None
    jev_settings = jev.load_settings({})
    if config_file().is_file():
        try:
            jev_settings = jev.load_settings(json.loads(config_file().read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    if jev.is_active(jev_settings):
        jev_findings = [
            {"kind": "threshold", "severity": a.get("severity", "yellow"),
             "summary": a.get("text", "")}
            for a in threshold_alerts
        ]
        for name, value in issues:
            if name == "zombie":
                count = len(value) if isinstance(value, list) else 1
                summary = f"{count} zombie process(es) detected"
            elif name == "kanban":
                summary = "Kanban integrity check reported an issue"
            elif name == "collector":
                summary = "Collector failed or was unavailable"
            else:
                summary = f"{name} check reported an issue"
            jev_findings.append({"kind": name, "severity": "yellow", "summary": summary})
        jev_result = jev.gate(jev_findings, prefs, {"jev": jev_settings})
        if jev_result.get("action") == "suppress":
            trigger_triage(";".join(issue_signature(n, d) for n, d in issues) or diagnosis)
            save_report_state(diagnosis, snap, issues)
            sys.exit(0)
    # 有异常 → 输出
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"🩺 mac-doctor 统一巡检 | {ts}")
    z_disp = "ok" if checks["zombie"] == "ok_silent" else checks["zombie"]
    m_disp = "ok" if checks["mcp"] == "ok_silent" else checks["mcp"]
    print(f"状态: kanban={checks['kanban']}  zombie={z_disp}  mcp={m_disp}")
    if jev_result and jev_result.get("answers"):
        result_answers = jev_result["answers"]
        print(f"Jev: urgency {result_answers['urgency']['score']:.1f}/3, "
              f"known-noise p={result_answers['known_noise']['noul']:.2f}")
    # 显示 zombie kill action(若有)— 让用户看到 L2 消费了 auto_kill
    if zombie_kill_action.get("killed"):
        print(f"🔪 已处理已授权 zombie PPID [{', '.join(zombie_kill_action['killed'])}]: SIGTERM first; identity-checked SIGKILL only if still alive (3h 冷却)")
    elif zombie_kill_action.get("gated"):
        # 修正: 只对当前 zombie 集里 PPID auto_kill=true 的才报拦截
        known_parents = prefs.get("facts", {}).get("known_zombie_parents", {}) or {}
        gated_ppids = sorted({str(z["ppid"]) for z in (data if isinstance(data, list) else [])
                              if isinstance(z, dict)
                              and (known_parents.get(str(z.get("ppid", ""))) or {}).get("auto_kill") is True})
        if gated_ppids:
            print(f"⏸️  zombie 父进程 auto_kill=true 被总开关拦截: PPID {', '.join(gated_ppids)} (auto_kill_zombies=False)— 仍按配置未杀")
    print()
    cpu = snap.get('cpu_percent')
    mem = snap.get('memory_pressure', '?')
    swap_mb = snap.get('swap_used_mb')
    disk_gb = snap.get('disk_free_gb')
    print(f"CPU: {f'{cpu:.1f}%' if cpu is not None else '?'}  |  Mem: {mem}  |  "
          f"Swap: {f'{swap_mb:.0f}MB' if swap_mb is not None else '?'}  |  "
          f"Disk: {f'{disk_gb:.1f}GB' if disk_gb is not None else '?'}")
    if diagnosis and diagnosis != "All clear":
        print(f"Root cause: {diagnosis}")
    if threshold_alerts:
        for a in threshold_alerts:
            print(f"  {a.get('text', a)}")
    print()
    # Other issues
    for check_name, data in issues:
        if check_name == "collector":
            print(f"⚠️ {data}")
        elif check_name == "kanban":
            print(f"📋 Kanban 异常: {data}")
        elif check_name == "zombie":
            zs = data if isinstance(data, list) else [data]
            print(f"👻 僵尸进程 ({len(zs)} 个):")
            for z in zs[:10]:
                if isinstance(z, dict):
                    print(f"  PID {z['pid']}: {z['cmd'][:60]}")
                else:
                    print(f"  {z}")
        elif check_name == "mcp":
            print(f"🧹 MCP: {data}")
        print()
    # 触发 triage（写文件失败不影响推送）+ 保存状态供下次去重
    trigger_triage(";".join(issue_signature(n, d) for n, d in issues) or diagnosis)
    save_report_state(diagnosis, snap, issues)


if __name__ == "__main__":
    main()
