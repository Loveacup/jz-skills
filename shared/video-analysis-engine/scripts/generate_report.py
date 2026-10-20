#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py — fetch_all 结果 → 分析引擎 → Obsidian Markdown 报告

定位（胶水层）：
  本脚本**不做任何采集、不做任何分析逻辑**，只负责把 fetch_all.py 采集到的
  原始结果（RESULT_JSON）收敛为 video_analysis_engine 的 AnalysisInput，
  调 analyze_video() → DraftReport → debug Markdown。正式 `B站笔记_*.md`
  输出仍必须通过 publishable gate 后才会写入。

输入三选一：
  --input FILE   fetch_all.py 的输出文件（纯 JSON，或含 RESULT_JSON_START/END 的文本）
  --bvid  BVxxx  直接读 /tmp/{bvid}_*.json（comments/danmaku/subtitle 各自落盘文件重建）
  （无参）       从 stdin 读 fetch_all.py 的 stdout（支持管道）

字段映射（fetch_all 结构 → AnalysisInput）：
  comments.hot_comments[] → Comment(platform='bilibili')
  danmaku.data[]          → Danmaku
  subtitle.json_path/txt_path → Transcript（读落盘字幕文件，含 whisper 转录）
  cross_platform          → 原样透传（引擎自带 youtube_comments 解析）
  fact_checks             → 读 /tmp/{bvid}_fact_checks.json，无则由字幕现场提取

输出：
  - --output FILE.md 落盘（默认 /tmp/{video_id}_report.md）
  - stdout 走 RESULT_JSON_START/END 协议（精简版，不灌全文 Markdown）

用法:
  python3 generate_report.py --bvid BV1xx
  python3 generate_report.py --input /tmp/BV1xx_fetch_all.json --output /tmp/BV1xx_report.md
  python3 fetch_all.py BV1xx | python3 generate_report.py
"""

import sys
import os

# 依赖兜底：与其它脚本一致，把脚本目录放进 sys.path 以便 import 同级模块。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import json
import argparse
from collections.abc import Mapping

import video_analysis_engine as _vae
from video_analysis_engine import (
    AnalysisInput, Transcript, TranscriptSegment, Comment, Danmaku,
    analyze_video, build_draft_report, render_debug_markdown, render_draft_markdown,
    publish_markdown, PublishableReportError,
    cli_writer_provider, deepseek_writer_provider,
)
import verify_publishable_report
import research_contract as _research_contract
import research_projection as _research_projection
from research_pipeline import build_research_plan, execute_research_once


def orchestrate_research(
    report,
    *,
    research_provider=None,
    research_context=None,
    research_policy="auto",
    research_archive=None,
):
    """Build one plan, execute one injected provider, validate, archive, and project.

    The legacy results-dict transport has no canonical EvidenceBundle hash and
    therefore remains explicitly untrusted. Only validated/adjudicated bundle
    objects may reach deterministic projection; raw candidates remain private.
    """
    if not research_context or not research_context.get("evidence_bundle_hash"):
        summary = {
            "status": "unavailable",
            "transport": "legacy_untrusted",
            "attempted": False,
            "executed": False,
            "validated_evidence_count": 0,
        }
        report["research"] = summary
        return summary

    frontmatter = report.get("frontmatter") or {}
    report_plan = report.get("report_plan") or {}
    plan = build_research_plan(
        evidence_bundle_hash=str(research_context["evidence_bundle_hash"]),
        claim_bundle=report.get("claim_bundle") or {},
        canonical_id=str(research_context.get("canonical_id") or frontmatter.get("video_id") or ""),
        platform=str(research_context.get("platform") or frontmatter.get("platform") or "unknown"),
        report_mode=str(report_plan.get("mode") or "condensed"),
        research_policy=research_policy,
        capability_snapshot=research_context.get("capability_snapshot") or {
            "available": research_provider is not None,
            "route": "injected" if research_provider is not None else "unavailable",
        },
        created_at=str(research_context.get("created_at") or ""),
        plan_id=str(research_context.get("plan_id") or ""),
        topic_hints=tuple(research_context.get("topic_hints") or ()),
    )
    raw_run = execute_research_once(plan, research_provider)
    artifacts = {"research_plan": plan, "raw_research_run": raw_run}
    bundle = None
    validation_error = None
    if raw_run.executed:
        try:
            bundle = _research_contract.validate_and_adjudicate_research(plan, raw_run)
        except _research_contract.ResearchContractViolation as exc:
            # Fail closed without projecting raw material or crashing legacy report
            # generation. No ResearchBundle means publication remains blocked.
            validation_error = str(exc)[:240]
        else:
            artifacts["research_bundle"] = bundle
            if research_archive is not None:
                source_hashes = set()
                candidates = raw_run.raw_research.get("candidates", ())
                if isinstance(candidates, (tuple, list)):
                    for candidate in candidates:
                        if not isinstance(candidate, Mapping):
                            continue
                        content = candidate.get("content")
                        if isinstance(content, str) and content:
                            source_hashes.add(research_archive.write_source(content))
                artifacts["archive_source_hashes"] = tuple(sorted(source_hashes))
                artifacts["archive_bundle_hash"] = research_archive.write_bundle(bundle)

            report_mode = str((report.get("report_plan") or {}).get("mode") or "")
            if report_mode in _research_contract.REPORT_MODES:
                projection = _research_projection.build_research_projection(
                    bundle,
                    report_plan_hash=_research_contract.semantic_sha256(
                        report.get("report_plan") or {}
                    ),
                    report_mode=report_mode,
                )
                artifacts["research_projection"] = projection
                artifacts["research_projection_records"] = (
                    _research_projection.materialize_research_projection(
                        projection, bundle
                    )
                )
    report["research_artifacts"] = artifacts
    validated_quotes = (
        bundle.validated_research.get("quotes", ()) if bundle is not None else ()
    )
    validated_evidence_count = (
        len(validated_quotes) if isinstance(validated_quotes, (tuple, list)) else 0
    )
    external = report.setdefault("evidence_gate", {}).setdefault("sources", {}).setdefault(
        "external_research", {}
    )
    external.update({
        "available": bool(validated_evidence_count),
        "validated_evidence_count": validated_evidence_count,
        "route": str(plan.capability_snapshot.get("route") or ""),
        "reason": "validated_research" if validated_evidence_count else raw_run.status,
    })
    report["research"] = {
        "status": "invalid" if validation_error else raw_run.status,
        "transport": "canonical_evidence_bundle",
        "capability_available": raw_run.capability_available,
        "attempted": raw_run.attempted,
        "executed": raw_run.executed,
        "validated_evidence_count": validated_evidence_count,
        "plan_semantic_hash": plan.plan_semantic_hash,
        "raw_hash": raw_run.raw_hash,
        "publication_disposition": (
            bundle.publication_disposition if bundle is not None else "block"
        ),
    }
    if validation_error:
        report["research"]["validation_error"] = validation_error
    elif bundle is not None:
        report["research"].update({
            "validated_semantic_hash": bundle.validated_semantic_hash,
            "audit_artifact_hash": bundle.audit_artifact_hash,
        })
    return artifacts


def assemble_draft_report_slice(
    report,
    section_ids=("1", "5"),
    provider=None,
    claim_qa_gate=False,
    depth_profile="v24-full",
):
    """Thin dynamic wrapper that preserves both monkeypatch seams.

    Seam 1: monkeypatching video_analysis_engine.assemble_draft_report_slice
             affects this wrapper (calls via _vae at invocation time).
    Seam 2: monkeypatching generate_report.assemble_draft_report_slice
             replaces the global name called by report_markdown.
    """
    return _vae.assemble_draft_report_slice(
        report,
        section_ids=section_ids,
        provider=provider,
        claim_qa_gate=claim_qa_gate,
        depth_profile=depth_profile,
    )


# ============ 通用解析工具 ============
def parse_result_json(text):
    """从文本中解析 RESULT_JSON 块；纯 JSON 文本也兼容。失败返回 None。"""
    if not text:
        return None
    if 'RESULT_JSON_START' in text and 'RESULT_JSON_END' in text:
        start = text.find('RESULT_JSON_START') + len('RESULT_JSON_START')
        end = text.find('RESULT_JSON_END')
        text = text[start:end]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def _safe(step):
    """fetch_all 的子步骤可能是 None / {'status':'failed'} / 正常 dict。
    仅当是「成功且有数据」的 dict 时返回它，否则 None。"""
    if not isinstance(step, dict):
        return None
    if step.get('status') == 'failed':
        return None
    return step


# 字幕 TXT 行格式：[m:ss] 正文  /  [h:mm:ss] 正文
_TXT_LINE = re.compile(r'^\s*\[(?:(\d+):)?(\d{1,2}):(\d{2})\]\s*(.*)$')
# H200 chunked ASR 格式：## Chunk 2 [05:00]；后续正文继承该 chunk 的时间。
_CHUNK_HEADING = re.compile(r'^\s*##\s+Chunk\s+\d+\s+\[(?:(\d+):)?(\d{1,2}):(\d{2})\]\s*$', re.I)


def _parse_txt_subtitle(path):
    """解析带行级或 H200 chunk 级时间戳的字幕 TXT。"""
    out = []
    current_chunk_start = 0.0
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                chunk = _CHUNK_HEADING.match(stripped)
                if chunk:
                    current_chunk_start = float(
                        int(chunk.group(1) or 0) * 3600
                        + int(chunk.group(2)) * 60
                        + int(chunk.group(3))
                    )
                    continue
                m = _TXT_LINE.match(line.rstrip('\n'))
                if m:
                    h = int(m.group(1) or 0)
                    start = h * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                    out.append((float(start), m.group(4).strip()))
                elif stripped and not stripped.startswith('#'):
                    # 无行级时间戳的 H200/whisper 正文继承当前 chunk；Markdown 标题不是正文。
                    out.append((current_chunk_start, stripped))
    except OSError:
        pass
    return out


def _coerce_float(value):
    """宽容地把值转 float；失败返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _segment_end(item, start):
    """从 json body item 推导片段终点：item.to / item.end / start+item.duration。

    三者皆缺则返回 None（终点未知，调用方回退 start）。
    """
    for key in ('to', 'end'):
        if key in item:
            end = _coerce_float(item.get(key))
            if end is not None:
                return end
    if 'duration' in item:
        dur = _coerce_float(item.get('duration'))
        if dur is not None:
            return start + dur
    return None


def _pick_language(data):
    """从 dict 取 language / lang / lan 中第一个非空值（统一为 str）。"""
    if not isinstance(data, dict):
        return None
    for key in ('language', 'lang', 'lan'):
        val = data.get(key)
        if val:
            return str(val)
    return None


def _encode_transcript_source(method, json_path, txt_path, parts, total_parts, failed_parts):
    """把 method + 路径 + 多P 分片信息编码进 Transcript.source（管道分隔）。

    形如：'official | json_path=/tmp/x.json | txt_path=/tmp/x.txt | parts=2/3 | failed_parts=P3: ...'
    """
    tokens = [method or 'unknown']
    if json_path:
        tokens.append(f'json_path={json_path}')
    if txt_path:
        tokens.append(f'txt_path={txt_path}')
    if parts is not None and total_parts is not None:
        tokens.append(f'parts={parts}/{total_parts}')
    elif parts is not None:
        tokens.append(f'parts={parts}')
    if failed_parts:
        if isinstance(failed_parts, (list, tuple)):
            failed_parts = ', '.join(str(x) for x in failed_parts)
        tokens.append(f'failed_parts={failed_parts}')
    return ' | '.join(tokens)


def _build_transcript(subtitle_step, bvid):
    """从 subtitle 子步骤重建 Transcript。优先 json_path 的 body，回退 txt_path。

    保真 metadata：
      - 片段 end（to/end/from+duration）写入 TranscriptSegment.end；
      - duration 取 max(end or start)，避免只看 start 低估时长；
      - language 从 step 的 language/lang/lan 继承，缺失时从 json data 继承；
      - source 保留 method，并编码 json_path/txt_path/多P parts/failed_parts。

    返回 (Transcript|None, derived_duration_sec)。
    """
    sub = _safe(subtitle_step)
    if not sub:
        return None, 0

    method = sub.get('method') or 'unknown'
    language = _pick_language(sub)
    segments = []

    # 路径1：json_path（B站官方/yt-dlp 字幕，结构 {body:[{from,content,to/end/duration}]}）
    json_path = sub.get('json_path') or (f'/tmp/{bvid}_subtitle_official.json' if bvid else None)
    json_path_present = bool(json_path and os.path.exists(json_path))
    if json_path_present:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            body = data.get('body') if isinstance(data, dict) else None
            for item in (body or []):
                if not isinstance(item, dict):
                    continue
                start = _coerce_float(item.get('from', 0))
                if start is None:
                    start = 0.0
                text = item.get('content') or item.get('text') or ''
                if text:
                    segments.append(TranscriptSegment(
                        start=start, text=text, end=_segment_end(item, start)))
            # step 未给 language 时，从 json data 继承
            if not language:
                language = _pick_language(data)
        except (OSError, json.JSONDecodeError):
            pass

    # 路径2：txt_path（whisper 转录无 json body 时）
    txt_path = sub.get('txt_path')
    if not segments:
        if txt_path and os.path.exists(txt_path):
            for start, text in _parse_txt_subtitle(txt_path):
                segments.append(TranscriptSegment(start=start, text=text))

    if not segments:
        return None, 0

    # duration 用 end（缺则回退 start），避免只取 max(start) 而漏掉末段时长
    duration = int(max(
        ((s.end if s.end is not None else s.start) for s in segments), default=0))
    source = _encode_transcript_source(
        method,
        json_path if json_path_present else None,
        txt_path,
        sub.get('parts'),
        sub.get('total_parts'),
        sub.get('failed_parts'),
    )
    return Transcript(segments=segments, language=language or 'unknown', source=source), duration


def _build_comments(comments_step):
    """从 comments 子步骤（fetch_comments 结构）重建 B站 Comment 列表。

    优先使用 merged_comments（去重后的全量评论），并追加高赞回复组中的单条回复，
    确保扩量采样后的评论数据能被分析引擎充分消费。
    """
    c = _safe(comments_step)
    if not c:
        return []

    seen = set()
    out = []

    def _add(comment_obj):
        text = comment_obj.get('content', '') or ''
        if not text or text in seen:
            return
        seen.add(text)
        user = comment_obj.get('user') or {}
        out.append(Comment(
            text=text,
            likes=int(comment_obj.get('like', 0) or 0),
            author=user.get('name', '') or '',
            platform='bilibili',
        ))

    # 1) 优先使用 merged_comments（去重后的热门+最新评论）
    for it in c.get('merged_comments', []) or []:
        _add(it)

    # 2) 如果没有 merged_comments，则合并 hot_comments + recent_comments（去重兜底）
    if not out:
        for it in (c.get('hot_comments', []) or []) + (c.get('recent_comments', []) or []):
            _add(it)

    # 3) 追加高赞回复组中的回复（作为独立 comment，但可能已在上游 merged，这里去重）
    for group in c.get('replies', []) or []:
        for r in group.get('replies', []) or []:
            _add(r)

    return out


def _build_danmaku(danmaku_step):
    """从 danmaku 子步骤重建 Danmaku 列表。兼容 data 键和 danmaku 键。"""
    d = _safe(danmaku_step)
    if not d:
        return []
    out = []
    # fetch_danmaku_v2 返回 stdout 用 'data'，但落盘 JSON 用 'danmaku'；两者都支持
    raw_list = d.get('data') or d.get('danmaku') or []
    for it in raw_list:
        try:
            t = float(it.get('time_sec', 0) or 0)
        except (TypeError, ValueError):
            t = 0.0
        out.append(Danmaku(text=it.get('text', '') or '', time=t))
    return out


def _load_fact_checks(bvid, transcript, run_fact_check):
    """获取 claim 核查数据：优先读已落盘的 /tmp/{bvid}_fact_checks.json；
    无则用字幕全文现场提取（best-effort，失败返回 None）。"""
    # 1) 已有落盘结果
    if bvid:
        fc_path = f'/tmp/{bvid}_fact_checks.json'
        if os.path.exists(fc_path):
            try:
                with open(fc_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

    # 2) 现场提取（仅当允许且有字幕）
    if run_fact_check and transcript and transcript.segments:
        try:
            import fact_check_wrr as fcw
            claims = fcw.extract_claims(transcript.full_text())
            return fcw.build_result(claims, bvid or 'unknown', dry_run=True)
        except Exception:
            return None
    return None


def build_analysis_input(results, run_fact_check=True):
    """把 fetch_all 的 results dict 收敛为 AnalysisInput。"""
    bvid = results.get('bvid') or ''
    sub = _safe(results.get('subtitle'))

    transcript, dur_from_sub = _build_transcript(results.get('subtitle'), bvid)
    comments = _build_comments(results.get('comments'))
    danmaku = _build_danmaku(results.get('danmaku'))

    # 时长：优先使用平台元信息；缺失或非法时才用字幕/弹幕最大时间点估算。
    dur_from_dm = int(max((d.time for d in danmaku), default=0))
    inferred_duration = max(dur_from_sub, dur_from_dm)
    raw_duration = results.get('duration', results.get('duration_seconds', results.get('duration_s')))
    try:
        explicit_duration = int(float(raw_duration or 0))
    except (TypeError, ValueError):
        explicit_duration = 0
    duration = explicit_duration if explicit_duration > 0 else inferred_duration

    title = (sub or {}).get('title') or results.get('title') or ''

    fact_checks = _load_fact_checks(bvid, transcript, run_fact_check)

    return AnalysisInput(
        video_id=bvid,
        title=title,
        author=results.get('author', '') or '',
        duration=duration,
        platform='bilibili',
        description=results.get('description', '') or '',
        transcript=transcript,
        comments=comments,
        danmaku=danmaku,
        fact_checks=fact_checks,
        cross_platform=results.get('cross_platform'),
    )


def resolve_writer_provider(args):
    """把 CLI 参数解析为 writer provider callable；默认 None 保持旧行为。"""
    name = getattr(args, 'writer_provider', 'none') or 'none'
    if name == 'none':
        return None
    if name == 'cli':
        return cli_writer_provider
    if name == 'deepseek':
        return deepseek_writer_provider
    raise ValueError(f'未知 writer provider: {name}')


class _CachingWriterProvider:
    """Cache writer-provider responses across QA assembly and debug rendering.

    Phase 3 calls the writer path once to produce section QA metadata and once
    through the legacy debug renderer. For real providers (`cli` / `deepseek`),
    those prompts are identical, so caching prevents double token spend while
    preserving the existing Markdown rendering path.
    """

    def __init__(self, provider):
        self.provider = provider
        self.cache = {}

    def __call__(self, system, user):
        key = (system, user)
        if key not in self.cache:
            self.cache[key] = self.provider(system, user)
        return self.cache[key]


def _serialize_section_qa(qa_results):
    """Convert SectionQualityResult dataclasses to JSON-able dicts."""
    section_qa = {}
    for sid, qa_result in qa_results.items():
        section_qa[sid] = {
            "overall_passed": qa_result.overall_passed,
            "blockers": qa_result.blockers,
            "critical_issues": qa_result.critical_issues,
            "improvements": qa_result.improvements,
            "word_count": qa_result.word_count,
            "evidence_refs_count": qa_result.evidence_refs_count,
            "time_anchor_count": qa_result.time_anchor_count,
            "dimensions": [
                {
                    "dimension": dim.dimension,
                    "passed": dim.passed,
                    "score": dim.score,
                    "issues": dim.issues,
                }
                for dim in qa_result.dimension_results
            ],
        }
    return section_qa


def report_markdown(
    results,
    run_fact_check=True,
    provider=None,
    depth_profile="v24-full",
    claim_qa_gate=False,
    mode='full',
    research_provider=None,
    research_context=None,
    research_policy="auto",
    research_archive=None,
):
    """results → (markdown 文本, report dict)。供 fetch_all --report 直接复用。

    mode='full' 是 API 兼容默认值；CLI 默认使用 'auto'。
    mode in (None, 'auto') → 由 EvidenceBudget 自动选择；其余值显式覆盖。

    所有正式模式（sparse/condensed/full）均经由 assemble_draft_report_slice 组装
    draft_with_qa，再用 render_draft_markdown(include_debug_marker=False) 渲染。
    Sparse 强制 provider=None；full/condensed 传入 caching provider（恰好 3 次调用）。
    """
    inp = build_analysis_input(results, run_fact_check=run_fact_check)
    mode_override = None if mode in (None, 'auto') else mode
    report = analyze_video(inp, mode_override=mode_override)
    effective_mode = (report.get('report_plan') or {}).get('mode', 'condensed')

    report["depth_profile"] = depth_profile
    shared_provider = _CachingWriterProvider(provider) if provider else None

    # Sparse freezes research before deterministic section assembly. Other modes
    # keep the S4 final-ClaimBundle boundary and attach projection afterward,
    # without a second writer/provider pass.
    if effective_mode == 'sparse':
        orchestrate_research(
            report,
            research_provider=research_provider,
            research_context=research_context,
            research_policy=research_policy,
            research_archive=research_archive,
        )

    if effective_mode == 'sparse':
        draft_with_qa = assemble_draft_report_slice(
            report,
            section_ids=("1", "3", "4", "5", "6", "7"),
            provider=None,
            claim_qa_gate=False,
            depth_profile='standard',
        )
    else:
        draft_with_qa = assemble_draft_report_slice(
            report,
            section_ids=("1", "3", "4", "5", "6", "7"),
            provider=shared_provider,
            claim_qa_gate=claim_qa_gate,
            depth_profile=depth_profile,
        )

    report["section_qa"] = _serialize_section_qa(draft_with_qa.qa_results)
    report["claim_bundle"] = draft_with_qa.claim_bundle
    report["draft_warnings"] = list(draft_with_qa.warnings)

    if effective_mode != 'sparse':
        orchestrate_research(
            report,
            research_provider=research_provider,
            research_context=research_context,
            research_policy=research_policy,
            research_archive=research_archive,
        )
        _vae.apply_research_projection_to_draft(draft_with_qa)

    markdown = render_draft_markdown(draft_with_qa, include_debug_marker=False)

    report["video_evidence_usage"] = verify_publishable_report.evaluate_video_evidence_usage(markdown, report)
    return markdown, report


# ============ 输入加载 ============
def _reconstruct_from_bvid(bvid):
    """无 fetch_all 聚合输出时，直接读 /tmp/{bvid}_*.json 重建 results。"""
    results = {'bvid': bvid, 'comments': None, 'danmaku': None,
               'subtitle': None, 'cross_platform': None}

    cpath = f'/tmp/{bvid}_comments.json'
    if os.path.exists(cpath):
        try:
            with open(cpath, 'r', encoding='utf-8') as f:
                results['comments'] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    dpath = f'/tmp/{bvid}_danmaku.json'
    if os.path.exists(dpath):
        try:
            with open(dpath, 'r', encoding='utf-8') as f:
                results['danmaku'] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    # 字幕：重建子步骤结构（仅需 json_path/txt_path/method 供 _build_transcript 使用）
    jp = f'/tmp/{bvid}_subtitle_official.json'
    txt_official = f'/tmp/{bvid}_subtitle_official.txt'
    txt_whisper = f'/tmp/{bvid}_subtitle_whisper.txt'
    if os.path.exists(jp):
        results['subtitle'] = {'method': 'official', 'json_path': jp,
                               'txt_path': txt_official if os.path.exists(txt_official) else None}
    elif os.path.exists(txt_whisper):
        results['subtitle'] = {'method': 'whisper', 'txt_path': txt_whisper}

    return results


def load_results(args):
    """按 --input / --bvid / stdin 优先级加载 fetch_all 结果 dict。"""
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        parsed = parse_result_json(text)
        if parsed is None:
            raise ValueError(f'无法从 --input 解析 fetch_all 结果: {args.input}')
        return parsed

    if args.bvid:
        return _reconstruct_from_bvid(args.bvid)

    # stdin 管道
    if not sys.stdin.isatty():
        parsed = parse_result_json(sys.stdin.read())
        if parsed is not None:
            return parsed

    raise ValueError('需提供 --input FILE 或 --bvid BVxxx，或通过管道传入 fetch_all 输出')


def is_formal_report_output(path) -> bool:
    """Return True for paths that look like final Obsidian video notes.

    Debug/tmp reports are allowed to be skeleton drafts. `B站笔记_*.md` and
    files saved under the formal video-note directory are publish artifacts and
    must pass the publishable gate.
    """
    p = os.fspath(path)
    name = os.path.basename(p)
    normalized = p.replace('\\', '/')
    return bool(
        (name.startswith('B站笔记_') and name.endswith('.md'))
        or '/30-Resources/60_视频笔记/' in normalized
    )


def validate_output_preflight(path, writer_provider, report_plan=None):
    """Reject a formal note that cannot generate writer-backed core sections.

    When report_plan is supplied the effective mode is used: sparse mode allows
    writer=none because §3/§4/§7 are deterministic. All other modes (including
    no report_plan yet) require a model-backed writer for formal outputs.
    """
    if not is_formal_report_output(path):
        return None
    if writer_provider == "none":
        effective_mode = (report_plan or {}).get('mode', '') if report_plan else ''
        if effective_mode != 'sparse':
            return {
                "status": "failed",
                "error_code": "FORMAL_OUTPUT_REQUIRES_WRITER",
                "writer_provider": writer_provider,
            }
    return None


def check_formal_output_publishable(path, markdown, report=None):
    """Check combined gates for formal outputs; debug paths are skipped.

    Uses publish_markdown() so the PublishedMarkdown artifact boundary is
    actually exercised. Debug output remains a plain string.
    """
    if not is_formal_report_output(path):
        return True, {'skipped': True, 'passed': True, 'failed_codes': []}
    try:
        pm = publish_markdown(markdown, report)
        return True, {
            'skipped': False,
            'passed': True,
            'failed_codes': [],
            'gates': pm.gates,
        }
    except PublishableReportError as exc:
        return False, {
            'skipped': False,
            'passed': False,
            'failed_codes': exc.failed_codes,
            'gates': exc.gates,
        }


def main():
    parser = argparse.ArgumentParser(
        description='fetch_all 结果 → 分析引擎 → Obsidian Markdown 报告（胶水层）',
    )
    parser.add_argument('--input', help='fetch_all 输出文件（JSON 或含 RESULT_JSON 标记）')
    parser.add_argument('--bvid', help='直接读 /tmp/{bvid}_*.json 重建')
    parser.add_argument('--output', help='Markdown 输出路径（默认 /tmp/{video_id}_report.md）')
    parser.add_argument('--no-fact-check', action='store_true',
                        help='不现场提取 claim（仍会读已落盘的 fact_checks.json）')
    parser.add_argument('--writer-provider', choices=('none', 'cli', 'deepseek'), default='none',
                        help='LLM writer provider：none=旧骨架/确定性输出；cli=沿用 BILI_WRITER_CLI/OMP；deepseek=直接 DeepSeek API')
    parser.add_argument(
        '--depth-profile',
        choices=('standard', 'v24-full', 'claim-first-full'),
        default='v24-full',
        help='Phase 5: Depth profile (v24-full=default v2.4 depth, standard=simplified backward-compatible, claim-first-full=claim-first architecture).',
    )
    parser.add_argument(
        '--mode',
        choices=('auto', 'sparse', 'condensed', 'full'),
        default='auto',
        help='Report mode: auto (default, uses evidence budget), or explicit sparse/condensed/full override.',
    )
    args = parser.parse_args()

    try:
        results = load_results(args)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f'❌ 加载输入失败: {e}')
        print('\nRESULT_JSON_START')
        print(json.dumps({'status': 'failed', 'error': str(e)}, ensure_ascii=False, indent=2))
        print('RESULT_JSON_END')
        sys.exit(1)

    bvid = results.get('bvid') or 'unknown'
    out_path = args.output or f'/tmp/{bvid}_report.md'

    print(f'📝 生成分析报告: {bvid}')
    print('=' * 60)

    provider = resolve_writer_provider(args)
    # 当 depth_profile 为 claim-first-full 或 v24-full 时，自动启用 claim_qa_gate
    claim_qa_gate = args.depth_profile in ("claim-first-full", "v24-full")
    markdown, report = report_markdown(
        results,
        run_fact_check=not args.no_fact_check,
        provider=provider,
        depth_profile=args.depth_profile,
        claim_qa_gate=claim_qa_gate,
        mode=args.mode,
    )

    # 预检在生成报告后执行，以便使用 effective plan mode 判断是否允许 writer=none
    report_plan = report.get('report_plan')
    preflight_error = validate_output_preflight(out_path, args.writer_provider, report_plan=report_plan)
    if preflight_error:
        print('❌ 正式报告需要 model-backed writer：请使用 --writer-provider cli 或 deepseek')
        print('\nRESULT_JSON_START')
        print(json.dumps({
            **preflight_error,
            'report_path': out_path,
        }, ensure_ascii=False, indent=2))
        print('RESULT_JSON_END')
        sys.exit(1)

    publishable_ok, publishable_summary = check_formal_output_publishable(out_path, markdown, report)
    if not publishable_ok:
        print('❌ 正式报告发布闸未通过：拒绝写入 B站笔记/正式视频库路径')
        for code in publishable_summary.get('failed_codes', []):
            gate = publishable_summary.get('gates', {}).get(code, {})
            print(f"   {code}: {gate.get('reason') or gate.get('measured')}")
        print('\nRESULT_JSON_START')
        print(json.dumps({
            'status': 'failed',
            'error': 'publishable gate failed for formal output path',
            'report_path': out_path,
            'publishable': publishable_summary,
        }, ensure_ascii=False, indent=2))
        print('RESULT_JSON_END')
        sys.exit(1)

    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f'💾 报告已保存: {out_path}  ({len(markdown)} 字符)')
    except OSError as e:
        out_path = None
        print(f'⚠️  报告保存失败: {e}')

    fm = report.get('frontmatter', {})
    print(f"   标题: {fm.get('title') or '（未知）'}")
    print(f"   字幕: {'有' if fm.get('has_transcript') else '无'} | "
          f"评论: {fm.get('comment_count', 0)} | 弹幕: {fm.get('danmaku_count', 0)} | "
          f"搬运: {'是' if fm.get('is_cross_platform') else '否'}")

    # RESULT_JSON：精简版（不灌全文 Markdown，避免 stdout 过大）
    # Phase 5: 包含 depth_profile 和 claim_bundle 统计
    claim_bundle = report.get('claim_bundle', {})
    out = {
        'status': 'ok',
        'video_id': fm.get('video_id', bvid),
        'platform': fm.get('platform', 'bilibili'),
        'report_path': out_path,
        'markdown_chars': len(markdown),
        'frontmatter': fm,
        'sections': list(report.get('sections', {}).keys()),
        'depth_profile': report.get('depth_profile', 'standard'),
        'claim_bundle_stats': {
            'claims_count': len(claim_bundle.get('claims', [])),
            'insights_count': len(claim_bundle.get('insights', [])),
        },
    }
    print('\n' + '=' * 60)
    print('RESULT_JSON_START')
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print('RESULT_JSON_END')


if __name__ == '__main__':
    main()
