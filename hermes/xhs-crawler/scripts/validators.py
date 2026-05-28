"""
数据契约验证模块

提供数据完整性验证、Schema 校验、字段检查等功能。
"""

from typing import Tuple, List, Dict, Any, Optional

# 数据契约定义
REQUIRED_FIELDS = ["title", "author", "content"]
OPTIONAL_FIELDS = [
    "tags",
    "comments",
    "stats",
    "carousel_ocr",
    "images",
    "full_content",
]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# 字段类型定义
FIELD_TYPES = {
    "title": str,
    "author": str,
    "content": str,
    "tags": list,
    "comments": list,
    "stats": dict,
    "carousel_ocr": list,
    "images": list,
    "full_content": str,
}


def validate_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证提取数据的完整性

    Args:
        data: 提取的 JSON 数据

    Returns:
        (是否有效, 缺失字段列表)

    Example:
        >>> data = {"title": "测试", "author": "用户", "content": "正文"}
        >>> valid, missing = validate_data(data)
        >>> print(valid, missing)
        True []

        >>> data = {"title": "测试"}
        >>> valid, missing = validate_data(data)
        >>> print(valid, missing)
        False ['author', 'content']
    """
    missing = []

    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            missing.append(field)

    return len(missing) == 0, missing


def validate_field_types(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证字段类型是否正确

    Args:
        data: 提取的 JSON 数据

    Returns:
        (是否有效, 类型错误字段列表)
    """
    type_errors = []

    for field, expected_type in FIELD_TYPES.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                type_errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(data[field]).__name__}"
                )

    return len(type_errors) == 0, type_errors


def validate_comment_structure(comments: List[Dict]) -> Tuple[bool, List[str]]:
    """
    验证评论数据结构

    Args:
        comments: 评论列表

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    if not isinstance(comments, list):
        return False, ["comments must be a list"]

    required_comment_fields = ["user", "text"]

    for i, comment in enumerate(comments):
        if not isinstance(comment, dict):
            errors.append(f"Comment {i} is not a dict")
            continue

        for field in required_comment_fields:
            if field not in comment:
                errors.append(f"Comment {i} missing field: {field}")

    return len(errors) == 0, errors


def validate_stats_structure(stats: Dict) -> Tuple[bool, List[str]]:
    """
    验证统计数据结构

    Args:
        stats: 统计数据字典

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    if not isinstance(stats, dict):
        return False, ["stats must be a dict"]

    # 检查是否为字符串或数字
    for key, value in stats.items():
        if not isinstance(value, (str, int)):
            errors.append(f"stats.{key} must be str or int, got {type(value).__name__}")

    return len(errors) == 0, errors


def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    清理和标准化数据

    - 去除字符串首尾空白
    - 确保列表字段为列表类型
    - 移除空值字段

    Args:
        data: 原始数据

    Returns:
        清理后的数据
    """
    cleaned = {}

    for key, value in data.items():
        if value is None:
            continue

        if isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value:  # 只保留非空字符串
                cleaned[key] = cleaned_value
        elif isinstance(value, list):
            cleaned[key] = value
        elif isinstance(value, dict):
            cleaned[key] = value
        else:
            cleaned[key] = value

    return cleaned


def generate_data_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成数据质量报告

    Args:
        data: 提取的 JSON 数据

    Returns:
        质量报告字典
    """
    report = {
        "valid": False,
        "missing_required": [],
        "missing_optional": [],
        "type_errors": [],
        "comment_errors": [],
        "stats_errors": [],
        "field_counts": {},
        "recommendations": [],
    }

    # 验证必需字段
    valid, missing = validate_data(data)
    report["valid"] = valid
    report["missing_required"] = missing

    # 检查可选字段
    for field in OPTIONAL_FIELDS:
        if field not in data or not data[field]:
            report["missing_optional"].append(field)

    # 验证类型
    _, type_errors = validate_field_types(data)
    report["type_errors"] = type_errors

    # 验证评论结构
    if "comments" in data and data["comments"]:
        _, comment_errors = validate_comment_structure(data["comments"])
        report["comment_errors"] = comment_errors

    # 验证统计数据
    if "stats" in data and data["stats"]:
        _, stats_errors = validate_stats_structure(data["stats"])
        report["stats_errors"] = stats_errors

    # 字段统计
    for field in ALL_FIELDS:
        if field in data and data[field]:
            if isinstance(data[field], list):
                report["field_counts"][field] = len(data[field])
            elif isinstance(data[field], str):
                report["field_counts"][field] = len(data[field])
            else:
                report["field_counts"][field] = 1

    # 生成建议
    if report["missing_required"]:
        report["recommendations"].append(
            f"缺少必需字段: {', '.join(report['missing_required'])}"
        )

    if "comments" not in data or not data["comments"]:
        report["recommendations"].append("评论数据缺失，可能影响报告质量")

    if "carousel_ocr" not in data or not data["carousel_ocr"]:
        report["recommendations"].append("轮播图 OCR 缺失，建议检查 OCR 服务")

    return report


# 便捷函数
def quick_validate(data: Dict[str, Any]) -> bool:
    """快速验证数据是否有效"""
    valid, _ = validate_data(data)
    return valid


def get_missing_fields(data: Dict[str, Any]) -> List[str]:
    """获取缺失的必需字段列表"""
    _, missing = validate_data(data)
    return missing


def is_field_present(data: Dict[str, Any], field: str) -> bool:
    """检查字段是否存在且非空"""
    return field in data and data[field] is not None and data[field] != ""
