#!/usr/bin/env python3
"""
获取 Bilibili 视频弹幕 - 支持 BV 号直接获取
用法: python3 fetch_danmaku_v2.py <BV号或CID> [SESSDATA]

改进:
- 支持 BV 号直接获取（自动获取 CID）
- 支持 CID 直接获取（兼容旧版）
- 更好的错误处理
"""

import sys
import os

# 添加依赖路径
sys.path.insert(0, '~/Library/Python/3.9/lib/python/site-packages')

import requests
import xml.etree.ElementTree as ET
import json
import re


def is_bvid(s):
    """判断是否为 BV 号"""
    return bool(re.match(r'^BV[a-zA-Z0-9]{10}$', s))


def get_cid_from_bvid(bvid):
    """通过 BV 号获取 CID"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com'
    }
    
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        data = resp.json()
        
        if data.get('code') == 0:
            return data['data']['cid'], data['data']
        else:
            print(f"   ❌ API 错误: {data.get('message', '未知错误')}")
            return None, None
            
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return None, None


def fetch_danmaku(cid, sessdata=None, max_danmaku=200):
    """获取弹幕"""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    
    cookies = {}
    if sessdata:
        cookies["SESSDATA"] = sessdata
    
    print(f"📥 正在获取弹幕 (CID: {cid})...")
    
    # B站弹幕 API
    url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
    
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        
        if resp.status_code != 200:
            print(f"❌ 获取失败: HTTP {resp.status_code}")
            return None
        
        # 解析 XML
        root = ET.fromstring(resp.content)
        danmakus = root.findall('.//d')
        
        total = len(danmakus)
        print(f"   共 {total} 条弹幕")
        
        if total == 0:
            print("   ⚠️ 该视频没有弹幕")
            return {
                'cid': cid,
                'total': 0,
                'sampled': 0,
                'danmaku': [],
                'path': None
            }
        
        # 提取数据（限制数量）
        data = []
        for dm in danmakus[:max_danmaku]:
            text = dm.text if dm.text else ""
            attrs = dm.get('p', '').split(',')
            
            if len(attrs) >= 8:
                time_sec = float(attrs[0])
                mode = int(attrs[1])
                size = int(attrs[2])
                color = int(attrs[3])
                timestamp = int(attrs[4])
                pool = int(attrs[5])
                user_id = attrs[6]
                row_id = int(attrs[7])
                
                minutes = int(time_sec // 60)
                seconds = int(time_sec % 60)
                
                data.append({
                    "text": text,
                    "time": f"{minutes}:{seconds:02d}",
                    "time_sec": time_sec,
                    "mode": mode,
                    "size": size,
                    "color": color
                })
        
        # 保存 JSON
        output_path = f"/tmp/cid_{cid}_danmaku.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "cid": cid,
                "total": total,
                "sampled": len(data),
                "danmaku": data
            }, f, ensure_ascii=False, indent=2)
        
        print(f"   💾 已保存: {output_path}")
        print(f"\n📝 前15条弹幕:")
        for i, dm in enumerate(data[:15], 1):
            print(f"{i:2d}. [{dm['time']}] {dm['text']}")
        
        return {
            "path": output_path,
            "total": total,
            "sampled": len(data),
            "data": data
        }
        
    except ET.ParseError as e:
        print(f"❌ XML 解析失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_danmaku_v2.py <BV号或CID> [SESSDATA] [MAX_COUNT]")
        print("示例:")
        print("  python3 fetch_danmaku_v2.py BV1ut6YByEZq")
        print("  python3 fetch_danmaku_v2.py 35701197640")
        sys.exit(1)
    
    input_id = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None
    max_count = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    
    video_info = None
    
    # 判断输入类型
    if is_bvid(input_id):
        print(f"🎬 检测到 BV 号: {input_id}")
        print("📋 正在获取视频信息...")
        
        cid, video_info = get_cid_from_bvid(input_id)
        if cid is None:
            print("❌ 无法获取 CID")
            sys.exit(1)
        
        print(f"   标题: {video_info['title']}")
        print(f"   UP主: {video_info['owner']['name']}")
        print(f"   CID: {cid}")
    else:
        try:
            cid = int(input_id)
            print(f"🎬 使用 CID: {cid}")
        except ValueError:
            print(f"❌ 无效的输入: {input_id}")
            print("   请输入 BV 号 (如 BV1ut6YByEZq) 或 CID (数字)")
            sys.exit(1)
    
    # 获取弹幕
    result = fetch_danmaku(cid, sessdata, max_count)
    
    if result:
        print(f"\n✅ 弹幕获取完成!")
        
        if video_info:
            result['bvid'] = input_id
            result['title'] = video_info['title']
            result['owner'] = video_info['owner']['name']
        
        # 输出 JSON 结果
        print("\n" + "="*60)
        print("RESULT_JSON_START")
        print(json.dumps(result, ensure_ascii=False))
        print("RESULT_JSON_END")
        print("="*60)
    else:
        print("\n❌ 弹幕获取失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
