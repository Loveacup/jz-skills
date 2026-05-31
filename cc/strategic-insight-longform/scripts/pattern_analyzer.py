#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战略分析跨会话模式分析器
从历史会话中发现重复出现的模式

模式类型：
1. framework_effectiveness - 特定框架在特定分析类型上的效果
2. source_reliability - 来源在特定领域的可靠性
3. writing_optimization - 写作策略优化
4. analysis_depth - 分析深度策略
5. topic_association - 主题关联模式
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
    """战略分析跨会话模式分析器"""

    # 质量评分等级映射（用于 source_reliability 分析）
    GRADE_SCORES = {'A': 4, 'B': 3, 'C': 2, 'D': 1}

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.sessions_data: List[dict] = []
        self.frameworks_data: Dict[str, dict] = {}
        self.sources_data: Dict[str, dict] = {}
        self.topics_data: Dict[str, dict] = {}
        self.patterns_data: List[dict] = []
        self.max_sessions: int = 50

    def load_memory(self):
        """加载记忆文件"""
        sessions_file = self._load_json('sessions.json')
        self.sessions_data = sessions_file.get('sessions', [])
        self.max_sessions = sessions_file.get('max_sessions', 50)

        frameworks_file = self._load_json('frameworks.json')
        self.frameworks_data = frameworks_file.get('frameworks', {})

        sources_file = self._load_json('sources.json')
        self.sources_data = sources_file.get('sources', {})

        topics_file = self._load_json('topics.json')
        self.topics_data = topics_file.get('topics', {})

        patterns_file = self._load_json('patterns.json')
        self.patterns_data = patterns_file.get('patterns', [])

        print(f"[pattern_analyzer] 已加载: "
              f"会话 {len(self.sessions_data)}, "
              f"框架 {len(self.frameworks_data)}, "
              f"来源 {len(self.sources_data)}, "
              f"主题 {len(self.topics_data)}, "
              f"现有模式 {len(self.patterns_data)}",
              file=sys.stderr)

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

    def _calculate_confidence(
        self, occurrences: int, total_sessions: int, evidence: List[str]
    ) -> float:
        """
        计算模式置信度

        base = occurrences / total_sessions
        连续出现加成: 最近连续出现 2+ 次 -> +0.1
        最终 confidence = min(base * 1.5 + consecutive_bonus, 1.0)
        """
        if total_sessions == 0:
            return 0.0

        base = occurrences / total_sessions

        # 检查最近是否连续出现
        consecutive_bonus = 0.0
        if evidence and self.sessions_data:
            sorted_sessions = sorted(
                self.sessions_data,
                key=lambda s: s.get('timestamp', ''),
                reverse=True,
            )
            recent_ids = [s.get('id', '') for s in sorted_sessions]

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

    def analyze_framework_effectiveness(self) -> List[dict]:
        """
        分析框架效果模式

        发现: 特定框架在特定分析类型上的效果
        例: "S-T-D 立方体在行业分析中平均质量 4.5/5"
        """
        candidates = []

        for fw_id, fw_info in self.frameworks_data.items():
            usage_count = fw_info.get('usage_count', 0)
            if usage_count < 2:
                continue

            display_name = fw_info.get('display_name', fw_id)
            avg_quality = fw_info.get('avg_quality_score', 0.0)
            effectiveness = fw_info.get('effectiveness_by_type', {})

            # 整体效果模式
            if avg_quality > 0:
                # 找到使用此框架的会话
                evidence = []
                for session in self.sessions_data:
                    if fw_id in session.get('frameworks_used', []):
                        evidence.append(session.get('id', ''))

                confidence = self._calculate_confidence(
                    len(evidence), len(self.sessions_data), evidence
                )

                quality_label = '优秀' if avg_quality >= 4.0 else '良好' if avg_quality >= 3.0 else '一般'
                candidates.append({
                    'type': 'framework_effectiveness',
                    'rule': f"{display_name} 整体表现{quality_label}，平均质量 {avg_quality:.1f}/5 ({usage_count}次使用)",
                    'confidence': round(confidence, 3),
                    'occurrences': usage_count,
                    'evidence': evidence[:10],
                })

            # 按分析类型的效果模式
            for analysis_type, type_info in effectiveness.items():
                type_count = type_info.get('count', 0)
                type_avg = type_info.get('avg_score', 0.0)
                if type_count < 2 or type_avg <= 0:
                    continue

                evidence = []
                for session in self.sessions_data:
                    if (fw_id in session.get('frameworks_used', []) and
                            session.get('analysis_type', '') == analysis_type):
                        evidence.append(session.get('id', ''))

                confidence = self._calculate_confidence(
                    len(evidence), len(self.sessions_data), evidence
                )

                candidates.append({
                    'type': 'framework_effectiveness',
                    'rule': f"{display_name} 在{analysis_type}分析中平均质量 {type_avg:.1f}/5 ({type_count}次)",
                    'confidence': round(confidence, 3),
                    'occurrences': type_count,
                    'evidence': evidence[:10],
                })

        return candidates

    def analyze_source_reliability(self) -> List[dict]:
        """
        分析来源可靠性模式

        发现: 来源在特定领域的可靠性
        例: "国家统计局数据在行业分析中被引用 15 次，准确率 95%"
        """
        candidates = []

        for source_name, source_info in self.sources_data.items():
            citation_count = source_info.get('citation_count', 0)
            if citation_count < 2:
                continue

            grade = source_info.get('credibility_grade', 'C')
            accuracy = source_info.get('accuracy_rate', 0.0)
            domains = source_info.get('domains', [])
            source_type = source_info.get('type', '')

            # 高引用来源模式
            grade_label = {
                'A': '高可靠', 'B': '较可靠', 'C': '一般', 'D': '待验证'
            }.get(grade, '未知')

            rule_parts = [f"来源'{source_name}'({grade_label})被引用 {citation_count} 次"]
            if accuracy > 0:
                rule_parts.append(f"准确率 {accuracy*100:.0f}%")
            if domains:
                rule_parts.append(f"擅长领域: {', '.join(domains[:3])}")

            # 用引用次数作为 occurrences
            # evidence 从会话中匹配（来源不直接关联会话，用引用次数模拟）
            confidence = min(citation_count / (citation_count + 3) * 1.5, 1.0)

            candidates.append({
                'type': 'source_reliability',
                'rule': '，'.join(rule_parts),
                'confidence': round(confidence, 3),
                'occurrences': citation_count,
                'evidence': [],
            })

        return candidates

    def analyze_writing_optimization(self) -> List[dict]:
        """
        分析写作策略优化模式

        发现: 特定模式下的写作策略效果
        例: "deep 模式下案例切入开篇策略质量评分更高"
        """
        candidates = []

        # 按 mode 分组统计质量
        mode_scores: Dict[str, List[float]] = defaultdict(list)
        for session in self.sessions_data:
            mode = session.get('mode', '')
            quality = session.get('quality_score', 0.0)
            if mode and quality > 0:
                mode_scores[mode].append(quality)

        if len(mode_scores) < 2:
            return candidates

        # 比较不同模式的质量
        mode_avgs = {}
        for mode, scores in mode_scores.items():
            if len(scores) >= 2:
                mode_avgs[mode] = sum(scores) / len(scores)

        if not mode_avgs:
            return candidates

        best_mode = max(mode_avgs, key=lambda m: mode_avgs[m])
        best_avg = mode_avgs[best_mode]

        # 与其他模式对比
        for mode, avg in mode_avgs.items():
            if mode == best_mode:
                continue
            diff = best_avg - avg
            if diff > 0.3:  # 显著差异
                evidence = [
                    s.get('id', '') for s in self.sessions_data
                    if s.get('mode') == best_mode and s.get('quality_score', 0) > 0
                ]
                confidence = self._calculate_confidence(
                    len(evidence), len(self.sessions_data), evidence
                )
                candidates.append({
                    'type': 'writing_optimization',
                    'rule': f"{best_mode} 模式质量 ({best_avg:.1f}) 显著优于 {mode} 模式 ({avg:.1f})，差异 {diff:.1f}",
                    'confidence': round(confidence, 3),
                    'occurrences': len(evidence),
                    'evidence': evidence[:10],
                })

        # 分析 patterns_applied 的效果
        pattern_scores: Dict[str, List[float]] = defaultdict(list)
        for session in self.sessions_data:
            quality = session.get('quality_score', 0.0)
            if quality <= 0:
                continue
            for pattern in session.get('patterns_applied', []):
                pattern_scores[pattern].append(quality)

        for pattern_name, scores in pattern_scores.items():
            if len(scores) < 2:
                continue
            avg = sum(scores) / len(scores)
            if avg >= 3.5:
                evidence = [
                    s.get('id', '') for s in self.sessions_data
                    if pattern_name in s.get('patterns_applied', [])
                ]
                confidence = self._calculate_confidence(
                    len(evidence), len(self.sessions_data), evidence
                )
                candidates.append({
                    'type': 'writing_optimization',
                    'rule': f"应用模式'{pattern_name}'时平均质量 {avg:.1f}/5 ({len(scores)}次)",
                    'confidence': round(confidence, 3),
                    'occurrences': len(scores),
                    'evidence': evidence[:10],
                })

        return candidates

    def analyze_analysis_depth(self) -> List[dict]:
        """
        分析深度策略模式

        发现: 不同分析类型在不同模式下的质量差异
        例: "行业分析类型在 deep 模式下质量显著优于 standard"
        """
        candidates = []

        # 按 (analysis_type, mode) 分组统计质量
        type_mode_scores: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        for session in self.sessions_data:
            analysis_type = session.get('analysis_type', '')
            mode = session.get('mode', '')
            quality = session.get('quality_score', 0.0)
            if analysis_type and mode and quality > 0:
                type_mode_scores[(analysis_type, mode)].append(quality)

        # 按分析类型分组，比较不同模式
        type_groups: Dict[str, Dict[str, List[float]]] = defaultdict(dict)
        for (atype, mode), scores in type_mode_scores.items():
            type_groups[atype][mode] = scores

        for atype, mode_data in type_groups.items():
            if len(mode_data) < 2:
                continue

            mode_avgs = {}
            for mode, scores in mode_data.items():
                if len(scores) >= 2:
                    mode_avgs[mode] = (sum(scores) / len(scores), len(scores))

            if len(mode_avgs) < 2:
                continue

            best_mode = max(mode_avgs, key=lambda m: mode_avgs[m][0])
            best_avg, best_count = mode_avgs[best_mode]

            for mode, (avg, count) in mode_avgs.items():
                if mode == best_mode:
                    continue
                diff = best_avg - avg
                if diff > 0.3:
                    evidence = [
                        s.get('id', '') for s in self.sessions_data
                        if s.get('analysis_type') == atype and s.get('mode') == best_mode
                    ]
                    confidence = self._calculate_confidence(
                        len(evidence), len(self.sessions_data), evidence
                    )
                    candidates.append({
                        'type': 'analysis_depth',
                        'rule': f"{atype}分析在 {best_mode} 模式下质量 ({best_avg:.1f}) 显著优于 {mode} ({avg:.1f})",
                        'confidence': round(confidence, 3),
                        'occurrences': best_count + count,
                        'evidence': evidence[:10],
                    })

        # 分析框架数量与质量的关系
        fw_count_scores: Dict[int, List[float]] = defaultdict(list)
        for session in self.sessions_data:
            fw_count = len(session.get('frameworks_used', []))
            quality = session.get('quality_score', 0.0)
            if quality > 0:
                fw_count_scores[fw_count].append(quality)

        # 检查多框架是否优于单框架
        if 1 in fw_count_scores and len(fw_count_scores) > 1:
            single_avg = sum(fw_count_scores[1]) / len(fw_count_scores[1]) if fw_count_scores[1] else 0
            for count, scores in fw_count_scores.items():
                if count <= 1 or len(scores) < 2:
                    continue
                multi_avg = sum(scores) / len(scores)
                diff = multi_avg - single_avg
                if diff > 0.3:
                    evidence = [
                        s.get('id', '') for s in self.sessions_data
                        if len(s.get('frameworks_used', [])) == count
                    ]
                    confidence = self._calculate_confidence(
                        len(evidence), len(self.sessions_data), evidence
                    )
                    candidates.append({
                        'type': 'analysis_depth',
                        'rule': f"使用 {count} 个框架时质量 ({multi_avg:.1f}) 优于单框架 ({single_avg:.1f})",
                        'confidence': round(confidence, 3),
                        'occurrences': len(scores),
                        'evidence': evidence[:10],
                    })

        return candidates

    def analyze_topic_association(self) -> List[dict]:
        """
        分析主题关联模式

        发现: 经常被一起分析的主题
        例: "'AI' 和 '就业' 经常被一起分析"
        """
        candidates = []

        # 从 topics.json 中提取 related_topics 关联
        topic_pairs: Dict[Tuple[str, str], int] = Counter()

        for topic_title, topic_info in self.topics_data.items():
            related = topic_info.get('related_topics', [])
            for rel in related:
                pair = tuple(sorted([topic_title, rel]))
                topic_pairs[pair] += 1

        # 从会话中提取同时出现的关键词模式
        # 检查不同会话的主题之间的关联
        session_topics = []
        for session in self.sessions_data:
            topic = session.get('topic', '')
            if topic:
                session_topics.append((session.get('id', ''), topic))

        # 用主题关键词匹配
        for (id1, topic1), (id2, topic2) in combinations(session_topics, 2):
            if topic1 == topic2:
                continue
            # 检查关键词重叠
            kw1 = set(self.topics_data.get(topic1, {}).get('keywords', []))
            kw2 = set(self.topics_data.get(topic2, {}).get('keywords', []))
            overlap = kw1 & kw2
            if len(overlap) >= 2:
                pair = tuple(sorted([topic1, topic2]))
                topic_pairs[pair] += 1

        # 生成候选模式
        for pair, count in topic_pairs.most_common(20):
            if count < 2:
                continue

            evidence = []
            for session in self.sessions_data:
                topic = session.get('topic', '')
                keywords = set(self.topics_data.get(topic, {}).get('keywords', []))
                # 检查是否与 pair 中的主题相关
                if topic in pair:
                    evidence.append(session.get('id', ''))

            confidence = self._calculate_confidence(
                count, max(len(self.sessions_data), len(self.topics_data), 1), evidence
            )

            candidates.append({
                'type': 'topic_association',
                'rule': f"'{pair[0]}' 和 '{pair[1]}' 存在主题关联 (关联度 {count})",
                'confidence': round(confidence, 3),
                'occurrences': count,
                'evidence': evidence[:10],
            })

        candidates.sort(key=lambda c: c['occurrences'], reverse=True)
        return candidates[:20]

    def assign_candidate_ids(self, candidates: List[dict]) -> List[dict]:
        """为候选模式分配 ID"""
        max_num = 0
        for pattern in self.patterns_data:
            pid = pattern.get('id', '')
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

        marked_count = 0
        for session in sessions:
            if not session.get('analyzed', False):
                session['analyzed'] = True
                marked_count += 1

        sessions_file['sessions'] = sessions

        filepath = self.memory_dir / 'sessions.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sessions_file, f, ensure_ascii=False, indent=2)
            f.write('\n')

        print(f"[pattern_analyzer] 已标记 {marked_count} 条会话为已分析", file=sys.stderr)

    def compute_statistics(self) -> dict:
        """计算统计信息"""
        total_topics = len(self.topics_data)
        total_sources = len(self.sources_data)
        total_frameworks = len(self.frameworks_data)

        # 分析类型分布
        type_counter = Counter()
        mode_counter = Counter()
        quality_scores = []

        for session in self.sessions_data:
            atype = session.get('analysis_type', '')
            if atype:
                type_counter[atype] += 1
            mode = session.get('mode', '')
            if mode:
                mode_counter[mode] += 1
            quality = session.get('quality_score', 0.0)
            if quality > 0:
                quality_scores.append(quality)

        most_common_type = type_counter.most_common(1)[0][0] if type_counter else ''
        most_common_mode = mode_counter.most_common(1)[0][0] if mode_counter else ''
        avg_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.0

        return {
            'total_sessions': len(self.sessions_data),
            'total_topics': total_topics,
            'total_sources': total_sources,
            'total_frameworks': total_frameworks,
            'most_common_type': most_common_type,
            'most_common_mode': most_common_mode,
            'average_quality': avg_quality,
            'type_distribution': dict(type_counter),
            'mode_distribution': dict(mode_counter),
        }

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

        candidates = []

        # 1. 框架效果模式
        print("[pattern_analyzer] 分析框架效果模式...", file=sys.stderr)
        fw_patterns = self.analyze_framework_effectiveness()
        candidates.extend(fw_patterns)
        print(f"[pattern_analyzer]   发现 {len(fw_patterns)} 个候选", file=sys.stderr)

        # 2. 来源可靠性模式
        print("[pattern_analyzer] 分析来源可靠性模式...", file=sys.stderr)
        src_patterns = self.analyze_source_reliability()
        candidates.extend(src_patterns)
        print(f"[pattern_analyzer]   发现 {len(src_patterns)} 个候选", file=sys.stderr)

        # 3. 写作优化模式
        print("[pattern_analyzer] 分析写作优化模式...", file=sys.stderr)
        writing_patterns = self.analyze_writing_optimization()
        candidates.extend(writing_patterns)
        print(f"[pattern_analyzer]   发现 {len(writing_patterns)} 个候选", file=sys.stderr)

        # 4. 分析深度模式
        print("[pattern_analyzer] 分析深度策略模式...", file=sys.stderr)
        depth_patterns = self.analyze_analysis_depth()
        candidates.extend(depth_patterns)
        print(f"[pattern_analyzer]   发现 {len(depth_patterns)} 个候选", file=sys.stderr)

        # 5. 主题关联模式
        print("[pattern_analyzer] 分析主题关联模式...", file=sys.stderr)
        topic_patterns = self.analyze_topic_association()
        candidates.extend(topic_patterns)
        print(f"[pattern_analyzer]   发现 {len(topic_patterns)} 个候选", file=sys.stderr)

        # 按置信度降序
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
        description='战略分析跨会话模式分析器 - 从历史会话中发现重复出现的模式'
    )
    parser.add_argument(
        'memory_dir',
        help='记忆目录路径（如 ~/.claude/skills/strategic-insight-longform-v3.0/memory/）'
    )
    parser.add_argument(
        'output_file',
        help='输出文件路径（如 pattern-candidates.json）'
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
