"""
进度汇报器模块

提供统一的进度显示、状态汇报、错误提示等功能。
遵循 xhs-crawler 的 emoji 前缀风格。
"""

import sys
from typing import Optional
from datetime import datetime


class ProgressReporter:
    """
    带 emoji 的进度汇报器

    使用示例：
        >>> progress = ProgressReporter("小红书提取器")
        >>> progress.step("🔌", "连接 CDP")
        # ... 执行操作 ...
        >>> progress.done("已连接")
        🔌 连接 CDP... ✓ 已连接
    """

    def __init__(self, task_name: str, verbose: bool = False):
        """
        初始化进度汇报器

        Args:
            task_name: 任务名称（显示在开头）
            verbose: 是否显示详细日志
        """
        self.task_name = task_name
        self.verbose = verbose
        self.start_time = datetime.now()
        self.steps_completed = 0
        self.steps_total = 0

        # 打印任务开始
        print(f"🚀 {task_name}")

        if verbose:
            print(f"[DEBUG] {self._timestamp()} - Task started")

    def _timestamp(self) -> str:
        """生成时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def step(self, emoji: str, message: str, newline: bool = False):
        """
        报告步骤开始

        Args:
            emoji: 步骤图标
            message: 步骤描述
            newline: 是否在步骤后换行（用于长时间操作）
        """
        self.steps_total += 1

        if newline:
            print(f"{emoji} {message}...")
            if self.verbose:
                print(f"[DEBUG] {self._timestamp()} - Starting: {message}")
        else:
            print(f"{emoji} {message}...", end=" ", flush=True)
            if self.verbose:
                print(f"\n[DEBUG] {self._timestamp()} - Starting: {message}", end="")

    def done(self, details: str = ""):
        """
        报告步骤完成

        Args:
            details: 完成的详细信息（可选）
        """
        self.steps_completed += 1

        if details:
            print(f"✓ {details}")
        else:
            print("✓")

        if self.verbose:
            print(f"[DEBUG] {self._timestamp()} - Completed")

    def error(self, message: str, fatal: bool = False):
        """
        报告错误

        Args:
            message: 错误信息
            fatal: 是否为致命错误（会终止程序）
        """
        print(f"❌ {message}", file=sys.stderr)

        if self.verbose:
            print(f"[ERROR] {self._timestamp()} - {message}", file=sys.stderr)

        if fatal:
            print(f"💥 {self.task_name} 失败", file=sys.stderr)
            sys.exit(1)

    def warning(self, message: str):
        """
        报告警告

        Args:
            message: 警告信息
        """
        print(f"⚠️  {message}")

        if self.verbose:
            print(f"[WARN] {self._timestamp()} - {message}")

    def info(self, message: str):
        """
        报告信息

        Args:
            message: 信息内容
        """
        print(f"ℹ️  {message}")

        if self.verbose:
            print(f"[INFO] {self._timestamp()} - {message}")

    def success(self, message: str = ""):
        """
        报告任务成功完成

        Args:
            message: 成功信息（可选）
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if message:
            print(f"✅ {message}")
        else:
            print(f"✅ {self.task_name} 完成！")

        print(
            f"   耗时: {elapsed:.1f}秒 | 步骤: {self.steps_completed}/{self.steps_total}"
        )

        if self.verbose:
            print(f"[DEBUG] {self._timestamp()} - Task completed in {elapsed:.1f}s")

    def progress_bar(self, current: int, total: int, prefix: str = ""):
        """
        显示进度条（用于批量操作）

        Args:
            current: 当前进度
            total: 总数量
            prefix: 前缀文字
        """
        percent = current / total * 100
        bar_length = 30
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(
            f"\r{prefix} [{bar}] {current}/{total} ({percent:.1f}%)", end="", flush=True
        )

        if current == total:
            print()  # 完成后换行

    def sub_step(self, message: str):
        """
        报告子步骤（缩进显示）

        Args:
            message: 子步骤描述
        """
        print(f"  → {message}")

        if self.verbose:
            print(f"[DEBUG] {self._timestamp()} - Sub-step: {message}")


class SilentReporter(ProgressReporter):
    """静默模式汇报器（用于批量操作或测试）"""

    def __init__(self, task_name: str, verbose: bool = False):
        self.task_name = task_name
        self.verbose = verbose
        self.start_time = datetime.now()
        self.steps_completed = 0
        self.steps_total = 0
        # 不打印任何输出

    def step(self, emoji: str, message: str, newline: bool = False):
        self.steps_total += 1

    def done(self, details: str = ""):
        self.steps_completed += 1

    def error(self, message: str, fatal: bool = False):
        if fatal:
            raise RuntimeError(message)

    def warning(self, message: str):
        pass

    def info(self, message: str):
        pass

    def success(self, message: str = ""):
        pass

    def progress_bar(self, current: int, total: int, prefix: str = ""):
        pass

    def sub_step(self, message: str):
        pass


# 便捷函数
def create_reporter(
    task_name: str, verbose: bool = False, silent: bool = False
) -> ProgressReporter:
    """
    创建进度汇报器

    Args:
        task_name: 任务名称
        verbose: 是否详细模式
        silent: 是否静默模式

    Returns:
        ProgressReporter 实例
    """
    if silent:
        return SilentReporter(task_name, verbose)
    return ProgressReporter(task_name, verbose)


# 预定义的 emoji 映射
EMOJI_MAP = {
    "connect": "🔌",
    "browser": "🌐",
    "scroll": "🖱️",
    "extract": "📊",
    "ocr": "🎠",
    "save": "💾",
    "complete": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "search": "🔍",
    "user": "👤",
    "image": "🖼️",
    "text": "📝",
    "data": "📦",
    "time": "⏱️",
}


def get_emoji(key: str) -> str:
    """获取预定义 emoji"""
    return EMOJI_MAP.get(key, "•")
