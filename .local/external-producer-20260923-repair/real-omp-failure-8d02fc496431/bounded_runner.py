import json, os, subprocess
from pathlib import Path
child = subprocess.Popen(["/bin/sleep", "45"])
root = Path(__file__).resolve().parent
ids = {"pid": os.getpid(), "pgid": os.getpgrp(), "sid": os.getsid(0), "ppid": os.getppid(), "child_ppid": os.getpid(), "child": child.pid, "child_pgid": os.getpgid(child.pid), "child_sid": os.getsid(child.pid)}
(root / "ready.tmp").write_text(json.dumps(ids))
os.replace(root / "ready.tmp", root / "ready.json")
try:
    child.wait(timeout=50)
finally:
    if child.poll() is None:
        child.terminate()
        child.wait(timeout=3)
