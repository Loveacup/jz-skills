# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨会话模式分析器
v5.0 新增 - 从历史会话中发现重复出现的模式

功能：
1. 说话人映射模式（同一别名在多个会话中映射到同一人）
2. 会议结构模式（特定参会人组合 -> 特定会议类型）
3. 话题关联模式（经常同时出现的话题）
4. 质量模式（哪些参数/场景获得更高评分）
5. 标记已分析的会话记录
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from itertools import combinations


class PatternAnalyzer:
    """跨会话模式分析器"""

    # 质量评分映射
    GRADE_SCORES = {'A': 4, 'B': 3, 'C': 2, 'D': 1}

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.speakers_data = {}
        self.sessions_data = []
        self.patterns_data = []
        self.max_sessions = 50

    def load_memory(self):
        """加载记忆文件"""
        speakers_file = self._load_json('speakers.json')
        self.speakers_data = speakers_file.get('speakers', {})

        sessions_file = self._load_json('sessions.json')
        self.sessions_data = sessions_file.get('sessions', [])
        self.max_sessions = sessions_file.get('max_sessions', 50)

        patterns_file = self._load_json('patterns.json')
        self.patterns_data = patterns_file.get('patterns', [])

    def _load_json(self, filename: str) -> dict:
        """安全加载 JSON 文件"""
        filepath = self.memory_dir / filename
        if not filepath.exists():
            print(f"[pattern_analyzer] 文件不存在: {filepath}", file=sys.stderr)
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[pattern_analyzer] JSON 解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def get_unanalyzed_sessions(self) -> List[dict]:
        """获取尚未分析的会话"""
        return [s for s in self.sessions_data if not s.get('analyzed', False)]

    def analyze_speaker_mapping_patterns(self) -> List[dict]:
        """
        分析说话人映射模式

        同一别名在多个会话中映射到同一人 -> speaker_mapping pattern
        """
        candidates = []

        for speaker_name, speaker_info in self.speakers_data.items():
            aliases = speaker_info.get('aliases', [])
            session_count = speaker_info.get('session_count', 0)

            for alias in aliases:
                if not alias or alias == speaker_name:
                    continue

                # 检查这个别名出现在多少个会话中
                sessions_with_alias = []
                for session in self.sessions_data:
                    session_speakers = session.get('speakers', [])
                    if speaker_name in session_speakers or alias in session_speakers:
                        sessions_with_alias.append(session.get('id', ''))

                occurrences = len(sessions_with_alias)
                if occurrences >= 2:
                    confidence = self._calculate_confidence(
                        occurrences, len(self.sessions_data), sessions_with_alias
                    )
                    candidates.append({
                        'type': 'speaker_mapping',
                        'rule': f"当出现'{alias}'时映射到'{speaker_name}'",
                        'confidence': round(confidence, 3),
                        'occurrences': occurrences,
                        'evidence': sessions_with_alias[:10],
                        'recommended_action': 'auto_apply' if confidence >= 0.8 else 'review',
                    })

        return candidates

    def analyze_meeting_structure_patterns(self) -> List[dict]:
        """
        分析会议结构模式

        特定参会人组合 -> 特定会议类型
        """
        candidates = []

        # 按 scene_type + meeting_subtype 分组
        type_groups = defaultdict(list)
        for session in self.sessions_data:
            scene_type = session.get('scene_type', '')
            subtype = session.get('meeting_subtype', '')
            key = f"{scene_type}:{subtype}" if subtype else scene_type
            if key:
                type_groups[key].append(session)

        for meeting_type, sessions in type_groups.items():
            if len(sessions) < 2:
                continue

            # 找出频繁的参会人组合
            speaker_sets = []
            for session in sessions:
                speakers = sorted(session.get('speakers', []))
                if len(speakers) >= 2:
                    speaker_sets.append(tuple(speakers))

            # 统计完全相同的参会人组合
            combo_counter = Counter(speaker_sets)
            for combo, count in combo_counter.items():
                if count >= 2:
                    evidence = []
                    for session in sessions:
                        if tuple(sorted(session.get('speakers', []))) == combo:
                            evidence.append(session.get('id', ''))

                    confidence = self._calculate_confidence(
                        count, len(self.sessions_data), evidence
                    )
                    participants = ', '.join(combo)
                    candidates.append({
                        'type': 'meeting_structure',
                        'rule': f"[{participants}] 参会时通常为 {meeting_type}",
                        'confidence': round(confidence, 3),
                        'occurrences': count,
                        'evidence': evidence[:10],
                        'recommended_action': 'review',
                    })

        return candidates

    def analyze_topic_association_patterns(self) -> List[dict]:
        """
        分析话题关联模式

        某些话题经常一起出现
        """
        candidates = []

        # 收集每个会话的话题
        session_topics = []
        for session in self.sessions_data:
            topics = session.get('topics', [])
            if len(topics) >= 2:
                session_topics.append((session.get('id', ''), set(topics)))

        if len(session_topics) < 2:
            return candidates

        # 统计话题对的共现频率
        pair_evidence = defaultdict(list)
        for session_id, topics in session_topics:
            for pair in combinations(sorted(topics), 2):
                pair_evidence[pair].append(session_id)

        for pair, evidence in pair_evidence.items():
            occurrences = len(evidence)
            if occurrences >= 2:
                confidence = self._calculate_confidence(
                    occurrences, len(session_topics), evidence
                )
                candidates.append({
                    'type': 'topic_association',
                    'rule': f"'{pair[0]}' 和 '{pair[1]}' 经常同时出现",
                    'confidence': round(confidence, 3),
                    'occurrences': occurrences,
                    'evidence': evidence[:10],
                    'recommended_action': 'review',
                })

        # 只保留高频的
        candidates.sort(key=lambda c: c['occurrences'], reverse=True)
        return candidates[:20]

    def analyze_quality_patterns(self) -> List[dict]:
        """
        分析质量模式

        哪些场景类型获得更高评分
        """
        candidates = []

        # 按 scene_type 分组统计质量评分
        type_scores = defaultdict(list)
        for session in self.sessions_data:
            scene_type = session.get('scene_type', '')
            quality = session.get('quality_score', '')
            if scene_type and quality and quality in self.GRADE_SCORES:
                type_scores[scene_type].append(quality)

        for scene_type, scores in type_scores.items():
            if len(scores) < 2:
                continue

            numeric_scores = [self.GRADE_SCORES[s] for s in scores]
            avg_score = sum(numeric_scores) / len(numeric_scores)

            # 找到对应的等级
            if avg_score >= 3.5:
                avg_grade = 'A'
            elif avg_score >= 2.5:
                avg_grade = 'B'
            elif avg_score >= 1.5:
                avg_grade = 'C'
            else:
                avg_grade = 'D'

            evidence = [s.get('id', '') for s in self.sessions_data
                        if s.get('scene_type') == scene_type and s.get('quality_score')]

            candidates.append({
                'type': 'quality_pattern',
                'rule': f"{scene_type} 类型的平均质量评分为 {avg_grade}",
                'confidence': round(len(scores) / (len(scores) + 3), 3),
                'occurrences': len(scores),
                'evidence': evidence[:10],
                'recommended_action': 'review',
            })

        return candidates

    def _calculate_confidence(
        self, occurrences: int, total_sessions: int, evidence: List[str]
    ) -> float:
        """
        计算模式置信度

        base = occurrences / total_sessions
        连续出现加成: 最近连续出现 +0.1
        最终 confidence = min(base * 1.5 + consecutive_bonus, 1.0)
        """
        if total_sessions == 0:
            return 0.0

        base = occurrences / total_sessions

        # 检查最近是否连续出现
        consecutive_bonus = 0.0
        if evidence and self.sessions_data:
            # 获取最近的会话 ID 列表（按时间降序）
            sorted_sessions = sorted(
                self.sessions_data,
                key=lambda s: s.get('timestamp', ''),
                reverse=True
            )
            recent_ids = [s.get('id', '') for s in sorted_sessions]

            # 检查 evidence 中的 ID 是否在最近的会话中连续出现
            evidence_set = set(evidence)
            consecutive = 0
            for sid in recent_ids:
                if sid in evidence_set:
                    consecutive += 1
                else:
                    break

            if consecutive >= 2:
                consecutive_bonus = 0.1

        confidence = min(base * 1.5 + consecutive_bonus, 1.0)
        return confidence

    def compute_statistics(self) -> dict:
        """计算统计信息"""
        total_speakers = len(self.speakers_data)

        all_topics = set()
        scene_type_counter = Counter()
        quality_scores = []

        for session in self.sessions_data:
            all_topics.update(session.get('topics', []))
            scene_type = session.get('scene_type', '')
            if scene_type:
                scene_type_counter[scene_type] += 1
            quality = session.get('quality_score', '')
            if quality:
                quality_scores.append(quality)

        most_common_scene = ''
        if scene_type_counter:
            most_common_scene = scene_type_counter.most_common(1)[0][0]

        avg_quality = ''
        if quality_scores:
            numeric = [self.GRADE_SCORES.get(q, 0) for q in quality_scores]
            avg = sum(numeric) / len(numeric)
            if avg >= 3.5:
                avg_quality = 'A'
            elif avg >= 2.5:
                avg_quality = 'B'
            elif avg >= 1.5:
                avg_quality = 'C'
            else:
                avg_quality = 'D'

        return {
            'total_speakers': total_speakers,
            'total_topics': len(all_topics),
            'most_common_scene_type': most_common_scene,
            'average_quality_score': avg_quality,
        }

    def assign_candidate_ids(self, candidates: List[dict]) -> List[dict]:
        """为候选模式分配 ID"""
        # 获取已有模式的最大编号
        max_num = 0
        for pattern in self.patterns_data:
            pid = pattern.get('id', '')
            # 支持 P001 和 P_NEW_001 格式
            for prefix in ['P_NEW_', 'P']:
                if pid.startswith(prefix):
                    num_str = pid[len(prefix):]
                    if num_str.isdigit():
                        max_num = max(max_num, int(num_str))

        for i, candidate in enumerate(candidates, start=1):
            candidate['id'] = f'P_NEW_{max_num + i:03d}'

        return candidates

    def mark_sessions_analyzed(self):
        """标记所有会话为已分析"""
        sessions_file = self._load_json('sessions.json')
        sessions = sessions_file.get('sessions', [])

        for session in sessions:
            session['analyzed'] = True

        sessions_file['sessions'] = sessions

        filepath = self.memory_dir / 'sessions.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sessions_file, f, ensure_ascii=False, indent=2)
            f.write('\n')

        print(f"[pattern_analyzer] 已标记 {len(sessions)} 条会话为已分析", file=sys.stderr)

    def analyze(self) -> dict:
        """执行完整分析"""
        self.load_memory()

        if not self.sessions_data:
            print("[pattern_analyzer] 无会话数据，跳过分析", file=sys.stderr)
            return {
                'analysis_timestamp': datetime.now().isoformat(timespec='seconds'),
                'sessions_analyzed': 0,
                'candidates': [],
                'statistics': self.compute_statistics(),
            }

        unanalyzed = self.get_unanalyzed_sessions()
        print(f"[pattern_analyzer] 总会话: {len(self.sessions_data)}, "
              f"未分析: {len(unanalyzed)}", file=sys.stderr)

        # 执行各维度分析（基于全部会话，不仅仅是未分析的）
        candidates = []

        print("[pattern_analyzer] 分析说话人映射模式...", file=sys.stderr)
        speaker_patterns = self.analyze_speaker_mapping_patterns()
        candidates.extend(speaker_patterns)
        print(f"[pattern_analyzer]   发现 {len(speaker_patterns)} 个候选", file=sys.stderr)

        print("[pattern_analyzer] 分析会议结构模式...", file=sys.stderr)
        structure_patterns = self.analyze_meeting_structure_patterns()
        candidates.extend(structure_patterns)
        print(f"[pattern_analyzer]   发现 {len(structure_patterns)} 个候选", file=sys.stderr)

        print("[pattern_analyzer] 分析话题关联模式...", file=sys.stderr)
        topic_patterns = self.analyze_topic_association_patterns()
        candidates.extend(topic_patterns)
        print(f"[pattern_analyzer]   发现 {len(topic_patterns)} 个候选", file=sys.stderr)

        print("[pattern_analyzer] 分析质量模式...", file=sys.stderr)
        quality_patterns = self.analyze_quality_patterns()
        candidates.extend(quality_patterns)
        print(f"[pattern_analyzer]   发现 {len(quality_patterns)} 个候选", file=sys.stderr)

        # 按置信度降序排列
        candidates.sort(key=lambda c: c['confidence'], reverse=True)

        # 分配 ID
        candidates = self.assign_candidate_ids(candidates)

        # 标记已分析
        self.mark_sessions_analyzed()

        statistics = self.compute_statistics()

        result = {
            'analysis_timestamp': datetime.now().isoformat(timespec='seconds'),
            'sessions_analyzed': len(self.sessions_data),
            'candidates': candidates,
            'statistics': statistics,
        }

        print(f"[pattern_analyzer] 分析完成: 共 {len(candidates)} 个候选模式", file=sys.stderr)
        return result


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='跨会话模式分析器 - 从历史会话中发现重复出现的模式'
    )
    parser.add_argument(
        'memory_dir',
        help='记忆目录路径（如 ~/.claude/skills/voice-to-markdown-workflow/memory/）'
    )
    parser.add_argument(
        'output_file',
        help='输出文件路径（如 /tmp/vtm-workspace/pattern-candidates.json）'
    )
    return parser.parse_args()


def main():
    """命令行入口"""
    args = parse_args()

    memory_dir = Path(args.memory_dir).expanduser()
    output_file = Path(args.output_file)

    if not memory_dir.exists():
        print(f"[pattern_analyzer] 错误: 记忆目录不存在: {memory_dir}", file=sys.stderr)
        sys.exit(1)

    analyzer = PatternAnalyzer(memory_dir)
    result = analyzer.analyze()

    # 保存输出
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[pattern_analyzer] 分析结果已保存到: {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
