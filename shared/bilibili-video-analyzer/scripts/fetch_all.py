#!/usr/bin/env python3
"""
Bilibili 视频全自动化获取 - 集成脚本
用法: python3 fetch_all.py <BV号> [SESSDATA]

自动获取:
1. 视频信息
2. 弹幕 (1048条)
3. 评论 (504条)
4. 字幕 (官方/AI/转录)
"""

import sys
import os

# 依赖兜底：把真实属主的用户级 site-packages 追加到 sys.path。
# 不能用 expanduser('~')——Hermes profile 会改写 $HOME，导致路径指向 profile home
# 而非真实家目录，requests 等依赖找不到。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site
ensure_user_site()

import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 子脚本需要可用的 requests + 可用的 xml/pyexpat。
# 本机 homebrew python3.12 的 pyexpat 是坏的（Symbol not found），无法解析弹幕 XML；
# /usr/bin/python3（CommandLineTools 3.9 + ~/Library/Python/3.9 user site）则齐全可用。
PYTHON = '/usr/bin/python3' if os.path.exists('/usr/bin/python3') else sys.executable


def run_script(script_name, *args):
    """运行子脚本并返回 (returncode, stdout, stderr)。"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [PYTHON, script_path] + list(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or '', f'TIMEOUT after 600s: {e}'


def parse_result_json(output):
    """从输出中解析 RESULT_JSON"""
    if 'RESULT_JSON_START' in output and 'RESULT_JSON_END' in output:
        start = output.find('RESULT_JSON_START') + len('RESULT_JSON_START')
        end = output.find('RESULT_JSON_END')
        json_str = output[start:end].strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None


def process_step(label, script_name, *args):
    """运行一个子步骤，返回统一的状态字典。

    关键: 失败绝不塌缩为 None —— 区分三种结果，让下游能分辨
    "失败" / "成功但无结构化结果" / "成功且有数据"。
      - 失败:           {'status': 'failed', 'returncode': N, 'error': <stderr 尾部>}
      - 成功但无 JSON:  {'status': 'ok', 'parsed': False}
      - 成功且有数据:   <原始解析结果> + {'status': 'ok', 'parsed': True}
    """
    returncode, stdout, stderr = run_script(script_name, *args)

    if returncode != 0:
        # 合并 stdout+stderr 再滤掉已知噪音（urllib3/LibreSSL 警告），避免真正的报错被警告盖住
        merged = (stdout or '') + '\n' + (stderr or '')
        noise = ('NotOpenSSLWarning', 'urllib3 v2 only supports', 'warnings.warn')
        meaningful = [ln for ln in merged.splitlines() if ln.strip() and not any(n in ln for n in noise)]
        err_tail = '\n'.join(meaningful)[-800:]
        print(f"   ❌ {label}获取失败 (returncode={returncode})")
        if meaningful:
            print(f"      ↳ {meaningful[-1]}")
        return {'status': 'failed', 'returncode': returncode, 'error': err_tail}

    parsed = parse_result_json(stdout)
    if parsed is not None:
        parsed['status'] = 'ok'
        parsed['parsed'] = True
        return parsed

    print(f"   ⚠️  {label}: 返回成功但未解析到 RESULT_JSON")
    return {'status': 'ok', 'parsed': False}


def is_failed(step):
    return isinstance(step, dict) and step.get('status') == 'failed'

def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_all.py <BV号> [SESSDATA]")
        print("示例: python3 fetch_all.py BV1ut6YByEZq")
        sys.exit(1)
    
    bvid = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🎬 全自动化获取: {bvid}")
    print("="*70)
    
    results = {
        'bvid': bvid,
        'info': None,
        'danmaku': None,
        'comments': None,
        'subtitle': None
    }

    # 1. 获取弹幕
    print("\n📊 [1/3] 获取弹幕...")
    results['danmaku'] = process_step('弹幕', 'fetch_danmaku_v2.py', bvid)
    if not is_failed(results['danmaku']):
        print(f"   ✅ 弹幕: {results['danmaku'].get('total', 0)} 条")

    # 2. 获取评论
    print("\n💬 [2/3] 获取评论...")
    comment_args = [bvid] + ([sessdata] if sessdata else [])
    results['comments'] = process_step('评论', 'fetch_comments.py', *comment_args)
    if not is_failed(results['comments']):
        print(f"   ✅ 评论: {results['comments'].get('total_count', 0)} 条")

    # 3. 获取字幕
    print("\n📖 [3/3] 获取字幕...")
    results['subtitle'] = process_step('字幕', 'fetch_subtitle_auto.py', bvid)
    if not is_failed(results['subtitle']):
        print(f"   ✅ 字幕: {results['subtitle'].get('method', 'unknown')}")

    # 失败步骤汇总（不再用 null 掩盖失败）
    failed_steps = [k for k in ('danmaku', 'comments', 'subtitle') if is_failed(results[k])]
    results['failed_steps'] = failed_steps
    results['ok'] = not failed_steps

    # 汇总
    print("\n" + "="*70)
    print("📦 获取结果汇总:")
    print(f"   BV号: {bvid}")
    
    d = results['danmaku']
    if is_failed(d):
        print(f"   弹幕: ❌ 失败 (returncode={d.get('returncode')})")
    else:
        print(f"   弹幕: {d.get('total', 0)} 条 → {d.get('path', 'N/A')}")

    c = results['comments']
    if is_failed(c):
        print(f"   评论: ❌ 失败 (returncode={c.get('returncode')})")
    else:
        print(f"   评论: {c.get('total_count', 0)} 条 → /tmp/{bvid}_comments.json")

    s = results['subtitle']
    if is_failed(s):
        print(f"   字幕: ❌ 失败 (returncode={s.get('returncode')})")
    else:
        print(f"   字幕: {s.get('method', 'unknown')} → {s.get('txt_path', s.get('json_path', 'N/A'))}")

    # 输出JSON
    print("\n" + "="*70)
    print("RESULT_JSON_START")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("RESULT_JSON_END")

    if failed_steps:
        print(f"\n⚠️  完成，但以下步骤失败: {', '.join(failed_steps)}")
        sys.exit(1)

    print("\n✅ 全自动化获取完成!")

if __name__ == "__main__":
    main()
