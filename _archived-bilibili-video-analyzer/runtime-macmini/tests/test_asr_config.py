# -*- coding: utf-8 -*-
"""P1 回归: ASR provider/model/language 配置。

锁定行为:
  - resolve_asr_config 解析 BILI_ASR_* 环境变量，非法 provider/language 抛 ValueError
  - provider=auto  : H200 HTTP ASR 优先，失败再 whisper.cpp → mlx-whisper
  - provider=h200_asr: 只走 H200 HTTP ASR，绝不调用本机 whisper/mlx
  - provider=whisper_cpp: 只走 whisper.cpp，绝不调用 mlx helper
  - provider=mlx_whisper: 只走 mlx-whisper，绝不调用 whisper.cpp
  - BILI_ASR_ENDPOINT 覆盖默认 H200 endpoint
  - BILI_ASR_MODEL_PATH 覆盖默认 VoiceInk whisper.cpp 模型路径
  - BILI_ASR_MODEL / BILI_ASR_MODEL_PATH 透传给 mlx helper 命令行
  - BILI_ASR_LANGUAGE 同时到达 H200 / whisper.cpp / mlx helper
  - 对外标识不暴露本地绝对路径
  - 全程 monkeypatch subprocess/os.path.exists，无真实 ffmpeg/whisper/mlx/网络
"""

import os

import pytest

import fetch_subtitle_auto as fsa


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text or ""

    def json(self):
        return self._payload


def _patch_no_duration(monkeypatch):
    """跳过 ffprobe 时长检测（否则会起真实子进程）。"""
    monkeypatch.setattr(fsa, "check_video_duration", lambda *a, **k: None)


def _install_fake_subprocess(monkeypatch, behavior):
    """安装捕获式 subprocess.run。

    behavior(cmd) -> FakeProc。所有命令都被记录到 calls。
    """
    calls = []

    def fake_run(cmd, *a, **k):
        calls.append(list(cmd))
        return behavior(cmd)

    monkeypatch.setattr(fsa.subprocess, "run", fake_run)
    return calls


def _install_fake_h200(monkeypatch, status_code=500, text="", payload=None):
    """安装捕获式 requests.post，默认让 H200 失败，避免真实网络。"""
    calls = []

    def fake_post(url, *a, **k):
        calls.append({"url": url, "args": a, "kwargs": k})
        return FakeResponse(status_code=status_code, payload=payload or {}, text=text)

    monkeypatch.setattr(fsa.requests, "post", fake_post)
    return calls


def _cmd_kind(cmd):
    """粗分类 subprocess 命令。"""
    if not cmd:
        return "empty"
    head = cmd[0]
    if head == "ffmpeg":
        return "ffmpeg"
    if head == "whisper-cli":
        return "whisper_cpp"
    if head == "/usr/bin/python3" and any("mlx_transcribe.py" in str(c) for c in cmd):
        return "mlx"
    if head == "ffprobe":
        return "ffprobe"
    return "other"


# ---------- resolve_asr_config ----------

def test_default_config_is_auto_zh():
    cfg = fsa.resolve_asr_config(env={})
    assert cfg.provider == "auto"
    assert cfg.language == "zh"
    assert cfg.model is None
    assert cfg.model_path is None
    assert cfg.endpoint == fsa.DEFAULT_H200_ASR_ENDPOINT


def test_invalid_provider_rejected():
    with pytest.raises(ValueError):
        fsa.resolve_asr_config(env={"BILI_ASR_PROVIDER": "bogus"})


def test_invalid_language_rejected():
    with pytest.raises(ValueError):
        fsa.resolve_asr_config(env={"BILI_ASR_LANGUAGE": "fr"})


def test_config_reads_all_env_vars():
    cfg = fsa.resolve_asr_config(env={
        "BILI_ASR_PROVIDER": "mlx_whisper",
        "BILI_ASR_MODEL": "mlx-community/whisper-tiny",
        "BILI_ASR_MODEL_PATH": "/Users/foo/models/snap",
        "BILI_ASR_LANGUAGE": "en",
        "BILI_ASR_ENDPOINT": "http://asr.example/transcribe",
    })
    assert cfg.provider == "mlx_whisper"
    assert cfg.model == "mlx-community/whisper-tiny"
    assert cfg.model_path == "/Users/foo/models/snap"
    assert cfg.language == "en"
    assert cfg.endpoint == "http://asr.example/transcribe"


# ---------- provider=auto ----------

def test_auto_h200_success_skips_local_providers(monkeypatch, tmp_path):
    """auto 默认先走 H200；H200 成功后不再调用 whisper.cpp / mlx。"""
    _patch_no_duration(monkeypatch)
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake-audio")
    out = tmp_path / "out.txt"
    h200_calls = _install_fake_h200(
        monkeypatch,
        status_code=200,
        payload={"text": "H200 转录成功", "language": "Chinese"},
    )
    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="auto", model=None, model_path=None, language="zh")

    engine = fsa.transcribe_audio(str(audio), str(out), config=cfg)

    assert engine == "h200-asr"
    assert out.read_text(encoding="utf-8") == "H200 转录成功"
    assert h200_calls[0]["url"] == fsa.DEFAULT_H200_ASR_ENDPOINT
    assert h200_calls[0]["kwargs"]["data"]["language"] == "Chinese"
    assert calls == []


def test_auto_long_audio_uses_h200_chunks(monkeypatch, tmp_path):
    """长音频默认切成 5 分钟 chunk 送 H200，避免整段超时/失败。"""
    monkeypatch.setattr(fsa, "check_video_duration", lambda *a, **k: 1200.0)  # 20min
    audio = tmp_path / "long.m4a"
    audio.write_bytes(b"fake-long-audio")
    out = tmp_path / "out.txt"

    def fake_run(cmd, *a, **k):
        # ffmpeg segment 命令最后一个参数是 chunk 输出 pattern
        if cmd and cmd[0] == "ffmpeg" and "segment" in cmd:
            pattern = cmd[-1]
            import pathlib
            pathlib.Path(pattern.replace("%03d", "000")).write_bytes(b"chunk0")
            pathlib.Path(pattern.replace("%03d", "001")).write_bytes(b"chunk1")
            return FakeProc(returncode=0)
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(fsa.subprocess, "run", fake_run)

    posts = []

    def fake_post(url, *a, **k):
        filename = k["files"]["file"][0]
        posts.append(filename)
        return FakeResponse(
            status_code=200,
            payload={"text": f"转录-{filename}", "language": "Chinese"},
        )

    monkeypatch.setattr(fsa.requests, "post", fake_post)

    engine = fsa.transcribe_audio(str(audio), str(out), config=fsa.AsrConfig(
        provider="auto", model=None, model_path=None, language="zh"
    ))

    assert engine == "h200-asr-chunked"
    assert posts == ["chunk_000.wav", "chunk_001.wav"]
    text = out.read_text(encoding="utf-8")
    assert "## Chunk 1" in text
    assert "转录-chunk_000.wav" in text
    assert "## Chunk 2" in text
    assert "转录-chunk_001.wav" in text


def test_auto_tries_h200_then_whisper_cpp_then_mlx(monkeypatch, tmp_path):
    """H200 失败、whisper.cpp 失败后降级到 mlx，且 mlx 成功。"""
    _patch_no_duration(monkeypatch)
    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"fake-audio")
    _install_fake_h200(monkeypatch, status_code=500, text="boom")
    # 模型存在（whisper.cpp 分支进入）；输出文件最终存在（mlx 成功判定）
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)

    def behavior(cmd):
        kind = _cmd_kind(cmd)
        if kind == "whisper_cpp":
            return FakeProc(returncode=1, stderr="boom")
        return FakeProc(returncode=0)

    calls = _install_fake_subprocess(monkeypatch, behavior)
    cfg = fsa.AsrConfig(provider="auto", model=None, model_path=None, language="zh")

    engine = fsa.transcribe_audio(str(audio), str(tmp_path / "out.txt"), config=cfg)

    kinds = [_cmd_kind(c) for c in calls]
    assert "whisper_cpp" in kinds  # H200 失败后尝试 whisper.cpp
    assert "mlx" in kinds          # whisper.cpp 失败后降级 mlx
    assert engine == "mlx-whisper"


def test_auto_h200_fail_whisper_cpp_success_skips_mlx(monkeypatch, tmp_path):
    _patch_no_duration(monkeypatch)
    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"fake-audio")
    _install_fake_h200(monkeypatch, status_code=500, text="boom")
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)
    monkeypatch.setattr(fsa.shutil, "copy2", lambda *a, **k: None)

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="auto", model=None, model_path=None, language="zh")

    engine = fsa.transcribe_audio(str(audio), str(tmp_path / "out.txt"), config=cfg)

    kinds = [_cmd_kind(c) for c in calls]
    assert engine == "whisper.cpp"
    assert "mlx" not in kinds  # whisper.cpp 成功就不应再调 mlx


# ---------- provider=h200_asr ----------

def test_provider_h200_only_success(monkeypatch, tmp_path):
    """显式 h200_asr 只调 HTTP ASR，成功写出文本。"""
    _patch_no_duration(monkeypatch)
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake-audio")
    out = tmp_path / "out.txt"
    h200_calls = _install_fake_h200(
        monkeypatch,
        status_code=200,
        payload={"text": "hello from h200", "language": "Chinese"},
    )
    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(
        provider="h200_asr",
        model=None,
        model_path=None,
        language="en",
        endpoint="http://test-asr/transcribe",
    )

    engine = fsa.transcribe_audio(str(audio), str(out), config=cfg)

    assert engine == "h200-asr"
    assert out.read_text(encoding="utf-8") == "hello from h200"
    assert h200_calls[0]["url"] == "http://test-asr/transcribe"
    assert h200_calls[0]["kwargs"]["data"]["language"] == "English"
    assert calls == []


def test_provider_h200_only_failure_does_not_fallback(monkeypatch, tmp_path):
    """显式 h200_asr 失败时不降级本机 ASR。"""
    _patch_no_duration(monkeypatch)
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake-audio")
    _install_fake_h200(monkeypatch, status_code=500, text="server down")
    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="h200_asr", model=None, model_path=None, language="zh")

    engine = fsa.transcribe_audio(str(audio), str(tmp_path / "out.txt"), config=cfg)

    assert engine is False
    assert calls == []


# ---------- provider=whisper_cpp ----------

def test_provider_whisper_cpp_only(monkeypatch, tmp_path):
    """whisper.cpp 失败也不降级到 mlx。"""
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)

    def behavior(cmd):
        if _cmd_kind(cmd) == "whisper_cpp":
            return FakeProc(returncode=1, stderr="boom")
        return FakeProc(returncode=0)

    calls = _install_fake_subprocess(monkeypatch, behavior)
    cfg = fsa.AsrConfig(provider="whisper_cpp", model=None, model_path=None, language="zh")

    engine = fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    kinds = [_cmd_kind(c) for c in calls]
    assert "whisper_cpp" in kinds
    assert "mlx" not in kinds  # 绝不降级到 mlx
    assert engine is False


# ---------- provider=mlx_whisper ----------

def test_provider_mlx_only(monkeypatch, tmp_path):
    """只调 mlx helper，绝不构建/执行 whisper-cli。"""
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="mlx_whisper", model=None, model_path=None, language="zh")

    engine = fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    kinds = [_cmd_kind(c) for c in calls]
    assert "mlx" in kinds
    assert "whisper_cpp" not in kinds
    assert "ffmpeg" not in kinds  # whisper.cpp 的 wav 转换也不应发生
    assert engine == "mlx-whisper"


# ---------- BILI_ASR_MODEL_PATH 覆盖 whisper.cpp 默认模型路径 ----------

def test_model_path_overrides_default_whisper_cpp_path(monkeypatch, tmp_path):
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)
    monkeypatch.setattr(fsa.shutil, "copy2", lambda *a, **k: None)

    custom_model = "/Users/foo/custom/ggml.bin"
    default_path = fsa.default_whisper_cpp_model_path()

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="whisper_cpp", model=None, model_path=custom_model, language="zh")

    fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    whisper_cmd = next(c for c in calls if _cmd_kind(c) == "whisper_cpp")
    assert custom_model in whisper_cmd
    assert default_path not in whisper_cmd


# ---------- model/model_path 透传给 mlx helper ----------

def test_model_and_path_passed_to_mlx_helper(monkeypatch, tmp_path):
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(
        provider="mlx_whisper",
        model="mlx-community/whisper-tiny",
        model_path="/Users/foo/snap",
        language="zh",
    )

    fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    mlx_cmd = next(c for c in calls if _cmd_kind(c) == "mlx")
    assert "--model" in mlx_cmd
    assert "mlx-community/whisper-tiny" in mlx_cmd
    assert "--model-path" in mlx_cmd
    assert "/Users/foo/snap" in mlx_cmd


def test_mlx_helper_omits_model_args_when_unset(monkeypatch, tmp_path):
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="mlx_whisper", model=None, model_path=None, language="zh")

    fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    mlx_cmd = next(c for c in calls if _cmd_kind(c) == "mlx")
    assert "--model" not in mlx_cmd
    assert "--model-path" not in mlx_cmd


# ---------- language 同时到达两个 provider ----------

def test_language_passed_to_whisper_cpp(monkeypatch, tmp_path):
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)
    monkeypatch.setattr(fsa.shutil, "copy2", lambda *a, **k: None)

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="whisper_cpp", model=None, model_path=None, language="en")

    fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    whisper_cmd = next(c for c in calls if _cmd_kind(c) == "whisper_cpp")
    # whisper-cli 语言参数: -l en
    assert "-l" in whisper_cmd
    assert whisper_cmd[whisper_cmd.index("-l") + 1] == "en"


def test_language_passed_to_mlx_helper(monkeypatch, tmp_path):
    _patch_no_duration(monkeypatch)
    monkeypatch.setattr(fsa.os.path, "exists", lambda p: True)

    calls = _install_fake_subprocess(monkeypatch, lambda cmd: FakeProc(returncode=0))
    cfg = fsa.AsrConfig(provider="mlx_whisper", model=None, model_path=None, language="en")

    fsa.transcribe_audio(str(tmp_path / "a.m4a"), str(tmp_path / "out.txt"), config=cfg)

    mlx_cmd = next(c for c in calls if _cmd_kind(c) == "mlx")
    assert "--language" in mlx_cmd
    assert mlx_cmd[mlx_cmd.index("--language") + 1] == "en"


# ---------- 对外标识不暴露本地绝对路径 ----------

def test_public_label_hides_absolute_model_path():
    cfg = fsa.AsrConfig(
        provider="whisper_cpp",
        model=None,
        model_path="/Users/alexcai/Library/.../ggml-large-v3-turbo.bin",
        language="zh",
    )
    public = fsa.asr_model_label(cfg)
    assert "/Users/" not in public
    assert "ggml-large-v3-turbo.bin" in public  # 仅 basename

    # include_local_path=True 时（仅调试日志）才暴露完整路径
    debug = fsa.asr_model_label(cfg, include_local_path=True)
    assert "/Users/" in debug


def test_public_label_uses_model_id_when_set():
    cfg = fsa.AsrConfig(
        provider="mlx_whisper",
        model="mlx-community/whisper-large-v3-turbo",
        model_path=None,
        language="zh",
    )
    assert fsa.asr_model_label(cfg) == "mlx_whisper:mlx-community/whisper-large-v3-turbo"


def test_public_label_for_h200_hides_endpoint():
    cfg = fsa.AsrConfig(
        provider="h200_asr",
        model=None,
        model_path=None,
        language="zh",
        endpoint="http://secret-internal-host/ASR/transcribe",
    )
    assert fsa.asr_model_label(cfg) == "h200_asr:SURGExZR-H200"
    assert "secret-internal-host" not in fsa.asr_model_label(cfg)
