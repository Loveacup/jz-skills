import sys
sys.path.insert(0, ".")
from xhshow import Xhshow

def test_xhshow_instantiation():
    """Xhshow can be instantiated"""
    client = Xhshow()
    assert client is not None

def test_sign_xs_get():
    """sign_xs generates a signature for GET"""
    client = Xhshow()
    sig = client.sign_xs("GET", "/api/sns/web/v1/user_posted", "test_a1_value_1234567890123456")
    assert isinstance(sig, str)
    assert len(sig) > 20

def test_sign_xs_post():
    """sign_xs generates a signature for POST"""
    client = Xhshow()
    sig = client.sign_xs("POST", "/api/sns/web/v1/feed", "test_a1_value_1234567890123456", payload={"source_note_id": "abc123"})
    assert isinstance(sig, str)
    assert len(sig) > 20

def test_sign_headers_get():
    """sign_headers_get returns all required header keys"""
    client = Xhshow()
    cookies = {"a1": "test_a1_value_1234567890123456", "web_session": "dummy"}
    headers = client.sign_headers_get(
        uri="/api/sns/web/v1/user_posted",
        cookies=cookies,
        params={"num": "30", "user_id": "testuser"}
    )
    assert "x-s" in headers
    assert "x-s-common" in headers
    assert "x-t" in headers
    assert "x-b3-traceid" in headers
    assert "x-xray-traceid" in headers

def test_sign_headers_post():
    """sign_headers_post returns all required header keys"""
    client = Xhshow()
    cookies = {"a1": "test_a1_value_1234567890123456", "web_session": "dummy"}
    headers = client.sign_headers_post(
        uri="/api/sns/web/v1/feed",
        cookies=cookies,
        payload={"source_note_id": "test123"}
    )
    assert "x-s" in headers
    assert "x-s-common" in headers
    assert "x-t" in headers

def test_get_b3_trace_id():
    """get_b3_trace_id returns 16-char hex string"""
    client = Xhshow()
    trace_id = client.get_b3_trace_id()
    assert isinstance(trace_id, str)
    assert len(trace_id) == 16
    # Should be valid hex
    int(trace_id, 16)

def test_get_xray_trace_id():
    """get_xray_trace_id returns 32-char hex string"""
    client = Xhshow()
    trace_id = client.get_xray_trace_id()
    assert isinstance(trace_id, str)
    assert len(trace_id) == 32

def test_get_x_t():
    """get_x_t returns millisecond timestamp"""
    client = Xhshow()
    x_t = client.get_x_t()
    assert isinstance(x_t, int)
    assert x_t > 1700000000000  # After 2023

def test_sign_xs_different_for_different_uris():
    """Different URIs produce different signatures"""
    client = Xhshow()
    a1 = "test_a1_value_1234567890123456"
    ts = 1700000000.0
    sig1 = client.sign_xs("GET", "/api/sns/web/v1/user_posted", a1, timestamp=ts)
    sig2 = client.sign_xs("GET", "/api/sns/web/v1/feed", a1, timestamp=ts)
    assert sig1 != sig2

def test_sign_headers_missing_a1():
    """sign_headers raises ValueError when a1 is missing"""
    client = Xhshow()
    try:
        client.sign_headers("GET", "/api/test", cookies={"web_session": "dummy"})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "a1" in str(e).lower()
