"""XHS-Downloader 返回数据 → 报告模板输入契约 的纯函数适配器。

把 XHS-Downloader `extract()` 单条结果（中文键 dict）映射成
references/xhs-report-prompt.md 第 3 节要求的输入字段，并对免登录模式
拿不到的字段（评论、图片 OCR）输出**标准标注**而非留空/杜撰（P0 约束）。

纯函数、不联网。这是整条链路里最稳定、最该先钉死的契约。

注：本模块运行在 skill 胶水层，目标 Python 3.9（Hermes 部署默认），
因此用 `from __future__ import annotations` 让类型注解延迟求值。
"""

from __future__ import annotations

BACKEND = "xhs-downloader"

# 图文/图集：正文常嵌在轮播图里，免登录模式拿不到 → 建议升级到 CDP 兜底
_IMAGE_TYPES = {"图文", "图集"}

_CONTENT_TRUNCATION_MARKER = (
    "\n\n[正文可能不完整：图文/图集正文常嵌在轮播图中，"
    "免登录模式无法 OCR；如需完整正文请用 CDP 兜底]"
)


def _dedup_preserve_order(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _split_tags(raw: str) -> list:
    """空格分隔的标签串 → 去重（保序）的列表。"""
    return _dedup_preserve_order((raw or "").split())


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _resolve_title(data: dict) -> str:
    """作品标题常为空 → fallback 到作品描述首行，再 fallback 到作品ID。"""
    title = (data.get("作品标题") or "").strip()
    if title:
        return title
    first = _first_line(data.get("作品描述", ""))
    if first:
        return first
    return data.get("作品ID", "") or "无标题"


def _resolve_content(data: dict, note_type: str) -> str:
    content = data.get("作品描述", "") or ""
    if note_type in _IMAGE_TYPES:
        content = content + _CONTENT_TRUNCATION_MARKER
    return content


def _resolve_url(data: dict, url: str | None) -> str:
    """优先保留原始链接（携带 xsec_token，免风控关键）；缺省则重建 explore 链接。"""
    if url:
        return url
    note_id = data.get("作品ID", "")
    return "https://www.xiaohongshu.com/explore/%s" % note_id


def _comments_marker(data: dict) -> str:
    count = data.get("评论数量", "未知")
    return (
        "[评论数据不足：XHS-Downloader 免登录模式无法提取评论，"
        "评论总数 %s 条]" % count
    )


def _ocr_marker(image_urls: list) -> str:
    return (
        "[图片OCR不可用：XHS-Downloader 仅返回图片 URL，"
        "共 %d 张图片未 OCR]" % len(image_urls)
    )


def adapt_to_report_input(data: dict, url: str | None = None) -> dict:
    """XHS-Downloader 单条结果 dict → 报告模板输入契约 dict。

    参数:
        data: XHS-Downloader `extract()` 返回列表里的单条结果（中文键）
        url:  原始输入链接；为 None 时按作品ID重建（会丢失 xsec_token）

    返回的契约键:
        模板字段 -> title / author / tags / url / content / ocr_content / comments
        元信息   -> note_id / author_id / note_type / publish_time / stats / image_urls
        决策辅助 -> backend / needs_cdp_fallback
    """
    note_type = data.get("作品类型", "") or ""
    image_urls = list(data.get("下载地址") or [])

    return {
        # ---- 报告模板第 3 节输入契约 ----
        "title": _resolve_title(data),
        "author": data.get("作者昵称", "") or "",
        "tags": _split_tags(data.get("作品标签", "")),
        "url": _resolve_url(data, url),
        "content": _resolve_content(data, note_type),
        "ocr_content": _ocr_marker(image_urls),
        "comments": _comments_marker(data),
        # ---- 元信息（Meta 表 / 决定是否升级）----
        "note_id": data.get("作品ID", "") or "",
        "author_id": data.get("作者ID", "") or "",
        "note_type": note_type,
        "publish_time": data.get("发布时间", "") or "",
        "stats": {
            "likes": data.get("点赞数量", "-1"),
            "collects": data.get("收藏数量", "-1"),
            "comments": data.get("评论数量", "-1"),
            "shares": data.get("分享数量", "-1"),
        },
        "image_urls": image_urls,
        # ---- 决策辅助 ----
        "backend": BACKEND,
        # 图文/图集且有图 → 正文/OCR 价值在图里，建议上 CDP 兜底
        "needs_cdp_fallback": note_type in _IMAGE_TYPES and len(image_urls) > 0,
    }
