#!/usr/bin/env python3
"""
小红书链接解析器
用法: python3 parse_xhs_url.py <小红书链接>

支持格式:
- 短链: http://xhslink.com/xxx
- 长链: https://www.xiaohongshu.com/discovery/item/xxx
- 笔记ID: 直接传入
"""

import sys
import re
import requests


# 交接给 XHS-Downloader 后端用：识别合法小红书链接并**原样保留 xsec_token**。
# tail 字符类排除空白和 CJK 标点，这样紧贴 URL 后的「。」「，」等不会被吞进链接。
_URL_TAIL = r'[^\s"<>\\^`{|}，。；！？、【】《》（）]'
_PREPARE_RE = re.compile(
    r'(?:https?://)?(?:'
    r'www\.xiaohongshu\.com/(?:explore|discovery/item|user/profile)/' + _URL_TAIL + r'+'
    r'|xhslink\.com/' + _URL_TAIL + r'+'
    r'|xhs\.cn/' + _URL_TAIL + r'+'
    r')'
)
_NOTE_ID_RE = re.compile(r'^[0-9a-f]{24}$')


def prepare_url(raw):
    """规范化用户输入，交给 XHS-Downloader 后端。

    - 合法链接（explore / discovery/item / user/profile / xhslink / xhs.cn）→ 原样返回，
      **保留 xsec_token 与全部 query**（免风控关键）；短链不在此解析，透传给后端。
    - 夹在文本中的链接 → 抽取，且不吞掉后续中文。
    - 裸 24 位十六进制笔记 ID → 重建 explore 链接（无 token，尽力而为）。
    - 非小红书链接 / 空 → None。

    纯函数、不联网。
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None
    if _NOTE_ID_RE.match(raw):
        return "https://www.xiaohongshu.com/explore/%s" % raw
    m = _PREPARE_RE.search(raw)
    if m:
        return m.group(0)
    return None


def extract_note_id(url_or_id):
    """从各种格式的小红书链接中提取笔记ID"""
    
    # 如果直接是笔记ID（16位十六进制）
    if re.match(r'^[0-9a-f]{24}$', url_or_id):
        return url_or_id
    
    # 短链跳转解析
    if 'xhslink.com' in url_or_id or 'xhs.cn' in url_or_id:
        try:
            # 使用GET请求才能正确跳转
            resp = requests.get(url_or_id, allow_redirects=True, timeout=10)
            final_url = resp.url
            print(f"🔄 短链跳转: {final_url[:80]}...")
        except Exception as e:
            print(f"❌ 短链解析失败: {e}")
            return None
    else:
        final_url = url_or_id
    
    # 从长链中提取笔记ID
    patterns = [
        r'/discovery/item/([0-9a-f]{24})',
        r'/explore/([0-9a-f]{24})',
        r'source=note&noteId=([0-9a-f]{24})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, final_url)
        if match:
            return match.group(1)
    
    return None


def get_basic_info(note_id):
    """通过小红书Web API获取基础信息"""
    
    url = f"https://www.xiaohongshu.com/discovery/item/{note_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.xiaohongshu.com/",
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        # 解析页面获取基本信息
        title_match = re.search(r'<title>(.*?)</title>', resp.text)
        title = title_match.group(1) if title_match else "未知标题"
        
        # 提取初始数据
        data_match = re.search(r'<script>window\.__INITIAL_STATE__=(.*?)</script>', resp.text)
        
        return {
            "note_id": note_id,
            "url": url,
            "title": title,
            "has_initial_data": bool(data_match)
        }
        
    except Exception as e:
        return {
            "note_id": note_id,
            "error": str(e)
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 parse_xhs_url.py <小红书链接>")
        print("示例: python3 parse_xhs_url.py 'http://xhslink.com/xxx'")
        sys.exit(1)
    
    input_str = sys.argv[1]
    
    print(f"🎯 解析链接: {input_str}")
    
    # 提取笔记ID
    note_id = extract_note_id(input_str)
    
    if not note_id:
        print("❌ 无法提取笔记ID")
        sys.exit(1)
    
    print(f"✅ 笔记ID: {note_id}")
    
    # 获取基础信息
    print("\n📄 获取基础信息...")
    info = get_basic_info(note_id)
    
    if "error" in info:
        print(f"❌ 获取失败: {info['error']}")
        sys.exit(1)
    
    print(f"   标题: {info['title']}")
    print(f"   URL: {info['url']}")
    print(f"   有初始数据: {info['has_initial_data']}")
    
    print("\n💡 提示: 要获取完整内容（图片、评论），请使用 fetch_xhs.py 并提供 Cookie")
    
    return info


if __name__ == "__main__":
    main()
