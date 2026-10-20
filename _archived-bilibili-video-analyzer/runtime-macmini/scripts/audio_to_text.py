#!/usr/bin/env python3
"""
Bilibili 视频音频下载 + 语音转文字
用法: python3 audio_to_text.py <BV号> [输出目录]

流程:
1. 获取视频下载链接 (使用 bilibili-api-python)
2. 下载音频流 (m4s格式)
3. 转换为 MP3/WAV (使用 ffmpeg)
4. 语音转文字 (使用 mlx-whisper)

依赖:
- bilibili-api-python
- ffmpeg
- mlx-whisper
"""

import sys
import os
import asyncio
import subprocess
import tempfile
import json

# 依赖兜底：append 真实属主的用户级 site-packages（原写法字面量 '~' 从不展开，
# 且 Hermes profile 会改写 $HOME）。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site
ensure_user_site()

from bilibili_api import video, Credential


async def download_audio(bvid, sessdata=None, output_dir="/tmp"):
    """下载B站视频的音频流"""
    
    print(f"🎬 正在获取视频信息: {bvid}")
    
    credential = None
    if sessdata:
        credential = Credential(sessdata=sessdata)
    
    v = video.Video(bvid=bvid, credential=credential)
    
    # 获取视频信息
    info = await v.get_info()
    title = info['title']
    cid = info['cid']
    duration = info['duration']
    
    print(f"   标题: {title}")
    print(f"   时长: {duration}秒")
    print(f"   CID: {cid}")
    
    # 获取下载链接
    print("\n📥 正在获取音频下载链接...")
    download_info = await v.get_download_url(page_index=0)
    
    # 从 DASH 中提取音频 URL
    dash = download_info.get('dash', {})
    audio_list = dash.get('audio', [])
    
    if not audio_list:
        print("❌ 无法获取音频流")
        return None
    
    # 选择最高音质的音频
    audio = audio_list[0]
    audio_url = audio.get('baseUrl') or audio.get('base_url')
    
    if not audio_url:
        print("❌ 音频URL为空")
        return None
    
    print(f"   音频质量: {audio.get('id', 'unknown')}")
    
    # 下载音频
    audio_file = os.path.join(output_dir, f"{bvid}_audio.m4s")
    print(f"\n📥 正在下载音频...")
    
    # 使用 curl 下载
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://www.bilibili.com/video/{bvid}/",
    }
    
    header_args = [f"-H '{k}: {v}'" for k, v in headers.items()]
    cmd = f"curl -L {' '.join(header_args)} '{audio_url}' -o {audio_file} --silent --show-error"
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 下载失败: {result.stderr}")
        return None
    
    file_size = os.path.getsize(audio_file) / (1024 * 1024)
    print(f"   ✅ 下载完成: {file_size:.2f} MB")
    print(f"   文件: {audio_file}")
    
    return {
        "audio_file": audio_file,
        "title": title,
        "duration": duration,
        "bvid": bvid
    }


def convert_to_wav(m4s_file, output_file):
    """将 m4s 转换为 wav 格式 (mlx-whisper 支持)"""
    
    print(f"\n🔄 正在转换音频格式...")
    cmd = [
        "ffmpeg",
        "-i", m4s_file,
        "-ar", "16000",  # 16kHz 采样率
        "-ac", "1",      # 单声道
        "-c:a", "pcm_s16le",  # 16位PCM
        "-y",            # 覆盖输出文件
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 转换失败: {result.stderr[:200]}")
        return False
    
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"   ✅ 转换完成: {file_size:.2f} MB")
    print(f"   文件: {output_file}")
    
    return True


def transcribe_audio(wav_file, output_dir, language="zh"):
    """使用 mlx-whisper 进行语音转文字"""
    
    print(f"\n🎤 正在进行语音转文字...")
    print(f"   语言: {language}")
    print(f"   工具: mlx-whisper (本地推理)")
    print(f"   注意: 首次使用需要下载模型，请耐心等待...")
    
    # 基于真实属主家目录解析（字面量 '~' 不会展开，且 $HOME 在 Hermes 下不可信）。
    from bili_env import real_home
    whisper_path = os.path.join(real_home(), "Library/Python/3.9/bin/mlx_whisper")
    
    # 输出文件前缀
    output_prefix = os.path.basename(wav_file).replace("_audio.wav", "")
    
    # 使用默认模型（无需指定，mlx_whisper 会自动下载）
    cmd = [
        whisper_path,
        wav_file,
        "--language", language,
        "--output-format", "txt",
        "--output-dir", output_dir,
        "--output-name", output_prefix
    ]
    
    print(f"   开始转录（可能需要几分钟）...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5分钟超时
    
    if result.returncode != 0:
        print(f"❌ 转录失败: {result.stderr[:500]}")
        return None
    
    # 读取转录结果
    transcript_file = os.path.join(output_dir, f"{output_prefix}.txt")
    if os.path.exists(transcript_file):
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript = f.read()
        
        # 显示前500字
        preview = transcript[:500] if len(transcript) > 500 else transcript
        print(f"\n📝 转录预览 (前500字):")
        print("-" * 50)
        print(preview)
        if len(transcript) > 500:
            print("...")
        print("-" * 50)
        
        print(f"\n✅ 转录完成!")
        print(f"   总字数: {len(transcript)}")
        print(f"   文件: {transcript_file}")
        
        return transcript_file
    else:
        print(f"❌ 未找到转录文件")
        return None


def main():
    if len(sys.argv) < 2:
        print("用法: python3 audio_to_text.py <BV号或URL> [SESSDATA] [输出目录]")
        print("示例: python3 audio_to_text.py BV12Q6TBwE2J")
        print("      python3 audio_to_text.py BV12Q6TBwE2J 'your_sessdata' /tmp/output")
        sys.exit(1)
    
    input_str = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "/tmp"
    
    # 提取BV号
    import re
    bvid = input_str
    if "bilibili.com" in input_str:
        match = re.search(r'BV[0-9A-Za-z]+', input_str)
        if match:
            bvid = match.group(0)
    
    print(f"🎯 目标视频: {bvid}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 下载音频
    download_result = asyncio.run(download_audio(bvid, sessdata, output_dir))
    
    if not download_result:
        print("❌ 音频下载失败")
        sys.exit(1)
    
    m4s_file = download_result["audio_file"]
    
    # 2. 转换为 WAV
    wav_file = m4s_file.replace(".m4s", ".wav")
    if not convert_to_wav(m4s_file, wav_file):
        print("❌ 音频转换失败")
        sys.exit(1)
    
    # 3. 语音转文字
    transcript_file = transcribe_audio(wav_file, output_dir, language="zh")
    
    if transcript_file:
        print(f"\n🎉 全部完成!")
        print(f"   音频文件: {wav_file}")
        print(f"   转录文件: {transcript_file}")
        
        # 清理临时文件
        os.remove(m4s_file)
        print(f"   已清理: {m4s_file}")
        
        # 输出结果JSON
        result = {
            "bvid": bvid,
            "title": download_result["title"],
            "duration": download_result["duration"],
            "audio_file": wav_file,
            "transcript_file": transcript_file
        }
        
        print("\n" + "="*60)
        print("RESULT_JSON_START")
        print(json.dumps(result, ensure_ascii=False))
        print("RESULT_JSON_END")
        print("="*60)
        
    else:
        print("❌ 语音转文字失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
