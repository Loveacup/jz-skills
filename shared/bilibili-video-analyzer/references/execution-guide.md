<!-- 用途说明：本文档包含 bilibili-video-analyzer 的所有脚本使用方法、依赖配置、音频转录方案等操作细节。在需要执行具体操作时加载。 -->

# Bilibili Video Analyzer 执行指南

## 依赖说明

### 核心依赖

| 依赖 | 用途 | 安装命令 |
|:---|:---|:---|
| **bilibili-api-python** | B站API封装（WBI签名） | `pip3 install bilibili-api-python` |
| **ffmpeg** | 音频处理 | `brew install ffmpeg` |

### 字幕/转录依赖（三选一）

| 方案 | 适用场景 | 安装命令 |
|:---|:---|:---|
| **官方字幕** | 视频自带字幕 | 无需安装 |
| **whisper-cpp** ⭐ | 已有本地模型/VoiceInk | `brew install whisper-cpp` |
| **mlx-whisper** | 首次使用/Apple Silicon | `pip3 install mlx-whisper` |

### 模型路径参考

**VoiceInk 模型**（如果已安装 VoiceInk）：
```
~/Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/
├── ggml-large-v3-turbo.bin (1.6GB) ⭐ 推荐
└── ggml-silero-v5.1.2.bin
```

**whisper.cpp 官方模型**：
- 下载地址：https://huggingface.co/ggerganov/whisper.cpp/tree/main
- 推荐：`ggml-large-v3-turbo.bin`

### 为什么使用 bilibili-api-python？
- ✅ 自动处理 **WBI 签名**（解决旧API字幕映射错误）
- ✅ 异步架构，性能更好
- ✅ 官方维护，适配B站最新API变更

### 已知问题
**旧API (`api.bilibili.com/x/player/v2`) 已弃用**
- 症状：返回随机/错误的字幕内容（iPhone评测、帕尼尼减肥等无关内容）
- 原因：B站更新了字幕系统，旧API返回映射错误的字幕
- 解决方案：使用 `bilibili-api-python` 的 WBI API

参考: [yt-dlp PR #11708](https://github.com/yt-dlp/yt-dlp/pull/11708)

---

## 脚本使用示例

### 基础流程

```bash
# 1. 获取视频信息+官方字幕
python3 scripts/fetch_subtitle.py BV12Q6TBwE2J "YOUR_SESSDATA"

# 2. 获取弹幕
python3 scripts/fetch_danmaku.py 35641886387 "YOUR_SESSDATA"

# 3. 获取评论
python3 scripts/fetch_comments.py BV12Q6TBwE2J "YOUR_SESSDATA" 50

# 4. 生成报告
python3 scripts/generate_report.py BV12Q6TBwE2J
```

### 无字幕视频处理（音频转录）

**方案A: whisper.cpp + VoiceInk 模型** ⭐ 推荐（已验证）

```bash
# 1. 安装依赖
brew install whisper-cpp ffmpeg

# 2. 获取音频流 URL（从视频页面提取）
# 输出: https://xy112x...mcdn.bilivideo.cn/...m4s

# 3. 下载并转录音频
ffmpeg -i "音频流URL" -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# 4. 转录（利用 VoiceInk 已有模型）
whisper-cli \
  -m "$HOME/Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo.bin" \
  -f audio.wav \
  -l zh \
  -otxt

# 输出: audio_transcript.txt（完整字幕）
```

**方案B: mlx-whisper**（首次使用）

```bash
# 安装
pip3 install mlx-whisper

# 使用（首次需下载 ~1.5GB 模型）
python3 scripts/audio_to_text.py BV12Q6TBwE2J "YOUR_SESSDATA"
```

### ⚠️ ffmpeg 直接下载 B站音频 → 403 Forbidden

B站音频 URL 含时效性签名，直接用 `ffmpeg -i "$AUDIO_URL"` 会报 403。**正确流程**：

```bash
# 1. 用 curl 下载（带 Referer + User-Agent）
curl -L -o audio.m4s \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  -H 'Referer: https://www.bilibili.com/' \
  "$AUDIO_URL"

# 2. ffmpeg 对本地文件转码
ffmpeg -i audio.m4s -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# 3. whisper-cli 转录
whisper-cli -m "$MODEL_PATH" -f audio.wav -l zh -otxt
```

> **原理**：B站 CDN 的签名 URL 有时效，ffmpeg 打开连接时签名可能已过期。curl 在获取 URL 后立即下载，时机更短。Ref: 本轮 BV1zWRrBnE6s 实测验证。

### 实测参考

**Hermes Profile 分身术视频**（BV1zWRrBnE6s，本轮实测）：
- 时长：~18分36秒
- 转录方案：curl 下载 `.m4s` → ffmpeg 转 `.wav` → whisper.cpp（VoiceInk 模型）
- 处理时间：~84s（Apple M4 GPU）
- 输出：13KB / 494 行
- **关键坑**：ffmpeg 直接下载返回 403 → 必须先 curl 再本地转码

**Agent Skills 蓝皮书视频**（BV1t467BFEPb）：
- 时长：32分钟
- 处理时间：~2分钟（whisper.cpp + M4）
- 输出：23KB / 23,475字符
- 准确率：中文 95%+

---

## 音频转录方案

### 方案对比

| 方案 | 适用场景 | 速度 | 依赖 |
|:---|:---|:---|:---|
| **官方/AI字幕** | 视频有字幕 | 最快 | 无需额外依赖 |
| **mlx-whisper** | 本地 Apple Silicon | 快 | 需下载模型 (~1.5GB) |
| **whisper.cpp + 本地模型** ⭐ | 已有 VoiceInk/whisper 模型 | **最快** | 利用已有模型 |

### 推荐方案：whisper.cpp + 本地模型

**适用条件**：Mac 用户且已安装 VoiceInk 或其他 whisper 模型

**流程**：
```
视频BV号 → 获取音频流URL → ffmpeg下载并转码 → whisper.cpp转录 → 生成字幕
```

**步骤**：

1. **安装 whisper-cpp**
   ```bash
   brew install whisper-cpp
   ```

2. **获取音频流**（从视频页面提取 DASH 音频 URL）

3. **转录**（使用 VoiceInk 已有模型）
   ```bash
   # 方法A: 直接转录（推荐，利用已有模型）
   whisper-cli \
     -m "/Users/$USER/Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo.bin" \
     -f audio.wav \
     -l zh \
     -otxt

   # 方法B: 使用一键脚本
   ~/clawd/scripts/stt_voiceink.sh audio.wav
   ```

**实测数据**（Apple M4）：
- 32分钟音频 → 约 2 分钟处理
- 准确率：中文 95%+
- 输出：23KB / 23,475 字符

### 备选方案：mlx-whisper

**适用条件**：首次使用或没有本地 whisper 模型

```bash
# 安装
pip3 install mlx-whisper

# 使用（首次需下载模型）
mlx_whisper audio.wav --language Chinese --output_format txt
```

### 通用依赖

| 工具 | 用途 | 安装 |
|:---|:---|:---|
| ffmpeg | 音频下载+格式转换 | `brew install ffmpeg` |

### 准确率说明
- ✅ 对于清晰的语音内容，准确率可达 **95%+**
- ✅ 支持中文、英文及混合语言
- ⚠️ 背景音乐较大会影响识别
- ⚠️ 专业术语可能需要人工校对

---

## 文件保存与清理

### 输出路径检测

**路径检测优先级**：
```
保存路径检测流程:
1. 查找标准 Obsidian Vault 位置
   └── ~/Documents/Obsidian/*/00-Inbox/
2. 若找到，使用第一个匹配路径
3. 若未找到，回退到工作区路径
   └── ~/clawd/00-Inbox/
4. 保存前验证路径存在，不存在则创建
```

**推荐路径结构**：
```
~/Documents/Obsidian/[VaultName]/
├── 000_日记/
├── 00-Inbox/
├── 002_工作/
├── 003_AI/
├── 00-Inbox/          ← 视频解析报告保存到这里
│   ├── 视频解析_xxx.md
│   └── 视频深度解析_xxx.md
├── 005_学习/
└── ...
```

**保存操作规范**：

1. **检测 Vault 位置**：
   ```bash
   # 查找可能的 Obsidian Vault 路径
   find ~ -maxdepth 3 -type d -name "Obsidian" 2>/dev/null
   # 或查找包含 .obsidian 文件夹的目录
   find ~ -maxdepth 4 -type d -name ".obsidian" 2>/dev/null | head -1 | xargs dirname
   ```

2. **确定目标目录**：
   - 优先：`~/Documents/Obsidian/[VaultName]/00-Inbox/`
   - 备选：`~/clawd/00-Inbox/`

3. **保存后验证**：
   ```bash
   # 验证文件是否存在
   ls -la "[目标路径]/视频解析_[关键词]_[作者].md"
   # 输出文件路径
   echo "报告已保存至：[完整路径]"
   ```

**输出规范**：
- **最终结果**：`00-Inbox/视频解析_[关键词]_[作者].md`
- **临时文件**：分析完成后自动清理（音频、JSON数据、页面缓存等）
- **路径确认**：保存后必须告知用户完整的文件路径

### Phase 4 清理与归档脚本

**步骤 1: 确定输出路径**

```bash
# 自动检测 Obsidian Vault 路径
VAULT_PATH=$(find ~ -maxdepth 3 -type d -name "Obsidian" 2>/dev/null | head -1)
if [ -n "$VAULT_PATH" ]; then
    # 找到 Vault，使用第一个子目录作为目标
    TARGET_DIR="${VAULT_PATH}/$(ls "$VAULT_PATH" | head -1)/00-Inbox"
else
    # 未找到 Vault，使用工作区路径
    TARGET_DIR="$HOME/clawd/00-Inbox"
fi

# 确保目录存在
mkdir -p "$TARGET_DIR"
```

**步骤 2: 移动报告到正确位置**

```bash
# 如果报告在工作区，移动到 Vault
if [ -f "$HOME/clawd/00-Inbox/视频解析_${KEYWORD}_${AUTHOR}.md" ]; then
    mv "$HOME/clawd/00-Inbox/视频解析_${KEYWORD}_${AUTHOR}.md" "$TARGET_DIR/"
fi

# 验证文件位置
ls -la "$TARGET_DIR/视频解析_${KEYWORD}_${AUTHOR}.md"
```

**步骤 3: 清理临时文件**

```bash
# 清理过程文件（保留最终结果）
rm -f /tmp/${BV}_*.json      # API响应数据
rm -f /tmp/${BV}_*.txt       # 中间文本文件
rm -f /tmp/${BV}_*.wav       # 音频文件
rm -f /tmp/${BV}_*.html      # 页面缓存

# 保留文件（可选，建议保留7天后清理）
# /tmp/${BV}_transcript_full.txt    # 完整转录文本
# /tmp/${BV}_danmaku.json           # 弹幕数据
```

**步骤 4: 输出确认信息**

保存完成后必须输出：
- ✅ 报告完整路径
- ✅ 文件大小
- ✅ 简要内容摘要

---

## 执行脚本清单

| 脚本 | 功能 | 依赖 |
|:---|:---|:---|
| `scripts/fetch_subtitle.py` | 获取官方/AI字幕 | bilibili-api-python |
| `scripts/fetch_danmaku.py` | 获取弹幕 | 无 |
| `scripts/fetch_comments.py` | 获取评论 | 无 |
| `scripts/audio_to_text.py` | 音频转录（mlx-whisper） | mlx-whisper |
| `scripts/transcribe_whisper_cpp.sh` ⭐ | 音频转录（whisper.cpp+本地模型） | whisper-cpp, ffmpeg |
| `scripts/generate_report.py` | 生成解析报告 | 无 |

### 使用 whisper.cpp 转录（推荐）

```bash
# 1. 准备脚本
chmod +x ~/clawd/scripts/stt_voiceink.sh

# 2. 转录音频
~/clawd/scripts/stt_voiceink.sh /path/to/audio.wav

# 输出: audio_transcript.txt
```

---

## 时间戳规则

- B站格式：`https://www.bilibili.com/video/BVxxxxx?t={总秒数}`
- 计算：Total Seconds = Minutes × 60 + Seconds
- 密度：每300字至少1个可点击时间戳

## 引用规则

- 金句原文用 `"` 包裹，与字幕完全一致
- 弹幕引用标注情绪类型和出现时机
- 删减内容用 `...` 标记
