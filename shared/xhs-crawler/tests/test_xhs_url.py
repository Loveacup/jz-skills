"""URL 交接给 XHS-Downloader 后端前的规范化。

核心坑（见 references/xhs-downloader-integration.md）：
裸 explore/<id> 缺 xsec_token 会触发风控失败；带 token 的链接 / 短链才稳。
所以 prepare_url 必须**原样保留 token**，短链原样透传（由 XHS-Downloader 自己解析），
绝不把链接削成裸 id。纯函数、不联网。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from parse_xhs_url import prepare_url  # noqa: E402


def test_explore_with_token_preserved():
    url = (
        "https://www.xiaohongshu.com/explore/"
        "6a116dd8000000003502a688?xsec_token=ABC123&xsec_source=pc_feed"
    )
    # token 是免风控关键，必须一字不差保留
    assert prepare_url(url) == url


def test_discovery_with_token_preserved():
    url = (
        "https://www.xiaohongshu.com/discovery/item/"
        "6a116dd8000000003502a688?xsec_token=Xy_9-Z"
    )
    assert prepare_url(url) == url


def test_short_link_passed_through():
    # 短链不在这里解析（交给 XHS-Downloader），原样返回
    url = "https://xhslink.com/o/6ftw6lhxIOy"
    assert prepare_url(url) == url


def test_short_link_http_passed_through():
    url = "http://xhslink.com/a/abcDEF123"
    assert prepare_url(url) == url


def test_user_profile_note_link_preserved():
    url = (
        "https://www.xiaohongshu.com/user/profile/"
        "65e17d09000000000500d97b/6a116dd8000000003502a688?xsec_token=Q1"
    )
    assert prepare_url(url) == url


def test_bare_explore_without_token_kept_as_is():
    # 没 token 也是合法形态，原样返回（不补、不削）
    url = "https://www.xiaohongshu.com/explore/6a116dd8000000003502a688"
    assert prepare_url(url) == url


def test_url_extracted_from_surrounding_text():
    raw = (
        "看看这个 https://www.xiaohongshu.com/explore/"
        "6a116dd8000000003502a688?xsec_token=ABC123 真不错"
    )
    out = prepare_url(raw)
    # token 仍在，且没把后面的「真不错」吞进去
    assert out == (
        "https://www.xiaohongshu.com/explore/"
        "6a116dd8000000003502a688?xsec_token=ABC123"
    )


def test_url_with_trailing_cjk_punctuation_stripped():
    raw = (
        "链接：https://xhslink.com/o/6ftw6lhxIOy。"
    )
    assert prepare_url(raw) == "https://xhslink.com/o/6ftw6lhxIOy"


def test_bare_note_id_reconstructed_to_explore():
    out = prepare_url("6a116dd8000000003502a688")
    assert out == "https://www.xiaohongshu.com/explore/6a116dd8000000003502a688"


def test_invalid_url_returns_none():
    assert prepare_url("https://www.google.com") is None


def test_garbage_returns_none():
    assert prepare_url("just some random text") is None


def test_empty_returns_none():
    assert prepare_url("") is None
    assert prepare_url(None) is None
