"""Fast, 零副作用的漂移检测逻辑测试。

全在 tmp_path + subprocess(diff/grep), 绝不触碰真 canonical/runtime。
验证 pdf-drift-gate.sh 依赖的核心判定(内容 diff 过滤 build 噪声 / 红线 grep)是可靠的。
"""
import subprocess
from pathlib import Path


def _diff_filtered(a, b):
    """模拟 gate 第1步: diff -rq 过滤 __pycache__/.pyc 噪声后剩余差异行。"""
    proc = subprocess.run(["diff", "-rq", str(a), str(b)], capture_output=True, text=True)
    return [l for l in proc.stdout.splitlines() if "__pycache__" not in l and ".pyc" not in l]


def test_identical_trees_no_drift(tmp_path):
    src, can = tmp_path / "src", tmp_path / "can"
    src.mkdir(); can.mkdir()
    (src / "f.py").write_text("x=1\n"); (can / "f.py").write_text("x=1\n")
    assert _diff_filtered(src, can) == []


def test_pycache_noise_ignored(tmp_path):
    src, can = tmp_path / "src", tmp_path / "can"
    src.mkdir(); can.mkdir()
    (src / "f.py").write_text("x=1\n"); (can / "f.py").write_text("x=1\n")
    (can / "__pycache__").mkdir(); (can / "__pycache__" / "f.pyc").write_text("blob")
    assert _diff_filtered(src, can) == []  # 仅噪声 → 视为无漂移


def test_803_hack_detected(tmp_path):
    src, can = tmp_path / "src", tmp_path / "can"
    src.mkdir(); can.mkdir()
    (src / "m.py").write_text("const b = await chromium.launch();\n")
    (can / "m.py").write_text("const b = await chromium.launch({ channel: 'chrome' });\n")
    assert _diff_filtered(src, can)  # 非空 = 抓到 803 漂移


def test_redline_grep_channel_chrome(tmp_path):
    can = tmp_path / "can" / "scripts"
    can.mkdir(parents=True)
    (can / "m.py").write_text("await chromium.launch({ channel: 'chrome', headless: true });\n")
    proc = subprocess.run(["grep", "-rn", "channel: *'chrome'", str(can)],
                          capture_output=True, text=True)
    assert proc.returncode == 0  # 命中红线


def test_redline_grep_clean_after_parameterized(tmp_path):
    """参数化后(executablePath 而非 channel:'chrome') 红线 grep 不应命中。"""
    can = tmp_path / "can" / "scripts"
    can.mkdir(parents=True)
    (can / "m.py").write_text('chromium.launch({ executablePath: "/x/chrome" })\n')
    proc = subprocess.run(["grep", "-rn", "channel: *'chrome'", str(can)],
                          capture_output=True, text=True)
    assert proc.returncode != 0  # 无命中
