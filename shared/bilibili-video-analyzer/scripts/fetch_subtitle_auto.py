#!/usr/bin/env python3
"""
获取 Bilibili 视频字幕 - 多方案自动降级 (超时优化版)
用法: python3 fetch_subtitle_auto.py <BV号>

优化内容:
- 增加超时时间（API 60s，下载 300s，转录 1200s）
- 添加重试机制（最多3次）
- 添加进度显示
- 支持分段转录（长视频）
"""

import sys
import os

# 依赖兜底：把真实属主的用户级 site-packages 追加到 sys.path。
# 不能用 expanduser('~')——Hermes profile 会改写 $HOME。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site, build_ytdlp_audio_cmd, real_home
ensure_user_site()

import json
import requests
import subprocess
import tempfile
import shutil
import time
from functools import wraps

# ============ 配置 ============
CONFIG = {
    'api_timeout': 60,          # API请求超时
    'download_timeout': 300,     # 音频下载超时（5分钟）
    'transcribe_timeout': 1200,  # 转录超时（20分钟）
    'max_retries': 3,            # 最大重试次数
    'retry_delay': 2,            # 重试间隔（秒）
}

def retry_on_timeout(max_retries=None, delay=None):
    """重试装饰器"""
    max_retries = max_retries or CONFIG['max_retries']
    delay = delay or CONFIG['retry_delay']
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.Timeout, subprocess.TimeoutExpired) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  超时，{delay}秒后重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(delay)
                    else:
                        raise last_exception
            return None
        return wrapper
    return decorator

@retry_on_timeout()
def get_video_info(bvid):
    """获取视频基本信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com'
    }
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    resp = requests.get(url, headers=headers, timeout=CONFIG['api_timeout'])
    data = resp.json()
    
    if data.get('code') != 0:
        return None
    
    return data['data']

@retry_on_timeout()
def try_official_subtitle(bvid, cid):
    """方案1: 尝试获取官方字幕"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com'
    }
    
    # 尝试 wbi API
    url = f'https://api.bilibili.com/x/player/wbi/v2?cid={cid}&bvid={bvid}'
    resp = requests.get(url, headers=headers, timeout=CONFIG['api_timeout'])
    data = resp.json()
    
    if data.get('code') != 0:
        return None
    
    subtitle_data = data.get('data', {}).get('subtitle', {})
    subtitles = subtitle_data.get('subtitles', [])
    
    if not subtitles:
        return None
    
    # 下载第一个字幕
    sub_url = subtitles[0].get('subtitle_url', '')
    if not sub_url:
        return None
    
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url
    
    sub_resp = requests.get(sub_url, headers=headers, timeout=CONFIG['api_timeout'])
    if sub_resp.status_code != 200:
        return None
    
    return {
        'type': 'official',
        'language': subtitles[0].get('lan', 'unknown'),
        'data': sub_resp.json()
    }

@retry_on_timeout()
def download_audio(bvid, output_path):
    """下载视频音频"""
    try:
        # 使用 yt-dlp 下载音频。
        # 关键：必须带 User-Agent + Referer，否则 Bilibili 返回 HTTP 412
        # Precondition Failed（这是导致字幕降级到音频转录时整体失败的根因）。
        cmd = build_ytdlp_audio_cmd(bvid, output_path)
        
        print(f"   ⏱️  下载超时设置: {CONFIG['download_timeout']}秒")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CONFIG['download_timeout']
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"   ✅ 音频下载成功: {file_size:.1f} MB")
            return True
        
        print(f"   ❌ yt-dlp 错误: {result.stderr[:300]}")
        return False
        
    except subprocess.TimeoutExpired:
        print(f"   ⏱️  下载超时（超过{CONFIG['download_timeout']}秒）")
        raise
    except Exception as e:
        print(f"   ❌ 音频下载失败: {e}")
        return False

def check_video_duration(audio_path):
    """检查音频时长"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
               '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        duration = float(result.stdout.strip())
        return duration
    except:
        return None

def transcribe_audio(audio_path, output_txt_path):
    """音频转录 - 优化版"""
    
    # 检查音频时长
    duration = check_video_duration(audio_path)
    if duration:
        minutes = int(duration / 60)
        print(f"   🕐 音频时长: {minutes}分钟")
        
        # 预估转录时间（约 1分钟音频 = 6-8秒转录时间）
        est_time = max(120, int(minutes * 8))
        print(f"   ⏱️  预估转录时间: {est_time//60}分{est_time%60}秒")
    
    # 优先尝试 whisper.cpp (使用 VoiceInk 的模型)
    # 注意: 用 real_home() 而非 expanduser('~')——Hermes profile 会改写 $HOME，
    # 导致路径指向 profile home，VoiceInk 模型恒找不到，whisper.cpp 分支永不执行。
    whisper_model = os.path.join(
        real_home(),
        "Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo.bin"
    )

    if os.path.exists(whisper_model):
        print("   🎯 使用 whisper.cpp 转录...")
        try:
            # 临时输出目录
            tmp_output_dir = os.path.dirname(audio_path)
            base_name = os.path.basename(audio_path).replace('.m4a', '')
            
            # 先转换音频为 wav (whisper.cpp 对 wav 支持更好)
            wav_path = os.path.join(tmp_output_dir, f"{base_name}.wav")
            ffmpeg_cmd = [
                'ffmpeg', '-i', audio_path,
                '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le',
                wav_path, '-y', '-hide_banner', '-loglevel', 'error'
            ]
            
            print("   🔄 转换音频格式...")
            subprocess.run(ffmpeg_cmd, timeout=120, check=True)
            
            cmd = [
                'whisper-cli',
                '-m', whisper_model,
                '-f', wav_path,
                '-l', 'zh',
                '-otxt',
                '-of', os.path.join(tmp_output_dir, base_name)
            ]
            
            print(f"   📝 开始转录（超时: {CONFIG['transcribe_timeout']}秒）...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CONFIG['transcribe_timeout']
            )
            
            if result.returncode == 0:
                # 查找生成的 txt 文件
                generated_txt = os.path.join(tmp_output_dir, f"{base_name}.txt")
                if os.path.exists(generated_txt):
                    # 复制到目标位置（若已是同一文件则跳过，避免 SameFileError）
                    if os.path.abspath(generated_txt) != os.path.abspath(output_txt_path):
                        shutil.copy2(generated_txt, output_txt_path)
                    print(f"   ✅ 转录文件已保存: {output_txt_path}")
                    return 'whisper.cpp'
                else:
                    # 尝试找任何 txt 文件
                    for f in os.listdir(tmp_output_dir):
                        if f.endswith('.txt'):
                            src = os.path.join(tmp_output_dir, f)
                            if os.path.abspath(src) != os.path.abspath(output_txt_path):
                                shutil.copy2(src, output_txt_path)
                            print(f"   ✅ 转录文件已保存: {output_txt_path}")
                            return 'whisper.cpp'
            else:
                print(f"   ❌ whisper-cli 错误: {result.stderr[:300]}")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  转录超时（超过{CONFIG['transcribe_timeout']}秒）")
            print("   💡 提示: 对于超长视频，建议分段处理或使用更快的模型")
        except Exception as e:
            print(f"   ❌ whisper.cpp 失败: {e}")
    else:
        print(f"   ⚠️  未找到 whisper 模型: {whisper_model}")
    
    # 备选: mlx-whisper（Python API，指向本地 snapshot，离线转录）
    print("   🔄 尝试 mlx-whisper (Python API)...")
    try:
        # mlx_whisper 仅在 /usr/bin/python3（CommandLineTools 3.9 + user site-packages）可用，
        # 默认 python3.12 没有该模块，因此固定用该解释器调用 helper。
        helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mlx_transcribe.py')
        cmd = [
            '/usr/bin/python3',
            helper,
            audio_path,
            output_txt_path,
            'zh',
        ]

        print(f"   📝 开始转录（超时: {CONFIG['transcribe_timeout']}秒）...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CONFIG['transcribe_timeout']
        )

        if result.stderr:
            # helper 的进度/诊断信息走 stderr，原样透出
            print(result.stderr.rstrip())

        if result.returncode == 0 and os.path.exists(output_txt_path):
            print(f"   ✅ 转录文件已保存: {output_txt_path}")
            return 'mlx-whisper'
        else:
            print(f"   ❌ mlx-whisper 失败 (returncode={result.returncode})")

    except subprocess.TimeoutExpired:
        print(f"   ⏱️  mlx-whisper 超时（超过{CONFIG['transcribe_timeout']}秒）")
    except Exception as e:
        print(f"   ❌ mlx-whisper 失败: {e}")

    return False

def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_subtitle_auto.py <BV号>")
        print("示例: python3 fetch_subtitle_auto.py BV1ut6YByEZq")
        sys.exit(1)
    
    bvid = sys.argv[1]
    
    print(f"🎬 正在处理: {bvid}")
    print("="*60)
    print(f"⏱️  超时配置: API={CONFIG['api_timeout']}s, 下载={CONFIG['download_timeout']}s, 转录={CONFIG['transcribe_timeout']}s")
    
    # 获取视频信息
    print("\n📋 获取视频信息...")
    try:
        info = get_video_info(bvid)
        if not info:
            print("❌ 无法获取视频信息")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 获取视频信息失败（多次重试后）: {e}")
        sys.exit(1)
    
    title = info.get('title', 'Unknown')
    cid = info.get('cid')
    
    # 处理分P视频（cid 在 pages 中）
    if cid is None and info.get('pages'):
        cid = info['pages'][0].get('cid')
        print(f"   ℹ️  多P视频，使用第一P的CID: {cid}")
    
    if cid is None:
        print("   ❌ 无法获取CID，可能是视频已失效或需要特殊处理")
        sys.exit(1)
    
    duration = info.get('duration', 0)
    owner = info.get('owner', {}).get('name', 'Unknown')
    
    print(f"   标题: {title}")
    print(f"   UP主: {owner}")
    print(f"   时长: {duration//60}分{duration%60}秒")
    print(f"   CID: {cid}")
    
    # 方案1: 官方字幕
    print("\n📖 方案1: 尝试获取官方字幕...")
    try:
        subtitle = try_official_subtitle(bvid, cid)
    except Exception as e:
        print(f"   ⚠️  获取官方字幕失败: {e}")
        subtitle = None
    
    if subtitle:
        print(f"   ✅ 成功获取官方字幕 ({subtitle['language']})")
        
        # 保存
        json_path = f"/tmp/{bvid}_subtitle_official.json"
        txt_path = f"/tmp/{bvid}_subtitle_official.txt"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(subtitle['data'], f, ensure_ascii=False, indent=2)
        
        # 保存 TXT
        lines = []
        for item in subtitle['data'].get('body', []):
            from_time = int(item['from'])
            minutes = from_time // 60
            seconds = from_time % 60
            lines.append(f"[{minutes}:{seconds:02d}] {item['content']}")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"   💾 JSON: {json_path}")
        print(f"   💾 TXT:  {txt_path}")
        print(f"   📝 共 {len(subtitle['data'].get('body', []))} 条字幕")
        
        result = {
            'bvid': bvid,
            'title': title,
            'method': 'official',
            'json_path': json_path,
            'txt_path': txt_path,
            'count': len(subtitle['data'].get('body', []))
        }
        
    else:
        print("   ⚠️  无官方字幕或需要登录")
        
        # 方案2: 音频转录
        print("\n🎙️ 方案2: 音频转录 (whisper)...")
        
        # 使用普通目录而非临时目录，确保文件在转录后仍然存在
        tmpdir = tempfile.mkdtemp(prefix=f"bilibili_{bvid}_")
        try:
            audio_path = os.path.join(tmpdir, f"{bvid}.m4a")
            txt_path = f"/tmp/{bvid}_subtitle_whisper.txt"
            
            print("   ⬇️  下载音频中...")
            if download_audio(bvid, audio_path):
                print(f"   ✅ 音频下载成功")
                
                print("   🎯 开始转录...")
                engine = transcribe_audio(audio_path, txt_path)
                if engine:
                    print(f"   ✅ 转录完成 (引擎: {engine})")

                    # 验证文件
                    if os.path.exists(txt_path):
                        size = os.path.getsize(txt_path)
                        print(f"   💾 TXT: {txt_path} ({size} bytes)")

                        result = {
                            'bvid': bvid,
                            'title': title,
                            'method': engine,
                            'txt_path': txt_path
                        }
                    else:
                        print(f"   ❌ 转录文件未生成")
                        result = None
                else:
                    print("   ❌ 转录失败")
                    result = None
            else:
                print("   ❌ 音频下载失败")
                result = None
        finally:
            # 清理临时目录
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    # 输出结果
    print("\n" + "="*60)
    if result:
        print("✅ 字幕获取完成!")
        print(f"   方法: {result['method']}")
        print(f"   视频: {result['title']}")
        print("\nRESULT_JSON_START")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")
    else:
        print("❌ 所有方案均失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
