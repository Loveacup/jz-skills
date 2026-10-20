# -*- coding: utf-8 -*-
"""§5「高光时刻」纯确定性 writer（P2-C2）。

约束：
  - write_highlights_section(section_context) 只读 section_context['evidence']，
    过滤 source_type=='transcript' 且 reason=='quote_candidate' 且 text 非空。
  - 每条金句渲染为独立 blockquote 组（组间空行），格式 `> "text" — [ts](url)`。
  - 无候选时只给 `### 高光时刻` + 占位行，不输出任何 blockquote。
  - render_markdown 经由 _emit_section_skeleton 自动调用本 writer；
    verify_report.measure_g5 能正确数出引用块组数量。
"""

import verify_report
from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    Transcript,
    TranscriptSegment,
    analyze_video,
    render_markdown,
    write_highlights_section,
)


def _quote_cand(text, timestamp, url, **over):
    cand = {
        'source_type': 'transcript',
        'section_id': '5',
        'timestamp': timestamp,
        'url': url,
        'text': text,
        'reason': 'quote_candidate',
    }
    cand.update(over)
    return cand


def _input_with_transcript():
    return AnalysisInput(
        video_id="BV1xx411c7mD",
        title="AI 应用能融下一轮吗？",
        author="马克汤",
        duration=754,
        platform="bilibili",
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, "开场：AI 应用融资和 ARR 的现状。", end=20.0),
                TranscriptSegment(150.0, "中段：wrapper 经济和护城河。", end=180.0),
                TranscriptSegment(305.7, "收尾：下一轮估值逻辑。", end=330.0),
            ],
            language="zh",
            source="mlx-whisper|json_path=/d/x.json|txt_path=/d/x.txt",
        ),
        comments=[Comment("讲得太好了", likes=120, author="观众A", platform="bilibili")],
        danmaku=[Danmaku("前排", 1.2)],
    )


# ---- 1. transcript 金句渲染为 blockquote，含 ### 高光时刻 标题 ----
def test_renders_quote_blockquotes():
    ctx = {
        'evidence': [
            _quote_cand("一切估值都建立在叙事之上。", "2:30",
                        "https://www.bilibili.com/video/BV1?t=150"),
            _quote_cand("护城河是结果不是前提。", "5:05",
                        "https://www.bilibili.com/video/BV1?t=305"),
        ],
    }
    body = write_highlights_section(ctx)
    assert body.startswith('### 高光时刻')
    assert '> "一切估值都建立在叙事之上。" — [2:30](https://www.bilibili.com/video/BV1?t=150)' in body
    assert '> "护城河是结果不是前提。" — [5:05](https://www.bilibili.com/video/BV1?t=305)' in body
    # 两条 blockquote 间有空行分隔（独立组）
    assert body.count('\n>') >= 1


# ---- 2. 过滤非 transcript / 非 quote_candidate 证据 ----
def test_filters_non_transcript_and_non_quote():
    ctx = {
        'evidence': [
            _quote_cand("保留：合格金句。", "0:10", "https://x?t=10"),
            _quote_cand("剔除：弹幕。", "0:05", "https://x?t=5", source_type='danmaku'),
            _quote_cand("剔除：别的用途。", "0:08", "https://x?t=8",
                        reason='logic_candidate'),
            _quote_cand("   ", "0:09", "https://x?t=9"),  # 空白 text 剔除
        ],
    }
    body = write_highlights_section(ctx)
    assert '保留：合格金句。' in body
    assert '剔除：弹幕。' not in body
    assert '剔除：别的用途。' not in body
    # 仅一条金句 → 仅一个 blockquote 行
    assert body.count('\n> ') == 1


# ---- 3. H200 长 chunk 先切句再去噪，不因整段超长/API 而全部丢弃 ----
def test_long_chunk_is_split_before_noise_filtering():
    long_chunk = (
        "这一段包含 API 一词，但它只是上下文说明。"
        "真正的结论是：代码智能体的扩展边界取决于稳定的核心与明确的接口。"
        "因此，先用最小工作流验证再逐步增加能力，比一次性堆叠工具更可靠。"
    )
    body = write_highlights_section({
        'evidence': [_quote_cand(long_chunk, "1:20", "https://x?t=80")],
    })

    assert '_骨架占位' not in body
    assert '> "真正的结论是：代码智能体的扩展边界取决于稳定的核心与明确的接口。"' in body


# ---- 4. 无候选 → 占位，无 blockquote 行 ----
def test_empty_evidence_yields_placeholder():
    assert write_highlights_section({'evidence': []}) == (
        '### 高光时刻\n\n_骨架占位：暂无原文金句。_\n'
    )
    # 全被过滤的情况同样给占位
    only_bad = {'evidence': [_quote_cand("弹幕", "0:01", "https://x?t=1",
                                         source_type='danmaku')]}
    out = write_highlights_section(only_bad)
    assert out == '### 高光时刻\n\n_骨架占位：暂无原文金句。_\n'
    assert '>' not in out


# ---- 4. measure_g5 数出正确的引用块组数 ----
def test_measure_g5_counts_blockquote_groups():
    report = analyze_video(_input_with_transcript())
    md = render_markdown(report)
    lines = md.split('\n')
    # 3 段 transcript → §5 有 3 条 quote_candidate → 3 个引用块组
    assert verify_report.measure_g5(lines) == 3
