#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-acp-probe.sh —— OD-OMP-2 交互式 ACP 方言探测器
#
# 【交互式探测器】本脚本以交互模式拉起 `omp acp`，先发送 initialize，
#   读取 agentCapabilities.sessionCapabilities 后再选择下一步探测方法：
#   OMP 16.3.x 方言优先探 `session/list`；标准方言探 `session/new` +
#   `session/prompt`。本脚本只产出证据，不改默认通道。
#
# 证据目录输出（--out <dir>）：summary.json / result.md / stdin.ndjson /
#   stdout.ndjson / stderr.log / timeline.ndjson / process.json
#
# 参数：
#   --out <dir>             证据目录（缺省：/tmp/omp-acp-probe-XXXXXX）
#   --timeout <秒>          总超时秒数（缺省 30）
#   --mock-omp1632          零 token：模拟 OMP 16.3.2 capabilities(list/fork/resume/close)
#   --mock-session-new      零 token：模拟标准 session/new + session/prompt 成功
#   --mock-initialize-only  零 token：模拟仅 initialize，无 capabilities
#   --mock-timeout          零 token：模拟启动/超时失败
#   -h|--help               打印本头注
#
# 退出码：0=dialect_detected · 2=initialize_only/protocol_incompatible ·
#         3=failed_to_start_or_timeout · 1=参数错误或内部异常
# ─────────────────────────────────────────────────────────────────
set -uo pipefail
exec python3 - "$@" <<'PY'
import argparse, json, os, select, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path

STAT_DIALECT = "dialect_detected"
STAT_INIT_ONLY = "initialize_only"
STAT_INCOMPAT = "protocol_incompatible"
STAT_FAILED = "failed_to_start_or_timeout"

METHOD_INIT = {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientInfo":{"name":"omp-acp-probe","version":"0.2.0"},"capabilities":{}}}
METHOD_INITIALIZED = {"jsonrpc":"2.0","method":"initialized","params":{}}
METHOD_LIST = {"jsonrpc":"2.0","id":2,"method":"session/list","params":{}}
METHOD_NEW = {"jsonrpc":"2.0","id":2,"method":"session/new","params":{"cwd":".","mcpServers":[]}}
METHOD_PROMPT = {"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{"sessionId":"omp-acp-probe-session","prompt":[{"type":"text","text":"Reply with exactly: probe-ok. Do not add thinking."}]}}


def now(): return int(time.time())

def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, separators=(",",":")) + "\n")

def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",",":")) + "\n")

def append_line(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")

def bytes_of(path):
    try: return os.path.getsize(path)
    except OSError: return 0

def parse_json_lines(path):
    out=[]
    p=Path(path)
    if not p.exists(): return out
    for line in p.read_text(errors="replace").splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def extract_initialize(objs):
    for o in objs:
        if o.get("id") == 1 and isinstance(o.get("result"), dict):
            return o["result"]
    return {}

def cap_keys(init_result):
    caps = (((init_result.get("agentCapabilities") or {}).get("sessionCapabilities")) or {})
    if isinstance(caps, dict): return sorted(caps.keys())
    if isinstance(caps, list): return sorted(str(x) for x in caps)
    return []

def result_has_id(objs, id_):
    return any(o.get("id") == id_ and ("result" in o or "error" in o) for o in objs)

def detect_prompt_update(objs, text_path):
    text = Path(text_path).read_text(errors="replace") if Path(text_path).exists() else ""
    return any((o.get("method") == "session/update") for o in objs) or "probe-ok" in text or result_has_id(objs, 3)

def make_summary(status, reason, sent, succeeded, init_result, outdir, exit_code, mock=None, elapsed=0, proc_exit=None, dialect="unknown"):
    objs = parse_json_lines(outdir/"stdout.ndjson")
    keys = cap_keys(init_result)
    summary = {
        "status": status,
        "reason": reason,
        "protocol_version": init_result.get("protocolVersion"),
        "agent_name": ((init_result.get("agentInfo") or {}).get("name")),
        "agent_version": ((init_result.get("agentInfo") or {}).get("version")),
        "dialect": dialect,
        "initialize_ok": bool(init_result.get("protocolVersion")),
        "capabilities_observed": bool(keys),
        "session_capabilities": keys,
        "probe_methods_sent": sent,
        "probe_methods_succeeded": succeeded,
        "session_list_observed": result_has_id(objs, 2) if "session/list" in sent else False,
        "session_new_ok": result_has_id(objs, 2) if "session/new" in sent else False,
        "session_prompt_ok": detect_prompt_update(objs, outdir/"stdout.ndjson") if "session/prompt" in sent else False,
        "elapsed_sec": elapsed,
        "stdin_bytes": bytes_of(outdir/"stdin.ndjson"),
        "stdout_bytes": bytes_of(outdir/"stdout.ndjson"),
        "stderr_bytes": bytes_of(outdir/"stderr.log"),
        "exit_code": proc_exit if proc_exit is not None else exit_code,
        "mock": mock,
    }
    write_json(outdir/"summary.json", summary)
    result = f"""# OMP ACP Interactive Probe — OD-OMP-2

**status**: {status}
**reason**: {reason}
**dialect**: {dialect}
**exit_code**: {summary['exit_code']}
**elapsed**: {elapsed}s

## Agent
- name: {summary['agent_name']}
- version: {summary['agent_version']}
- protocol_version: {summary['protocol_version']}

## Capabilities
- session_capabilities: {', '.join(keys) if keys else '(none)'}

## Probe methods
- sent: {', '.join(sent) if sent else '(none)'}
- succeeded: {', '.join(succeeded) if succeeded else '(none)'}

## Evidence files
- `stdin.ndjson`
- `stdout.ndjson`
- `stderr.log`
- `timeline.ndjson`
- `process.json`
- `summary.json`

---
本探针只产出证据，不修改 call-omp 默认通道。
"""
    (outdir/"result.md").write_text(result)
    return exit_code

def send(proc, outdir, obj, sent):
    line = json.dumps(obj, ensure_ascii=False, separators=(",",":"))
    proc.stdin.write(line + "\n")
    proc.stdin.flush()
    append_line(outdir/"stdin.ndjson", line)
    sent.append(obj.get("method", "<unknown>"))
    append_jsonl(outdir/"timeline.ndjson", {"ts":now(),"event":"stdin_sent","method":obj.get("method"),"id":obj.get("id")})

def read_line(proc, outdir, timeout, succeeded):
    if proc.stdout is None: return None
    r, _, _ = select.select([proc.stdout], [], [], timeout)
    if not r: return None
    line = proc.stdout.readline()
    if not line: return None
    append_line(outdir/"stdout.ndjson", line)
    append_jsonl(outdir/"timeline.ndjson", {"ts":now(),"event":"stdout_line","bytes":len(line.encode())})
    try:
        obj=json.loads(line)
        if isinstance(obj.get("id"), int):
            if obj["id"] == 1: succeeded.append("initialize")
            elif obj["id"] == 2:
                # caller interprets whether this was list/new
                pass
            elif obj["id"] == 3: succeeded.append("session/prompt")
        if obj.get("method") == "session/update" and "session/update" not in succeeded:
            succeeded.append("session/update")
    except Exception:
        pass
    return line

def setup_out(path):
    outdir = Path(path) if path else Path(tempfile.mkdtemp(prefix="omp-acp-probe."))
    outdir.mkdir(parents=True, exist_ok=True)
    for f in ["summary.json","result.md","stdin.ndjson","stdout.ndjson","stderr.log","timeline.ndjson","process.json"]:
        (outdir/f).write_text("")
    return outdir.resolve()

def mock_run(outdir, mock):
    sent=[]; succeeded=[]; init={}; dialect="unknown"; status=STAT_INCOMPAT; reason=""; rc=2
    if mock == "timeout":
        (outdir/"stderr.log").write_text("mock stderr: timeout exceeded\n")
        write_json(outdir/"process.json", {"omp_path":"/mock/omp","version":"mock","pid":None,"exit_code":3})
        append_jsonl(outdir/"timeline.ndjson", {"ts":now(),"event":"mock_mode_entered","mock":mock})
        return make_summary(STAT_FAILED, "mock_timeout", [], [], {}, outdir, 3, mock=mock, dialect="unknown", proc_exit=3)
    append_jsonl(outdir/"timeline.ndjson", {"ts":now(),"event":"mock_mode_entered","mock":mock})
    if mock == "omp1632":
        init={"protocolVersion":1,"agentInfo":{"name":"oh-my-pi","version":"16.3.2"},"agentCapabilities":{"sessionCapabilities":{"list":{},"fork":{},"resume":{},"close":{}}}}
        for obj in [METHOD_INIT, METHOD_INITIALIZED, METHOD_LIST]: append_line(outdir/"stdin.ndjson", json.dumps(obj,separators=(",",":"))); sent.append(obj["method"])
        append_line(outdir/"stdout.ndjson", json.dumps({"jsonrpc":"2.0","id":1,"result":init},separators=(",",":")))
        append_line(outdir/"stdout.ndjson", json.dumps({"jsonrpc":"2.0","id":2,"result":{"sessions":[]}},separators=(",",":")))
        succeeded=["initialize","session/list"]; status=STAT_DIALECT; reason="omp_session_capabilities_detected"; dialect="omp-session-capabilities"; rc=0
    elif mock == "session-new":
        init={"protocolVersion":1,"agentInfo":{"name":"mock-omp","version":"standard"},"agentCapabilities":{"sessionCapabilities":{"new":{},"prompt":{}}}}
        for obj in [METHOD_INIT, METHOD_INITIALIZED, METHOD_NEW, METHOD_PROMPT]: append_line(outdir/"stdin.ndjson", json.dumps(obj,separators=(",",":"))); sent.append(obj["method"])
        append_line(outdir/"stdout.ndjson", json.dumps({"jsonrpc":"2.0","id":1,"result":init},separators=(",",":")))
        append_line(outdir/"stdout.ndjson", json.dumps({"jsonrpc":"2.0","id":2,"result":{"sessionId":"omp-acp-probe-session"}},separators=(",",":")))
        append_line(outdir/"stdout.ndjson", json.dumps({"jsonrpc":"2.0","id":3,"result":{"ok":True}},separators=(",",":")))
        succeeded=["initialize","session/new","session/prompt"]; status=STAT_DIALECT; reason="standard_session_new_prompt_detected"; dialect="standard-session-new-prompt"; rc=0
    elif mock == "initialize-only":
        init={"protocolVersion":1,"agentInfo":{"name":"early-omp","version":"unknown"}}
        for obj in [METHOD_INIT, METHOD_INITIALIZED]: append_line(outdir/"stdin.ndjson", json.dumps(obj,separators=(",",":"))); sent.append(obj["method"])
        append_line(outdir/"stdout.ndjson", json.dumps({"jsonrpc":"2.0","id":1,"result":init},separators=(",",":")))
        succeeded=["initialize"]; status=STAT_INIT_ONLY; reason="initialize_ok_no_session_capabilities"; dialect="unknown"; rc=2
    write_json(outdir/"process.json", {"omp_path":"/mock/omp","version":"mock-v16.3.2","pid":None,"exit_code":rc})
    return make_summary(status, reason, sent, succeeded, init, outdir, rc, mock=mock, dialect=dialect, proc_exit=rc)

def real_run(outdir, timeout):
    omp = os.environ.get("OMP_BIN") or shutil.which("omp") or ("/opt/homebrew/bin/omp" if Path("/opt/homebrew/bin/omp").exists() else None) or ("/usr/local/bin/omp" if Path("/usr/local/bin/omp").exists() else None)
    if not omp:
        write_json(outdir/"process.json", {"omp_path":None,"version":None,"pid":None,"exit_code":3})
        return make_summary(STAT_FAILED, "omp_binary_not_found", [], [], {}, outdir, 3, dialect="unknown", proc_exit=3)
    try:
        version = subprocess.run([omp,"--version"], text=True, capture_output=True, timeout=5).stdout.splitlines()[0]
    except Exception:
        version = "unknown"
    start=time.time(); sent=[]; succeeded=[]; init={}; dialect="unknown"; proc_exit=None
    append_jsonl(outdir/"timeline.ndjson", {"ts":now(),"event":"omp_acp_spawn","path":omp,"version":version})
    proc = subprocess.Popen([omp,"acp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    write_json(outdir/"process.json", {"omp_path":omp,"version":version,"pid":proc.pid,"exit_code":None})
    try:
        send(proc,outdir,METHOD_INIT,sent)
        line=read_line(proc,outdir,min(5,timeout),succeeded)
        objs=parse_json_lines(outdir/"stdout.ndjson")
        init=extract_initialize(objs)
        keys=cap_keys(init)
        if init and "initialize" not in succeeded: succeeded.append("initialize")
        if not init:
            reason="initialize_response_missing_or_invalid"; status=STAT_INCOMPAT; rc=2
        else:
            send(proc,outdir,METHOD_INITIALIZED,sent)
            if "list" in keys:
                dialect="omp-session-capabilities"
                send(proc,outdir,METHOD_LIST,sent)
                # OMP 16.3.2 may close after initialize; wait briefly for id=2 but dialect is already identified.
                line2=read_line(proc,outdir,min(3,max(1,timeout-int(time.time()-start))),succeeded)
                if result_has_id(parse_json_lines(outdir/"stdout.ndjson"),2):
                    succeeded.append("session/list")
                status=STAT_DIALECT; reason="omp_session_capabilities_detected"; rc=0
            elif {"new","prompt"}.intersection(set(keys)):
                dialect="standard-session-new-prompt"
                send(proc,outdir,METHOD_NEW,sent)
                read_line(proc,outdir,3,succeeded)
                if result_has_id(parse_json_lines(outdir/"stdout.ndjson"),2) and "session/new" not in succeeded: succeeded.append("session/new")
                send(proc,outdir,METHOD_PROMPT,sent)
                read_line(proc,outdir,3,succeeded)
                if detect_prompt_update(parse_json_lines(outdir/"stdout.ndjson"), outdir/"stdout.ndjson") and "session/prompt" not in succeeded: succeeded.append("session/prompt")
                status=STAT_DIALECT; reason="standard_session_capabilities_detected"; rc=0
            else:
                status=STAT_INIT_ONLY; reason="initialize_ok_no_session_capabilities"; rc=2
    except BrokenPipeError:
        status=STAT_DIALECT if init and "list" in cap_keys(init) else STAT_INCOMPAT
        reason="process_closed_after_initialize" if init else "broken_pipe_before_initialize"
        rc=0 if status == STAT_DIALECT else 2
    except Exception as e:
        (outdir/"stderr.log").write_text(str(e)+"\n")
        status=STAT_FAILED; reason="internal_exception"; rc=3
    finally:
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try: proc.terminate()
            except Exception: pass
            try: proc.wait(timeout=1)
            except Exception:
                try: proc.kill()
                except Exception: pass
        try:
            if proc.stderr:
                err = proc.stderr.read()
                if err: (outdir/"stderr.log").write_text(err)
        except Exception:
            pass
        proc_exit=proc.poll()
        write_json(outdir/"process.json", {"omp_path":omp,"version":version,"pid":proc.pid,"exit_code":proc_exit})
    elapsed=int(time.time()-start)
    return make_summary(status, reason, sent, succeeded, init, outdir, rc, elapsed=elapsed, proc_exit=proc_exit, dialect=dialect)

def main(argv):
    ap=argparse.ArgumentParser(add_help=False)
    ap.add_argument("--out")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--mock-omp1632", action="store_true")
    ap.add_argument("--mock-session-new", action="store_true")
    ap.add_argument("--mock-initialize-only", action="store_true")
    ap.add_argument("--mock-timeout", action="store_true")
    ap.add_argument("-h","--help", action="store_true")
    ns=ap.parse_args(argv)
    if ns.help:
        print(Path(sys.argv[0]).read_text().split("exec python3",1)[0] if Path(sys.argv[0]).exists() else "omp-acp-probe.sh")
        return 0
    mocks=[("omp1632",ns.mock_omp1632),("session-new",ns.mock_session_new),("initialize-only",ns.mock_initialize_only),("timeout",ns.mock_timeout)]
    enabled=[name for name,on in mocks if on]
    if len(enabled)>1:
        print("omp-acp-probe: mock modes are mutually exclusive", file=sys.stderr); return 1
    outdir=setup_out(ns.out)
    if enabled: return mock_run(outdir, enabled[0])
    return real_run(outdir, ns.timeout)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PY
