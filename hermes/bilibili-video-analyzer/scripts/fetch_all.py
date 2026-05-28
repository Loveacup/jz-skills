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

# 添加依赖路径
sys.path.insert(0, '~/Library/Python/3.9/lib/python/site-packages')

import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(script_name, *args):
    """运行子脚本并返回结果"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = ['python3', script_path] + list(args)
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600
    )
    
    return result.returncode == 0, result.stdout, result.stderr

def parse_result_json(output):
    """从输出中解析 RESULT_JSON"""
    if 'RESULT_JSON_START' in output and 'RESULT_JSON_END' in output:
        start = output.find('RESULT_JSON_START') + len('RESULT_JSON_START')
        end = output.find('RESULT_JSON_END')
        json_str = output[start:end].strip()
        try:
            return json.loads(json_str)
        except:
            return None
    return None

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
    success, stdout, stderr = run_script('fetch_danmaku_v2.py', bvid)
    if success:
        result = parse_result_json(stdout)
        if result:
            results['danmaku'] = result
            print(f"   ✅ 弹幕: {result.get('total', 0)} 条")
        else:
            print(f"   ✅ 弹幕获取成功")
    else:
        print(f"   ❌ 弹幕获取失败")
    
    # 2. 获取评论
    print("\n💬 [2/3] 获取评论...")
    args = ['fetch_comments.py', bvid]
    if sessdata:
        args.append(sessdata)
    
    success, stdout, stderr = run_script(*args)
    if success:
        result = parse_result_json(stdout)
        if result:
            results['comments'] = result
            print(f"   ✅ 评论: {result.get('total_count', 0)} 条")
        else:
            print(f"   ✅ 评论获取成功")
    else:
        print(f"   ❌ 评论获取失败")
    
    # 3. 获取字幕
    print("\n📖 [3/3] 获取字幕...")
    success, stdout, stderr = run_script('fetch_subtitle_auto.py', bvid)
    if success:
        result = parse_result_json(stdout)
        if result:
            results['subtitle'] = result
            print(f"   ✅ 字幕: {result.get('method', 'unknown')}")
        else:
            print(f"   ✅ 字幕获取成功")
    else:
        print(f"   ❌ 字幕获取失败")
    
    # 汇总
    print("\n" + "="*70)
    print("📦 获取结果汇总:")
    print(f"   BV号: {bvid}")
    
    if results['danmaku']:
        d = results['danmaku']
        print(f"   弹幕: {d.get('total', 0)} 条 → {d.get('path', 'N/A')}")
    
    if results['comments']:
        c = results['comments']
        print(f"   评论: {c.get('total_count', 0)} 条 → /tmp/{bvid}_comments.json")
    
    if results['subtitle']:
        s = results['subtitle']
        print(f"   字幕: {s.get('method', 'unknown')} → {s.get('txt_path', s.get('json_path', 'N/A'))}")
    
    # 输出JSON
    print("\n" + "="*70)
    print("RESULT_JSON_START")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("RESULT_JSON_END")
    
    print("\n✅ 全自动化获取完成!")

if __name__ == "__main__":
    main()
