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

# 依赖兜底：append 真实属主的用户级 site-packages（不能用 expanduser('~')，
# Hermes profile 会改写 $HOME）。ensure_user_site 内部用 append（非 insert(0)），
# 避免 3.9 编译的 xml/pyexpat 遮蔽当前解释器 stdlib。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site
ensure_user_site()

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


def stratified_sample(danmakus, max_danmaku, stratify=True):
    """分层时间段采样弹幕。

    策略:
    - 当 total <= max_danmaku: 全取
    - 当 total > max_danmaku:
      - stratify=True: 按前/中/后三段时间比例(30%/40%/30%)分配配额,段内按序取
      - stratify=False: 简单取前 max_danmaku 条(兼容旧逻辑)

    返回: 采样后的弹幕列表(保留原始顺序)
    """
    total = len(danmakus)
    if total <= max_danmaku:
        return danmakus

    if not stratify:
        return danmakus[:max_danmaku]

    # 分层采样: 前30% / 中40% / 后30%
    # 段内按原始顺序取前配额条
    front_quota = int(max_danmaku * 0.3)
    mid_quota = int(max_danmaku * 0.4)
    back_quota = max_danmaku - front_quota - mid_quota

    front_end = total // 3
    mid_end = total * 2 // 3

    front_seg = danmakus[:front_end]
    mid_seg = danmakus[front_end:mid_end]
    back_seg = danmakus[mid_end:]

    sampled = (
        front_seg[:front_quota]
        + mid_seg[:mid_quota]
        + back_seg[:back_quota]
    )

    return sampled


def keyword_boost(data, max_danmaku):
    """关键词密度加权: 统计高频词,优先保留含高频词的弹幕。

    简单策略:
    - 统计所有弹幕中长度>=2的词频
    - 取 top-10 高频词作为关键词
    - 优先保留含关键词的弹幕,剩余位置填充未含关键词的
    - 保留总数不超过 max_danmaku

    返回: 重排后的弹幕列表
    """
    if len(data) <= max_danmaku:
        return data

    # 简单分词: 按长度>=2的子串统计(不引入新依赖)
    word_freq = {}
    for dm in data:
        text = dm.get('text', '')
        # 简单切词: 2-4字词
        for length in (4, 3, 2):
            for i in range(len(text) - length + 1):
                word = text[i:i+length]
                if word.strip():
                    word_freq[word] = word_freq.get(word, 0) + 1

    # 取 top-10 高频词
    if not word_freq:
        return data[:max_danmaku]

    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    keywords = set(w for w, _ in top_keywords)

    # 分组: 含关键词 vs 不含
    with_kw = []
    without_kw = []
    for dm in data:
        text = dm.get('text', '')
        if any(kw in text for kw in keywords):
            with_kw.append(dm)
        else:
            without_kw.append(dm)

    # 优先保留含关键词的,剩余位置填充
    result = with_kw[:max_danmaku]
    remain = max_danmaku - len(result)
    if remain > 0:
        result.extend(without_kw[:remain])

    return result


def fetch_danmaku(cid, sessdata=None, max_danmaku=1000, bvid=None, stratify=True):
    """获取弹幕。bvid 提供时，落盘文件名使用 BV 前缀，便于与其它产物（评论/字幕）对齐。

    Args:
        cid: 视频 CID
        sessdata: B站会话令牌
        max_danmaku: 最大采样数(默认1000)
        bvid: BV号(可选,用于文件命名)
        stratify: 是否启用分层采样(默认True)
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }

    cookies = {}
    if sessdata:
        cookies["SESSDATA"] = sessdata

    print(f"📥 正在获取弹幕 (CID: {cid}, max={max_danmaku}, 分层={'是' if stratify else '否'})...")
    
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

        # 分层采样
        sampled_elements = stratified_sample(danmakus, max_danmaku, stratify)

        # 提取数据
        data = []
        for dm in sampled_elements:
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

        # 关键词加权(可选,仅在采样数 > 100 时启用)
        if len(data) > 100:
            data = keyword_boost(data, max_danmaku)
        
        # 保存 JSON（优先 BV 前缀，纯 CID 输入时回退旧命名）
        output_path = f"/tmp/{bvid}_danmaku.json" if bvid else f"/tmp/cid_{cid}_danmaku.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "bvid": bvid,
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
        print("用法: python3 fetch_danmaku_v2.py <BV号或CID> [SESSDATA] [MAX_COUNT] [--stratify | --no-stratify]")
        print("示例:")
        print("  python3 fetch_danmaku_v2.py BV1ut6YByEZq")
        print("  python3 fetch_danmaku_v2.py BV1ut6YByEZq <SESSDATA> 1000")
        print("  python3 fetch_danmaku_v2.py BV1ut6YByEZq <SESSDATA> 1000 --no-stratify")
        sys.exit(1)

    # 解析参数
    args = sys.argv[1:]
    stratify = True
    if '--no-stratify' in args:
        stratify = False
        args.remove('--no-stratify')
    if '--stratify' in args:
        stratify = True
        args.remove('--stratify')

    input_id = args[0]
    sessdata = args[1] if len(args) > 1 else None
    max_count = int(args[2]) if len(args) > 2 else 1000

    video_info = None
    bvid = input_id if is_bvid(input_id) else None
    
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
    result = fetch_danmaku(cid, sessdata, max_count, bvid=bvid, stratify=stratify)
    
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
