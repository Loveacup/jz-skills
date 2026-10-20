#!/usr/bin/env python3
"""
获取 Bilibili 视频字幕 - 使用 bilibili-api-python (WBI API)
用法: python3 fetch_subtitle.py <BV号> [SESSDATA]

特点:
- 使用 bilibili-api-python 库，自动处理 WBI 签名
- 解决旧 API 字幕映射错误问题
- 支持异步操作，性能更好
"""

import sys
import os
import json
import asyncio

# 依赖兜底：append 真实属主的用户级 site-packages（原写法字面量 '~' 从不展开，
# 且 Hermes profile 会改写 $HOME）。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site
ensure_user_site()

from bilibili_api import video, Credential

async def fetch_subtitle(bvid, sessdata=None):
    """异步获取字幕"""
    
    # 创建 Credential
    credential = None
    if sessdata:
        credential = Credential(sessdata=sessdata)
    
    # 创建视频对象
    v = video.Video(bvid=bvid, credential=credential)
    
    # 获取视频信息
    print(f"🎬 正在获取视频信息: {bvid}")
    info = await v.get_info()
    
    title = info['title']
    cid = info['cid']
    duration = info['duration']
    owner = info['owner']['name']
    
    print(f"   标题: {title}")
    print(f"   UP主: {owner}")
    print(f"   时长: {duration//60}分{duration%60}秒")
    print(f"   CID: {cid}")
    
    # 获取字幕
    print(f"\n📥 正在获取字幕...")
    subtitles = await v.get_subtitle(cid)
    
    sub_list = subtitles.get('subtitles', [])
    print(f"   找到 {len(sub_list)} 个字幕轨道")
    
    if not sub_list:
        print("⚠️ 该视频没有字幕")
        return None
    
    results = []
    
    for i, sub in enumerate(sub_list):
        print(f"\n[{i}] {sub['lan_doc']} ({sub['lan']}):")
        
        sub_url = sub['subtitle_url']
        if not sub_url:
            print("   ⚠️ 字幕URL为空，跳过")
            continue
        
        # 修复URL（添加 https: 前缀）
        if sub_url.startswith('//'):
            sub_url = 'https:' + sub_url
        
        # 下载字幕内容
        import requests
        sub_resp = requests.get(sub_url, timeout=30)
        
        if sub_resp.status_code != 200:
            print(f"   ❌ 下载失败: {sub_resp.status_code}")
            continue
        
        sub_data = sub_resp.json()
        count = len(sub_data.get('body', []))
        print(f"   ✅ 下载成功: {count} 条字幕")
        
        # 保存 JSON
        json_path = f"/tmp/{bvid}_subtitle_{sub['lan']}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sub_data, f, ensure_ascii=False, indent=2)
        
        # 保存 TXT（带时间戳）
        txt_path = f"/tmp/{bvid}_subtitle_{sub['lan']}.txt"
        lines = []
        for item in sub_data.get('body', []):
            from_time = int(item['from'])
            minutes = from_time // 60
            seconds = from_time % 60
            lines.append(f"[{minutes}:{seconds:02d}] {item['content']}")
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"   💾 JSON: {json_path}")
        print(f"   💾 TXT:  {txt_path}")
        
        # 内容验证
        sample = ' '.join([item['content'] for item in sub_data.get('body', [])[:10]])
        print(f"   📝 前50字: {sample[:50]}...")
        
        results.append({
            'language': sub['lan'],
            'language_doc': sub['lan_doc'],
            'count': count,
            'json_path': json_path,
            'txt_path': txt_path,
            'sample': sample[:100]
        })
    
    return {
        'bvid': bvid,
        'title': title,
        'owner': owner,
        'cid': cid,
        'subtitles': results
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_subtitle.py <BV号> [SESSDATA]")
        print("示例: python3 fetch_subtitle.py BV12Q6TBwE2J")
        sys.exit(1)
    
    bvid = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 运行异步函数
    result = asyncio.run(fetch_subtitle(bvid, sessdata))
    
    if result:
        print(f"\n✅ 字幕获取完成!")
        print(f"   视频: {result['title']}")
        print(f"   共 {len(result['subtitles'])} 个字幕轨道")
        
        # 输出 JSON 结果（供调用方解析）
        print("\n" + "="*60)
        print("RESULT_JSON_START")
        print(json.dumps(result, ensure_ascii=False))
        print("RESULT_JSON_END")
        print("="*60)
    else:
        print("\n❌ 字幕获取失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
