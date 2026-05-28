#!/usr/bin/env python3
"""
获取 Bilibili 视频弹幕
用法: python3 fetch_danmaku.py <CID> [SESSDATA]

输出: JSON 格式的弹幕数据
"""

import sys
import requests
import xml.etree.ElementTree as ET
import json


def fetch_danmaku(cid, sessdata=None, max_danmaku=200):
    """获取弹幕"""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://www.bilibili.com",
    }
    
    cookies = {}
    if sessdata:
        cookies["SESSDATA"] = sessdata
    
    print(f"📥 正在获取弹幕 (CID: {cid})...")
    
    # B站弹幕 API
    url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
    
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ 获取失败: {resp.status_code}")
        return None
    
    # 解析 XML
    root = ET.fromstring(resp.content)
    danmakus = root.findall('.//d')
    
    total = len(danmakus)
    print(f"   共 {total} 条弹幕")
    
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


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_danmaku.py <CID> [SESSDATA] [MAX_COUNT]")
        print("示例: python3 fetch_danmaku.py 35641886387")
        sys.exit(1)
    
    cid = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None
    max_count = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    
    result = fetch_danmaku(cid, sessdata, max_count)
    
    if result:
        print(f"\n✅ 弹幕获取完成!")
        
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
