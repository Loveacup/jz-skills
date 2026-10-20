#!/usr/bin/env python3
"""
测试跨平台证据注入（YouTube 评论）

验证场景：
1. cross_platform.youtube_comments 存在且成功 → 生成 YouTube evidence candidates
2. cross_platform 为 None → 不生成 YouTube evidence
3. youtube_comments 抓取失败（status='failed'）→ 不生成 YouTube evidence，不阻塞主流程
4. YouTube 评论分配到 §3/§4/§7
5. source_type='youtube' 正确标记
"""

import pytest
from video_analysis_engine import (
    AnalysisInput,
    build_report_plan,
    build_evidence_map,
    Transcript,
    TranscriptSegment,
)


def test_youtube_comments_generate_evidence_candidates():
    """有 YouTube 评论时，应生成 source='youtube' 的 evidence candidates"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=0.0, text='测试字幕'),
            ],
            source='official'
        ),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'youtube_comments': {
                'status': 'ok',
                'parsed': True,
                'comments': [
                    {'text': 'Great video!', 'author': 'User1', 'likes': 100, 'platform': 'youtube'},
                    {'text': 'Very informative', 'author': 'User2', 'likes': 50, 'platform': 'youtube'},
                ],
                'count': 2,
                'source': 'youtube-comment-downloader',
            }
        }
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    # 验证 §3/§4/§7 应包含 YouTube 证据
    for section_id in ['3', '4', '7']:
        candidates = evidence_map.by_section.get(section_id, [])
        youtube_candidates = [c for c in candidates if c.source_type == 'youtube']

        assert len(youtube_candidates) == 2, f"§{section_id} 应有 2 个 YouTube 评论候选"
        assert youtube_candidates[0].text == 'Great video!'
        assert youtube_candidates[0].url == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        assert youtube_candidates[0].reason == 'cross_platform_sentiment'
        assert 'YouTube评论' in youtube_candidates[0].context


def test_no_cross_platform_no_youtube_evidence():
    """无 cross_platform 数据时，不生成 YouTube evidence"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=0.0, text='测试字幕'),
            ],
            source='official'
        ),
        cross_platform=None
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    # §3/§4/§7 应只包含 transcript 候选，无 YouTube 候选
    for section_id in ['3', '4', '7']:
        candidates = evidence_map.by_section.get(section_id, [])
        youtube_candidates = [c for c in candidates if c.source_type == 'youtube']
        assert len(youtube_candidates) == 0, f"§{section_id} 不应有 YouTube 候选"


def test_youtube_comments_fetch_failed_no_evidence():
    """YouTube 评论抓取失败时，不生成证据，不阻塞主流程"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=0.0, text='测试字幕'),
            ],
            source='official'
        ),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'youtube_comments': {
                'status': 'failed',
                'returncode': 1,
                'error': 'Network timeout',
            }
        }
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    # 验证主流程未被阻塞
    assert plan.can_generate_formal_report  # 有字幕，应允许生成报告

    # §3/§4/§7 不应有 YouTube 候选
    for section_id in ['3', '4', '7']:
        candidates = evidence_map.by_section.get(section_id, [])
        youtube_candidates = [c for c in candidates if c.source_type == 'youtube']
        assert len(youtube_candidates) == 0, f"§{section_id} 不应有 YouTube 候选（抓取失败）"


def test_youtube_comments_empty_list_no_evidence():
    """YouTube 评论列表为空时，不生成证据"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=0.0, text='测试字幕'),
            ],
            source='official'
        ),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'youtube_comments': {
                'status': 'ok',
                'parsed': True,
                'comments': [],  # 空列表
                'count': 0,
            }
        }
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    # §3/§4/§7 不应有 YouTube 候选
    for section_id in ['3', '4', '7']:
        candidates = evidence_map.by_section.get(section_id, [])
        youtube_candidates = [c for c in candidates if c.source_type == 'youtube']
        assert len(youtube_candidates) == 0, f"§{section_id} 不应有 YouTube 候选（评论列表为空）"


def test_youtube_comments_merged_with_transcript_evidence():
    """YouTube 评论应与字幕证据合并，不覆盖"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=0.0, text='字幕片段1'),
                TranscriptSegment(start=10.0, text='字幕片段2'),
            ],
            source='official'
        ),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=test',
            'youtube_comments': {
                'status': 'ok',
                'parsed': True,
                'comments': [
                    {'text': 'YouTube comment', 'author': 'User1', 'likes': 10, 'platform': 'youtube'},
                ],
                'count': 1,
            }
        }
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    # §3 应同时包含 transcript 和 YouTube 候选
    candidates_3 = evidence_map.by_section.get('3', [])
    transcript_candidates = [c for c in candidates_3 if c.source_type == 'transcript']
    youtube_candidates = [c for c in candidates_3 if c.source_type == 'youtube']

    assert len(transcript_candidates) == 2, "§3 应有 2 个字幕候选"
    assert len(youtube_candidates) == 1, "§3 应有 1 个 YouTube 候选"
    assert len(candidates_3) == 3, "§3 总共应有 3 个候选（2 字幕 + 1 YouTube）"


def test_youtube_comments_score_with_likes():
    """YouTube 评论的 score 应包含点赞数加权"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[TranscriptSegment(start=0.0, text='test')],
            source='official'
        ),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=test',
            'youtube_comments': {
                'status': 'ok',
                'parsed': True,
                'comments': [
                    {'text': 'High likes comment', 'author': 'User1', 'likes': 1000, 'platform': 'youtube'},
                    {'text': 'Low likes comment', 'author': 'User2', 'likes': 10, 'platform': 'youtube'},
                ],
                'count': 2,
            }
        }
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    candidates_3 = evidence_map.by_section.get('3', [])
    youtube_candidates = [c for c in candidates_3 if c.source_type == 'youtube']

    # 高点赞评论应有更高的 score
    high_likes_cand = [c for c in youtube_candidates if 'High likes' in c.text][0]
    low_likes_cand = [c for c in youtube_candidates if 'Low likes' in c.text][0]

    assert high_likes_cand.score > low_likes_cand.score, "高点赞评论应有更高 score"


def test_youtube_comments_score_accepts_string_likes_from_fetcher():
    """youtube-comment-downloader returns vote counts as strings in real payloads."""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(segments=[TranscriptSegment(start=0.0, text='test')], source='official'),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=test',
            'youtube_comments': {
                'status': 'ok',
                'comments': [
                    {'text': 'String high likes', 'author': 'User1', 'likes': '53', 'platform': 'youtube'},
                    {'text': 'Missing likes', 'author': 'User2', 'likes': 'not-a-number', 'platform': 'youtube'},
                ],
            },
        },
    )

    evidence_map = build_evidence_map(inp, build_report_plan(inp))
    youtube_candidates = [c for c in evidence_map.by_section['3'] if c.source_type == 'youtube']
    high = next(c for c in youtube_candidates if c.text == 'String high likes')
    missing = next(c for c in youtube_candidates if c.text == 'Missing likes')

    assert high.score > missing.score


def test_youtube_comments_only_in_section_3_4_7():
    """YouTube 评论应只分配给 §3/§4/§7，不出现在 §1/§2 等"""
    inp = AnalysisInput(
        video_id='BV1test',
        title='测试视频',
        platform='bilibili',
        transcript=Transcript(
            segments=[TranscriptSegment(start=0.0, text='test')],
            source='official'
        ),
        cross_platform={
            'youtube_url': 'https://www.youtube.com/watch?v=test',
            'youtube_comments': {
                'status': 'ok',
                'parsed': True,
                'comments': [
                    {'text': 'Test comment', 'author': 'User1', 'likes': 10, 'platform': 'youtube'},
                ],
                'count': 1,
            }
        }
    )

    plan = build_report_plan(inp)
    evidence_map = build_evidence_map(inp, plan)

    # §1, §2, §5 不应有 YouTube 候选
    for section_id in ['1', '2', '5']:
        candidates = evidence_map.by_section.get(section_id, [])
        if candidates:
            youtube_candidates = [c for c in candidates if c.source_type == 'youtube']
            assert len(youtube_candidates) == 0, f"§{section_id} 不应有 YouTube 候选"
