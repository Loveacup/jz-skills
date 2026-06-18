#!/usr/bin/env python3
"""
小红书自动化获取 - 纯算法签名方案
无需浏览器，无需二维码，直接调用API

用法:
    python3 xhs_api.py <笔记链接>
"""

import sys
import os
import re
import json
import time
import random
import requests
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse, parse_qs

# 添加 xhshow 库路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# Define Xhshow type for type checking
if TYPE_CHECKING:
    from xhshow import Xhshow as XhshowType

HAS_XHSHOW = False

try:
    from xhshow import Xhshow

    HAS_XHSHOW = True
except ImportError:
    print(f"⚠️  xhshow 库未安装，部分功能将受限")
    Xhshow = None  # type: ignore[assignment]


def base36encode(number: int) -> str:
    """将整数编码为 base36 字符串"""
    if number < 0:
        raise ValueError("负数不支持")
    if number == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = []
    while number > 0:
        number, remainder = divmod(number, 36)
        result.append(digits[remainder])
    return "".join(reversed(result))


class XHSAPI:
    """小红书API调用（使用xhshow签名）"""

    def __init__(self, cookies=None):
        self.cookies = cookies or {}
        self.client = Xhshow() if HAS_XHSHOW else None  # type: ignore[operator]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.xiaohongshu.com/",
            }
        )

    def parse_note_url(self, url):
        """解析笔记链接"""
        # 处理短链
        if "xhslink.com" in url or "xhs.cn" in url:
            resp = self.session.get(url, allow_redirects=True, timeout=10)
            url = resp.url

        # 提取 note_id
        match = re.search(r"/(?:explore|discovery/item|item)/([0-9a-f]{24})", url)
        if match:
            return match.group(1)
        return None

    def _get_search_id(self) -> str:
        """生成搜索ID (base36编码)"""
        timestamp_ms = int(time.time() * 1000)
        combined = (timestamp_ms << 64) + random.randint(0, 2147483646)
        return base36encode(combined)

    def _request_with_retry(self, method, url, headers, **kwargs):
        """带重试的请求方法"""
        proxy = os.environ.get("XHS_PROXY")
        proxies = {"http": proxy, "https": proxy} if proxy else None

        for attempt in range(3):
            try:
                if method.upper() == "GET":
                    resp = self.session.get(
                        url, headers=headers, proxies=proxies, timeout=15, **kwargs
                    )
                else:
                    resp = self.session.post(
                        url, headers=headers, proxies=proxies, timeout=15, **kwargs
                    )

                if resp.status_code == 200:
                    return resp
                else:
                    return {
                        "error": f"API 请求失败: {resp.status_code}",
                        "response": resp.text[:500] if resp.text else "",
                    }

            except Exception as e:
                if attempt < 2:  # 还有重试机会
                    time.sleep(2)  # 2秒后退重试
                else:
                    return {"error": f"请求异常 (已重试3次): {e}"}

        return {"error": "未知错误"}

    def search_notes(self, keyword, sort="general", page=1, page_size=20):
        """搜索笔记

        Args:
            keyword: 搜索关键词
            sort: 排序方式 (general, time, popularity)
            page: 页码
            page_size: 每页数量

        Returns:
            dict: API响应结果
        """
        if not HAS_XHSHOW:
            return {"error": "xhshow 库未安装，无法生成签名"}

        assert self.client is not None, "xhshow 客户端未初始化"

        uri = "/api/sns/web/v1/search/notes"
        url = f"https://edith.xiaohongshu.com{uri}"

        body = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": self._get_search_id(),
            "sort": sort,
            "note_type": 0,
        }

        try:
            sign_headers = self.client.sign_headers_post(  # type: ignore[union-attr]
                uri=uri, cookies=self.cookies, payload=body
            )
        except Exception as e:
            return {"error": f"签名生成失败: {e}"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
            "Content-Type": "application/json",
            **sign_headers,
        }

        result = self._request_with_retry("POST", url, headers, json=body)
        if isinstance(result, dict):
            return result
        return result.json()

    def get_note_detail(self, note_id, xsec_token="", xsec_source="pc_search"):
        """获取笔记详情

        Args:
            note_id: 笔记ID
            xsec_token: 安全令牌
            xsec_source: 来源标识

        Returns:
            dict: API响应结果
        """
        if not HAS_XHSHOW:
            return {"error": "xhshow 库未安装，无法生成签名"}

        if not self.client:
            return {"error": "xhshow 客户端未初始化"}

        uri = "/api/sns/web/v1/feed"
        url = f"https://edith.xiaohongshu.com{uri}"

        body = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
        }

        try:
            sign_headers = self.client.sign_headers_post(  # type: ignore[union-attr]
                uri=uri, cookies=self.cookies, payload=body
            )
        except Exception as e:
            return {"error": f"签名生成失败: {e}"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
            "Content-Type": "application/json",
            **sign_headers,
        }

        result = self._request_with_retry("POST", url, headers, json=body)
        if isinstance(result, dict):
            return result
        return result.json()

    def get_note_comments(self, note_id, cursor="", xsec_token=""):
        """获取笔记评论

        Args:
            note_id: 笔记ID
            cursor: 分页游标
            xsec_token: 安全令牌

        Returns:
            dict: API响应结果
        """
        if not HAS_XHSHOW:
            return {"error": "xhshow 库未安装，无法生成签名"}

        if not self.client:
            return {"error": "xhshow 客户端未初始化"}

        uri = "/api/sns/web/v2/comment/page"
        url = f"https://edith.xiaohongshu.com{uri}"

        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
            "xsec_token": xsec_token,
        }

        try:
            sign_headers = self.client.sign_headers_get(  # type: ignore[union-attr]
                uri=uri, cookies=self.cookies, params=params
            )
        except Exception as e:
            return {"error": f"签名生成失败: {e}"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
            **sign_headers,
        }

        result = self._request_with_retry("GET", url, headers, params=params)
        if isinstance(result, dict):
            return result
        return result.json()

    def get_creator_info(self, user_id):
        """获取创作者信息

        Args:
            user_id: 用户ID

        Returns:
            dict: 解析后的用户信息
        """
        url = f"https://www.xiaohongshu.com/user/profile/{user_id}"

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return {"error": f"请求失败: {resp.status_code}"}

            # 从HTML中提取 __INITIAL_STATE__ JSON
            match = re.search(
                r"<script>window\.__INITIAL_STATE__=(.+)</script>", resp.text
            )
            if not match:
                return {"error": "无法从页面提取用户数据"}

            json_str = match.group(1)
            # 替换 :undefined 为 :null
            json_str = json_str.replace(":undefined", ":null")

            data = json.loads(json_str)

            # 提取用户信息
            user_data = data.get("user", {}).get("userPageData", {})
            return {
                "user_id": user_id,
                "nickname": user_data.get("nickname"),
                "avatar": user_data.get("avatar"),
                "description": user_data.get("desc"),
                "followers": user_data.get("fansCount"),
                "following": user_data.get("followCount"),
                "notes_count": user_data.get("noteCount"),
                "liked": user_data.get("likedCount"),
                "ip_location": user_data.get("ipLocation"),
            }

        except json.JSONDecodeError as e:
            return {"error": f"JSON解析失败: {e}"}
        except Exception as e:
            return {"error": f"获取用户信息失败: {e}"}

    def get_creator_notes(
        self, user_id, cursor="", page_size=30, xsec_token="", xsec_source="pc_feed"
    ):
        """获取创作者发布的笔记列表

        Args:
            user_id: 用户ID
            cursor: 分页游标
            page_size: 每页数量
            xsec_token: 安全令牌
            xsec_source: 来源标识

        Returns:
            dict: API响应结果
        """
        if not HAS_XHSHOW:
            return {"error": "xhshow 库未安装，无法生成签名"}

        if not self.client:
            return {"error": "xhshow 客户端未初始化"}

        uri = "/api/sns/web/v1/user_posted"
        url = f"https://edith.xiaohongshu.com{uri}"

        params = {
            "num": page_size,
            "cursor": cursor,
            "user_id": user_id,
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
        }

        try:
            sign_headers = self.client.sign_headers_get(  # type: ignore[union-attr]
                uri=uri, cookies=self.cookies, params=params
            )
        except Exception as e:
            return {"error": f"签名生成失败: {e}"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
            **sign_headers,
        }

        result = self._request_with_retry("GET", url, headers, params=params)
        if isinstance(result, dict):
            return result
        return result.json()


def main():
    if len(sys.argv) < 2:
        print("用法: python3 xhs_api.py <小红书链接>")
        sys.exit(1)

    url = sys.argv[1]

    # 检查 xhshow
    if not HAS_XHSHOW:
        print("❌ xhshow 库未正确安装")
        print("\n请尝试:")
        project_dir = Path(__file__).parent.parent
        print(f"   cd {project_dir}")
        print("   pip3 install xhshow")
        sys.exit(1)

    print("🚀 小红书 API 获取工具（纯算法签名）")
    print("=" * 60)

    # 创建 API 实例（需要有效的 Cookie）
    # 注意: 需要提供有效的 a1 和 web_session
    cookies = {}  # 这里需要从用户获取或使用已保存的

    # 尝试加载保存的 Cookie
    cookie_file = os.path.expanduser("~/.xhs_cookie")
    if os.path.exists(cookie_file):
        with open(cookie_file, "r") as f:
            cookie_str = f.read().strip()
            # 解析 Cookie 字符串
            for item in cookie_str.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookies[k] = v
        print(f"📂 已加载 Cookie: {list(cookies.keys())}")
    else:
        print("⚠️  未找到 Cookie 文件")
        print("   需要有效的 a1 和 web_session 才能调用 API")
        print("\n💡 获取方法:")
        print("   1. 浏览器登录小红书网页版")
        print("   2. F12 → Application → Cookies")
        print("   3. 复制 a1 和 web_session 字段")
        print(f"   4. 保存到 {cookie_file}")
        sys.exit(1)

    api = XHSAPI(cookies=cookies)

    # 解析笔记ID
    print(f"\n🎯 解析链接: {url}")
    note_id = api.parse_note_url(url)

    if not note_id:
        print("❌ 无法提取笔记ID")
        sys.exit(1)

    print(f"✅ 笔记ID: {note_id}")

    # 获取笔记详情
    print("\n📥 调用小红书 API...")
    result = api.get_note_detail(note_id)

    # 输出结果
    print("\n" + "=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)

    # 保存
    output_file = f"/tmp/xhs_api_{note_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 已保存到: {output_file}")


if __name__ == "__main__":
    main()
