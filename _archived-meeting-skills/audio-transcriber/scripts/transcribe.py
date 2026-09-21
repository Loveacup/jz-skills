#!/usr/bin/env python3
"""Audio Transcriber CLI — 音频转录工具。

子命令:
  single   单文件完整流程 (降噪→声纹分离→ASR)
  batch    批量两阶段处理 (Phase A: diarize all → Phase B: ASR all)
  denoise  单独降噪
  diarize  单独声纹分离
  asr      单独 ASR 转录 (需 segments.json)
  register 注册声纹
  speakers 查看已注册声纹

环境要求:
  - Python 3.11+ (使用 .venv)
  - ffmpeg (非 WAV 格式转换)
  - HF_HOME 默认 ~/models/huggingface
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

# ─── 常量 ────────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent

# 默认记忆目录
DEFAULT_MEMORY_DIR = Path.home() / ".claude/skills/voice-to-markdown-workflow/memory"

# 声纹库放在共享记忆目录，两个 skill 共用
VOICEPRINT_PATH = DEFAULT_MEMORY_DIR / "voiceprints.json"

MODELS = {
    "default": "mlx-community/Qwen3-ASR-1.7B-8bit",
    "small": "mlx-community/Qwen3-ASR-0.6B-4bit",
}

VOICEPRINT_THRESHOLD_CANDIDATE = 0.60   # 候选匹配下限
VOICEPRINT_THRESHOLD_CONFIRMED = 0.75   # 确认匹配下限
MERGE_UNKNOWN_THRESHOLD = 0.75          # 未知说话人合并阈值

# soundfile 支持的格式
_SF_EXTENSIONS = {".wav", ".flac", ".ogg", ".aiff", ".aif"}

# HF_HOME 默认值
if "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = str(Path.home() / "models/huggingface")

# P3: ASR 模型缓存存在时自动启用离线模式
_HF_CACHE_DIR = Path(os.environ.get("HF_HOME", str(Path.home() / "models/huggingface")))
for _model_name in MODELS.values():
    _cache_path = _HF_CACHE_DIR / f"hub/models--{_model_name.replace('/', '--')}"
    if not _cache_path.exists():
        # 也检查默认 HF 缓存路径
        _cache_path = Path.home() / ".cache/huggingface/hub" / f"models--{_model_name.replace('/', '--')}"
    if _cache_path.exists() and "HF_HUB_OFFLINE" not in os.environ:
        os.environ["HF_HUB_OFFLINE"] = "1"
        break

# ─── 懒加载模型缓存 ──────────────────────────────────────────────────────────

_diarization_pipeline = None
_embedding_inference = None
_asr_models = {}


# ─── 进度输出 ─────────────────────────────────────────────────────────────────

def _progress(phase: str, step: str, detail: str = "", pct: int = -1):
    """结构化进度输出到 stdout，便于 Claude Code 解析。"""
    parts = [f"[{phase}]", step]
    if detail:
        parts.append(detail)
    if pct >= 0:
        parts.append(f"({pct}%)")
    print(" ".join(parts), flush=True)


def _log(msg: str):
    """日志输出到 stderr。"""
    print(f"[audio-transcriber] {msg}", file=sys.stderr, flush=True)


# ─── 音频格式处理 ─────────────────────────────────────────────────────────────

def _ensure_wav(audio_path: str) -> tuple[str, bool]:
    """确保音频为 WAV 格式。非 WAV 用 ffmpeg 转换。

    Returns:
        (wav_path, is_temp) — is_temp=True 表示临时文件，用完需删除
    """
    ext = Path(audio_path).suffix.lower()
    if ext in _SF_EXTENSIONS:
        return audio_path, False

    _log(f"格式 {ext} 不被 soundfile 支持，用 ffmpeg 转换...")
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", tmp.name],
            capture_output=True, check=True,
        )
        _log(f"已转换为 WAV: {tmp.name}")
        return tmp.name, True
    except subprocess.CalledProcessError as e:
        os.unlink(tmp.name)
        raise RuntimeError(f"ffmpeg 转换失败: {e.stderr.decode()[:500]}")


def _get_duration(audio_path: str) -> float:
    """获取音频时长（秒）。"""
    wav_path, is_temp = _ensure_wav(audio_path)
    try:
        info = sf.info(wav_path)
        return info.duration
    finally:
        if is_temp:
            os.unlink(wav_path)


# ─── 降噪 ────────────────────────────────────────────────────────────────────

def denoise_audio(audio_path: str, output_path: str = "") -> str:
    """频谱门控降噪 (noisereduce)。"""
    import noisereduce as nr

    audio_path = os.path.expanduser(audio_path)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"文件不存在: {audio_path}")

    _progress("denoise", "开始降噪", os.path.basename(audio_path))

    wav_path, is_temp = _ensure_wav(audio_path)
    try:
        audio, sr = sf.read(wav_path)
        _log(f"音频: sr={sr}, shape={audio.shape}, duration={len(audio)/sr:.1f}s")

        reduced = nr.reduce_noise(y=audio, sr=sr, prop_decrease=0.8)

        if not output_path:
            stem = Path(audio_path).stem
            output_path = str(Path(audio_path).parent / f"{stem}_denoised.wav")
        output_path = os.path.expanduser(output_path)

        sf.write(output_path, reduced, sr)
        _progress("denoise", "完成", output_path)
        return output_path
    finally:
        if is_temp:
            os.unlink(wav_path)


# ─── 声纹分离 ────────────────────────────────────────────────────────────────

def _load_diarization():
    """加载 pyannote diarization 管线，启用 MPS GPU 加速。"""
    global _diarization_pipeline
    if _diarization_pipeline is None:
        _progress("model", "加载 pyannote diarization...")
        from pyannote.audio import Pipeline
        import torch
        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1",
            cache_dir=os.environ.get("HF_HOME"),
        )
        if torch.backends.mps.is_available():
            _diarization_pipeline.to(torch.device("mps"))
            _progress("model", "pyannote 加载完成 (MPS GPU)")
        else:
            _progress("model", "pyannote 加载完成 (CPU)")
    return _diarization_pipeline


def _unload_diarization():
    """显式卸载 diarization 模型，释放 GPU 显存。"""
    global _diarization_pipeline
    if _diarization_pipeline is not None:
        del _diarization_pipeline
        _diarization_pipeline = None
        try:
            import torch
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except Exception:
            pass
        _progress("model", "pyannote 已卸载，GPU 显存已释放")


def _unload_embedding():
    """显式卸载 embedding 模型。"""
    global _embedding_inference
    if _embedding_inference is not None:
        del _embedding_inference
        _embedding_inference = None
        _progress("model", "embedding 模型已卸载")


def diarize_audio(audio_path: str, num_speakers: int = 0) -> list:
    """声纹分离，返回分段列表。短音频直接处理，长音频自动分块。"""
    # 检测音频时长，超过阈值自动使用分块模式
    try:
        info = sf.info(audio_path)
        duration = info.duration
    except Exception:
        duration = 0

    if duration > CHUNK_THRESHOLD_SECONDS:
        _progress("diarize", f"音频 {duration:.0f}s > {CHUNK_THRESHOLD_SECONDS}s，启用分块模式")
        return diarize_audio_chunked(audio_path, num_speakers=num_speakers)

    return _diarize_single(audio_path, num_speakers=num_speakers)


def _diarize_single(audio_path: str, num_speakers: int = 0) -> list:
    """单次声纹分离（不分块）。"""
    pipeline = _load_diarization()

    _progress("diarize", "开始", os.path.basename(audio_path))
    kwargs = {}
    if num_speakers > 0:
        kwargs["num_speakers"] = num_speakers
    output = pipeline(audio_path, **kwargs)

    diarization = getattr(output, "speaker_diarization", output)

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
        })

    _progress("diarize", "完成",
              f"{len(segments)} 段, {len(set(s['speaker'] for s in segments))} 位说话人")
    return segments


# ─── 分块 Diarization ─────────────────────────────────────────────────────────

CHUNK_THRESHOLD_SECONDS = 600   # 超过 10 分钟启用分块
CHUNK_DURATION_SECONDS = 600    # 每块 10 分钟
CHUNK_OVERLAP_SECONDS = 30      # 块间重叠 30 秒
CHUNK_MERGE_THRESHOLD = 0.70    # 跨块说话人合并阈值


def diarize_audio_chunked(audio_path: str, num_speakers: int = 0,
                           cache_dir: str = None) -> list:
    """分块 diarization：切块 → 逐块处理(有进度+断点恢复) → 跨块说话人合并。

    解决三个痛点：
    1. 进度可见: chunk 3/17 (18%)
    2. 断点恢复: 已完成的 chunk 保存到 cache_dir，重跑时跳过
    3. 单块失败只重跑该块，不影响已完成的块
    """
    audio_path = os.path.expanduser(audio_path)
    info = sf.info(audio_path)
    total_duration = info.duration
    sr = info.samplerate

    # 确定 cache 目录
    if not cache_dir:
        cache_dir = str(Path(audio_path).parent / f".diarize_cache_{Path(audio_path).stem}")
    os.makedirs(cache_dir, exist_ok=True)

    # 计算分块
    chunks = []
    start = 0.0
    while start < total_duration:
        end = min(start + CHUNK_DURATION_SECONDS, total_duration)
        chunks.append((start, end))
        start += CHUNK_DURATION_SECONDS - CHUNK_OVERLAP_SECONDS
        if start >= total_duration:
            break

    total_chunks = len(chunks)
    _progress("diarize-chunked", f"分为 {total_chunks} 块",
              f"每块 {CHUNK_DURATION_SECONDS}s, 重叠 {CHUNK_OVERLAP_SECONDS}s")

    # 加载模型（只加载一次）
    pipeline = _load_diarization()

    # ── Phase 1: 逐块 diarize ──
    chunk_results: list[list[dict]] = []
    audio_data, audio_sr = sf.read(audio_path)
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    for idx, (chunk_start, chunk_end) in enumerate(chunks):
        chunk_cache = os.path.join(cache_dir, f"chunk_{idx:04d}.json")

        # 断点恢复: 检查已保存的块
        if os.path.exists(chunk_cache):
            try:
                cached = json.loads(Path(chunk_cache).read_text())
                chunk_results.append(cached)
                _progress("diarize-chunked", f"块 {idx+1}/{total_chunks} (缓存)",
                          f"{chunk_start:.0f}s-{chunk_end:.0f}s",
                          int((idx + 1) / total_chunks * 100))
                continue
            except Exception:
                pass  # 缓存损坏，重新处理

        _progress("diarize-chunked", f"块 {idx+1}/{total_chunks}",
                  f"{chunk_start:.0f}s-{chunk_end:.0f}s",
                  int(idx / total_chunks * 100))

        # 提取音频块，写临时文件
        start_sample = int(chunk_start * audio_sr)
        end_sample = min(int(chunk_end * audio_sr), len(audio_data))
        chunk_audio = audio_data[start_sample:end_sample]

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            sf.write(tmp_path, chunk_audio, audio_sr)

        try:
            kwargs = {}
            if num_speakers > 0:
                kwargs["num_speakers"] = num_speakers
            output = pipeline(tmp_path, **kwargs)
            diarization = getattr(output, "speaker_diarization", output)

            chunk_segs = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                chunk_segs.append({
                    "start": round(chunk_start + turn.start, 2),
                    "end": round(chunk_start + turn.end, 2),
                    "speaker": f"chunk{idx}_{speaker}",  # 加 chunk 前缀避免混淆
                })

            chunk_results.append(chunk_segs)

            # 立即保存到缓存
            Path(chunk_cache).write_text(
                json.dumps(chunk_segs, ensure_ascii=False), encoding="utf-8"
            )
            _progress("diarize-chunked", f"块 {idx+1}/{total_chunks} 完成",
                      f"{len(chunk_segs)} 段",
                      int((idx + 1) / total_chunks * 100))
        except Exception as e:
            _log(f"块 {idx+1} diarization 失败: {e}")
            chunk_results.append([])
        finally:
            os.unlink(tmp_path)

    # ── Phase 2: 去重重叠区域 ──
    _progress("diarize-chunked", "合并重叠区域...")
    all_segments = _merge_overlapping_chunks(chunk_results, chunks)

    # ── Phase 3: 跨块说话人合并 ──
    _progress("diarize-chunked", "跨块说话人合并...")
    all_segments = _reconcile_chunk_speakers(audio_path, all_segments, audio_data, audio_sr)

    # 清理缓存目录
    import shutil
    shutil.rmtree(cache_dir, ignore_errors=True)

    _progress("diarize-chunked", "完成",
              f"{len(all_segments)} 段, {len(set(s['speaker'] for s in all_segments))} 位说话人")
    return all_segments


def _merge_overlapping_chunks(chunk_results: list[list[dict]],
                               chunks: list[tuple[float, float]]) -> list[dict]:
    """去重重叠区域的片段：重叠区域只保留前一块的结果。"""
    all_segments = []
    for idx, segs in enumerate(chunk_results):
        if idx + 1 < len(chunks):
            # 有下一块: 当前块的结束点是下一块开始点（即去掉重叠部分）
            next_start = chunks[idx + 1][0]
            for seg in segs:
                if seg["start"] < next_start:
                    # 片段开始在非重叠区域内
                    clipped = dict(seg)
                    clipped["end"] = min(seg["end"], next_start)
                    if clipped["end"] - clipped["start"] > 0.1:
                        all_segments.append(clipped)
        else:
            # 最后一块: 全部保留
            all_segments.extend(segs)

    all_segments.sort(key=lambda s: s["start"])
    return all_segments


def _reconcile_chunk_speakers(audio_path: str, segments: list,
                               audio_data: np.ndarray, sr: int) -> list:
    """跨块说话人 ID 合并：提取每个 chunk_speaker 的嵌入，聚类合并。

    使用 union-find 把相似的 chunk speakers 合并为统一 SPEAKER_XX。
    """
    from pyannote.core import Segment as PyannoteSegment

    # 收集所有 chunk_speaker 标签
    speaker_labels = sorted(set(s["speaker"] for s in segments))
    if len(speaker_labels) <= 1:
        return segments

    # 对每个 speaker 提取嵌入（取最长片段）
    inference = _load_embedding_model()
    label_embeddings: dict[str, np.ndarray] = {}

    for label in speaker_labels:
        label_segs = [s for s in segments if s["speaker"] == label]
        # 取最长的片段
        longest = max(label_segs, key=lambda s: s["end"] - s["start"])
        duration = longest["end"] - longest["start"]
        if duration < 1.0:
            continue
        try:
            excerpt = PyannoteSegment(longest["start"], longest["end"])
            emb = inference.crop(audio_path, excerpt)
            if emb.ndim > 1:
                emb = emb.squeeze(0)
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            label_embeddings[label] = emb
        except Exception:
            continue

    if len(label_embeddings) <= 1:
        return segments

    # Union-find 合并相似说话人
    labels_with_emb = list(label_embeddings.keys())
    parent = {l: l for l in labels_with_emb}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    merge_count = 0
    for i, la in enumerate(labels_with_emb):
        for lb in labels_with_emb[i+1:]:
            sim = _cosine_similarity(label_embeddings[la], label_embeddings[lb])
            if sim >= CHUNK_MERGE_THRESHOLD:
                union(la, lb)
                merge_count += 1

    if merge_count:
        _log(f"  跨块合并: {merge_count} 对说话人")

    # 构建统一映射
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)
    for l in labels_with_emb:
        groups[find(l)].append(l)

    # 没有嵌入的 label 也需要映射
    label_map: dict[str, str] = {}
    speaker_idx = 0
    for root, group in groups.items():
        unified_name = f"SPEAKER_{speaker_idx:02d}"
        for l in group:
            label_map[l] = unified_name
        speaker_idx += 1

    # 未提取到嵌入的 label 单独编号
    for label in speaker_labels:
        if label not in label_map:
            label_map[label] = f"SPEAKER_{speaker_idx:02d}"
            speaker_idx += 1

    # 应用映射
    for seg in segments:
        seg["speaker"] = label_map.get(seg["speaker"], seg["speaker"])

    _progress("diarize-chunked",
              f"统一为 {len(set(label_map.values()))} 位说话人 (从 {len(speaker_labels)} 个标签)")
    return segments


# ─── ASR 转录 ─────────────────────────────────────────────────────────────────

def _load_asr(model_key: str = "default"):
    """加载 ASR 模型 (MLX)。"""
    if model_key not in _asr_models:
        model_name = MODELS.get(model_key, MODELS["default"])
        _progress("model", f"加载 ASR 模型: {model_name}")
        from mlx_audio.stt import load
        _asr_models[model_key] = load(model_name)
        _progress("model", f"ASR 模型加载完成: {model_key}")
    return _asr_models[model_key]


def _unload_asr():
    """显式卸载 ASR 模型。"""
    global _asr_models
    if _asr_models:
        _asr_models.clear()
        _progress("model", "ASR 模型已卸载")


# ─── 记忆系统 ─────────────────────────────────────────────────────────────────

def _load_corrections(memory_dir: Path) -> dict[str, str]:
    """从 voice-to-markdown 记忆系统加载 ASR 纠错规则。

    合并来源:
    1. corrections.json — 直接纠错映射
    2. patterns.json — type=asr_correction 的结晶化规则
    """
    replacements: dict[str, str] = {}

    # Source 1: corrections.json
    corrections_path = memory_dir / "corrections.json"
    if corrections_path.exists():
        try:
            data = json.loads(corrections_path.read_text())
            for c in data.get("corrections", []):
                wrong = c.get("wrong", "")
                correct = c.get("correct", "")
                if wrong and correct and wrong != correct:
                    replacements[wrong] = correct
            _log(f"加载纠错规则: {len(replacements)} 条 (corrections.json)")
        except Exception as e:
            _log(f"加载 corrections.json 失败: {e}")

    # Source 2: patterns.json (type=asr_correction)
    patterns_path = memory_dir / "patterns.json"
    if patterns_path.exists():
        try:
            data = json.loads(patterns_path.read_text())
            count = 0
            for p in data.get("patterns", []):
                if p.get("type") == "asr_correction" and p.get("status") == "active":
                    rule = p.get("rule", "")
                    # 解析 "X" → "Y" 格式
                    if "→" in rule:
                        parts = rule.split("→")
                        wrong = parts[0].strip().strip('"').strip('"').strip('"')
                        # 取 → 后第一个引号对
                        right_part = parts[1].strip()
                        correct = right_part.split('"')[1] if '"' in right_part else \
                                  right_part.split('"')[1] if '"' in right_part else ""
                        if wrong and correct and wrong not in replacements:
                            replacements[wrong] = correct
                            count += 1
            if count:
                _log(f"加载结晶规则: {count} 条 (patterns.json)")
        except Exception as e:
            _log(f"加载 patterns.json 失败: {e}")

    return replacements


def _load_speaker_names(memory_dir: Path) -> dict[str, list[str]]:
    """从记忆系统加载已知说话人名称和别名。

    Returns:
        {canonical_name: [alias1, alias2, ...]}
    """
    speaker_names: dict[str, list[str]] = {}
    speakers_path = memory_dir / "speakers.json"
    if speakers_path.exists():
        try:
            data = json.loads(speakers_path.read_text())
            for name, info in data.get("speakers", {}).items():
                aliases = info.get("aliases", [])
                speaker_names[name] = aliases
            _log(f"加载说话人信息: {len(speaker_names)} 位")
        except Exception as e:
            _log(f"加载 speakers.json 失败: {e}")
    return speaker_names


def _apply_corrections(text: str, replacements: dict[str, str],
                       stats: dict[str, int] = None) -> str:
    """对 ASR 输出做即时纠错替换，可选追踪应用次数。

    Args:
        stats: 若提供，记录 {wrong_text: applied_count}（P5 纠错回写）
    """
    if not replacements:
        return text
    for wrong, correct in replacements.items():
        count = text.count(wrong)
        if count > 0:
            text = text.replace(wrong, correct)
            if stats is not None:
                stats[wrong] = stats.get(wrong, 0) + count
    return text


def _save_corrections_applied(stats: dict[str, int], replacements: dict[str, str],
                               output_path: str):
    """P5: 保存纠错应用统计，供 workflow Phase 8 读取更新 corrections.json。"""
    if not stats:
        return None

    base = output_path.rsplit(".", 1)[0] if "." in output_path else output_path
    stats_path = f"{base}-corrections-applied.json"

    data = {
        "version": "1.0",
        "session": datetime.now().isoformat(),
        "source": os.path.basename(output_path),
        "applied": {
            f"{wrong}→{replacements[wrong]}": count
            for wrong, count in stats.items()
            if wrong in replacements
        },
        "total_replacements": sum(stats.values()),
    }

    with open(stats_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _progress("corrections", f"纠错统计已保存: {os.path.basename(stats_path)} ({sum(stats.values())} 次替换)")
    return stats_path


def _sync_to_speaker_memory(name: str, memory_dir: Path,
                            roles: list[str] = None,
                            org: str = None,
                            aliases: list[str] = None):
    """将声纹注册信息同步写入 voice-to-markdown-workflow 的 speakers.json。

    - 已存在: 更新 last_seen，合并 roles/aliases
    - 不存在: 创建最小条目
    """
    speakers_path = memory_dir / "speakers.json"
    if not speakers_path.exists():
        _log(f"speakers.json 不存在: {speakers_path}，跳过同步")
        return

    try:
        data = json.loads(speakers_path.read_text(encoding="utf-8"))
        speakers = data.get("speakers", {})
        today = datetime.now().strftime("%Y-%m-%d")

        if name in speakers:
            # 已存在: 更新
            speakers[name]["last_seen"] = today
            if roles:
                existing = set(speakers[name].get("roles", []))
                existing.update(roles)
                speakers[name]["roles"] = sorted(existing)
            if org:
                existing = set(speakers[name].get("organizations", []))
                existing.add(org)
                speakers[name]["organizations"] = sorted(existing)
            if aliases:
                existing = set(speakers[name].get("aliases", []))
                existing.update(aliases)
                speakers[name]["aliases"] = sorted(existing)
            _log(f"更新说话人记忆: {name}")
        else:
            # 新建最小条目
            speakers[name] = {
                "roles": roles or [],
                "organizations": [org] if org else [],
                "aliases": aliases or [],
                "first_seen": today,
                "last_seen": today,
                "session_count": 0,
                "co_speakers": [],
                "typical_topics": [],
            }
            _log(f"新建说话人记忆: {name}")

        data["speakers"] = speakers
        speakers_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        _progress("memory", "已同步到 voice-to-markdown-workflow/memory/speakers.json")
    except Exception as e:
        _log(f"同步 speakers.json 失败: {e}")


# ─── 声纹库 ───────────────────────────────────────────────────────────────────

def _load_voiceprints() -> list:
    if VOICEPRINT_PATH.exists():
        with open(VOICEPRINT_PATH, "r") as f:
            return json.load(f)
    return []


def _save_voiceprints(data: list):
    with open(VOICEPRINT_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_embedding_model():
    """加载 pyannote wespeaker embedding 模型。"""
    global _embedding_inference
    if _embedding_inference is None:
        _log("加载 wespeaker embedding 模型...")
        from pyannote.audio import Model, Inference
        model = Model.from_pretrained(
            "pyannote/wespeaker-voxceleb-resnet34-LM",
            cache_dir=os.environ.get("HF_HOME"),
        )
        _embedding_inference = Inference(model, window="whole")
        _log("wespeaker embedding 模型加载完成")
    return _embedding_inference


def _extract_embedding(audio_path: str) -> np.ndarray:
    """提取说话人嵌入向量。"""
    inference = _load_embedding_model()
    emb = inference(audio_path)
    if emb is not None and emb.size > 0:
        if emb.ndim > 1:
            emb = emb.squeeze(0)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        return emb
    raise RuntimeError("无法提取说话人嵌入向量")


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def _get_embeddings(vp: dict) -> list[list[float]]:
    """兼容新旧格式：新格式 embeddings (列表), 旧格式 embedding (单条)。"""
    if "embeddings" in vp:
        return vp["embeddings"]
    if "embedding" in vp:
        return [vp["embedding"]]
    return []


def _match_speaker(embedding: np.ndarray, voiceprints: list = None) -> tuple[str | None, float]:
    """在声纹库中匹配说话人，支持多嵌入（取最高分）。

    Returns:
        (name_or_None, best_score) — 分层匹配:
        - score >= 0.75: 确认匹配
        - 0.60 <= score < 0.75: 候选匹配
        - score < 0.60: 未匹配
    """
    if voiceprints is None:
        voiceprints = _load_voiceprints()
    best_name = None
    best_score = 0.0

    for vp in voiceprints:
        for stored in _get_embeddings(vp):
            score = _cosine_similarity(embedding, np.array(stored))
            if score > best_score:
                best_score = score
                best_name = vp["name"]

    if best_score >= VOICEPRINT_THRESHOLD_CANDIDATE:
        level = "确认" if best_score >= VOICEPRINT_THRESHOLD_CONFIRMED else "候选"
        _log(f"  声纹匹配: {best_name} ({level}, 相似度 {best_score:.3f})")
        return best_name, best_score
    return None, best_score


def _extract_topn_embedding(audio_path: str, segments: list, speaker_label: str,
                             inference, n: int = 3, min_duration: float = 3.0) -> np.ndarray | None:
    """P2: 从 Top-N 最长片段提取嵌入后取归一化均值。

    比只用最长片段更稳健，减少噪音/重叠对嵌入质量的影响。

    Args:
        n: 最多取几个片段
        min_duration: 片段最短时长（秒）
    """
    from pyannote.core import Segment as PyannoteSegment

    label_segs = sorted(
        [s for s in segments if s["speaker"] == speaker_label],
        key=lambda s: s["end"] - s["start"],
        reverse=True,
    )

    embeddings = []
    for seg in label_segs:
        duration = seg["end"] - seg["start"]
        if duration < min_duration and embeddings:
            # 如果已经有至少一个嵌入，跳过过短片段
            # 但如果一个都没有，降低要求到 1 秒
            if duration < 1.0:
                continue
        try:
            excerpt = PyannoteSegment(seg["start"], seg["end"])
            emb = inference.crop(audio_path, excerpt)
            if emb.ndim > 1:
                emb = emb.squeeze(0)
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            embeddings.append(emb)
        except Exception:
            continue
        if len(embeddings) >= n:
            break

    if not embeddings:
        return None
    if len(embeddings) == 1:
        return embeddings[0]
    avg = np.mean(embeddings, axis=0)
    return avg / (np.linalg.norm(avg) + 1e-8)


def _merge_same_speakers(speaker_name_map: dict[str, str],
                          label_embeddings: dict[str, np.ndarray],
                          match_scores: dict[str, float]) -> dict[str, str]:
    """P0: 声纹匹配后合并同一说话人。

    两种合并:
    1. 已匹配: 多个 label 映射到同一人名 → 保留分数最高的 label 名，其余合并
    2. 未匹配: 未知说话人之间相似度 > MERGE_UNKNOWN_THRESHOLD → 合并为同一 Speaker N
    """
    # === 第一步: 合并已匹配到同一人名的 labels ===
    from collections import defaultdict
    name_to_labels: dict[str, list[str]] = defaultdict(list)
    for label, name in speaker_name_map.items():
        if not name.startswith("Speaker "):
            name_to_labels[name].append(label)

    merged_map = dict(speaker_name_map)
    merge_count = 0
    for name, labels in name_to_labels.items():
        if len(labels) > 1:
            # 多个 label 匹配到同一人，全部统一
            _log(f"  合并 {len(labels)} 个标签为 {name}: {labels}")
            merge_count += len(labels) - 1

    # === 第二步: 合并未知说话人 ===
    unknown_labels = [l for l, n in merged_map.items() if n.startswith("Speaker ")]
    if len(unknown_labels) > 1:
        # 构建 union-find
        parent = {l: l for l in unknown_labels}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i, la in enumerate(unknown_labels):
            if la not in label_embeddings:
                continue
            for lb in unknown_labels[i+1:]:
                if lb not in label_embeddings:
                    continue
                sim = _cosine_similarity(label_embeddings[la], label_embeddings[lb])
                if sim >= MERGE_UNKNOWN_THRESHOLD:
                    union(la, lb)
                    _log(f"  合并未知说话人: {merged_map[la]} + {merged_map[lb]} (相似度 {sim:.3f})")
                    merge_count += 1

        # 重新编号合并后的未知说话人
        groups: dict[str, list[str]] = defaultdict(list)
        for l in unknown_labels:
            groups[find(l)].append(l)

        speaker_counter = 1
        for root, group_labels in groups.items():
            group_name = f"Speaker {speaker_counter}"
            for l in group_labels:
                merged_map[l] = group_name
            speaker_counter += 1

    if merge_count:
        _progress("voiceprint", f"合并了 {merge_count} 个重复说话人标签")
    return merged_map


def _match_speakers_for_segments(audio_path: str, segments: list,
                                 speaker_names: dict[str, list[str]] = None) -> tuple[dict[str, str], dict[str, list[float]]]:
    """为分段中的说话人标签匹配真实姓名，并收集未匹配说话人的嵌入向量。

    改进 (P0+P1+P2):
    - P2: Top-3 嵌入平均代替单一最长片段
    - P1: 分层匹配 (确认 ≥0.75 / 候选 0.60-0.75 / 未知 <0.60)
    - P0: 自动合并映射到同一人的 labels + 合并相似未知说话人

    Returns:
        (speaker_name_map, unknown_embeddings)
        - speaker_name_map: {label: display_name}  候选匹配带 "?" 后缀
        - unknown_embeddings: {display_name: embedding_list} 未匹配 + 候选匹配的嵌入
    """
    speaker_labels = sorted(set(s["speaker"] for s in segments))
    speaker_name_map: dict[str, str] = {}
    match_scores: dict[str, float] = {}
    label_embeddings: dict[str, np.ndarray] = {}
    voiceprints = _load_voiceprints()

    inference = _load_embedding_model()

    for label in speaker_labels:
        try:
            emb = _extract_topn_embedding(audio_path, segments, label, inference)
            if emb is None:
                continue
            label_embeddings[label] = emb

            if voiceprints:
                matched_name, score = _match_speaker(emb, voiceprints)
                if matched_name and score >= VOICEPRINT_THRESHOLD_CONFIRMED:
                    speaker_name_map[label] = matched_name
                    match_scores[label] = score
                elif matched_name and score >= VOICEPRINT_THRESHOLD_CANDIDATE:
                    speaker_name_map[label] = f"{matched_name}?"
                    match_scores[label] = score
        except Exception as e:
            _log(f"  声纹匹配失败 ({label}): {e}")

    # P0: 合并同一说话人
    # 先给未匹配的临时编号
    speaker_counter = 1
    for label in speaker_labels:
        if label not in speaker_name_map:
            speaker_name_map[label] = f"Speaker {speaker_counter}"
            speaker_counter += 1

    speaker_name_map = _merge_same_speakers(speaker_name_map, label_embeddings, match_scores)

    # 收集未匹配 + 候选匹配的嵌入（候选也保存，因为可能判断错误）
    unknown_embeddings: dict[str, list[float]] = {}
    seen_names = set()
    for label in speaker_labels:
        name = speaker_name_map[label]
        if name in seen_names:
            continue
        seen_names.add(name)
        if label in label_embeddings:
            if name.startswith("Speaker ") or name.endswith("?"):
                unknown_embeddings[name] = label_embeddings[label].tolist()

    _progress("voiceprint", "说话人映射",
              str({l: n for l, n in speaker_name_map.items()}))
    if unknown_embeddings:
        _progress("voiceprint", f"{len(unknown_embeddings)} 位未知/候选说话人嵌入已提取")
    return speaker_name_map, unknown_embeddings


# ─── ASR 转录核心 ─────────────────────────────────────────────────────────────

def transcribe_segments(audio_path: str, segments: list,
                        language: str = "Chinese",
                        model_key: str = "default",
                        replacements: dict[str, str] = None,
                        correction_stats: dict[str, int] = None) -> list:
    """按分段逐段转录。

    Args:
        correction_stats: P5 纠错统计字典，传入则追踪应用次数

    Returns:
        [(speaker, text), ...]
    """
    audio_path = os.path.expanduser(audio_path)
    model = _load_asr(model_key)
    replacements = replacements or {}

    wav_path, is_temp = _ensure_wav(audio_path)
    try:
        audio, sr = sf.read(wav_path)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        results = []
        total = len(segments)
        for i, seg in enumerate(segments):
            start_sample = int(seg["start"] * sr)
            end_sample = int(seg["end"] * sr)
            segment_audio = audio[start_sample:end_sample]

            if len(segment_audio) < sr * 0.1:
                continue

            pct = int((i + 1) / total * 100)
            _progress("asr", f"转录 {i+1}/{total}",
                      f"{seg['start']:.1f}s-{seg['end']:.1f}s ({seg['speaker']})", pct)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
                sf.write(tmp_path, segment_audio, sr)

            try:
                result = model.generate(tmp_path, language=language)
                text = result.text
                if text and text.strip():
                    text = _apply_corrections(text.strip(), replacements, correction_stats)
                    results.append((seg["speaker"], text))
            except Exception as e:
                _log(f"  转录段 {i+1} 失败: {e}")
                results.append((seg["speaker"], f"[转录失败: {e}]"))
            finally:
                os.unlink(tmp_path)

        return results
    finally:
        if is_temp:
            os.unlink(wav_path)


# ─── Sidecar 输出 ────────────────────────────────────────────────────────────

def _save_unknown_embeddings(unknown_embeddings: dict[str, list[float]],
                              output_path: str):
    """保存未知说话人嵌入向量为 sidecar JSON 文件。

    文件名: <transcript>-speaker-embeddings.json
    下游 voice-to-markdown-workflow Phase 5 读取此文件，
    用户确认身份后自动注册声纹。
    """
    if not unknown_embeddings:
        return None

    # 根据输出路径生成 sidecar 路径
    base = output_path.rsplit(".", 1)[0] if "." in output_path else output_path
    sidecar_path = f"{base}-speaker-embeddings.json"

    sidecar_data = {
        "version": "1.0",
        "source": os.path.basename(output_path),
        "unknown_speakers": {
            name: {"embedding": emb}
            for name, emb in unknown_embeddings.items()
        }
    }

    with open(sidecar_path, "w") as f:
        json.dump(sidecar_data, f, ensure_ascii=False, indent=2)

    _progress("voiceprint", f"未知声纹已保存: {os.path.basename(sidecar_path)}")
    return sidecar_path


# ─── 格式化输出 ───────────────────────────────────────────────────────────────

def _format_transcript(transcription: list, speaker_name_map: dict[str, str],
                       audio_path: str, elapsed: float, model_key: str,
                       num_speakers: int = 0) -> str:
    """将转录结果格式化为 Markdown。"""
    lines = []
    prev_speaker = None
    current_texts = []

    for speaker_label, text in transcription:
        speaker_name = speaker_name_map.get(speaker_label, speaker_label)
        if speaker_name == prev_speaker:
            current_texts.append(text)
        else:
            if prev_speaker is not None and current_texts:
                lines.append(f"{prev_speaker}: {''.join(current_texts)}")
            prev_speaker = speaker_name
            current_texts = [text]

    if prev_speaker is not None and current_texts:
        lines.append(f"{prev_speaker}: {''.join(current_texts)}")

    speaker_labels = sorted(set(s for s, _ in transcription))
    header = f"# 音频转录结果\n"
    header += f"- 文件: {os.path.basename(audio_path)}\n"
    header += f"- 说话人: {len(speaker_labels)} 位\n"
    header += f"- 处理时间: {elapsed:.1f}s\n"
    header += f"- 模型: {MODELS.get(model_key, model_key)}\n\n"

    return header + "\n".join(lines)


# ─── 单文件流程 ───────────────────────────────────────────────────────────────

def cmd_single(args):
    """单文件完整流程: 降噪 → 声纹分离 → ASR。

    P4 改进: 保存中间结果 (segments.json + speaker_map.json)，重跑可跳过 diarization。
    P5 改进: 保存纠错应用统计 (corrections_applied.json)。
    """
    audio_path = os.path.expanduser(args.audio)
    if not os.path.exists(audio_path):
        print(f"错误: 文件不存在 - {audio_path}", file=sys.stderr)
        sys.exit(1)

    memory_dir = Path(args.memory_dir) if args.memory_dir else DEFAULT_MEMORY_DIR
    replacements = _load_corrections(memory_dir) if memory_dir.exists() else {}
    speaker_names = _load_speaker_names(memory_dir) if memory_dir.exists() else {}

    start_time = time.time()
    _progress("pipeline", "开始", os.path.basename(audio_path))

    # P4: 确定中间结果目录
    if args.output:
        out_path = os.path.expanduser(args.output)
        if out_path.endswith("/") or os.path.isdir(out_path):
            os.makedirs(out_path, exist_ok=True)
            base_name = Path(audio_path).stem
            out_path = os.path.join(out_path, f"{base_name}_transcript.md")
        else:
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        intermediate_dir = os.path.dirname(out_path) or "."
    else:
        out_path = None
        intermediate_dir = None

    # P4: 检查是否有中间结果可恢复
    segments = None
    speaker_name_map = None
    unknown_embeddings = None
    process_path = audio_path

    if intermediate_dir:
        seg_cache = os.path.join(intermediate_dir, f"{Path(audio_path).stem}_segments.json")
        map_cache = os.path.join(intermediate_dir, f"{Path(audio_path).stem}_speaker_map.json")
        if os.path.exists(seg_cache) and os.path.exists(map_cache):
            _progress("pipeline", "检测到中间结果，跳过 diarization + voiceprint 阶段")
            segments = json.loads(Path(seg_cache).read_text())
            cache_data = json.loads(Path(map_cache).read_text())
            speaker_name_map = cache_data.get("speaker_name_map", {})
            unknown_embeddings = cache_data.get("unknown_embeddings", {})
            process_path = cache_data.get("process_path", audio_path)

    if segments is None:
        # Step 1: 降噪
        if not args.no_denoise:
            _progress("pipeline", "Step 1/4: 降噪")
            try:
                denoised = denoise_audio(audio_path)
                process_path = denoised
            except Exception as e:
                _log(f"降噪失败，使用原始音频: {e}")
        else:
            _progress("pipeline", "Step 1/4: 跳过降噪")

        # Step 2: 声纹分离
        _progress("pipeline", "Step 2/4: 声纹分离")
        segments = diarize_audio(process_path, args.speakers)
        if not segments:
            print("错误: 声纹分离未检测到任何说话人段", file=sys.stderr)
            sys.exit(1)

        # P4: 立即保存 segments 中间结果
        if intermediate_dir:
            seg_cache = os.path.join(intermediate_dir, f"{Path(audio_path).stem}_segments.json")
            Path(seg_cache).write_text(
                json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            _progress("pipeline", f"中间结果已保存: {os.path.basename(seg_cache)}")

        # Step 3: 声纹匹配
        _progress("pipeline", "Step 3/4: 声纹匹配")
        speaker_name_map, unknown_embeddings = _match_speakers_for_segments(process_path, segments, speaker_names)

        # P4: 保存 speaker_map 中间结果
        if intermediate_dir:
            map_cache = os.path.join(intermediate_dir, f"{Path(audio_path).stem}_speaker_map.json")
            Path(map_cache).write_text(json.dumps({
                "speaker_name_map": speaker_name_map,
                "unknown_embeddings": unknown_embeddings,
                "process_path": process_path,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        # 卸载 diarization + embedding 释放 GPU
        _unload_diarization()
        _unload_embedding()

    # Step 4: ASR 转录
    _progress("pipeline", "Step 4/4: ASR 转录")
    correction_stats: dict[str, int] = {}  # P5
    transcription = transcribe_segments(
        process_path, segments, args.language, args.model, replacements,
        correction_stats=correction_stats,
    )

    elapsed = time.time() - start_time
    output = _format_transcript(transcription, speaker_name_map, audio_path, elapsed, args.model)

    # 输出到文件或 stdout
    if out_path:
        Path(out_path).write_text(output, encoding="utf-8")
        if unknown_embeddings:
            _save_unknown_embeddings(unknown_embeddings, out_path)
        # P5: 保存纠错统计
        if correction_stats and replacements:
            _save_corrections_applied(correction_stats, replacements, out_path)
        # P4: 清理中间结果（转录成功后）
        for cache_file in [
            os.path.join(intermediate_dir, f"{Path(audio_path).stem}_segments.json"),
            os.path.join(intermediate_dir, f"{Path(audio_path).stem}_speaker_map.json"),
        ]:
            if os.path.exists(cache_file):
                os.unlink(cache_file)
        _progress("pipeline", "完成", f"输出: {out_path}, 耗时: {elapsed:.1f}s")
    else:
        print(output)
        if unknown_embeddings:
            sidecar_data = {
                "version": "1.0",
                "unknown_speakers": {
                    name: {"embedding": emb}
                    for name, emb in unknown_embeddings.items()
                }
            }
            print(f"\n<!-- speaker-embeddings: {json.dumps(sidecar_data, ensure_ascii=False)} -->", file=sys.stderr)
        _progress("pipeline", "完成", f"耗时: {elapsed:.1f}s")


# ─── 批量处理 ─────────────────────────────────────────────────────────────────

def cmd_batch(args):
    """批量两阶段处理。

    Phase A: 加载 pyannote 一次 → 降噪+diarize 所有文件 → 卸载
    Phase B: 加载 ASR 一次 → 转录所有文件 → 输出
    """
    audio_files = [os.path.expanduser(f) for f in args.audios]
    for f in audio_files:
        if not os.path.exists(f):
            print(f"错误: 文件不存在 - {f}", file=sys.stderr)
            sys.exit(1)

    output_dir = os.path.expanduser(args.output_dir) if args.output_dir else None
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    memory_dir = Path(args.memory_dir) if args.memory_dir else DEFAULT_MEMORY_DIR
    replacements = _load_corrections(memory_dir) if memory_dir.exists() else {}
    speaker_names = _load_speaker_names(memory_dir) if memory_dir.exists() else {}

    total_start = time.time()
    total_files = len(audio_files)
    _progress("batch", f"开始批量处理 {total_files} 个文件")

    # ──── Phase A: Diarize All ────
    _progress("Phase-A", f"=== 声纹分离阶段 ({total_files} 文件) ===")

    # 中间数据: {audio_path: {"segments": [...], "process_path": str, "speaker_map": dict}}
    file_data: dict[str, dict] = {}

    for idx, audio_path in enumerate(audio_files):
        fname = os.path.basename(audio_path)
        _progress("Phase-A", f"文件 {idx+1}/{total_files}", fname,
                  int((idx) / total_files * 50))

        # 降噪
        process_path = audio_path
        if not args.no_denoise:
            try:
                process_path = denoise_audio(audio_path)
            except Exception as e:
                _log(f"降噪失败 ({fname}): {e}")

        # 声纹分离
        segments = diarize_audio(process_path, args.speakers)
        if not segments:
            _log(f"跳过 {fname}: 未检测到说话人")
            continue

        # 声纹匹配
        speaker_map, unknown_embs = _match_speakers_for_segments(process_path, segments, speaker_names)

        file_data[audio_path] = {
            "segments": segments,
            "process_path": process_path,
            "speaker_map": speaker_map,
            "unknown_embeddings": unknown_embs,
        }

    # 卸载 Phase A 模型
    _unload_diarization()
    _unload_embedding()
    _progress("Phase-A", "完成，模型已卸载")

    # ──── Phase B: ASR All ────
    _progress("Phase-B", f"=== ASR 转录阶段 ({len(file_data)} 文件) ===")

    results: list[tuple[str, str, dict, dict]] = []

    for idx, (audio_path, data) in enumerate(file_data.items()):
        fname = os.path.basename(audio_path)
        _progress("Phase-B", f"文件 {idx+1}/{len(file_data)}", fname,
                  int(50 + (idx) / len(file_data) * 50))

        file_start = time.time()
        file_correction_stats: dict[str, int] = {}
        transcription = transcribe_segments(
            data["process_path"], data["segments"],
            args.language, args.model, replacements,
            correction_stats=file_correction_stats,
        )
        file_elapsed = time.time() - file_start

        output = _format_transcript(
            transcription, data["speaker_map"],
            audio_path, file_elapsed, args.model
        )
        results.append((audio_path, output, data.get("unknown_embeddings", {}), file_correction_stats))

    # 卸载 ASR
    _unload_asr()

    # 输出结果
    total_elapsed = time.time() - total_start

    for audio_path, transcript, unknown_embs, corr_stats in results:
        fname = Path(audio_path).stem
        if output_dir:
            out_path = os.path.join(output_dir, f"{fname}.md")
            Path(out_path).write_text(transcript, encoding="utf-8")
            if unknown_embs:
                _save_unknown_embeddings(unknown_embs, out_path)
            if corr_stats and replacements:
                _save_corrections_applied(corr_stats, replacements, out_path)
            _progress("output", f"已保存: {out_path}")
        else:
            print(f"\n{'='*60}")
            print(transcript)

    _progress("batch", "全部完成",
              f"{len(results)}/{total_files} 文件, 总耗时: {total_elapsed:.1f}s", 100)


# ─── 独立子命令 ───────────────────────────────────────────────────────────────

def cmd_denoise(args):
    """单独降噪。"""
    audio_path = os.path.expanduser(args.audio)
    if not os.path.exists(audio_path):
        print(f"错误: 文件不存在 - {audio_path}", file=sys.stderr)
        sys.exit(1)
    output = denoise_audio(audio_path, args.output or "")
    print(f"降噪完成: {output}")


def cmd_diarize(args):
    """单独声纹分离，输出 segments.json。"""
    out_dir = os.path.expanduser(args.output_dir) if args.output_dir else None
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    for audio_path in args.audios:
        audio_path = os.path.expanduser(audio_path)
        if not os.path.exists(audio_path):
            print(f"跳过: 文件不存在 - {audio_path}", file=sys.stderr)
            continue

        wav_path, is_temp = _ensure_wav(audio_path)
        try:
            segments = diarize_audio(wav_path, args.speakers)
        finally:
            if is_temp:
                os.unlink(wav_path)

        fname = Path(audio_path).stem
        if out_dir:
            out_path = os.path.join(out_dir, f"{fname}_segments.json")
        else:
            out_path = str(Path(audio_path).parent / f"{fname}_segments.json")

        Path(out_path).write_text(
            json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"声纹分离完成: {out_path} ({len(segments)} 段)")

    _unload_diarization()


def cmd_asr(args):
    """单独 ASR 转录，需要 segments.json。"""
    out_dir = os.path.expanduser(args.output_dir) if args.output_dir else None
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    memory_dir = Path(args.memory_dir) if args.memory_dir else DEFAULT_MEMORY_DIR
    replacements = _load_corrections(memory_dir) if memory_dir.exists() else {}

    seg_dir = os.path.expanduser(args.segments_dir)

    for audio_path in args.audios:
        audio_path = os.path.expanduser(audio_path)
        if not os.path.exists(audio_path):
            print(f"跳过: 文件不存在 - {audio_path}", file=sys.stderr)
            continue

        fname = Path(audio_path).stem
        seg_path = os.path.join(seg_dir, f"{fname}_segments.json")
        if not os.path.exists(seg_path):
            print(f"跳过: segments 不存在 - {seg_path}", file=sys.stderr)
            continue

        segments = json.loads(Path(seg_path).read_text())
        transcription = transcribe_segments(audio_path, segments, args.language, args.model, replacements)

        # 简单格式化
        lines = []
        prev_speaker = None
        current_texts = []
        for speaker, text in transcription:
            if speaker == prev_speaker:
                current_texts.append(text)
            else:
                if prev_speaker is not None and current_texts:
                    lines.append(f"{prev_speaker}: {''.join(current_texts)}")
                prev_speaker = speaker
                current_texts = [text]
        if prev_speaker is not None and current_texts:
            lines.append(f"{prev_speaker}: {''.join(current_texts)}")

        output = "\n".join(lines)

        if out_dir:
            out_path = os.path.join(out_dir, f"{fname}.md")
            Path(out_path).write_text(output, encoding="utf-8")
            print(f"转录完成: {out_path}")
        else:
            print(output)

    _unload_asr()


def cmd_register(args):
    """注册声纹，同步写入 voice-to-markdown-workflow 记忆。"""
    audio_path = os.path.expanduser(args.audio)
    if not os.path.exists(audio_path):
        print(f"错误: 文件不存在 - {audio_path}", file=sys.stderr)
        sys.exit(1)

    _progress("register", "提取声纹", args.name)
    try:
        embedding = _extract_embedding(audio_path)
        voiceprints = _load_voiceprints()

        found = False
        for vp in voiceprints:
            if vp["name"] == args.name:
                # 迁移旧格式: embedding → embeddings
                if "embedding" in vp and "embeddings" not in vp:
                    vp["embeddings"] = [vp.pop("embedding")]
                elif "embeddings" not in vp:
                    vp["embeddings"] = []
                vp["embeddings"].append(embedding.tolist())
                vp["updated_at"] = datetime.now().isoformat()
                found = True
                break

        if not found:
            voiceprints.append({
                "name": args.name,
                "embeddings": [embedding.tolist()],
                "created_at": datetime.now().isoformat(),
            })

        _save_voiceprints(voiceprints)
        action = "更新" if found else "注册"
        print(f"已{action}说话人声纹: {args.name}")

        # 同步到 voice-to-markdown-workflow 记忆
        memory_dir = Path(args.memory_dir) if args.memory_dir else DEFAULT_MEMORY_DIR
        roles = [r.strip() for r in args.role.split(",")] if args.role else None
        aliases = [a.strip() for a in args.alias.split(",")] if args.alias else None
        _sync_to_speaker_memory(args.name, memory_dir,
                                roles=roles, org=args.org, aliases=aliases)

    except Exception as e:
        print(f"声纹注册失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_speakers(args):
    """查看已注册声纹。"""
    voiceprints = _load_voiceprints()
    if not voiceprints:
        print("暂无已注册说话人")
        return

    print("已注册说话人:")
    for vp in voiceprints:
        created = vp.get("created_at", "未知")
        updated = vp.get("updated_at", "")
        n_emb = len(_get_embeddings(vp))
        info = f"  - {vp['name']} ({n_emb} 条声纹, 注册: {created})"
        if updated:
            info += f" (更新: {updated})"
        print(info)


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Audio Transcriber — 音频转录工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- single ---
    p_single = subparsers.add_parser("single", help="单文件完整流程")
    p_single.add_argument("audio", help="音频文件路径")
    p_single.add_argument("--speakers", type=int, default=0, help="说话人数量 (0=自动)")
    p_single.add_argument("--language", default="Chinese", help="语言 (默认 Chinese)")
    p_single.add_argument("--model", default="default", choices=["default", "small"])
    p_single.add_argument("--no-denoise", action="store_true", help="跳过降噪")
    p_single.add_argument("--memory-dir", dest="memory_dir", help="记忆目录路径")
    p_single.add_argument("-o", "--output", help="输出文件路径 (默认 stdout)")
    p_single.set_defaults(func=cmd_single)

    # --- batch ---
    p_batch = subparsers.add_parser("batch", help="批量两阶段处理")
    p_batch.add_argument("audios", nargs="+", help="音频文件路径列表")
    p_batch.add_argument("--speakers", type=int, default=0, help="说话人数量 (0=自动)")
    p_batch.add_argument("--language", default="Chinese", help="语言 (默认 Chinese)")
    p_batch.add_argument("--model", default="default", choices=["default", "small"])
    p_batch.add_argument("--no-denoise", action="store_true", help="跳过降噪")
    p_batch.add_argument("--memory-dir", dest="memory_dir", help="记忆目录路径")
    p_batch.add_argument("-o", "--output-dir", help="输出目录 (默认 stdout)")
    p_batch.set_defaults(func=cmd_batch)

    # --- denoise ---
    p_denoise = subparsers.add_parser("denoise", help="单独降噪")
    p_denoise.add_argument("audio", help="音频文件路径")
    p_denoise.add_argument("-o", "--output", help="输出路径")
    p_denoise.set_defaults(func=cmd_denoise)

    # --- diarize ---
    p_diarize = subparsers.add_parser("diarize", help="单独声纹分离")
    p_diarize.add_argument("audios", nargs="+", help="音频文件路径列表")
    p_diarize.add_argument("--speakers", type=int, default=0, help="说话人数量 (0=自动)")
    p_diarize.add_argument("-o", "--output-dir", help="segments 输出目录")
    p_diarize.set_defaults(func=cmd_diarize)

    # --- asr ---
    p_asr = subparsers.add_parser("asr", help="单独 ASR 转录")
    p_asr.add_argument("audios", nargs="+", help="音频文件路径列表")
    p_asr.add_argument("-s", "--segments-dir", required=True, help="segments.json 目录")
    p_asr.add_argument("--language", default="Chinese", help="语言 (默认 Chinese)")
    p_asr.add_argument("--model", default="default", choices=["default", "small"])
    p_asr.add_argument("--memory-dir", dest="memory_dir", help="记忆目录路径")
    p_asr.add_argument("-o", "--output-dir", help="输出目录")
    p_asr.set_defaults(func=cmd_asr)

    # --- register ---
    p_register = subparsers.add_parser("register", help="注册声纹")
    p_register.add_argument("audio", help="含说话人语音的音频")
    p_register.add_argument("--name", required=True, help="说话人姓名")
    p_register.add_argument("--role", help="角色 (逗号分隔，如 'CEO,创始人')")
    p_register.add_argument("--org", help="所属组织")
    p_register.add_argument("--alias", help="别名 (逗号分隔，如 '老王,王总')")
    p_register.add_argument("--memory-dir", dest="memory_dir", help="记忆目录路径")
    p_register.set_defaults(func=cmd_register)

    # --- speakers ---
    p_speakers = subparsers.add_parser("speakers", help="查看已注册声纹")
    p_speakers.set_defaults(func=cmd_speakers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
