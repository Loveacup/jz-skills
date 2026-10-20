#!/usr/bin/env python3
"""
小红书 Cookie 管理工具
用法: python3 cookie_manager.py <save|show> [cookie字符串]
"""

import sys
import os
import json

COOKIE_FILE = os.path.expanduser("~/.xhs_cookie")


def save_cookie(cookie_str):
    """保存 Cookie 到文件"""
    
    # 简单验证 Cookie 格式
    required_fields = ["web_session", "a1"]
    
    for field in required_fields:
        if field not in cookie_str:
            print(f"⚠️  Cookie 中缺少 {field} 字段")
    
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie_str)
    
    # 设置权限
    os.chmod(COOKIE_FILE, 0o600)
    
    print(f"✅ Cookie 已保存到: {COOKIE_FILE}")
    print("   权限: 600（仅当前用户可读）")


def show_cookie():
    """显示保存的 Cookie"""
    
    if not os.path.exists(COOKIE_FILE):
        print("❌ 未找到保存的 Cookie")
        print(f"\n💡 获取方法:")
        print("   1. 登录小红书网页版: https://www.xiaohongshu.com")
        print("   2. 打开浏览器开发者工具 (F12)")
        print("   3. 切换到 Application/Storage 标签")
        print("   4. 找到 Cookies 中的 web_session 和 a1")
        print("   5. 复制所有 Cookie 字段")
        print(f"\n   然后运行: python3 cookie_manager.py save '你的cookie'")
        return None
    
    with open(COOKIE_FILE, "r") as f:
        cookie = f.read().strip()
    
    # 脱敏显示
    if len(cookie) > 50:
        masked = cookie[:30] + "..." + cookie[-10:]
    else:
        masked = cookie[:20] + "..."
    
    print(f"✅ Cookie 已保存")
    print(f"   内容: {masked}")
    print(f"   文件: {COOKIE_FILE}")
    
    return cookie


def get_cookie_for_mediacrawler():
    """获取 MediaCrawler 格式的 Cookie"""
    
    cookie = show_cookie()
    if not cookie:
        return None
    
    # 解析为字典
    cookie_dict = {}
    for item in cookie.split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            cookie_dict[key] = value
    
    return cookie_dict


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  保存Cookie: python3 cookie_manager.py save 'web_session=xxx;a1=xxx'")
        print("  查看Cookie: python3 cookie_manager.py show")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "save":
        if len(sys.argv) < 3:
            print("❌ 请提供 Cookie 字符串")
            sys.exit(1)
        save_cookie(sys.argv[2])
    
    elif action == "show":
        show_cookie()
    
    else:
        print(f"❌ 未知操作: {action}")
        print("可用操作: save, show")


if __name__ == "__main__":
    main()
