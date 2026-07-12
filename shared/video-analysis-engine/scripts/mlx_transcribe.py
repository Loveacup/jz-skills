#!/usr/bin/env python3
"""Use the mlx-whisper Python API for local/offline audio transcription."""

import argparse
import glob
import os
import sys
from dataclasses import dataclass
from typing import Mapping, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site, real_home

ensure_user_site()

MODEL_REPO = "mlx-community/whisper-large-v3-turbo"
SNAPSHOTS_DIR = os.path.join(
    real_home(),
    ".cache/huggingface/hub",
    f"models--{MODEL_REPO.replace('/', '--')}",
    "snapshots",
)


def resolve_local_model():
    """Return the newest valid local model snapshot, if one exists."""
    if not os.path.isdir(SNAPSHOTS_DIR):
        return None
    candidates = [
        path
        for path in sorted(glob.glob(os.path.join(SNAPSHOTS_DIR, "*")))
        if os.path.exists(os.path.join(path, "config.json"))
    ]
    return candidates[-1] if candidates else None


@dataclass(frozen=True)
class MlxAsrConfig:
    model: Optional[str]
    model_path: Optional[str]
    language: str


def resolve_mlx_asr_config(args, env: Optional[Mapping[str, str]] = None) -> MlxAsrConfig:
    """Resolve CLI > environment > default configuration for the mlx helper."""
    env = os.environ if env is None else env
    model = args.model or (env.get("BILI_ASR_MODEL") or "").strip() or None
    model_path = args.model_path or (env.get("BILI_ASR_MODEL_PATH") or "").strip() or None
    language = (
        args.language
        or args.language_pos
        or (env.get("BILI_ASR_LANGUAGE") or "").strip()
        or "zh"
    )
    return MlxAsrConfig(model=model, model_path=model_path, language=language)


def resolve_model_ref(config: MlxAsrConfig):
    """Prefer explicit local path, then model ref, then local/default model."""
    if config.model_path:
        return config.model_path
    if config.model:
        return config.model
    return resolve_local_model() or MODEL_REPO


def transcribe(audio_path, output_txt_path, config: MlxAsrConfig):
    import mlx_whisper

    model_ref = resolve_model_ref(config)
    print(f"   📦 使用模型: {model_ref}", file=sys.stderr)
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_ref,
        language=config.language,
        verbose=False,
    )
    text = result.get("text", "").strip()
    if not text:
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)) or ".", exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return True


def build_parser():
    parser = argparse.ArgumentParser(description="mlx-whisper 离线转录")
    parser.add_argument("audio_path")
    parser.add_argument("output_txt_path")
    parser.add_argument("language_pos", nargs="?", default=None, help="兼容位置参数形式的语言")
    parser.add_argument("--model", default=None, help="模型名或 HF repo id")
    parser.add_argument("--model-path", dest="model_path", default=None, help="本地模型目录")
    parser.add_argument("--language", default=None, choices=["zh", "en", "auto"])
    return parser


def main():
    args = build_parser().parse_args()
    config = resolve_mlx_asr_config(args)
    if not os.path.exists(args.audio_path):
        print(f"   ❌ 音频文件不存在: {args.audio_path}", file=sys.stderr)
        sys.exit(1)
    try:
        ok = transcribe(args.audio_path, args.output_txt_path, config)
    except ImportError as exc:
        print(f"   ❌ 无法导入 mlx_whisper（请用 /usr/bin/python3 运行）: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"   ❌ mlx-whisper 转录失败: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
