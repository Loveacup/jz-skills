"""TDD 主战场：XHS-Downloader 返回数据 → 报告模板输入契约 的纯函数适配器。

固定 references/xhs-report-prompt.md 第 3 节的输入契约：
    {title} {author} {tags} {url} {content} {ocr_content} {comments}

样本取自 references/xhs-downloader-integration.md 中已抓到的真实返回
（笔记 ID 6a116dd8000000003502a688），并把占位的「17 image URLs」补成真实长度的列表。

适配器只做纯映射，不联网；这让契约完全确定、一把钉死。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from xhs_adapter import adapt_to_report_input  # noqa: E402


def make_sample():
    """XHS-Downloader `extract()` 单条结果的真实形态。"""
    return {
        "收藏数量": "1641",
        "评论数量": "15",
        "分享数量": "190",
        "点赞数量": "959",
        # 注意：「Obsidian插件」重复出现两次 → 适配器必须去重
        "作品标签": "Obsidian Obsidian插件 Ob ob插件 Obsidian插件 AI工具 插件",
        "作品ID": "6a116dd8000000003502a688",
        "作品标题": "",  # 常为空 → 必须 fallback 到描述首行
        "作品描述": "Obsidian 用得越久，我反而越离不开这 3 个插件\n"
        "分享三个高效插件：自动保存历史、图片处理和智能搜索...",
        "作品类型": "图文",
        "发布时间": "2026-05-23_20:01:14",
        "作者昵称": "艾康的AI自留地",
        "作者ID": "65e17d09000000000500d97b",
        "下载地址": [
            "https://sns-img.xhscdn.com/img_%02d.webp" % i for i in range(17)
        ],
    }


# ---- 直接字段映射 ----------------------------------------------------------


def test_author():
    result = adapt_to_report_input(make_sample())
    assert result["author"] == "艾康的AI自留地"


def test_stats_mapping():
    result = adapt_to_report_input(make_sample())
    stats = result["stats"]
    assert stats["likes"] == "959"
    assert stats["collects"] == "1641"
    assert stats["comments"] == "15"
    assert stats["shares"] == "190"


def test_metadata_passthrough():
    result = adapt_to_report_input(make_sample())
    assert result["note_id"] == "6a116dd8000000003502a688"
    assert result["author_id"] == "65e17d09000000000500d97b"
    assert result["note_type"] == "图文"
    assert result["publish_time"] == "2026-05-23_20:01:14"


def test_backend_label():
    result = adapt_to_report_input(make_sample())
    assert result["backend"] == "xhs-downloader"


# ---- 标签：拆分 + 去重（保序）---------------------------------------------


def test_tags_is_list_and_contains_obsidian():
    result = adapt_to_report_input(make_sample())
    assert isinstance(result["tags"], list)
    assert "Obsidian" in result["tags"]


def test_tags_deduplicated():
    result = adapt_to_report_input(make_sample())
    tags = result["tags"]
    # 「Obsidian插件」在原始串里出现两次，去重后只剩一个
    assert tags.count("Obsidian插件") == 1
    assert len(tags) == len(set(tags))


# ---- 标题：空则 fallback 到描述首行 ----------------------------------------


def test_title_fallback_to_first_line_when_empty():
    result = adapt_to_report_input(make_sample())
    assert result["title"] == "Obsidian 用得越久，我反而越离不开这 3 个插件"


def test_title_uses_original_when_present():
    sample = make_sample()
    sample["作品标题"] = "我的原标题"
    result = adapt_to_report_input(sample)
    assert result["title"] == "我的原标题"


# ---- 正文：保留原描述 + 图文截断标注 --------------------------------------


def test_content_startswith_description():
    sample = make_sample()
    result = adapt_to_report_input(sample)
    assert result["content"].startswith(sample["作品描述"])


def test_content_has_truncation_marker_for_image_note():
    # 图文/图集：正文常在图片里，免登录模式拿不到 → 必须标注可能不完整
    result = adapt_to_report_input(make_sample())
    assert "[正文可能不完整" in result["content"]


# ---- 缺失字段：标准标注而非杜撰（P0）--------------------------------------


def test_comments_marker_with_count():
    result = adapt_to_report_input(make_sample())
    comments = result["comments"]
    assert comments.startswith("[评论数据不足")
    # 评论总数已知（15）→ 标注里必须带出来
    assert "15" in comments


def test_ocr_marker_with_image_count():
    result = adapt_to_report_input(make_sample())
    ocr = result["ocr_content"]
    assert ocr.startswith("[图片OCR不可用")
    # 17 张图片未 OCR → 数量必须出现在标注里
    assert "17" in ocr


# ---- URL：保留 xsec_token，缺省则重建 -------------------------------------


def test_url_preserves_xsec_token():
    sample = make_sample()
    url = (
        "https://www.xiaohongshu.com/explore/"
        "6a116dd8000000003502a688?xsec_token=ABC123&xsec_source=pc_feed"
    )
    result = adapt_to_report_input(sample, url=url)
    # token 是免风控的关键，绝不能被削掉
    assert result["url"] == url


def test_url_reconstructed_when_absent():
    result = adapt_to_report_input(make_sample(), url=None)
    assert "6a116dd8000000003502a688" in result["url"]


# ---- 升级建议：图文 + 有图 + 正文短 → 建议上 CDP 兜底 ----------------------


def test_needs_cdp_fallback_for_image_note():
    result = adapt_to_report_input(make_sample())
    assert result["needs_cdp_fallback"] is True


def test_image_urls_passthrough():
    result = adapt_to_report_input(make_sample())
    assert len(result["image_urls"]) == 17
