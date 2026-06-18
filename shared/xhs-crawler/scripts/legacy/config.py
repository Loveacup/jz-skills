"""
配置管理模块

集中管理所有环境变量和配置项，支持 .env 文件加载。
"""

import os
from pathlib import Path
from typing import Optional

# 尝试加载 python-dotenv
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


# 基础目录
BASE_DIR = Path(__file__).parent.parent

# 加载 .env 文件
if DOTENV_AVAILABLE:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)


class Config:
    """
    配置管理类

    所有配置项都从此类获取，支持环境变量覆盖。
    """

    # ========== CDP 配置 ==========
    CHROME_CDP_URL: str = os.getenv("CHROME_CDP_URL", "http://127.0.0.1:19222")
    """Chrome CDP 连接地址"""

    # ========== API 配置 ==========
    XHS_API_BASE: str = os.getenv("XHS_API_BASE", "https://www.xiaohongshu.com")
    """小红书 API 基础地址"""

    # ========== OCR 配置 ==========
    QWEN_API_URL: Optional[str] = os.getenv("QWEN_API_URL")
    """Qwen3-VL OCR 服务地址"""

    OCR_TIMEOUT: int = int(os.getenv("OCR_TIMEOUT", "60"))
    """OCR 请求超时时间（秒）"""

    # ========== 输出配置 ==========
    @classmethod
    def get_output_dir(cls) -> Path:
        """获取报告输出目录"""
        output_dir = os.getenv("XHS_OUTPUT_DIR")

        if output_dir:
            return Path(output_dir).expanduser()

        # 自动检测 Obsidian Vault
        vault_path = cls._detect_obsidian_vault()
        if vault_path:
            return vault_path / "00-Inbox"

        # 回退到默认路径
        return Path.home() / ".hermes" / "xhs-output"

    @staticmethod
    def _detect_obsidian_vault() -> Optional[Path]:
        """自动检测 Obsidian Vault 路径"""
        possible_paths = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Obsidian",
            Path.home()
            / "Library"
            / "Mobile Documents"
            / "iCloud~md~obsidian"
            / "Documents",
        ]

        for path in possible_paths:
            if path.exists():
                # 查找包含 .obsidian 的子目录
                for subdir in path.iterdir():
                    if subdir.is_dir() and (subdir / ".obsidian").exists():
                        return subdir

        return None

    # ========== Cookie 配置 ==========
    COOKIE_FILE: Path = Path(os.getenv("XHS_COOKIE_FILE", "~/.xhs_cookie")).expanduser()
    """Cookie 存储文件路径"""

    # ========== 爬虫配置 ==========
    REQUEST_TIMEOUT: int = int(os.getenv("XHS_REQUEST_TIMEOUT", "30"))
    """HTTP 请求超时时间（秒）"""

    MAX_RETRIES: int = int(os.getenv("XHS_MAX_RETRIES", "3"))
    """最大重试次数"""

    RATE_LIMIT_DELAY: float = float(os.getenv("XHS_RATE_LIMIT_DELAY", "1.0"))
    """请求间隔延迟（秒）"""

    SCROLL_TIMES: int = int(os.getenv("XHS_SCROLL_TIMES", "5"))
    """评论区滚动次数"""

    SCROLL_DELAY: float = float(os.getenv("XHS_SCROLL_DELAY", "1.0"))
    """每次滚动后的等待时间（秒）"""

    # ========== 代理配置 ==========
    PROXY: Optional[str] = os.getenv("XHS_PROXY")
    """HTTP 代理地址，格式：http://host:port"""

    # ========== 调试配置 ==========
    VERBOSE: bool = os.getenv("XHS_VERBOSE", "").lower() in ("true", "1", "yes")
    """是否启用详细日志"""

    DEBUG: bool = os.getenv("XHS_DEBUG", "").lower() in ("true", "1", "yes")
    """是否启用调试模式"""

    # ========== 清理配置 ==========
    AUTO_CLEANUP: bool = os.getenv("XHS_AUTO_CLEANUP", "").lower() in (
        "true",
        "1",
        "yes",
    )
    """是否自动清理临时文件"""

    KEEP_RAW_DATA: bool = os.getenv("XHS_KEEP_RAW_DATA", "").lower() in (
        "true",
        "1",
        "yes",
    )
    """是否保留原始 JSON 数据"""

    @classmethod
    def get_proxy_dict(cls) -> Optional[dict]:
        """获取代理配置字典（用于 requests）"""
        if cls.PROXY:
            return {
                "http": cls.PROXY,
                "https": cls.PROXY,
            }
        return None

    @classmethod
    def validate(cls) -> list:
        """
        验证配置是否有效

        Returns:
            错误信息列表（空列表表示验证通过）
        """
        errors = []

        # 检查必需配置
        if not cls.QWEN_API_URL:
            errors.append("QWEN_API_URL 未设置，OCR 功能将不可用")

        # 检查输出目录可写
        output_dir = cls.get_output_dir()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            test_file = output_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            errors.append(f"输出目录无写入权限: {output_dir}")

        return errors

    @classmethod
    def print_config(cls):
        """打印当前配置（用于调试）"""
        print("当前配置:")
        print(f"  Chrome CDP URL: {cls.CHROME_CDP_URL}")
        print(f"  Qwen API: {cls.QWEN_API_URL or '(未设置)'}")
        print(f"  输出目录: {cls.get_output_dir()}")
        print(f"  Cookie 文件: {cls.COOKIE_FILE}")
        print(f"  超时: {cls.REQUEST_TIMEOUT}s")
        print(f"  重试: {cls.MAX_RETRIES}次")
        print(f"  延迟: {cls.RATE_LIMIT_DELAY}s")
        print(f"  代理: {cls.PROXY or '(无)'}")
        print(f"  详细日志: {cls.VERBOSE}")


# 便捷访问函数
def get_config() -> Config:
    """获取配置类实例"""
    return Config()


def validate_config() -> bool:
    """验证配置是否有效"""
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"  ❌ {error}")
        return False
    return True


# 如果直接运行此文件，打印配置
if __name__ == "__main__":
    Config.print_config()

    errors = Config.validate()
    if errors:
        print("\n⚠️  配置警告:")
        for error in errors:
            print(f"  {error}")
    else:
        print("\n✅ 配置验证通过")
