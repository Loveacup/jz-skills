#!/bin/bash
# Bilibili 视频音频转录脚本（whisper.cpp + 本地模型）
# 使用方法: ./transcribe_whisper_cpp.sh <BV号> [音频文件]

set -e

BV="${1:-}"
AUDIO_FILE="${2:-}"

# 配置
MODEL_PATH="${WHISPER_MODEL:-$HOME/Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo.bin}"
OUTPUT_DIR="/tmp"

echo "🎙️ Bilibili 视频音频转录"
echo "=========================="

# 检查依赖
if ! command -v whisper-cli &> /dev/null; then
    echo "❌ 未安装 whisper-cpp"
    echo "   安装: brew install whisper-cpp"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 未安装 ffmpeg"
    echo "   安装: brew install ffmpeg"
    exit 1
fi

# 检查模型
if [ ! -f "$MODEL_PATH" ]; then
    echo "⚠️  未找到本地模型: $MODEL_PATH"
    echo ""
    echo "解决方案:"
    echo "1. 安装 VoiceInk（推荐）: https://voiceink.app"
    echo "2. 或下载 whisper.cpp 模型:"
    echo "   curl -L -o ggml-large-v3-turbo.bin \"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin\""
    exit 1
fi

echo "✅ 模型: $(basename "$MODEL_PATH")"

# 如果提供了音频文件，直接转录
if [ -n "$AUDIO_FILE" ] && [ -f "$AUDIO_FILE" ]; then
    echo "📁 音频: $AUDIO_FILE"
    
    OUTPUT_NAME="${AUDIO_FILE%.*}_transcript"
    
    echo "📝 开始转录..."
    whisper-cli \
        -m "$MODEL_PATH" \
        -f "$AUDIO_FILE" \
        -l zh \
        -otxt \
        -of "$OUTPUT_NAME" \
        --no-timestamps
    
    echo ""
    echo "✅ 转录完成!"
    echo "📄 输出: ${OUTPUT_NAME}.txt"
    exit 0
fi

# 如果没有提供音频文件，尝试从 BV 号下载
if [ -z "$BV" ]; then
    echo "❌ 请提供 BV 号或音频文件"
    echo ""
    echo "用法:"
    echo "  $0 <BV号>"
    echo "  $0 <BV号> <音频文件>"
    echo ""
    echo "示例:"
    echo "  $0 BV1t467BFEPb"
    echo "  $0 BV1t467BFEPb /path/to/audio.wav"
    exit 1
fi

echo "🎯 BV号: $BV"
echo "📥 获取视频信息..."

# 获取视频信息
python3 << PYEOF
import requests
import re
import json

bv = "$BV"
url = f"https://www.bilibili.com/video/{bv}"

resp = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/"
}, timeout=15)

# 提取音频流
playinfo = re.search(r'window\.__playinfo__\s*=\s*({.*?})</script>', resp.text, re.DOTALL)

if playinfo:
    data = json.loads(playinfo.group(1))
    dash = data.get('data', {}).get('dash', {})
    audios = dash.get('audio', [])
    
    if audios:
        best_audio = max(audios, key=lambda x: x.get('bandwidth', 0))
        audio_url = best_audio.get('baseUrl') or best_audio.get('backupUrl', [None])[0]
        
        if audio_url:
            with open(f"/tmp/{bv}_audio_url.txt", "w") as f:
                f.write(audio_url)
            print(f"✅ 找到音频流")
        else:
            print("❌ 未找到音频 URL")
    else:
        print("❌ 未找到音频流")
else:
    print("❌ 未找到 playinfo")
PYEOF

# 检查是否获取到音频 URL
if [ ! -f "/tmp/${BV}_audio_url.txt" ]; then
    echo "❌ 获取音频流失败"
    exit 1
fi

AUDIO_URL=$(cat "/tmp/${BV}_audio_url.txt")
WAV_FILE="${OUTPUT_DIR}/${BV}_audio.wav"

echo ""
echo "📥 下载音频..."
ffmpeg -headers "Referer: https://www.bilibili.com/" \
    -i "$AUDIO_URL" \
    -vn -acodec pcm_s16le -ar 16000 -ac 1 \
    "$WAV_FILE" -y 2>&1 | tail -5

if [ ! -f "$WAV_FILE" ]; then
    echo "❌ 下载音频失败"
    exit 1
fi

echo "✅ 音频已保存: $WAV_FILE"

# 转录
OUTPUT_NAME="${OUTPUT_DIR}/${BV}_transcript"

echo ""
echo "📝 开始转录..."
echo "   模型: $(basename "$MODEL_PATH")"
echo "   语言: 中文"
echo ""

whisper-cli \
    -m "$MODEL_PATH" \
    -f "$WAV_FILE" \
    -l zh \
    -otxt \
    -of "$OUTPUT_NAME" \
    --no-timestamps 2>&1 | tail -10

echo ""
echo "✅ 转录完成!"
echo "=================="
echo "📄 字幕文件: ${OUTPUT_NAME}.txt"
echo "📊 文件大小: $(ls -lh ${OUTPUT_NAME}.txt 2>/dev/null | awk '{print $5}' || echo 'unknown')"
echo "📝 字符数: $(wc -c < ${OUTPUT_NAME}.txt 2>/dev/null || echo '0')"
echo ""
echo "💡 提示:"
echo "   字幕文件可用于生成视频解析报告"
echo "   或导入 Obsidian 进行进一步分析"
