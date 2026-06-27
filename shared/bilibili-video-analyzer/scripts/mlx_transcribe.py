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

退出码: 0 成功，非 0 失败。
"""

import glob
import os
import sys

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


def transcribe(audio_path, output_txt_path, language="zh"):
    import mlx_whisper  # 延迟导入，便于在缺失时给出清晰报错

    model_path = resolve_local_model()
    if model_path is None:
        # 回退到联网 repo 名（保持可用性，但优先本地路径）
        model_path = MODEL_REPO
        print(f"   ⚠️  未找到本地 snapshot，回退到 HF repo: {model_path}", file=sys.stderr)
    else:
        print(f"   📦 使用本地模型: {model_path}", file=sys.stderr)

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_path,
        language=language,
        verbose=False,
    )

    text = result.get("text", "").strip()
    if not text:
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)) or ".", exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def main():
    if len(sys.argv) < 3:
        print("用法: mlx_transcribe.py <audio_path> <output_txt_path> [language]", file=sys.stderr)
        sys.exit(2)

    audio_path = sys.argv[1]
    output_txt_path = sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else "zh"

    if not os.path.exists(audio_path):
        print(f"   ❌ 音频文件不存在: {audio_path}", file=sys.stderr)
        sys.exit(1)

    try:
        ok = transcribe(audio_path, output_txt_path, language)
    except ImportError as e:
        print(f"   ❌ 无法导入 mlx_whisper（请用 /usr/bin/python3 运行）: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ mlx-whisper 转录失败: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
