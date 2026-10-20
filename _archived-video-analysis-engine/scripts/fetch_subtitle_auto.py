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
from bili_env import (
    ensure_user_site, build_ytdlp_audio_cmd, real_home,
    ensure_cookie_file, BROWSER_UA, BILI_REFERER,
)
ensure_user_site()

import json
import re
import requests
import subprocess
import tempfile
import shutil
import time
import warnings
import base64
import urllib.parse
from pathlib import Path
from hashlib import md5
from functools import wraps, reduce
from dataclasses import dataclass
from typing import Mapping, Optional

# ============ ASR provider/model/language 配置 ============
# 通过环境变量切换转录后端与模型，默认 auto 使用 H200 HTTP ASR 优先，
# 失败再降级到本机 whisper.cpp → mlx-whisper。
#   VIDEO_ANALYSIS_ASR_PROVIDER=auto|h200_asr|whisper_cpp|mlx_whisper
#   VIDEO_ANALYSIS_ASR_ENDPOINT=<ASR HTTP endpoint>    （默认本机兼容端点；远端必须显式配置）
#   VIDEO_ANALYSIS_ASR_MODEL=<模型名/repo id>          （主要给 mlx-whisper）
#   VIDEO_ANALYSIS_ASR_MODEL_PATH=<本地绝对路径/snapshot 目录>
#   VIDEO_ANALYSIS_ASR_LANGUAGE=zh|en|auto
#   BILI_ASR_* 仅为一个弃用周期内的兼容 alias。
ASR_PROVIDERS = ('auto', 'h200_asr', 'whisper_cpp', 'mlx_whisper')
ASR_LANGUAGES = ('zh', 'en', 'auto')
DEFAULT_H200_ASR_ENDPOINT = 'http://127.0.0.1:8088/ASR/transcribe'
DEFAULT_ASR_ENDPOINT_FILE = '~/.config/video-analysis-engine/asr_endpoint'
H200_CHUNK_THRESHOLD_SECONDS = 15 * 60
H200_CHUNK_SECONDS = 5 * 60


def resolve_subtitle_cache_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    """Resolve the persistent subtitle artifact directory."""
    if env is None:
        env = os.environ
    canonical = (env.get('VIDEO_ANALYSIS_CACHE_DIR') or '').strip()
    legacy = (env.get('BILI_ANALYSIS_CACHE_DIR') or '').strip()
    if canonical:
        raw = canonical
    elif legacy:
        warnings.warn(
            'BILI_ANALYSIS_CACHE_DIR is deprecated; use VIDEO_ANALYSIS_CACHE_DIR',
            DeprecationWarning,
            stacklevel=2,
        )
        raw = legacy
    else:
        raw = str(Path(__file__).resolve().parent.parent / '.p6r-cache')
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def subtitle_artifact_path(
    bvid: str,
    suffix: str,
    extension: str,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    """Build a sanitized persistent artifact path for one Bilibili video."""
    if not re.fullmatch(r'BV[0-9A-Za-z]+', bvid or ''):
        raise ValueError(f'invalid BVID: {bvid!r}')
    if not re.fullmatch(r'[0-9A-Za-z_-]+', suffix or ''):
        raise ValueError(f'invalid artifact suffix: {suffix!r}')
    if not re.fullmatch(r'[0-9A-Za-z]+', extension or ''):
        raise ValueError(f'invalid artifact extension: {extension!r}')
    return (resolve_subtitle_cache_dir(env) / f'{bvid}_{suffix}.{extension}').resolve()


@dataclass(frozen=True)
class AsrConfig:
    provider: str
    model: Optional[str]
    model_path: Optional[str]
    language: str
    endpoint: str = DEFAULT_H200_ASR_ENDPOINT


def default_whisper_cpp_model_path():
    """VoiceInk 自带的 whisper.cpp 模型默认路径。

    用 real_home() 而非 expanduser('~')——Hermes profile 会改写 $HOME，
    导致路径指向 profile home，VoiceInk 模型恒找不到，whisper.cpp 分支永不执行。
    """
    return os.path.join(
        real_home(),
        "Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo.bin",
    )


def _asr_env_value(
    env: Mapping[str, str],
    suffix: str,
    default: str = '',
) -> str:
    canonical_name = f'VIDEO_ANALYSIS_ASR_{suffix}'
    legacy_name = f'BILI_ASR_{suffix}'
    canonical = (env.get(canonical_name) or '').strip()
    if canonical:
        return canonical
    legacy = (env.get(legacy_name) or '').strip()
    if legacy:
        warnings.warn(
            f'{legacy_name} is deprecated; use {canonical_name}',
            DeprecationWarning,
            stacklevel=3,
        )
        return legacy
    return default


def _asr_endpoint_file(env: Mapping[str, str]) -> str:
    raw_path = (env.get('VIDEO_ANALYSIS_ASR_ENDPOINT_FILE') or DEFAULT_ASR_ENDPOINT_FILE).strip()
    try:
        endpoint = Path(raw_path).expanduser().read_text(encoding='utf-8').strip()
    except OSError:
        return ''
    return endpoint


def resolve_asr_config(env: Optional[Mapping[str, str]] = None) -> AsrConfig:
    """Resolve canonical ASR configuration with deprecated BILI aliases."""
    if env is None:
        env = os.environ
    provider = _asr_env_value(env, 'PROVIDER', 'auto').lower()
    if provider not in ASR_PROVIDERS:
        raise ValueError(
            f"VIDEO_ANALYSIS_ASR_PROVIDER 非法: {provider!r}，允许 {ASR_PROVIDERS}"
        )
    language = _asr_env_value(env, 'LANGUAGE', 'zh').lower()
    if language not in ASR_LANGUAGES:
        raise ValueError(
            f"VIDEO_ANALYSIS_ASR_LANGUAGE 非法: {language!r}，允许 {ASR_LANGUAGES}"
        )
    model = _asr_env_value(env, 'MODEL') or None
    model_path = _asr_env_value(env, 'MODEL_PATH') or None
    endpoint = _asr_env_value(env, 'ENDPOINT') or _asr_endpoint_file(env) or DEFAULT_H200_ASR_ENDPOINT
    return AsrConfig(
        provider=provider,
        model=model,
        model_path=model_path,
        language=language,
        endpoint=endpoint,
    )


def asr_model_label(config: AsrConfig, *, include_local_path: bool = False) -> str:
    """安全的模型标识。include_local_path=False（默认）时绝不暴露本地绝对路径，
    供最终对外报告/结果使用；trace/调试日志可传 True 看完整路径。"""
    if config.provider == 'h200_asr':
        base = 'SURGExZR-H200'
    elif config.model:
        base = config.model
    elif config.model_path:
        base = config.model_path if include_local_path else os.path.basename(config.model_path.rstrip('/'))
    else:
        base = 'default'
    return f"{config.provider}:{base}"


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

# ============ 通用 header & trace 日志 ============
HEADERS = {
    'User-Agent': BROWSER_UA,
    'Referer': BILI_REFERER,
}

# 字幕 fallback 链的逐步 trace，最终随 RESULT_JSON 输出，便于诊断每步失败原因
TRACE = []


def trace(step, status, reason=''):
    """记录某一步的结果。status: 'ok' | 'fail' | 'skip'。"""
    TRACE.append({'step': step, 'status': status, 'reason': reason})
    icon = {'ok': '✅', 'fail': '✗', 'skip': '·'}.get(status, '•')
    line = f"   {icon} [trace] {step}: {status}"
    if reason:
        line += f" — {reason}"
    print(line)


# ============ wbi 签名（Player API 直连所需）============
# Bilibili wbi 风控：请求需用 nav 接口下发的 img_key/sub_key 经固定置换表
# 生成 mixin_key，再对参数做 md5 签名（w_rid）。否则 x/player/wbi/v2 返回 -403/412。
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

# 进程内缓存 wbi key，避免每次都打 nav 接口
_WBI_KEYS = None


def _get_mixin_key(orig):
    """按置换表重排 img_key+sub_key，取前 32 位得到 mixin_key。"""
    return reduce(lambda s, i: s + orig[i], _MIXIN_KEY_ENC_TAB, '')[:32]


def get_wbi_keys():
    """从 nav 接口取 img_key / sub_key（带进程内缓存）。"""
    global _WBI_KEYS
    if _WBI_KEYS is not None:
        return _WBI_KEYS
    resp = requests.get(
        'https://api.bilibili.com/x/web-interface/nav',
        headers=HEADERS, timeout=CONFIG['api_timeout'],
    )
    wbi = resp.json()['data']['wbi_img']
    img_key = wbi['img_url'].rsplit('/', 1)[-1].split('.')[0]
    sub_key = wbi['sub_url'].rsplit('/', 1)[-1].split('.')[0]
    _WBI_KEYS = (img_key, sub_key)
    return _WBI_KEYS


def enc_wbi(params, img_key, sub_key):
    """对 params 做 wbi 签名，返回带 wts/w_rid 的新 dict。"""
    mixin_key = _get_mixin_key(img_key + sub_key)
    params = dict(params)
    params['wts'] = round(time.time())
    # 按 key 排序并过滤特殊字符（wbi 要求）
    params = dict(sorted(params.items()))
    params = {
        k: ''.join(c for c in str(v) if c not in "!'()*")
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    params['w_rid'] = md5((query + mixin_key).encode()).hexdigest()
    return params


def _build_dm_params():
    """Player API 用的 dm_img 风控参数（与 bilibili_dm_patch 同源思路）。"""
    return {
        'web_location': '1315873',
        'dm_img_list': '[]',
        'dm_img_str': base64.b64encode(os.urandom(32)).decode().rstrip('='),
        'dm_cover_img_str': base64.b64encode(os.urandom(32)).decode().rstrip('='),
        'dm_img_inter': '{"ds":[],"wh":[6093,6631,31],"of":[430,760,380]}',
    }


def _subtitle_priority(sub):
    """字幕优先级打分：人工中文 > AI 中文 > 任意。分越高越优先。"""
    lan = (sub.get('lan') or '').lower()
    is_ai = lan.startswith('ai-') or sub.get('ai_type', 0) or sub.get('ai_status', 0)
    is_zh = ('zh' in lan) or lan.startswith('ai-zh')
    if is_zh and not is_ai:
        return 3   # 人工中文
    if is_zh and is_ai:
        return 2   # AI 中文
    return 1       # 任意语言


@retry_on_timeout()
def try_player_api_subtitle(bvid, cid):
    """方案0: Player API 直连（wbi 签名 + dm_img），成功率最高、最快。

    走 x/player/wbi/v2，按 人工中文 > AI 中文 > 任意 选取，
    GET subtitle_url 拿到字幕 JSON body。失败返回 None（不抛）。
    """
    img_key, sub_key = get_wbi_keys()

    params = {'bvid': bvid, 'cid': cid}
    params.update(_build_dm_params())
    signed = enc_wbi(params, img_key, sub_key)

    resp = requests.get(
        'https://api.bilibili.com/x/player/wbi/v2',
        params=signed, headers=HEADERS, timeout=CONFIG['api_timeout'],
    )
    data = resp.json()
    if data.get('code') != 0:
        trace('player-api', 'fail', f"code={data.get('code')} {data.get('message','')}")
        return None

    subtitles = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
    if not subtitles:
        trace('player-api', 'fail', '无字幕列表（可能无人工/AI字幕）')
        return None

    # 按优先级降序挑选
    best = sorted(subtitles, key=_subtitle_priority, reverse=True)[0]
    sub_url = best.get('subtitle_url', '')
    if not sub_url:
        trace('player-api', 'fail', '首选字幕无 subtitle_url')
        return None
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url

    sub_resp = requests.get(sub_url, headers=HEADERS, timeout=CONFIG['api_timeout'])
    if sub_resp.status_code != 200:
        trace('player-api', 'fail', f'subtitle_url HTTP {sub_resp.status_code}')
        return None

    trace('player-api', 'ok', f"lan={best.get('lan')} 优先级={_subtitle_priority(best)}")
    return {
        'type': 'official',
        'language': best.get('lan', 'unknown'),
        'data': sub_resp.json(),
    }


@retry_on_timeout()
def try_ytdlp_subtitle(bvid):
    """方案2: 用 yt-dlp 抓字幕（带 cookie），解析为统一格式。失败返回 None。

    优先复用 Netscape cookie 文件；仅下载字幕不下载视频。
    Bilibili 字幕 yt-dlp 多导出为 json3 风格，解析其 body[from/content]。
    """
    tmpdir = tempfile.mkdtemp(prefix=f"bili_subs_{bvid}_")
    try:
        out_tpl = os.path.join(tmpdir, '%(id)s.%(ext)s')
        cmd = [
            'yt-dlp',
            '--user-agent', BROWSER_UA,
            '--referer', BILI_REFERER,
            '--skip-download',
            '--write-subs', '--write-auto-subs',
            '--sub-langs', 'zh.*,ai-zh,zh-Hans,zh-CN,zh-Hant',
            '--no-playlist',
            '-o', out_tpl,
            f'https://www.bilibili.com/video/{bvid}/',
        ]
        # cookie：优先 Netscape 文件，退回浏览器直读
        cookie_path = ensure_cookie_file()
        if cookie_path:
            cmd[1:1] = ['--cookies', cookie_path]
        else:
            cmd[1:1] = ['--cookies-from-browser', 'chrome']

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=CONFIG['api_timeout'] * 2,
        )

        # 收集生成的字幕文件
        sub_files = [
            os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
            if f.endswith(('.json', '.json3', '.srt', '.vtt'))
        ]
        if not sub_files:
            trace('yt-dlp-subs', 'fail', (result.stderr or 'no subtitle file')[-160:])
            return None

        # 优先 json（bilibili body 格式），否则取首个
        sub_files.sort(key=lambda p: (not p.endswith(('.json', '.json3')), p))
        target = sub_files[0]

        with open(target, 'r', encoding='utf-8') as f:
            raw = f.read()

        body = None
        if target.endswith(('.json', '.json3')):
            try:
                j = json.loads(raw)
                # bilibili 原生格式 {body:[{from,content}]}；json3 为 {events:[...]}
                if isinstance(j, dict) and j.get('body'):
                    body = j['body']
                elif isinstance(j, dict) and j.get('events'):
                    body = [
                        {'from': ev.get('tStartMs', 0) / 1000.0,
                         'content': ''.join(s.get('utf8', '') for s in ev.get('segs', []))}
                        for ev in j['events'] if ev.get('segs')
                    ]
            except json.JSONDecodeError:
                body = None

        if not body:
            trace('yt-dlp-subs', 'fail', f'无法解析字幕文件 {os.path.basename(target)}')
            return None

        trace('yt-dlp-subs', 'ok', f'{len(body)} 条 ← {os.path.basename(target)}')
        return {'type': 'ytdlp', 'language': 'zh', 'data': {'body': body}}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


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

def _select_audio_for_asr(audio_list):
    """为 ASR 选择 DASH audio 流。

    ASR 不需要高码率，优先最低 bandwidth，可显著降低长视频下载/转码成本。
    若没有 bandwidth 字段，保持原顺序取第一条，兼容旧接口。
    """
    if not audio_list:
        return None
    with_bandwidth = [a for a in audio_list if a.get('bandwidth')]
    if with_bandwidth:
        return min(with_bandwidth, key=lambda a: int(a.get('bandwidth') or 0))
    return audio_list[0]


def _download_audio_url_stream(audio_url, output_path, headers):
    """普通 stream 下载。成功 True，异常向上抛给 Range fallback。"""
    with requests.get(audio_url, headers=headers, stream=True,
                      timeout=CONFIG['download_timeout']) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def _content_range_total(value):
    """解析 Content-Range: bytes 0-1023/4096 → 4096。失败返回 None。"""
    if not value:
        return None
    m = re.search(r'/([0-9]+)$', value)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _download_audio_url_range(audio_url, output_path, headers, chunk_size=10 * 1024 * 1024):
    """HTTP Range 分块下载兜底。

    用于普通 stream 因 CDN/连接问题失败时，避免把 PlayURL 误判为不可用。
    """
    print("   🔁 普通下载失败，尝试 HTTP Range 分块下载...")
    start = 0
    total = None
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        while True:
            end = start + chunk_size - 1
            range_headers = dict(headers)
            range_headers['Range'] = f'bytes={start}-{end}'
            with requests.get(audio_url, headers=range_headers, stream=True,
                              timeout=CONFIG['download_timeout']) as r:
                r.raise_for_status()
                payload_size = 0
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        payload_size += len(chunk)
                total = total or _content_range_total(r.headers.get('Content-Range'))

            if payload_size <= 0:
                break
            start += payload_size
            if total is not None and start >= total:
                break
            # 服务器未返回 total 且本次不足一个 range，说明已经到尾部。
            if total is None and payload_size < chunk_size:
                break

    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def _download_audio_url(audio_url, output_path, headers):
    """下载 PlayURL 音频：stream 优先，失败后 Range 兜底。"""
    try:
        return _download_audio_url_stream(audio_url, output_path, headers)
    except Exception as e:
        print(f"   ⚠️  普通 stream 下载失败: {type(e).__name__}: {e}")
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            return _download_audio_url_range(audio_url, output_path, headers)
        except Exception as e2:
            print(f"   ⚠️  Range 下载也失败: {type(e2).__name__}: {e2}")
            return False


@retry_on_timeout()
def download_audio(bvid, output_path, cid=None):
    """下载视频音频。

    优先走 B站公开 PlayURL API 直拉 DASH audio，绕开 yt-dlp 412；
    为 ASR 选择低码率音频；普通 stream 下载失败时自动 Range 兜底。
    失败时才回退 yt-dlp。

    cid 可选：多 P 视频必须传入对应 page 的 cid，否则默认第一 P。
    """
    headers = {
        'User-Agent': BROWSER_UA,
        'Referer': f'https://www.bilibili.com/video/{bvid}/',
    }

    # 方案A：公开 playurl 接口 → DASH audio URL → requests stream / Range 直下 m4s
    try:
        if cid is None:
            info = get_video_info(bvid)
            cid = info.get('cid') if info else None
            if cid is None and info and info.get('pages'):
                cid = info['pages'][0].get('cid')

        if cid:
            print("   🎯 使用 PlayURL API 直拉音频（绕开 yt-dlp 412）...")
            resp = requests.get(
                'https://api.bilibili.com/x/player/playurl',
                params={'bvid': bvid, 'cid': cid, 'fnval': 16, 'fnver': 0, 'fourk': 1},
                headers=headers,
                timeout=CONFIG['api_timeout'],
            )
            data = resp.json()
            audio_list = data.get('data', {}).get('dash', {}).get('audio', [])
            if audio_list:
                audio = _select_audio_for_asr(audio_list)
                audio_url = audio.get('baseUrl') or audio.get('base_url') if audio else None
                if audio_url:
                    bw = audio.get('bandwidth') if audio else None
                    suffix = f", bandwidth={bw}" if bw else ""
                    print(f"   ⏱️  下载超时设置: {CONFIG['download_timeout']}秒{suffix}")
                    if _download_audio_url(audio_url, output_path, headers):
                        file_size = os.path.getsize(output_path) / (1024 * 1024)
                        print(f"   ✅ 音频下载成功: {file_size:.1f} MB (PlayURL API)")
                        return True
            print("   ⚠️  PlayURL API 未返回可用音频流，回退 yt-dlp")
        else:
            print("   ⚠️  无法获取 CID，回退 yt-dlp")
    except Exception as e:
        print(f"   ⚠️  PlayURL API 音频下载失败，回退 yt-dlp: {type(e).__name__}: {e}")

    # 方案B：旧 yt-dlp 回退（保留向后兼容）
    try:
        cmd = build_ytdlp_audio_cmd(bvid, output_path)
        print(f"   ⏱️  yt-dlp 下载超时设置: {CONFIG['download_timeout']}秒")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CONFIG['download_timeout']
        )

        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"   ✅ 音频下载成功: {file_size:.1f} MB (yt-dlp)")
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

def _asr_language_for_h200(language):
    """H200 ASR 的 language 参数较宽松；这里只做友好映射，不依赖其强约束。"""
    return {
        'zh': 'Chinese',
        'en': 'English',
        'auto': 'auto',
    }.get(language, language)


def _transcribe_h200(audio_path, output_txt_path, config):
    """SURGExZR H200 HTTP ASR。成功返回 'h200-asr'，否则 False。"""
    print(f"   🚀 尝试 H200 ASR ({config.endpoint})...")
    try:
        with open(audio_path, 'rb') as f:
            response = requests.post(
                config.endpoint,
                files={'file': (os.path.basename(audio_path), f, 'application/octet-stream')},
                data={'language': _asr_language_for_h200(config.language)},
                timeout=CONFIG['transcribe_timeout'],
            )
        if response.status_code != 200:
            print(f"   ❌ H200 ASR HTTP {response.status_code}: {response.text[:300]}")
            return False

        try:
            data = response.json()
        except ValueError:
            print(f"   ❌ H200 ASR 返回非 JSON: {response.text[:300]}")
            return False

        text = (data.get('text') or data.get('result') or data.get('transcription') or '').strip()
        if not text:
            print(f"   ❌ H200 ASR 返回空文本: keys={list(data.keys())}")
            return False

        os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)) or '.', exist_ok=True)
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"   ✅ H200 ASR 转录文件已保存: {output_txt_path} ({len(text)} 字符)")
        return 'h200-asr'

    except requests.Timeout:
        print(f"   ⏱️  H200 ASR 超时（超过{CONFIG['transcribe_timeout']}秒）")
    except Exception as e:
        print(f"   ❌ H200 ASR 失败: {e}")

    return False


def _transcribe_h200_chunked(audio_path, output_txt_path, config, chunk_seconds=H200_CHUNK_SECONDS):
    """长音频 H200 分块转写。成功返回 'h200-asr-chunked'，否则 False。

    这条路径来自 BV1sxT56TE39 实测：105 分钟音频整段风险高，ffmpeg 切 5 分钟
    wav chunk 后逐段 POST H200，22/22 成功。
    """
    print(f"   🚀 长音频启用 H200 分块 ASR（chunk={chunk_seconds}s）...")
    tmpdir = tempfile.mkdtemp(prefix="h200_chunks_")
    try:
        pattern = os.path.join(tmpdir, "chunk_%03d.wav")
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-i', audio_path,
            '-ar', '16000', '-ac', '1',
            '-f', 'segment', '-segment_time', str(chunk_seconds),
            '-reset_timestamps', '1',
            pattern,
        ]
        subprocess.run(cmd, timeout=CONFIG['transcribe_timeout'], check=True)
        chunks = sorted(
            os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
            if f.startswith('chunk_') and f.endswith('.wav')
        )
        if not chunks:
            print("   ❌ H200 分块失败：ffmpeg 未生成 chunk")
            return False

        merged = []
        for idx, chunk_path in enumerate(chunks, 1):
            print(f"   🎙️  H200 chunk {idx}/{len(chunks)}: {os.path.basename(chunk_path)}")
            with open(chunk_path, 'rb') as f:
                response = requests.post(
                    config.endpoint,
                    files={'file': (os.path.basename(chunk_path), f, 'audio/wav')},
                    data={'language': _asr_language_for_h200(config.language)},
                    timeout=CONFIG['transcribe_timeout'],
                )
            if response.status_code != 200:
                print(f"   ❌ H200 chunk HTTP {response.status_code}: {response.text[:300]}")
                return False
            try:
                data = response.json()
            except ValueError:
                print(f"   ❌ H200 chunk 返回非 JSON: {response.text[:300]}")
                return False
            text = (data.get('text') or data.get('result') or data.get('transcription') or '').strip()
            if not text:
                print(f"   ❌ H200 chunk 返回空文本: keys={list(data.keys())}")
                return False
            start_sec = (idx - 1) * chunk_seconds
            mm, ss = divmod(start_sec, 60)
            merged.append(f"## Chunk {idx} [{mm:02d}:{ss:02d}]\n\n{text}")

        os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)) or '.', exist_ok=True)
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(merged).strip() + '\n')
        print(f"   ✅ H200 分块转录文件已保存: {output_txt_path} ({len(chunks)} chunks)")
        return 'h200-asr-chunked'

    except subprocess.TimeoutExpired:
        print(f"   ⏱️  H200 分块 ffmpeg 超时（超过{CONFIG['transcribe_timeout']}秒）")
    except Exception as e:
        print(f"   ❌ H200 分块 ASR 失败: {e}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return False


def _transcribe_whisper_cpp(audio_path, output_txt_path, config):
    """whisper.cpp (VoiceInk 本地模型) 转录。成功返回 'whisper.cpp'，否则 False。"""
    # 模型路径：BILI_ASR_MODEL_PATH 覆盖默认 VoiceInk 路径
    whisper_model = config.model_path or default_whisper_cpp_model_path()

    if not os.path.exists(whisper_model):
        print(f"   ⚠️  未找到 whisper 模型: {whisper_model}")
        return False

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
            '-l', config.language,
            '-otxt',
            '-of', os.path.join(tmp_output_dir, base_name)
        ]

        print(f"   📝 开始转录（超时: {CONFIG['transcribe_timeout']}秒，模型={asr_model_label(config)}）...")

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

    return False


def _transcribe_mlx(audio_path, output_txt_path, config):
    """mlx-whisper（Python API helper）转录。成功返回 'mlx-whisper'，否则 False。"""
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
            '--language', config.language,
        ]
        # 把 model/model_path 透传给 helper（仅在配置时附加，不硬编码单一 repo）
        if config.model:
            cmd += ['--model', config.model]
        if config.model_path:
            cmd += ['--model-path', config.model_path]

        print(f"   📝 开始转录（超时: {CONFIG['transcribe_timeout']}秒，模型={asr_model_label(config)}）...")
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


def transcribe_audio(audio_path, output_txt_path, config=None):
    """音频转录 - provider 可配置版。

    provider=auto       : H200 HTTP ASR 优先，失败再 whisper.cpp → mlx-whisper。
    provider=h200_asr   : 只走 SURGExZR H200 HTTP ASR，绝不调用本机 whisper/mlx。
    provider=whisper_cpp: 只走 whisper.cpp，绝不调用 mlx helper。
    provider=mlx_whisper: 只走 mlx-whisper，绝不调用 whisper.cpp。
    config 缺省时从环境变量解析（resolve_asr_config）。成功返回引擎名，否则 False。
    """
    if config is None:
        config = resolve_asr_config()

    # 检查音频时长
    duration = check_video_duration(audio_path)
    if duration:
        minutes = int(duration / 60)
        print(f"   🕐 音频时长: {minutes}分钟")

        # 预估转录时间（约 1分钟音频 = 6-8秒转录时间）
        est_time = max(120, int(minutes * 8))
        print(f"   ⏱️  预估转录时间: {est_time//60}分{est_time%60}秒")

    # H200 HTTP ASR 阶段（auto / h200_asr）
    if config.provider in ('auto', 'h200_asr'):
        if duration and duration >= H200_CHUNK_THRESHOLD_SECONDS:
            engine = _transcribe_h200_chunked(audio_path, output_txt_path, config)
        else:
            engine = _transcribe_h200(audio_path, output_txt_path, config)
        if engine:
            return engine
        if config.provider == 'h200_asr':
            # 显式指定 h200_asr 时不降级到本机 ASR
            return False

    # whisper.cpp 阶段（auto / whisper_cpp）
    if config.provider in ('auto', 'whisper_cpp'):
        engine = _transcribe_whisper_cpp(audio_path, output_txt_path, config)
        if engine:
            return engine
        if config.provider == 'whisper_cpp':
            # 显式指定 whisper_cpp 时不降级到 mlx
            return False

    # mlx-whisper 阶段（auto / mlx_whisper）
    if config.provider in ('auto', 'mlx_whisper'):
        engine = _transcribe_mlx(audio_path, output_txt_path, config)
        if engine:
            return engine

    return False

def transcribe_pages_merge(bvid, title, pages, tmpdir, output_txt_path=None):
    """逐 P 下载音频 → 转录 → 合并为单文件，保留 ## P{n} 标题。

    多 P 视频必须逐 P 下载/转录再合并；否则只会拿到 P1（曾踩坑：双语+纯享各一 P）。
    每个 page 用其自身 cid 调 download_audio(bvid, path, cid=page['cid'])，
    绝不退回 P1 的 cid。返回 result dict；全部失败返回 None（绝不塌缩成异常）。
    """
    if output_txt_path is None:
        output_txt_path = str(subtitle_artifact_path(bvid, 'subtitle_whisper', 'txt'))

    merged_parts = []
    engine = None
    failed_parts = []

    for page in pages:
        page_no = page.get('page') or (len(merged_parts) + 1)
        page_cid = page.get('cid')
        part_title = page.get('part') or f'P{page_no}'
        if not page_cid:
            failed_parts.append(f'P{page_no}: no cid')
            continue

        safe_part = re.sub(r'[^0-9A-Za-z_-]+', '_', str(page_no))
        audio_path = os.path.join(tmpdir, f"{bvid}_p{safe_part}.m4a")
        part_txt_path = os.path.join(tmpdir, f"{bvid}_p{safe_part}.txt")

        print(f"\n   ⬇️  [P{page_no}] 下载音频：{part_title}")
        if not download_audio(bvid, audio_path, cid=page_cid):
            print(f"   ❌ [P{page_no}] 音频下载失败")
            failed_parts.append(f'P{page_no}: download failed')
            continue

        print(f"   🎯 [P{page_no}] 开始转录...")
        part_engine = transcribe_audio(audio_path, part_txt_path)
        if not part_engine or not os.path.exists(part_txt_path):
            print(f"   ❌ [P{page_no}] 转录失败")
            failed_parts.append(f'P{page_no}: transcribe failed')
            continue

        engine = engine or part_engine
        with open(part_txt_path, 'r', encoding='utf-8') as f:
            part_text = f.read().strip()
        merged_parts.append((page_no, part_title, part_text))
        print(f"   ✅ [P{page_no}] 转录完成 ({len(part_text)} 字符, 引擎={part_engine})")

    if merged_parts:
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            for page_no, part_title, part_text in merged_parts:
                f.write(f"\n\n## P{page_no} {part_title}\n\n")
                f.write(part_text)
                f.write("\n")

        size = os.path.getsize(output_txt_path)
        print(f"   💾 合并TXT: {output_txt_path} ({size} bytes, {len(merged_parts)}/{len(pages)} P)")
        reason = f'引擎={engine}; parts={len(merged_parts)}/{len(pages)}'
        if failed_parts:
            reason += '; failed=' + ', '.join(failed_parts[:3])
        trace('whisper', 'ok', reason)
        return {
            'bvid': bvid,
            'title': title,
            'method': engine or 'whisper',
            'txt_path': output_txt_path,
            'parts': len(merged_parts),
            'total_parts': len(pages),
            'failed_parts': failed_parts,
        }

    print("   ❌ 所有分P转录均失败")
    trace('whisper', 'fail', '所有分P转录均失败')
    return None


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
    
    # 字幕 fallback 链：Player API 直连(wbi+dm_img) → 官方 wbi(原逻辑) → yt-dlp cookie → whisper
    subtitle = None

    # 方案0: Player API 直连（wbi 签名 + dm_img，成功率最高）
    print("\n📖 方案0: Player API 直连（wbi 签名 + dm_img）...")
    try:
        subtitle = try_player_api_subtitle(bvid, cid)
    except Exception as e:
        trace('player-api', 'fail', f'{type(e).__name__}: {e}')
        subtitle = None

    # 方案1: 原 try_official_subtitle（保留为 fallback，逻辑不动）
    if not subtitle:
        print("\n📖 方案1: 官方字幕接口（兼容回退）...")
        try:
            subtitle = try_official_subtitle(bvid, cid)
            trace('official-legacy', 'ok' if subtitle else 'fail',
                  '' if subtitle else '无字幕')
        except Exception as e:
            trace('official-legacy', 'fail', f'{type(e).__name__}: {e}')
            subtitle = None

    # 方案2: yt-dlp 带 cookie 抓字幕
    if not subtitle:
        print("\n📖 方案2: yt-dlp 抓字幕（带 cookie）...")
        try:
            subtitle = try_ytdlp_subtitle(bvid)
        except Exception as e:
            trace('yt-dlp-subs', 'fail', f'{type(e).__name__}: {e}')
            subtitle = None

    if subtitle:
        method = subtitle.get('type', 'official')
        print(f"   ✅ 成功获取字幕 (来源={method}, 语言={subtitle['language']})")

        # 保存
        json_path = str(subtitle_artifact_path(bvid, 'subtitle_official', 'json'))
        txt_path = str(subtitle_artifact_path(bvid, 'subtitle_official', 'txt'))
        
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
            'method': method,
            'json_path': json_path,
            'txt_path': txt_path,
            'count': len(subtitle['data'].get('body', []))
        }

    else:
        print("   ⚠️  Player API / 官方接口 / yt-dlp 均无字幕，降级音频转录")

        # 方案3: 音频转录（最后手段）
        print("\n🎙️ 方案3: 音频转录 (whisper)...")
        
        # 使用普通目录而非临时目录，确保文件在转录后仍然存在。
        # 多 P 视频必须逐 P 下载/转录再合并；否则只会拿到 P1（曾踩坑：双语+纯享各一 P）。
        tmpdir = tempfile.mkdtemp(prefix=f"bilibili_{bvid}_")
        try:
            pages = info.get('pages') or [{'page': 1, 'cid': cid, 'part': title, 'duration': duration}]
            if len(pages) > 1:
                print(f"   ℹ️  检测到多P视频：{len(pages)} P，将逐P转录并合并")

            result = transcribe_pages_merge(bvid, title, pages, tmpdir)
        finally:
            # 清理临时目录
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    # 输出结果（附带 fallback 链 trace，便于诊断每步失败原因）
    print("\n" + "="*60)
    if result:
        result['trace'] = TRACE
        print("✅ 字幕获取完成!")
        print(f"   方法: {result['method']}")
        print(f"   视频: {result['title']}")
        print("\nRESULT_JSON_START")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")
    else:
        print("❌ 所有方案均失败")
        print("\nRESULT_JSON_START")
        print(json.dumps({'bvid': bvid, 'method': None, 'trace': TRACE},
                         ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")
        sys.exit(1)

if __name__ == "__main__":
    main()
