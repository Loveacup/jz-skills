---
name: audio-transcriber
description: "音频转录工具。将音频文件转为带说话人标签的文字记录。核心能力：(1) 频谱门控降噪 (2) 声纹分离+说话人识别 (3) 中文 ASR 转录 (4) 批量两阶段处理 (5) 声纹注册与匹配 (6) 记忆系统纠错 (7) 过度分割自动合并 (8) 分层匹配 (9) 中间结果恢复 (10) 纠错统计回写 (11) 长音频分块 diarization。技术栈：noisereduce (降噪) + pyannote.audio 4.x (声纹分离, MPS GPU) + Qwen3-ASR (MLX, ASR 转录)。触发词：转录音频、语音转文字、audio transcribe、transcribe、声纹分离、diarize、降噪音频、denoise、注册声纹。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [audio, transcription, asr, diarization, speech-to-text]
---

# Audio Transcriber Skill

## 变量定义

```
PYTHON=~/.hermes/skills/audio-transcriber/scripts/.venv/bin/python
SCRIPT=~/.hermes/skills/audio-transcriber/scripts/transcribe.py
```

> 从 jz-skills 部署时路径为 `~/.hermes/skills/audio-transcriber/`，开发时可用 jz-skills/shared/audio-transcriber/ 路径。

## 用法

### 单文件转录

最常用场景。完整流程：降噪 → 声纹分离 → 声纹匹配 → ASR 转录。

```bash
$PYTHON $SCRIPT single <音频文件> [选项]
```

选项：
- `--speakers N` — 指定说话人数量 (0=自动检测, 默认)
- `--language Chinese` — 语言 (默认 Chinese)
- `--model default|small` — ASR 模型 (default=1.7B 高精度, small=0.6B 快速)
- `--no-denoise` — 跳过降噪步骤
- `-o <file>` — 输出到文件 (默认 stdout)
- `--memory-dir <dir>` — 自定义记忆目录

示例：
```bash
# 基本用法
$PYTHON $SCRIPT single ~/audio/meeting.wav

# 指定2位说话人，输出到文件
$PYTHON $SCRIPT single ~/audio/meeting.wav --speakers 2 -o ~/output/meeting.md

# 快速模式，跳过降噪
$PYTHON $SCRIPT single ~/audio/short.wav --model small --no-denoise
```

### 批量处理

多文件两阶段优化：Phase A 一次性加载 pyannote 处理所有声纹分离，卸载后 Phase B 一次性加载 ASR 处理所有转录。模型各只加载一次。

```bash
$PYTHON $SCRIPT batch <文件1> <文件2> ... [选项]
```

选项同 single，额外：
- `-o <dir>` — 输出目录 (每文件生成 `{stem}.md`)

示例：
```bash
# 批量处理目录下所有 wav
$PYTHON $SCRIPT batch ~/audio/*.wav -o ~/output/

# 指定文件
$PYTHON $SCRIPT batch file1.wav file2.wav file3.wav -o /tmp/results/
```

### 独立操作

当只需要管线中某个步骤时使用：

```bash
# 仅降噪
$PYTHON $SCRIPT denoise <音频> [-o output_path]

# 仅声纹分离 (输出 segments.json)
$PYTHON $SCRIPT diarize <文件1> <文件2> ... [-o segments_dir]

# 仅 ASR (需要 segments.json)
$PYTHON $SCRIPT asr <文件1> <文件2> ... -s <segments_dir> [-o output_dir]
```

### 声纹管理

```bash
# 注册声纹
$PYTHON $SCRIPT register <含说话人语音的音频> --name <姓名>

# 查看已注册声纹
$PYTHON $SCRIPT speakers
```

## 执行策略

### 短音频 (< 10 分钟)

直接使用 `terminal` 工具同步执行：
```bash
$PYTHON $SCRIPT single <audio> -o <output>
```

### 长音频 (10-70 分钟)

使用后台执行避免阻塞：
```bash
$PYTHON $SCRIPT single <audio> -o <output>
```
使用 `terminal(background=true, notify_on_complete=true)`。

> 超过 10 分钟的音频自动启用分块 diarization，逐块输出进度 `块 3/17 (18%)`，
> 失败后重跑自动跳过已完成的块。详见"分块 Diarization"章节。

进度输出格式：`[phase] step detail (pct%)`

### 超长音频或多文件

batch 子命令自动做两阶段优化：
```bash
$PYTHON $SCRIPT batch <files...> -o <dir>
```
同样建议后台执行。

## 记忆系统协同

本 skill 只读 voice-to-markdown-workflow 的记忆系统：

| 文件 | 用途 |
|------|------|
| `corrections.json` | ASR 纠错："底裤"→"底库" |
| `patterns.json` (type=asr_correction) | 结晶化纠错规则 |
| `speakers.json` | 已知说话人信息 (辅助命名) |

默认路径：`~/.hermes/skills/voice-to-markdown-workflow/memory/`

可通过 `--memory-dir` 覆盖。

## 声纹匹配改进 (v2)

### 分层匹配阈值

| 分数范围 | 标签 | 输出格式 | 说明 |
|---------|------|---------|------|
| ≥ 0.75 | 确认 | `邵总：` | 高置信度，直接使用 |
| 0.60-0.75 | 候选 | `杨文?：` | 带 ? 标记，需 workflow Phase 5 确认 |
| < 0.60 | 未知 | `Speaker 1：` | 保存嵌入到 sidecar |

### 过度分割自动合并

pyannote 在长录音中会将同一说话人拆分为多个 SPEAKER ID。新版自动合并：
1. 多个 label 匹配到同一已知人名 → 自动合并
2. 未知说话人之间嵌入相似度 > 0.75 → 合并为同一 Speaker N

### Top-3 嵌入平均

每个说话人取最长的 3 个片段(≥3 秒)提取嵌入后取归一化均值，比单一最长片段更稳健。

### 候选匹配的 sidecar 处理

候选匹配(带 ? 标记)的嵌入也保存到 sidecar，因为可能判断错误。下游 workflow Phase 5 可以：
- 确认候选 → 去掉 ? 后缀
- 否认候选 → 重新标记为 Speaker N

## 分块 Diarization (长音频)

超过 10 分钟的音频自动启用分块模式，解决三个痛点：

| 痛点 | 解决方案 |
|------|---------|
| 无进度可见 | 逐块输出 `块 3/17 (18%)` |
| 失败需全部重来 | 每块完成后缓存到磁盘，重跑跳过已完成的块 |
| 单块失败污染全局 | 只重跑失败的块 |

### 工作流程

```
音频 (70min) → 切为 10min × 7 块 (30s 重叠)
  ↓
逐块 diarize (每块完成存 cache)
  ↓
去重重叠区域 (保留前一块)
  ↓
跨块说话人合并 (嵌入相似度 ≥ 0.70 → union-find 合并)
  ↓
统一 SPEAKER_XX 标签
```

### 参数

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_THRESHOLD_SECONDS` | 600 | 超过此时长启用分块 |
| `CHUNK_DURATION_SECONDS` | 600 | 每块时长 |
| `CHUNK_OVERLAP_SECONDS` | 30 | 块间重叠 |
| `CHUNK_MERGE_THRESHOLD` | 0.70 | 跨块说话人合并阈值 |

### 缓存目录

缓存存放在音频文件同目录的 `.diarize_cache_{stem}/` 下：
- `chunk_0000.json`, `chunk_0001.json`, ... — 每块的 diarization 结果
- 全部完成后自动清理

### 注意事项

- 分块模式会将完整音频读入内存（`sf.read`），70 分钟 16kHz 单声道约 ~130MB
- 跨块合并阈值 0.70 略低于声纹库匹配阈值 0.75，因为同一说话人在不同片段的嵌入差异更大
- `--speakers N` 在分块模式下对每块独立生效，长音频建议设为 0（自动检测）

## 中间结果恢复 (P4)

使用 `-o` 输出时，diarization 完成后立即保存中间结果：
- `{stem}_segments.json` — 声纹分离结果
- `{stem}_speaker_map.json` — 声纹匹配映射

若 ASR 阶段中断，重跑时自动检测并跳过 diarization 阶段，直接进入 ASR。转录成功后自动清理中间文件。

## 纠错统计回写 (P5)

转录完成后，输出 `{stem}-corrections-applied.json`：
```json
{
  "session": "2026-02-12T14:30:00",
  "source": "meeting_transcript.md",
  "applied": {"底裤→底库": 12, "伤保→商保": 3},
  "total_replacements": 15
}
```
供 voice-to-markdown-workflow Phase 8 读取，更新 corrections.json 的统计数据。

## HF 离线模式

ASR 模型缓存存在时自动启用 `HF_HUB_OFFLINE=1`，无需手动设置。检测路径：
- `$HF_HOME/hub/models--{model_id}`
- `~/.cache/huggingface/hub/models--{model_id}`

## 输出格式

Markdown，包含：
- 文件名、说话人数、处理时间、模型信息
- 带说话人标签的转录文本 (连续同一说话人合并)

```markdown
# 音频转录结果
- 文件： meeting.wav
- 说话人： 3 位
- 处理时间： 95.2s
- 模型： mlx-community/Qwen3-ASR-1.7B-8bit

邵总： 今天我们讨论一下项目进展...
杨文?： 好的，我先汇报一下...
Speaker 1： 我补充一点...
```

## 与 voice-to-markdown-workflow 的配合

典型工作流：
1. **audio-transcriber** 将音频转为带说话人标签的文字
2. **voice-to-markdown-workflow** 将文字整理为结构化文档

两步分离的好处：
- 转录可后台运行，不阻塞
- 用户可在转录完成后检查、修正，再交给下游处理
- 批量转录多文件后，逐个或打包送入 workflow
