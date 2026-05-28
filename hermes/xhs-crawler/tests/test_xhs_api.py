import sys
sys.path.insert(0, "scripts")
from xhs_api import XHSAPI, base36encode

def test_base36encode_zero():
    assert base36encode(0) == "0"

def test_base36encode_small():
    assert base36encode(35) == "z"
    assert base36encode(36) == "10"

def test_base36encode_large():
    result = base36encode(123456789)
    assert isinstance(result, str)
    assert len(result) > 0

def test_xhsapi_init():
    """XHSAPI can be instantiated with cookies"""
    api = XHSAPI(cookies={"a1": "test_a1", "web_session": "test_session"})
    assert api.cookies == {"a1": "test_a1", "web_session": "test_session"}

def test_xhsapi_init_no_cookies():
    """XHSAPI defaults to empty cookies"""
    api = XHSAPI()
    assert api.cookies == {}

def test_parse_note_url_discovery():
    """parse_note_url extracts from discovery URLs"""
    api = XHSAPI()
    # Mock session.get to avoid network call - just test regex on direct URL
    note_id = api.parse_note_url("https://www.xiaohongshu.com/discovery/item/6789abcdef0123456789abcd")
    assert note_id == "6789abcdef0123456789abcd"

def test_parse_note_url_explore():
    """parse_note_url extracts from explore URLs"""
    api = XHSAPI()
    note_id = api.parse_note_url("https://www.xiaohongshu.com/explore/6789abcdef0123456789abcd")
    assert note_id == "6789abcdef0123456789abcd"

def test_parse_note_url_invalid():
    """parse_note_url returns None for invalid URLs"""
    api = XHSAPI()
    assert api.parse_note_url("https://www.google.com") is None

def test_search_notes_no_xhshow():
    """search_notes returns error when xhshow not available"""
    api = XHSAPI()
    api.client = None  # Force no xhshow
    # Temporarily set HAS_XHSHOW to False
    import xhs_api
    original = xhs_api.HAS_XHSHOW
    xhs_api.HAS_XHSHOW = False
    result = api.search_notes("test keyword")
    xhs_api.HAS_XHSHOW = original
    assert "error" in result

def test_get_search_id():
    """_get_search_id returns a non-empty string"""
    api = XHSAPI()
    search_id = api._get_search_id()
    assert isinstance(search_id, str)
    assert len(search_id) > 0

def test_all_api_methods_exist():
    """Verify all required API methods exist on XHSAPI"""
    api = XHSAPI()
    assert hasattr(api, 'search_notes')
    assert hasattr(api, 'get_note_detail')
    assert hasattr(api, 'get_note_comments')
    assert hasattr(api, 'get_creator_info')
    assert hasattr(api, 'get_creator_notes')
    assert callable(api.search_notes)
    assert callable(api.get_note_detail)
    assert callable(api.get_note_comments)
    assert callable(api.get_creator_info)
    assert callable(api.get_creator_notes)
