"""联网金丝雀：用真实 runner 打已知好笔记，验证整条链路还活着。

默认跳过；仅当 XHS_LIVE_TEST=1 且后端已 bootstrap 时运行。
这是「后端是否还工作」的探针，不进 TDD 红绿循环——手动跑。

已知好样本（references/xhs-downloader-integration.md，2026-06-10 实测）：
    短链 http://xhslink.com/o/6ftw6lhxIOy → 作品ID 6a116dd8000000003502a688
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from xhs_backend import fetch_note  # noqa: E402
from xhs_bootstrap import doctor  # noqa: E402

_LIVE = os.environ.get("XHS_LIVE_TEST") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _LIVE, reason="设 XHS_LIVE_TEST=1 才跑联网金丝雀"),
]

KNOWN_SHORT_LINK = "http://xhslink.com/o/6ftw6lhxIOy"
EXPECTED_NOTE_ID = "6a116dd8000000003502a688"


def test_backend_ready():
    assert doctor()["ready"], "后端未就绪，先跑：python scripts/xhs_bootstrap.py"


def test_live_extract_known_note():
    out = fetch_note(KNOWN_SHORT_LINK, timeout=90)
    assert out["status"] == "ok", out
    assert out["report_input"]["note_id"] == EXPECTED_NOTE_ID
    assert out["report_input"]["author"]
    # 免登录模式：评论/OCR 必须是标注而非杜撰
    assert out["report_input"]["comments"].startswith("[评论数据不足")
