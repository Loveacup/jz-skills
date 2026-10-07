# Audio Transcriber 架构参考

## 两阶段批量处理架构

### 为什么是两阶段

Apple Silicon 统一内存架构下，pyannote (PyTorch/MPS) 和 Qwen3-ASR (MLX) 共享 GPU 显存:

| 模型 | 框架 | GPU 占用 | 加载时间 |
|------|------|---------|---------|
| pyannote diarization | PyTorch MPS | ~3GB | ~6s |
| wespeaker embedding | PyTorch CPU | ~0.5GB | ~2s |
| Qwen3-ASR 1.7B-8bit | MLX | ~2GB | ~2s |

32GB 统一内存理论上可同时容纳，但实际存在问题:
- PyTorch MPS 和 MLX 的 GPU 调度有竞争
- 同时运行不提速（GPU 是单一计算资源）
- 内存碎片化导致 OOM 风险

两阶段串行方案:
- Phase A: 加载 pyannote + embedding → 处理所有文件 → 显式卸载 + `torch.mps.empty_cache()`
- Phase B: 加载 ASR → 处理所有文件 → 完成

### 流程图

```
输入: [file1.wav, file2.wav, file3.wav]
    │
    ▼
┌─────────── Phase A: Diarize ───────────┐
│ 1. 加载 pyannote (一次, ~6s)            │
│ 2. 对每个文件:                          │
│    a. 降噪 (noisereduce, CPU)           │
│    b. 声纹分离 → segments              │
│    c. 声纹匹配 → speaker_map           │
│ 3. 卸载 pyannote + embedding           │
│    del pipeline; torch.mps.empty_cache()│
└─────────────────────────────────────────┘
    │ 中间数据: {file: {segments, speaker_map}}
    ▼
┌─────────── Phase B: ASR ───────────────┐
│ 1. 加载 ASR 模型 (一次, ~2s)            │
│ 2. 加载纠错规则 (memory)                │
│ 3. 对每个文件:                          │
│    a. 读取 segments                    │
│    b. 逐段转录 + 即时纠错              │
│    c. 格式化输出                       │
│ 4. 卸载 ASR                            │
└─────────────────────────────────────────┘
    │
    ▼
输出: [file1.md, file2.md, file3.md]
```

## 性能基准 (MPS GPU)

测试环境: Apple M5, 32GB, macOS 26.2

### 单文件

| 时长 | 降噪 | 声纹分离 | ASR | 总计 |
|------|------|---------|-----|------|
| 2 min | ~2s | ~3s | ~20s | ~25s |
| 5 min | ~4s | ~6s | ~45s | ~55s |
| 10 min | ~8s | ~10s | ~80s | ~100s |
| 70 min | ~50s | ~70s | ~10min | ~12min |

### 批量 (两阶段优化)

| 场景 | 模型加载 | 处理 | 总计 | vs 逐个 |
|------|---------|------|------|--------|
| 5 × 10min | ~8s | ~9min | ~10min | 节省 ~30s |
| 5 × 70min | ~8s | ~58min | ~60min | 节省 ~30s |

批量优化主要节省模型加载时间 (~6s×N)。实际处理时间受 GPU 算力限制，接近线性增长。

### MPS vs CPU

| 步骤 | CPU | MPS | 加速比 |
|------|-----|-----|--------|
| 声纹分离 (10min) | ~63s | ~10s | 6.3x |
| ASR 转录 | MLX 原生 | MLX 原生 | - |
| 降噪 | CPU only | CPU only | - |

关键: pyannote diarization 的 MPS 加速是最大性能收益来源。

## 进度输出协议

所有进度信息输出到 stdout，格式:

```
[phase] step detail (pct%)
```

示例:
```
[model] 加载 pyannote diarization...
[model] pyannote 加载完成 (MPS GPU)
[diarize] 开始 meeting.wav
[diarize] 完成 42 段, 3 位说话人
[model] pyannote 已卸载，GPU 显存已释放
[model] 加载 ASR 模型: mlx-community/Qwen3-ASR-1.7B-8bit
[asr] 转录 1/42 0.0s-3.2s (SPEAKER_00) (2%)
[asr] 转录 42/42 298.1s-301.5s (SPEAKER_01) (100%)
[pipeline] 完成 耗时: 95.2s
```

## 纠错规则格式

### corrections.json

```json
{
  "corrections": [
    {"wrong": "底裤", "correct": "底库", "type": "term", "occurrences": 8}
  ]
}
```

加载方式: 直接取 `wrong` → `correct` 构建替换字典。

### patterns.json (asr_correction)

```json
{
  "patterns": [
    {
      "type": "asr_correction",
      "rule": "\"底裤\" → \"底库\"：ASR高频错误...",
      "status": "active"
    }
  ]
}
```

加载方式: 解析 `rule` 字段中 `"X" → "Y"` 格式，提取替换对。

两个来源合并去重后统一应用。

## 文件格式兼容性

### soundfile 原生支持
`.wav`, `.flac`, `.ogg`, `.aiff`, `.aif`

### ffmpeg 转换
`.mp3`, `.m4a`, `.aac`, `.wma`, `.opus`, `.qta` 等 — 自动调用 ffmpeg 转 16kHz mono WAV。

## 声纹数据库

路径: `~/.claude/skills/audio-transcriber/voiceprints.json`

格式:
```json
[
  {
    "name": "张三",
    "embedding": [0.123, -0.456, ...],  // 256维向量
    "created_at": "2026-02-12T10:00:00",
    "updated_at": "2026-02-12T12:00:00"
  }
]
```

匹配阈值: cosine similarity > 0.7
