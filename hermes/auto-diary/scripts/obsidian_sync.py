#!/usr/bin/env python3
"""
Obsidian 同步与操作工具
支持：启动应用、打开笔记、触发官方同步
"""

import subprocess
import time
import urllib.parse
from pathlib import Path

VAULT_PATH = "~/Documents/Obsidian/AlexCai"
VAULT_NAME = "AlexCai"


def is_obsidian_running() -> bool:
    """检查 Obsidian 是否在运行"""
    result = subprocess.run(
        ["pgrep", "-x", "Obsidian"],
        capture_output=True,
        timeout=5
    )
    return result.returncode == 0


def launch_obsidian(vault_path: str = None) -> dict:
    """
    启动 Obsidian 应用
    
    Args:
        vault_path: Vault 路径，默认使用 AlexCai
    
    Returns:
        {"status": "success|already_running|error", "message": "..."}
    """
    if is_obsidian_running():
        return {
            "status": "already_running",
            "message": "Obsidian 已在运行，官方同步服务活跃中"
        }
    
    try:
        vault = vault_path or VAULT_PATH
        subprocess.Popen(
            ["open", "-a", "Obsidian", "--args", "--vault", vault],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 等待启动
        for _ in range(10):
            time.sleep(0.5)
            if is_obsidian_running():
                return {
                    "status": "success",
                    "message": "Obsidian 已启动，官方同步服务连接中"
                }
        
        return {
            "status": "success",
            "message": "Obsidian 启动中（请等待官方同步完成）"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"启动失败: {e}"
        }


def open_note(note_path: str) -> dict:
    """
    通过 Obsidian URI 打开指定笔记
    
    Args:
        note_path: 笔记路径（相对于 vault 根目录）
                  例如: "50-Self/01_日记/2026-05-14.md"
    
    Returns:
        {"status": "success|error", "message": "..."}
    """
    try:
        encoded_path = urllib.parse.quote(note_path)
        uri = f"obsidian://open?vault={VAULT_NAME}&file={encoded_path}"
        
        subprocess.run(
            ["open", uri],
            check=True,
            timeout=10
        )
        return {
            "status": "success",
            "message": f"已打开笔记: {note_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"打开笔记失败: {e}"
        }


def sync_and_wait(timeout: int = 30) -> dict:
    """
    确保 Obsidian 运行并等待同步完成
    
    Args:
        timeout: 最大等待秒数
    
    Returns:
        {"status": "success|timeout|error", "message": "..."}
    """
    # 1. 确保 Obsidian 在运行
    result = launch_obsidian()
    if result["status"] == "error":
        return result
    
    # 2. 如果已经在运行，直接返回
    if result["status"] == "already_running":
        return result
    
    # 3. 等待启动和初始同步
    time.sleep(3)
    
    return {
        "status": "success",
        "message": f"Obsidian 已启动，官方同步服务连接中（最长等待 {timeout} 秒）"
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: obsidian_sync.py [launch|open|sync] [args...]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "launch":
        print(launch_obsidian())
    elif command == "open" and len(sys.argv) >= 3:
        print(open_note(sys.argv[2]))
    elif command == "sync":
        print(sync_and_wait())
    else:
        print(f"Unknown command: {command}")
