"""测试 generate_report.py 能消费扩量采样后的评论/弹幕数据。"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import generate_report as gr
from video_analysis_engine import Comment, Danmaku


def sample_comment(cid, text, likes=0, name='u'):
    return {
        'content': text,
        'like': likes,
        'user': {'name': name},
        # 额外字段可能来自 fetch_comments，但 _build_comments 不应依赖它们
        'rpid': cid,
    }


def test_build_comments_uses_merged_comments():
    """优先使用 merged_comments 而不是只取 hot_comments。"""
    step = {
        'status': 'ok',
        'parsed': True,
        'hot_comments': [sample_comment('h1', '热门评论1')],
        'recent_comments': [sample_comment('r1', '最新评论1')],
        'merged_comments': [
            sample_comment('h1', '热门评论1'),
            sample_comment('r1', '最新评论1'),
            sample_comment('m1', '去重后评论1', likes=10),
        ],
        'replies': [],
    }
    comments = gr._build_comments(step)
    texts = [c.text for c in comments]
    assert '去重后评论1' in texts
    assert len(comments) == 3


def test_build_comments_dedupes_across_sources():
    """merged、hot、recent 之间的重复评论不应重复。"""
    step = {
        'status': 'ok',
        'parsed': True,
        'hot_comments': [sample_comment('h1', 'same')],
        'recent_comments': [sample_comment('r1', 'same')],
        'merged_comments': [sample_comment('h1', 'same')],
        'replies': [],
    }
    comments = gr._build_comments(step)
    assert len(comments) == 1


def test_build_comments_includes_replies():
    """高赞回复组中的单条回复应被追加。"""
    step = {
        'status': 'ok',
        'parsed': True,
        'hot_comments': [sample_comment('h1', '热门')],
        'recent_comments': [],
        'merged_comments': [sample_comment('h1', '热门')],
        'replies': [
            {
                'rpid': 'root1',
                'replies': [
                    sample_comment('rep1', '回复1', likes=5),
                    sample_comment('rep2', '回复2', likes=2),
                ],
            }
        ],
    }
    comments = gr._build_comments(step)
    texts = [c.text for c in comments]
    assert '回复1' in texts
    assert '回复2' in texts


def test_build_comments_fallback_when_no_merged():
    """旧版输出没有 merged_comments 时，应 fallback 到 hot + recent。"""
    step = {
        'status': 'ok',
        'parsed': True,
        'hot_comments': [sample_comment('h1', '热门')],
        'recent_comments': [sample_comment('r1', '最新', likes=3)],
        'replies': [],
    }
    comments = gr._build_comments(step)
    texts = [c.text for c in comments]
    assert '热门' in texts
    assert '最新' in texts


def test_build_comments_empty():
    assert gr._build_comments(None) == []
    assert gr._build_comments({}) == []
    assert gr._build_comments({'status': 'failed'}) == []


def test_build_danmaku_uses_sampled_data():
    """fetch_danmaku_v2 采样后的 data 列表应被消费。"""
    step = {
        'status': 'ok',
        'parsed': True,
        'total': 5000,
        'sampled': 1000,
        'data': [
            {'text': '弹幕1', 'time_sec': 12.0},
            {'text': '弹幕2', 'time_sec': 45.5},
        ],
    }
    danmaku = gr._build_danmaku(step)
    assert len(danmaku) == 2
    assert isinstance(danmaku[0], Danmaku)
    assert danmaku[0].text == '弹幕1'
    assert danmaku[0].time == 12.0


def test_build_danmaku_invalid_time():
    step = {
        'status': 'ok',
        'parsed': True,
        'data': [{'text': 'bad', 'time_sec': 'not-a-number'}],
    }
    danmaku = gr._build_danmaku(step)
    assert len(danmaku) == 1
    assert danmaku[0].time == 0.0


def test_analysis_input_includes_more_data():
    """扩量的评论和弹幕应被正确收敛到 AnalysisInput。"""
    results = {
        'bvid': 'BV1test',
        'title': '测试视频',
        'comments': {
            'status': 'ok',
            'parsed': True,
            'merged_comments': [sample_comment('m1', '评论A', likes=10)],
            'replies': [],
        },
        'danmaku': {
            'status': 'ok',
            'parsed': True,
            'data': [{'text': '弹幕A', 'time_sec': 10.0}],
        },
        'subtitle': None,
        'cross_platform': None,
    }
    inp = gr.build_analysis_input(results, run_fact_check=False)
    assert len(inp.comments) == 1
    assert inp.comments[0].text == '评论A'
    assert len(inp.danmaku) == 1
    assert inp.danmaku[0].text == '弹幕A'


def test_analysis_input_preserves_cross_platform():
    results = {
        'bvid': 'BV1test',
        'comments': {'status': 'ok', 'parsed': True, 'merged_comments': [], 'replies': []},
        'danmaku': {'status': 'ok', 'parsed': True, 'data': []},
        'subtitle': None,
        'cross_platform': {'youtube_url': 'https://youtu.be/test', 'youtube_comments': {'status': 'ok', 'count': 10}},
    }
    inp = gr.build_analysis_input(results, run_fact_check=False)
    assert inp.cross_platform == results['cross_platform']
