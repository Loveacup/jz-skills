#!/usr/bin/env python3
"""
使用 mlx-whisper Python API 转录音频（不走 CLI，不联网）。

设计要点:
- 直接调用 mlx_whisper.transcribe()，通过 path_or_hf_repo 指向本地 HF snapshot，
  避免每次转录都去 HuggingFace Hub 解析仓库（离线可用、更快、更稳）。
- 必须用带 mlx_whisper 的解释器运行（本机为 /usr/bin/python3，即 CommandLineTools 3.9
  + ~/Library/Python/3.9 site-packages）。默认的 python3.12 没有 mlx_whisper。

用法:
    /usr/bin/python3 mlx_transcribe.py <audio_path> <output_txt_path> [language]
    /usr/bin/python3 mlx_transcribe.py <audio_path> <output_txt_path> \
        [--language zh|en|auto] [--model <repo id>] [--model-path <本地 snapshot 目录>]

模型/语言来源优先级（高→低）：CLI 参数 → 环境变量(BILI_ASR_*) → 内置默认。
退出码: 0 成功，非 0 失败。
"""

import argparse
import glob
import os
import sys
from dataclasses import dataclass
from typing import Mapping, Optional

# 依赖兜底：mlx_whisper 装在真实属主的 ~/Library/Python/3.9 user-site。
# Python 默认按 $HOME 推断 user-site，Hermes profile 改写 $HOME 后会指向
# profile home（无 mlx_whisper），故必须显式 append 真实属主的 site-packages。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site, real_home
ensure_user_site()

# 本地 mlx-whisper 模型 snapshot 根目录（基于真实家目录，非 $HOME）
MODEL_REPO = "mlx-community/whisper-large-v3-turbo"
SNAPSHOTS_DIR = os.path.join(
    real_home(),
    ".cache/huggingface/hub",
    f"models--{MODEL_REPO.replace('/', '--')}",
    "snapshots",
)


def resolve_local_model():
    """返回本地 snapshot 目录；找不到则返回 None（调用方可回退到 repo 名联网）。"""
    if not os.path.isdir(SNAPSHOTS_DIR):
        return None
    candidates = [
        d for d in sorted(glob.glob(os.path.join(SNAPSHOTS_DIR, "*")))
        if os.path.exists(os.path.join(d, "config.json"))
    ]
    return candidates[-1] if candidates else None


@dataclass(frozen=True)
class MlxAsrConfig:
    model: Optional[str]
    model_path: Optional[str]
    language: str


def resolve_mlx_asr_config(args, env: Optional[Mapping[str, str]] = None) -> MlxAsrConfig:
    """解析 model/model_path/language。优先级：CLI 参数 → 环境变量 → 默认。"""
    if env is None:
        env = os.environ
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
    """决定传给 mlx_whisper 的 path_or_hf_repo：
    显式 model_path > 显式 model(repo/路径) > 本地 snapshot > 内置 MODEL_REPO。"""
    if config.model_path:
        return config.model_path
    if config.model:
        return config.model
    local = resolve_local_model()
    if local is not None:
        return local
    return MODEL_REPO


def transcribe(audio_path, output_txt_path, config: MlxAsrConfig):
    import mlx_whisper  # 延迟导入，便于在缺失时给出清晰报错

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
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def build_parser():
    parser = argparse.ArgumentParser(description="mlx-whisper 离线转录")
    parser.add_argument("audio_path")
    parser.add_argument("output_txt_path")
    # 向后兼容：第三个位置参数仍可作为 language
    parser.add_argument("language_pos", nargs="?", default=None,
                        help="(兼容) 位置参数形式的语言，等价于 --language")
    parser.add_argument("--model", default=None, help="模型名/HF repo id")
    parser.add_argument("--model-path", dest="model_path", default=None,
                        help="本地模型/snapshot 目录绝对路径")
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
    except ImportError as e:
        print(f"   ❌ 无法导入 mlx_whisper（请用 /usr/bin/python3 运行）: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ mlx-whisper 转录失败: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
