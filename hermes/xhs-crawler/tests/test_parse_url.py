import sys
sys.path.insert(0, "scripts")
from parse_xhs_url import extract_note_id

def test_direct_note_id():
    """24-char hex string returns as-is"""
    assert extract_note_id("6789abcdef0123456789abcd") == "6789abcdef0123456789abcd"

def test_discovery_url():
    """Standard discovery URL"""
    assert extract_note_id("https://www.xiaohongshu.com/discovery/item/6789abcdef0123456789abcd") == "6789abcdef0123456789abcd"

def test_explore_url():
    """Explore URL format"""
    assert extract_note_id("https://www.xiaohongshu.com/explore/6789abcdef0123456789abcd") == "6789abcdef0123456789abcd"

def test_explore_url_with_params():
    """Explore URL with query params"""
    assert extract_note_id("https://www.xiaohongshu.com/explore/6789abcdef0123456789abcd?xsec_token=abc") == "6789abcdef0123456789abcd"

def test_note_id_param():
    """noteId query parameter format"""
    assert extract_note_id("https://www.xiaohongshu.com/search_result?source=note&noteId=6789abcdef0123456789abcd") == "6789abcdef0123456789abcd"

def test_invalid_url():
    """Invalid URL returns None"""
    assert extract_note_id("https://www.google.com") is None

def test_invalid_short_hex():
    """Too-short hex string is not a valid note ID"""
    assert extract_note_id("abcdef123456") is None
