"""marker_runner.py 的隔离与失败边界契约：真实子进程 + tmp_path，不 mock、不装 Marker。

不依赖排版引擎依赖；不访问网络；HOME 指向 tmp，绝不触碰真实 ~/.venvs。
"""
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parent.parent / "scripts" / "marker_runner.py"
BIN = "Scripts" if os.name == "nt" else "bin"


def _run(args, home, env_extra=None, cwd=None):
    env = dict(os.environ)
    env.pop("JZ2PDF_MARKER_VENV", None)
    env.pop("JZ2PDF_MARKER_PYTHONPATH", None)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(RUNNER)] + list(args), capture_output=True,
                          text=True, env=env, cwd=cwd, timeout=120)


def _snapshot(root):
    return sorted((str(p.relative_to(root)), p.read_bytes() if p.is_file() else None)
                  for p in root.rglob("*"))


def _modern_python():
    if (3, 10) <= sys.version_info[:2] < (4, 0):
        return sys.executable
    for name in ("python3.13", "python3.12", "python3.11", "python3.10"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _write_dist(site, name, version):
    info = site / f"{name.replace('-', '_')}-{version}.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")


def _make_exe(path, body):
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def fake_marker_venv(tmp_path):
    """真实 venv（>=3.10），只写入与 requirements 精确版本一致的元数据与核心入口文件。"""
    py = _modern_python()
    if py is None:
        pytest.skip("本机没有 Python >=3.10，无法构造 Marker venv 形态")
    venv_dir = tmp_path / "marker-venv"
    subprocess.run([py, "-m", "venv", "--without-pip", str(venv_dir)], check=True, timeout=120)
    vpy = venv_dir / BIN / ("python.exe" if os.name == "nt" else "python")
    site = Path(subprocess.run([str(vpy), "-I", "-c",
                                "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
                               capture_output=True, text=True, check=True).stdout.strip())
    _write_dist(site, "marker-pdf", "2.0.0")
    _write_dist(site, "surya-ocr", "0.22.1")
    for entry in ("marker", "marker_single"):
        _make_exe(venv_dir / BIN / entry, "#!/bin/sh\nexit 0\n")
    return venv_dir


def test_preflight_missing_env_fails_without_creating_it(tmp_path):
    target = tmp_path / "absent-marker"
    proc = _run(["preflight", "--json"], tmp_path, {"JZ2PDF_MARKER_VENV": str(target)})
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["overall"] == "fail"
    assert any(c["name"] == "venv:python" and c["status"] == "fail" for c in report["checks"])
    assert not target.exists()


@pytest.mark.parametrize("op", ["setup", "preflight", "single"])
def test_explicit_empty_venv_value_is_usage_error(tmp_path, op):
    work = tmp_path / "cwd"
    work.mkdir()
    proc = _run([op], tmp_path, {"JZ2PDF_MARKER_VENV": ""}, cwd=work)
    assert proc.returncode == 2
    assert list(work.iterdir()) == []


def test_setup_refuses_non_empty_non_venv_directory(tmp_path):
    target = tmp_path / "user-data"
    target.mkdir()
    (target / "notes.txt").write_text("keep me")
    before = _snapshot(target)
    proc = _run(["setup"], tmp_path, {"JZ2PDF_MARKER_VENV": str(target)})
    assert proc.returncode == 1
    assert _snapshot(target) == before


@pytest.mark.parametrize("rel", [".venvs/pdf-skill", ".venvs/pdf-skill/nested", ".venvs"])
def test_setup_refuses_legacy_venv_and_its_relatives(tmp_path, rel):
    home = tmp_path / "home"
    legacy = home / ".venvs" / "pdf-skill"
    legacy.mkdir(parents=True)
    (legacy / "pyvenv.cfg").write_text("include-system-site-packages = false\nversion = 3.9.6\n")
    # 只比对 ~/.venvs：系统 Python 可能按 HOME 写自己的字节码缓存，与 runner 无关
    before = _snapshot(home / ".venvs")
    proc = _run(["setup"], home, {"JZ2PDF_MARKER_VENV": str(home / rel)})
    assert proc.returncode == 2
    assert _snapshot(home / ".venvs") == before


@pytest.mark.skipif(os.name == "nt", reason="用 POSIX shell 包装解释器")
def test_setup_refuses_interpreter_whose_prefix_is_elsewhere(tmp_path):
    real = tmp_path / "other-venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(real)], check=True, timeout=120)
    fake = tmp_path / "fake-venv"
    (fake / "bin").mkdir(parents=True)
    (fake / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    log = tmp_path / "calls.log"
    _make_exe(fake / "bin" / "python",
              f'#!/bin/sh\necho "$@" >> "{log}"\nexec "{real}/bin/python" "$@"\n')
    proc = _run(["setup"], tmp_path, {"JZ2PDF_MARKER_VENV": str(fake)})
    assert proc.returncode == 1
    assert "prefix" in proc.stderr
    calls = log.read_text().splitlines()
    assert calls, "隔离探测应当执行过"
    assert not any("-m pip install" in line for line in calls)


def test_run_env_ignores_parent_pythonpath_and_scopes_extension(tmp_path, fake_marker_venv):
    shadow = tmp_path / "shadow"
    _write_dist(shadow, "marker-pdf", "9.9.9")  # 若进入 sys.path 会顶替真实版本
    base = {"JZ2PDF_MARKER_VENV": str(fake_marker_venv)}
    code = ("import json,sys\nfrom importlib import metadata\n"
            "print(json.dumps({'path': sys.path, 'prefix': sys.prefix,"
            " 'marker': metadata.version('marker-pdf')}))")

    polluted = dict(base, PYTHONPATH=str(shadow))
    pre = _run(["preflight", "--json"], tmp_path, polluted)
    assert pre.returncode == 0, pre.stdout + pre.stderr
    seen = json.loads(_run(["python", "--", "-c", code], tmp_path, polluted).stdout)
    assert str(shadow) not in seen["path"]
    assert seen["marker"] == "2.0.0"
    assert Path(seen["prefix"]).resolve() == fake_marker_venv.resolve()

    scoped = dict(base, JZ2PDF_MARKER_PYTHONPATH=str(shadow))
    pre = _run(["preflight", "--json"], tmp_path, scoped)
    assert pre.returncode == 0, pre.stdout + pre.stderr
    seen = json.loads(_run(["python", "--", "-c", code], tmp_path, scoped).stdout)
    assert str(shadow) in seen["path"]
    assert seen["marker"] == "9.9.9"

    rel = _run(["python", "--", "-c", "pass"], tmp_path, dict(base, JZ2PDF_MARKER_PYTHONPATH="rel/dir"))
    assert rel.returncode == 2


def test_run_returns_upstream_exit_code(tmp_path, fake_marker_venv):
    proc = _run(["python", "--", "-c", "raise SystemExit(7)"], tmp_path,
                {"JZ2PDF_MARKER_VENV": str(fake_marker_venv)})
    assert proc.returncode == 7


@pytest.mark.skipif(os.name == "nt", reason="POSIX PATH 哨兵")
def test_gui_without_optional_deps_never_borrows_parent_streamlit(tmp_path, fake_marker_venv):
    decoy = tmp_path / "decoy-bin"
    decoy.mkdir()
    hit = tmp_path / "decoy-ran"
    for name in ("streamlit", "marker_gui"):
        _make_exe(decoy / name, f'#!/bin/sh\ntouch "{hit}"\n')
    env = {"JZ2PDF_MARKER_VENV": str(fake_marker_venv),
           "PATH": str(decoy) + os.pathsep + os.environ.get("PATH", "")}
    proc = _run(["gui", "--"], tmp_path, env)
    assert proc.returncode == 1
    assert "--gui" in proc.stderr
    assert not hit.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX 进程组信号")
def test_sigterm_stops_owned_app_group_promptly(tmp_path, fake_marker_venv):
    env = dict(os.environ, HOME=str(tmp_path), JZ2PDF_MARKER_VENV=str(fake_marker_venv))
    code = "import os,time; print(os.getpid(), flush=True); time.sleep(60)"
    # 模拟脚本里 `&` 后台启动：runner 继承 SIGINT=SIG_IGN，上游仍须响应转发的 SIGINT
    runner = subprocess.Popen([sys.executable, str(RUNNER), "python", "--", "-c", code],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                              preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN))
    child = int(runner.stdout.readline())
    runner.send_signal(signal.SIGTERM)
    assert runner.wait(timeout=20) == 143  # 上游以 SIGINT 优雅退出，无需等 30s 升级
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)
