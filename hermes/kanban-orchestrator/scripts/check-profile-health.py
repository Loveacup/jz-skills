#!/usr/bin/env python3
"""
Profile Health Check — 五部 profile 健康状态检查

检查维度：
  1. Config 有效性（YAML 语法、必填字段）
  2. 凭证池有效性（API_KEY 是否存在、非空、非占位符）
  3. 快速冒烟（hermes CLI 调用 + HTTP 状态码解析）

用法：
  python3 ~/.hermes/scripts/check-profile-health.py
  python3 ~/.hermes/scripts/check-profile-health.py --timeout 60
  python3 ~/.hermes/scripts/check-profile-health.py --json   # JSON 输出

输出：
  彩色终端表格 + 问题汇总
"""

import json
import os
import re
import subprocess
import sys
import time
import yaml

# ── 配置 ───────────────────────────────────────────────────────────────────

def get_real_home():
    """获取真实用户 home，适用于 HOME 环境变量被覆盖的场景"""
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_dir
    except (ImportError, KeyError):
        pass
    home = os.path.expanduser("~")
    if os.path.isdir(os.path.join(home, ".hermes", "profiles")):
        return home
    for cand in ("~", "/home/alexcai"):
        if os.path.isdir(os.path.join(cand, ".hermes", "profiles")):
            return cand
    return home

HOME = get_real_home()
PROFILES_DIR = os.path.join(HOME, ".hermes", "profiles")
ENV_PATH = os.path.join(HOME, ".hermes", ".env")
DEFAULT_TIMEOUT = 45

PROFILES = ["planner", "reviewer", "engineer", "auditor", "archivist"]

PROVIDER_ENV_MAP = {
    "deepseek":    "DEEPSEEK_API_KEY",
    "moonshot":    "KIMI_API_KEY",
    "kimi-coding": "KIMI_API_KEY",
    "minimax-cn":  "MINIMAX_CN_API_KEY",
    "minimax":     "MINIMAX_API_KEY",
    "openai":      "OPENAI_API_KEY",
    "openai-codex": "OPENAI_API_KEY",
    "openrouter":  "OPENROUTER_API_KEY",
    "anthropic":   "ANTHROPIC_API_KEY",
    "google":      "GOOGLE_API_KEY",
    "gemini":      "GEMINI_API_KEY",
}

# ── 工具函数 ───────────────────────────────────────────────────────────────

def load_env(env_path: str) -> dict:
    env = {}
    if not os.path.isfile(env_path):
        return env
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$', line)
            if not match:
                continue
            key, val = match.group(1), match.group(2).strip()
            if val and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            env[key] = val
    return env

def profile_config_path(name: str) -> str:
    return os.path.join(PROFILES_DIR, name, "config.yaml")

def read_config(profile: str):
    path = profile_config_path(profile)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        return None

def check_config_validity(cfg):
    if cfg is None:
        return False, "CONFIG_NONE"
    model = cfg.get("model")
    if not isinstance(model, dict):
        return False, "model block missing"
    if not model.get("default"):
        return False, "model.default empty"
    if not model.get("provider"):
        return False, "model.provider empty"
    agent = cfg.get("agent")
    if not isinstance(agent, dict):
        return False, "agent block missing"
    if not agent.get("system_prompt"):
        return False, "agent.system_prompt empty"
    toolsets = cfg.get("toolsets")
    if not isinstance(toolsets, list) or len(toolsets) == 0:
        return False, "toolsets empty"
    return True, "ok"

def check_credential(provider: str, env: dict):
    env_var = PROVIDER_ENV_MAP.get(provider)
    if env_var is None:
        return False, f"UNMAPPED_PROVIDER:{provider}"
    key = env.get(env_var)
    if not key:
        return False, "KEY_MISSING"
    if key in ("your_key_here", "YOUR_API_KEY_HERE", "replace_me"):
        return False, "KEY_PLACEHOLDER"
    if len(key) < 10:
        return False, "KEY_TOO_SHORT"
    return True, "key:present"

def check_smoke(profile: str, env: dict, timeout: int):
    cmd = ["hermes", "-p", profile, "chat", "-q", "回复OK", "-Q", "--yolo"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, env={**os.environ, **env})
        combined = (proc.stdout or "") + (proc.stderr or "")
        auth_errors = ["401", "Authentication Fails", "AuthenticationError",
                       "unauthorized", "Unauthorized", "invalid_api_key"]
        for kw in auth_errors:
            if kw.lower() in combined.lower():
                for code in ("401", "403"):
                    if code in combined:
                        return False, int(code)
                return False, "AUTH_FAILED"
        if "429" in combined or "RateLimit" in combined:
            return False, 429
        conn_errors = ["ConnectionError", "connection refused", "timeout"]
        for kw in conn_errors:
            if kw.lower() in combined.lower():
                return False, "CONNECTION_ERROR"
        for code in ("500", "502", "503", "504"):
            if code in combined:
                return False, int(code)
        if proc.returncode == 0 and (proc.stdout or "").strip():
            return True, 200
        elif proc.returncode == 0:
            return False, "EMPTY_RESPONSE"
        else:
            return False, f"EXIT_{proc.returncode}"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except FileNotFoundError:
        return False, "HERMES_CLI_NOT_FOUND"
    except Exception as e:
        return False, f"ERROR:{str(e)[:60]}"

# ── 表格渲染 ───────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS_SYM  = f"{GREEN}✅{RESET}"
FAIL_SYM  = f"{RED}❌{RESET}"
WARN_SYM  = f"{YELLOW}⚠️{RESET}"

STATUS_SYMBOLS = {
    "HEALTHY":   f"{GREEN}{BOLD}HEALTHY{RESET}",
    "KEY_INV":   f"{RED}{BOLD}KEY_INV{RESET}",
    "KEY_MISS":  f"{RED}{BOLD}KEY_MISS{RESET}",
    "CFG_INV":   f"{RED}{BOLD}CFG_INV{RESET}",
    "RATE_LIM":  f"{YELLOW}RATE_LIM{RESET}",
    "PROV_DOWN": f"{YELLOW}PROV_DOWN{RESET}",
    "NO_CLI":    f"{RED}{BOLD}NO_CLI{RESET}",
    "UNKNOWN":   f"{YELLOW}UNKNOWN{RESET}",
}

def compute_status(config_ok, cred_ok, smoke_ok, smoke_diag):
    if not config_ok:
        return "CFG_INV"
    if not cred_ok:
        return "KEY_MISS"
    if not smoke_ok:
        diag = smoke_diag
        if isinstance(diag, int):
            if diag in (401, 403): return "KEY_INV"
            elif diag == 429: return "RATE_LIM"
            elif diag >= 500: return "PROV_DOWN"
            else: return f"HTTP_{diag}"
        diag_str = str(diag)
        if "TIMEOUT" in diag_str or "CONNECTION" in diag_str:
            return "PROV_DOWN"
        if "AUTH" in diag_str or "INV" in diag_str:
            return "KEY_INV"
        if "CLI_NOT_FOUND" in diag_str:
            return "NO_CLI"
        return "UNKNOWN"
    return "HEALTHY"

def render_table(rows):
    col_widths = {"Profile": 10, "Config": 6, "Credential": 6, "Smoke Test": 12, "Status": 12}
    def cell(text, width):
        text = str(text)
        if len(text) > width - 1:
            text = text[:width - 2] + "…"
        return text.ljust(width)
    top = f"┌{'─' * (col_widths['Profile'] + 2)}┬{'─' * (col_widths['Config'] + 2)}┬{'─' * (col_widths['Credential'] + 2)}┬{'─' * (col_widths['Smoke Test'] + 2)}┬{'─' * (col_widths['Status'] + 2)}┐"
    header = f"│ {BOLD}{cell('Profile', col_widths['Profile'])}{RESET} │ {BOLD}{cell('Config', col_widths['Config'])}{RESET} │ {BOLD}{cell('Cred', col_widths['Credential'])}{RESET} │ {BOLD}{cell('Smoke Test', col_widths['Smoke Test'])}{RESET} │ {BOLD}{cell('Status', col_widths['Status'])}{RESET} │"
    sep2 = f"├{'─' * (col_widths['Profile'] + 2)}┼{'─' * (col_widths['Config'] + 2)}┼{'─' * (col_widths['Credential'] + 2)}┼{'─' * (col_widths['Smoke Test'] + 2)}┼{'─' * (col_widths['Status'] + 2)}┤"
    bottom = f"└{'─' * (col_widths['Profile'] + 2)}┴{'─' * (col_widths['Config'] + 2)}┴{'─' * (col_widths['Credential'] + 2)}┴{'─' * (col_widths['Smoke Test'] + 2)}┴{'─' * (col_widths['Status'] + 2)}┘"
    lines = [top, header, sep2]
    for row in rows:
        name = row["name"]
        config_sym = PASS_SYM if row["config_ok"] else FAIL_SYM
        cred_sym = PASS_SYM if row["cred_ok"] else FAIL_SYM
        if row["smoke_ok"]:
            smoke_str = f"{PASS_SYM} {row['smoke_diag']}"
        else:
            smoke_str = f"{FAIL_SYM} {row['smoke_diag']}"
        status_str = STATUS_SYMBOLS.get(row["status"], row["status"])
        def rpad(s, w):
            plain = re.sub(r'\033\[[0-9;]*m', '', str(s))
            return str(s) + " " * max(0, w - len(plain))
        line = (f"│ {rpad(name, col_widths['Profile'])} "
                f"│ {rpad(config_sym, col_widths['Config'])} "
                f"│ {rpad(cred_sym, col_widths['Credential'])} "
                f"│ {rpad(smoke_str, col_widths['Smoke Test'])} "
                f"│ {rpad(status_str, col_widths['Status'])} │")
        lines.append(line)
    lines.append(bottom)
    return "\n".join(lines)

def render_json(rows):
    output = []
    for row in rows:
        output.append({
            "profile": row["name"],
            "config_valid": row["config_ok"],
            "config_note": row["config_note"],
            "credential_valid": row["cred_ok"],
            "credential_note": row["cred_note"],
            "smoke_test_ok": row["smoke_ok"],
            "smoke_test_diag": row["smoke_diag"],
            "status": row["status"],
        })
    return json.dumps(output, indent=2, ensure_ascii=False)

def render_issues(rows):
    issues = []
    unhealthy = [r for r in rows if r["status"] != "HEALTHY"]
    if not unhealthy:
        return [f"{GREEN}{BOLD}五部安好，无异常。{RESET}"]
    for row in unhealthy:
        detail_parts = []
        if not row["config_ok"]:
            detail_parts.append(f"config: {row['config_note']}")
        if not row["cred_ok"]:
            detail_parts.append(f"credential: {row['cred_note']}")
        if not row["smoke_ok"]:
            detail_parts.append(f"smoke: {row['smoke_diag']}")
        issues.append(f"  {FAIL_SYM} {row['name']} ({row['status']}): {', '.join(detail_parts)}")
    return issues

# ── 主流程 ─────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="五部 Profile 健康检查")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--profiles", nargs="+", default=PROFILES)
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    start = time.time()
    rows = []

    for profile in args.profiles:
        cfg = read_config(profile)
        config_ok, config_note = check_config_validity(cfg)
        provider = ""
        if cfg and isinstance(cfg.get("model"), dict):
            provider = cfg["model"].get("provider", "")
        cred_ok, cred_note = (False, "N/A")
        if config_ok and provider:
            cred_ok, cred_note = check_credential(provider, env)
        elif not config_ok:
            cred_note = "skip:config_invalid"
        smoke_ok, smoke_diag = (False, "skip")
        if config_ok and cred_ok:
            smoke_ok, smoke_diag = check_smoke(profile, env, args.timeout)
        status = compute_status(config_ok, cred_ok, smoke_ok, smoke_diag)
        rows.append(dict(name=profile, config_ok=config_ok, config_note=config_note,
                         cred_ok=cred_ok, cred_note=cred_note,
                         smoke_ok=smoke_ok, smoke_diag=smoke_diag, status=status))

    elapsed = time.time() - start
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    if args.json:
        output = {"timestamp": timestamp, "elapsed_seconds": round(elapsed, 1),
                  "profiles": [json.loads(render_json([r]))[0] for r in rows]}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\n{CYAN}{BOLD}Profile Health Report — {timestamp}{RESET}\n")
        print(render_table(rows))
        print(f"{BOLD}Issues:{RESET}")
        for issue in render_issues(rows):
            print(issue)
        print(f"\n耗时：{elapsed:.1f}s")

    healthy = all(r["status"] == "HEALTHY" for r in rows)
    sys.exit(0 if healthy else 1)

if __name__ == "__main__":
    main()
