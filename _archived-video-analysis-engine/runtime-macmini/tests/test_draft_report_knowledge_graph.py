# -*- coding: utf-8 -*-
"""DraftReport deterministic §6 knowledge graph slice."""

import re
import verify_publishable_report
from test_verify_publishable_report import _good_report
from video_analysis_engine import (
    _OBSIDIAN_MOC_FALLBACK,
    _concepts_in_text,
    _load_obsidian_moc,
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    analyze_video,
    assemble_draft_report_slice,
    build_draft_report,
    evaluate_draft_section_quality,
    render_debug_markdown,
    write_knowledge_graph_section,
)


def test_moc_path_is_explicit_and_does_not_guess_user_vault(monkeypatch):
    monkeypatch.delenv("VIDEO_ANALYSIS_MOC_PATH", raising=False)
    assert _load_obsidian_moc() == list(_OBSIDIAN_MOC_FALLBACK)


def test_moc_path_loads_configured_wikilinks(monkeypatch, tmp_path):
    moc = tmp_path / "moc.md"
    moc.write_text("[[ComfyUI]] and [[Model Context Protocol|MCP]]")
    monkeypatch.setenv("VIDEO_ANALYSIS_MOC_PATH", str(moc))
    assert _load_obsidian_moc() == ["ComfyUI", "Model Context Protocol", "MCP"]


def test_concept_extraction_rejects_unknown_lowercase_asr_fragments():
    concepts = _concepts_in_text("Usage code x get factories copy all")
    assert "copy all" in concepts
    assert "code x" not in concepts
    assert "get factories" not in concepts


def test_concept_extraction_rejects_sentence_starts_and_truncated_english_tokens():
    concepts = _concepts_in_text(
        "Hey, They, You, That, Not, Com, ComfyU, Comf, new, ComfyUI, MCP, API, Mac, Windows"
    )
    for noise in ("Hey", "They", "You", "That", "Not", "Com", "ComfyU", "Comf", "new", "MD", "11", "20", "yet"):
        assert noise not in _concepts_in_text(
            "Hey, They, You, That, Not, Com, ComfyU, Comf, new, MD, Claude 11 Codex 20 yet"
        )
    for concept in ("ComfyUI", "MCP", "API", "Mac", "Windows"):
        assert concept in concepts


def _kg_candidate(text, reason="knowledge_candidate", source_type="transcript", timestamp="0:10"):
    return {
        "section_id": "6",
        "source_type": source_type,
        "reason": reason,
        "timestamp": timestamp,
        "url": "https://www.bilibili.com/video/BVkg?t=10",
        "text": text,
    }


def _report_with_section6(candidates):
    return {
        "frontmatter": {"title": "KG test", "video_id": "BVkg"},
        "report_plan": {
            "can_generate_formal_report": True,
            "sections": [
                {"id": "6", "title": "知识图谱 (Knowledge Graph)", "purpose": "抽取概念、关系和应用", "quality_gate": ""},
            ],
        },
        "evidence_map": {"by_section": {"6": candidates}, "warnings": []},
        "evidence_gate": {"sources": {"transcript": {"available": True, "source": "h200-asr", "language": "zh", "segments": len(candidates), "chars": 200}}},
    }


def test_knowledge_graph_writer_outputs_concepts_relations_and_applications():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("虚拟偶像依赖人格资产，粉丝信任来自连续互动和稳定人设。"),
            _kg_candidate("人格资产影响商业化边界，过度商业化会削弱粉丝信任。"),
            _kg_candidate("可以把虚拟偶像治理转化为 Obsidian 知识卡片和行动清单。", reason="application_candidate"),
        ]
    })

    assert "### 核心概念" in body
    assert "### 关系链" in body
    assert "### 可落库/可行动项" in body
    assert "[[虚拟偶像]]" in body
    assert "[[人格资产]]" in body
    assert "[[粉丝信任]]" in body
    assert "[[虚拟偶像]] → [[人格资产]]" in body
    assert "Obsidian 知识卡片" in body
    assert "0:10" in body
    assert evaluate_draft_section_quality("6", body).overall_passed is True
    assert "_骨架占位" not in body


def test_knowledge_graph_deduplicates_reverse_pair_relations():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("AI connects to ComfyUI."),
            _kg_candidate("ComfyUI connects to AI."),
        ]
    })
    relation_lines = [line for line in body.splitlines() if "AI" in line and "ComfyUI" in line and "→" in line]
    assert len(relation_lines) == 1


def test_knowledge_graph_extracts_explicit_action_from_knowledge_candidate():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate(
                "从最小配置开始。如果某个操作已经重复三四次，那就应该制作一个扩展来自动化。"
            )
        ]
    })
    assert "应该制作一个扩展来自动化" in body
    assert "_暂无可抽取行动项_" not in body


def test_knowledge_graph_does_not_treat_descriptive_can_need_sentences_as_actions():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate(
                "一个完全自定义的扩展真的只需要这些？我可以用 copy 抓取消息。"
                "因为扩展可以在执行过程中发送消息。"
            )
        ]
    })
    assert "_暂无可抽取行动项_" in body


def test_knowledge_graph_writer_filters_noise_and_deduplicates_concepts():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("虚拟偶像和虚拟偶像重复出现，但应该只输出一次概念。"),
            _kg_candidate("这个评论不错", source_type="comments"),
            _kg_candidate("高光不是知识图谱输入", reason="quote_candidate"),
            _kg_candidate("", reason="knowledge_candidate"),
        ]
    })

    assert body.count("[[虚拟偶像]]") <= 3  # concept list + relation at most
    assert "这个评论不错" not in body
    assert "高光不是知识图谱输入" not in body


def test_knowledge_graph_writer_filters_sentence_fragments_but_keeps_technical_entities():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("几周前我发了一期关于 Pi 的视频，SDK 用于构建扩展。"),
        ]
    })

    assert "- Pi" in body
    assert "- SDK" in body
    assert "几周前我发了一期关于" not in body
    assert "可落库/可行动项" in body
    assert "几周前我发了一期关于 Pi 的视频" not in body


def test_knowledge_graph_rejects_asr_letter_fragments_and_short_noise():
    body = write_knowledge_graph_section({
        "evidence": [
            _kg_candidate("Pi 的 SDK 支持 copy B T C A 与 Py 这类转录噪音。"),
        ]
    })

    assert "- Pi" in body
    assert "- SDK" in body
    assert "B T C A" not in body
    assert "\n- B\n" not in body
    assert "\n- T\n" not in body
    assert "\n- C\n" not in body
    assert "\n- A\n" not in body
    assert "- Py" not in body


def test_knowledge_graph_empty_evidence_is_non_publishable_placeholder():
    body = write_knowledge_graph_section({"evidence": []})

    assert "_骨架占位" in body
    md = _good_report().replace("- [[虚拟偶像]] → [[人格资产]] → [[信任机制]]", body)
    results, passed = verify_publishable_report.evaluate(md)
    assert passed is False
    assert results["P0_NO_SKELETON"]["pass"] is False


def test_assemble_draft_report_slice_writes_section6_only_when_requested():
    report = _report_with_section6([
        _kg_candidate("虚拟偶像依赖人格资产，粉丝信任来自连续互动。"),
        _kg_candidate("人格资产影响商业化边界，过度商业化会削弱粉丝信任。"),
    ])

    draft = assemble_draft_report_slice(report, section_ids=("6",))

    assert draft.publishable is False
    assert set(draft.draft_sections) == {"6"}
    assert "### 核心概念" in draft.draft_sections["6"]
    assert "[[虚拟偶像]]" in draft.draft_sections["6"]


# ─── Slice B: metadata-backed §6 tests ───────────────────────────────────────

_REAL_TITLE = '央视独家画面！90秒多视角看长征十号乙运载火箭发射回收'
_REAL_DESC = '长征十号乙运载火箭，发射回收。'


def _sparse_inp(title='', description=''):
    return AnalysisInput(
        video_id='BVtest01',
        platform='bilibili',
        title=title,
        description=description,
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=0.0, text='01准备就绪', end=5.0),
                TranscriptSegment(start=5.0, text='T减10秒', end=10.0),
                TranscriptSegment(start=15.0, text='点火', end=20.0),
            ],
            language='zh',
            source='asr',
        ),
    )


def test_sparse_transcript_with_metadata_title_yields_nons_skeleton_kg_with_required_concepts():
    """Slice B test 1: real sparse case → non-skeleton §6 with both verbatim concepts."""
    inp = _sparse_inp(title=_REAL_TITLE, description=_REAL_DESC)
    report = analyze_video(inp)
    cands = report['evidence_map']['by_section'].get('6', [])
    body = write_knowledge_graph_section({'evidence': cands})
    assert '长征十号乙运载火箭' in body
    assert '发射回收' in body
    assert '_骨架占位' not in body


def test_metadata_concepts_are_verbatim_substrings_of_title_or_description():
    """Slice B test 2: every metadata-derived concept is a literal substring of title/description."""
    inp = _sparse_inp(title=_REAL_TITLE, description=_REAL_DESC)
    report = analyze_video(inp)
    cands = report['evidence_map']['by_section'].get('6', [])
    meta_cands = [c for c in cands if c.get('source_type') == 'metadata']
    assert meta_cands, 'Expected metadata candidates in §6'
    body = write_knowledge_graph_section({'evidence': meta_cands})
    source_text = _REAL_TITLE + _REAL_DESC
    # All wikilinks must be verbatim in source
    for link in re.findall(r'\[\[([^\]]+)\]\]', body):
        assert link in source_text, f'[[{link}]] is not verbatim in title or description'
    # Plain concept bullets (not relation lines with →, not placeholder lines)
    for plain in re.findall(r'^- ([^\[_].+)$', body, re.MULTILINE):
        plain = plain.strip()
        if '→' in plain or plain.startswith('_'):
            continue
        assert plain in source_text, f'plain concept "{plain}" is not verbatim in title or description'


def test_metadata_candidates_produce_no_action_items_and_no_causal_relations():
    """Slice B test 3: metadata candidates never produce action items; relations are co-occurrence only."""
    # Title with verbs that would trigger transcript action extraction
    title = '长征十号乙运载火箭应该建议制作自动化发射系统'
    cand = {
        'section_id': '6', 'source_type': 'metadata',
        'reason': 'metadata_title_candidate',
        'timestamp': '', 'url': '',
        'text': title,
    }
    body = write_knowledge_graph_section({'evidence': [cand]})
    assert '- _暂无可抽取行动项_' in body
    # relation prose must not use causal language about the content
    assert '导致' not in body
    assert '因此' not in body or '不等同于' in body  # reasoning_frame is OK to keep


def test_empty_metadata_and_sparse_transcript_remains_skeleton():
    """Slice B test 4: empty title/description + sparse transcript → skeleton, P0_NO_SKELETON fails."""
    inp = _sparse_inp(title='', description='')
    report = analyze_video(inp)
    cands = report['evidence_map']['by_section'].get('6', [])
    body = write_knowledge_graph_section({'evidence': cands})
    assert '_骨架占位' in body
    md = _good_report().replace('- [[虚拟偶像]] → [[人格资产]] → [[信任机制]]', body)
    results, passed = verify_publishable_report.evaluate(md)
    assert results['P0_NO_SKELETON']['pass'] is False


def test_boilerplate_only_metadata_produces_no_concept_and_remains_skeleton():
    """Slice B test 5: boilerplate/duration/verb wrappers alone → no concept, skeleton."""
    for boilerplate in ['央视独家画面', '90秒', '多视角看']:
        cand = {
            'section_id': '6', 'source_type': 'metadata',
            'reason': 'metadata_title_candidate',
            'timestamp': '', 'url': '',
            'text': boilerplate,
        }
        body = write_knowledge_graph_section({'evidence': [cand]})
        assert '_骨架占位' in body, f'Expected skeleton for boilerplate-only: "{boilerplate}"'


def test_only_canonical_title_description_feed_section6_not_author_duration_or_counts():
    """Slice B test 6: author, duration, counts do not appear in §6 evidence."""
    inp = AnalysisInput(
        video_id='BVtest02', platform='bilibili',
        title='', description='',
        author='航天频道', duration=90,
        transcript=Transcript(
            segments=[TranscriptSegment(start=0.0, text='准备就绪', end=5.0)],
            language='zh', source='asr',
        ),
    )
    report = analyze_video(inp)
    cands = report['evidence_map']['by_section'].get('6', [])
    meta_cands = [c for c in cands if c.get('source_type') == 'metadata']
    # title and description are both empty → no metadata candidates
    assert len(meta_cands) == 0
    # author, duration do not appear in any §6 candidate text
    for cand in cands:
        text = cand.get('text') or ''
        assert '航天频道' not in text


def test_sparse_transcript_does_not_falsely_claim_transcript_basis_when_metadata_contributes_all():
    """Review-1 regression: evidence frame must say title/description when sparse transcript
    contributes zero concepts and metadata provides all KG content."""
    inp = _sparse_inp(title=_REAL_TITLE, description=_REAL_DESC)
    report = analyze_video(inp)
    cands = report['evidence_map']['by_section'].get('6', [])
    body = write_knowledge_graph_section({'evidence': cands})
    # Must be non-skeleton
    assert '_骨架占位' not in body
    # Evidence frame must reference title/description, not transcript-only basis
    assert '标题' in body or '描述' in body
    assert '本节基于当前转录中的知识与应用证据' not in body


def test_metadata_extraction_strips_action_prefix_and_rejects_arbitrary_promo_phrase():
    prefixed = {
        'section_id': '6', 'source_type': 'metadata',
        'reason': 'metadata_title_candidate', 'timestamp': '', 'url': '',
        'text': '成功发射长征十号乙运载火箭',
    }
    body = write_knowledge_graph_section({'evidence': [prefixed]})
    assert '- 长征十号乙运载火箭' in body
    assert '- 成功发射长征十号乙运载火箭' not in body

    promo = dict(prefixed, text='重磅来袭精彩呈现')
    assert '_骨架占位' in write_knowledge_graph_section({'evidence': [promo]})


def test_final_renderer_keeps_metadata_after_more_than_five_transcript_candidates():
    inp = AnalysisInput(
        video_id='douyin-many-segments', platform='douyin',
        title=_REAL_TITLE, description=_REAL_DESC,
        transcript=Transcript(
            segments=[
                TranscriptSegment(start=float(i), end=float(i + 1), text=f'{i}号遥测信号正常')
                for i in range(8)
            ],
            language='zh', source='h200-asr-browser-media',
        ),
    )
    report = analyze_video(inp)
    assert len([
        c for c in report['evidence_map']['by_section']['6']
        if c.get('source_type') == 'transcript'
    ]) == 8
    markdown = render_debug_markdown(build_draft_report(report))
    section6 = markdown.split('## 6.', 1)[1].split('## 7.', 1)[0]
    assert '长征十号乙运载火箭' in section6
    assert '发射回收' in section6
    assert '_骨架占位' not in section6


def test_provenance_ignores_metadata_concept_removed_by_max_items():
    transcript = _kg_candidate(
        'ComfyUI MCP API Mac Windows Codex GitHub TypeScript OpenAI',
        source_type='transcript',
    )
    metadata = _kg_candidate(
        '发射回收', reason='metadata_title_candidate',
        source_type='metadata', timestamp='',
    )
    body = write_knowledge_graph_section({'evidence': [transcript, metadata]}, max_items=8)
    assert '发射回收' not in body
    assert body.startswith('本节基于转录')
    assert '标题和描述' not in body
