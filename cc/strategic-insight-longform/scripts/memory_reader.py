#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战略分析记忆上下文读取器
从持久化记忆中匹配与当前分析主题相关的上下文

功能：
1. 读取 memory/ 下所有 6 个 JSON 文件
2. 根据输入主题/关键词匹配相关历史分析（topics.json）
3. 获取来源可靠性记录（sources.json）
4. 获取框架推荐（frameworks.json - 根据分析类型推荐最佳框架）
5. 获取最近会话（sessions.json - 最近 N 条）
6. 获取活跃模式（patterns.json - status==active）
7. 获取用户偏好（preferences.json）
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Set, Tuple


class MemoryReader:
    """战略分析记忆上下文读取器"""

    # 中文关键词提取模式（2-6字）
    KEYWORD_PATTERN = re.compile(r'[\u4e00-\u9fff]{2,6}')

    # 英文关键词/缩写模式
    EN_KEYWORD_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9\-]{1,20}')

    # 常见停用词
    STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
        '没有', '看', '好', '自己', '这', '那', '里', '后', '以', '所',
        '如果', '可以', '因为', '所以', '但是', '而且', '或者', '还是',
        '已经', '正在', '可能', '应该', '需要', '能够', '这个', '那个',
        '什么', '怎么', '哪个', '为什么', '大家', '我们', '你们', '他们',
        '今天', '明天', '昨天', '现在', '然后', '其实', '觉得', '知道',
        '时候', '问题', '工作', '情况', '方面', '进行', '开始', '通过',
        '关于', '对于', '之后', '之前', '比较', '这样', '那样', '一下',
        '一些', '一起', '一直', '不是', '没有', '还有', '这里', '那里',
        '分析', '研究', '报告', '内容', '部分', '整体', '具体', '相关',
    }

    DEFAULT_DECAY_RATE = 0.995

    # 分析类型列表
    ANALYSIS_TYPES = {
        'phenomenon', 'industry', 'enterprise',
        'trend', 'comparison', 'exploratory',
    }

    def __init__(
        self,
        memory_dir: Path,
        max_recent_sessions: int = 5,
        analysis_type: Optional[str] = None,
    ):
        self.memory_dir = memory_dir
        self.max_recent_sessions = max_recent_sessions
        self.analysis_type = analysis_type
        self.topics_data: Dict[str, dict] = {}
        self.sources_data: Dict[str, dict] = {}
        self.frameworks_data: Dict[str, dict] = {}
        self.sessions_data: List[dict] = []
        self.patterns_data: List[dict] = []
        self.preferences_data: dict = {}

    def load_memory(self):
        """加载所有记忆文件"""
        topics_file = self._load_json('topics.json')
        self.topics_data = topics_file.get('topics', {})

        sources_file = self._load_json('sources.json')
        self.sources_data = sources_file.get('sources', {})

        frameworks_file = self._load_json('frameworks.json')
        self.frameworks_data = frameworks_file.get('frameworks', {})

        sessions_file = self._load_json('sessions.json')
        self.sessions_data = sessions_file.get('sessions', [])

        patterns_file = self._load_json('patterns.json')
        self.patterns_data = patterns_file.get('patterns', [])

        self.preferences_data = self._load_json('preferences.json')

        print(f"[memory_reader] 已加载记忆: "
              f"主题 {len(self.topics_data)}, "
              f"来源 {len(self.sources_data)}, "
              f"框架 {len(self.frameworks_data)}, "
              f"会话 {len(self.sessions_data)}, "
              f"模式 {len(self.patterns_data)}",
              file=sys.stderr)

    def _load_json(self, filename: str) -> dict:
        """安全加载 JSON 文件"""
        filepath = self.memory_dir / filename
        if not filepath.exists():
            print(f"[memory_reader] 记忆文件不存在，使用空数据: {filepath}", file=sys.stderr)
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[memory_reader] JSON 解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def extract_keywords(self, text: str) -> List[str]:
        """从输入文本提取关键词"""
        from collections import Counter

        # 中文关键词
        zh_matches = self.KEYWORD_PATTERN.findall(text)
        zh_keywords = [w for w in zh_matches if w not in self.STOPWORDS]

        # 英文关键词/缩写
        en_matches = self.EN_KEYWORD_PATTERN.findall(text)
        en_keywords = [w for w in en_matches if len(w) >= 2]

        all_keywords = zh_keywords + en_keywords
        counter = Counter(all_keywords)

        # 取出现2次以上的词，或前30个高频词
        result = [word for word, count in counter.most_common(50) if count >= 2]
        if len(result) < 10:
            result = [word for word, _ in counter.most_common(30)]

        return result

    def match_topics(self, keywords: List[str]) -> Dict[str, dict]:
        """根据关键词匹配历史分析主题"""
        matched = {}
        keyword_set = set(keywords)
        today = date.today()

        for topic_title, topic_info in self.topics_data.items():
            topic_keywords = set(topic_info.get('keywords', []))
            topic_type = topic_info.get('type', '')

            # 匹配分数计算
            score = 0.0

            # 1. 主题标题包含在输入中
            title_words = set(self.KEYWORD_PATTERN.findall(topic_title))
            title_overlap = title_words & keyword_set
            if title_overlap:
                score += len(title_overlap) * 2.0

            # 2. 关键词交集
            keyword_overlap = topic_keywords & keyword_set
            if keyword_overlap:
                score += len(keyword_overlap) * 1.0

            # 3. 分析类型匹配
            if self.analysis_type and topic_type == self.analysis_type:
                score += 1.0

            if score <= 0:
                continue

            # 贝叶斯平滑置信度
            analysis_count = topic_info.get('analysis_count', 0)
            base_confidence = analysis_count / (analysis_count + 3)

            # 时间衰减
            last_analyzed_str = topic_info.get('last_analyzed', '')
            if last_analyzed_str:
                try:
                    last_analyzed = datetime.fromisoformat(last_analyzed_str).date()
                    days_since = (today - last_analyzed).days
                except (ValueError, TypeError):
                    days_since = 30
            else:
                days_since = 30

            confidence = base_confidence * (self.DEFAULT_DECAY_RATE ** days_since)

            matched[topic_title] = {
                'historical_insights': topic_info.get('historical_insights', []),
                'quality_scores': topic_info.get('quality_scores', []),
                'analysis_count': analysis_count,
                'type': topic_type,
                'related_topics': topic_info.get('related_topics', []),
                'match_score': round(score, 2),
                'confidence': round(confidence, 3),
            }

        # 按匹配分数降序排列
        matched = dict(sorted(
            matched.items(),
            key=lambda x: x[1]['match_score'],
            reverse=True,
        ))

        return matched

    def recommend_frameworks(self) -> List[dict]:
        """根据分析类型推荐最佳框架"""
        recommendations = []

        for fw_id, fw_info in self.frameworks_data.items():
            best_for = fw_info.get('best_for', [])
            usage_count = fw_info.get('usage_count', 0)
            avg_quality = fw_info.get('avg_quality_score', 0.0)
            display_name = fw_info.get('display_name', fw_id)

            score = 0.0
            reason_parts = []

            # 1. 分析类型匹配
            if self.analysis_type and self.analysis_type in best_for:
                score += 3.0
                reason_parts.append(f"适合{self.analysis_type}类型分析")

            # 2. 历史质量评分加权
            if usage_count > 0 and avg_quality > 0:
                quality_weight = avg_quality / 5.0  # 归一化到 0-1
                bayesian_quality = (usage_count * quality_weight) / (usage_count + 3)
                score += bayesian_quality * 2.0
                reason_parts.append(f"历史质量 {avg_quality:.1f}/5 ({usage_count}次使用)")

            # 3. 按分析类型的效果加成
            if self.analysis_type:
                effectiveness = fw_info.get('effectiveness_by_type', {})
                type_score = effectiveness.get(self.analysis_type, {}).get('avg_score', 0)
                if type_score > 0:
                    score += type_score / 5.0
                    reason_parts.append(f"该类型效果评分 {type_score:.1f}")

            # 即使没有历史数据，适合该类型的框架也应推荐
            if score <= 0 and self.analysis_type and self.analysis_type in best_for:
                score = 1.0
                reason_parts.append(f"适合{self.analysis_type}类型（暂无使用数据）")

            if score > 0 or (not self.analysis_type and best_for):
                # 无指定类型时也列出所有框架
                if not reason_parts:
                    reason_parts.append(f"适合: {', '.join(best_for)}")
                    score = 0.5

                recommendations.append({
                    'id': fw_id,
                    'display_name': display_name,
                    'score': round(score, 3),
                    'reason': '; '.join(reason_parts),
                    'best_for': best_for,
                })

        # 按分数降序
        recommendations.sort(key=lambda r: r['score'], reverse=True)
        return recommendations

    def get_reliable_sources(self) -> Dict[str, dict]:
        """获取来源可靠性记录，按可靠性排序"""
        # 可靠性等级排序权重
        grade_weights = {'A': 4, 'B': 3, 'C': 2, 'D': 1}

        sources = {}
        for source_name, source_info in self.sources_data.items():
            grade = source_info.get('credibility_grade', 'C')
            citation_count = source_info.get('citation_count', 0)
            accuracy_rate = source_info.get('accuracy_rate', 0.0)
            domains = source_info.get('domains', [])

            # 综合排序分数: 等级权重 * 10 + 引用次数
            sort_score = grade_weights.get(grade, 0) * 10 + citation_count

            sources[source_name] = {
                'type': source_info.get('type', ''),
                'credibility_grade': grade,
                'citation_count': citation_count,
                'accuracy_rate': accuracy_rate,
                'domains': domains,
                'sort_score': sort_score,
            }

        # 按 sort_score 降序
        sources = dict(sorted(
            sources.items(),
            key=lambda x: x[1]['sort_score'],
            reverse=True,
        ))

        return sources

    def get_active_patterns(self) -> List[dict]:
        """筛选 status==active 的模式"""
        active = []
        for pattern in self.patterns_data:
            if pattern.get('status') == 'active':
                active.append({
                    'id': pattern.get('id', ''),
                    'type': pattern.get('type', ''),
                    'rule': pattern.get('rule', ''),
                    'confidence': pattern.get('confidence', 0.0),
                })
        return active

    def get_recent_sessions(self) -> List[dict]:
        """获取最近 N 条会话"""
        sorted_sessions = sorted(
            self.sessions_data,
            key=lambda s: s.get('timestamp', ''),
            reverse=True,
        )
        recent = sorted_sessions[:self.max_recent_sessions]

        result = []
        for session in recent:
            result.append({
                'id': session.get('id', ''),
                'timestamp': session.get('timestamp', ''),
                'topic': session.get('topic', ''),
                'analysis_type': session.get('analysis_type', ''),
                'mode': session.get('mode', ''),
                'quality_score': session.get('quality_score', 0.0),
                'key_insights': session.get('key_insights', []),
            })
        return result

    def get_user_preferences(self) -> dict:
        """读取用户偏好"""
        output_prefs = self.preferences_data.get('output_preferences', {})
        analysis_prefs = self.preferences_data.get('analysis_preferences', {})
        return {
            'default_mode': output_prefs.get('default_mode', 'standard'),
            'preferred_format': output_prefs.get('preferred_format', 'obsidian_v3'),
            'wikilink_style': output_prefs.get('wikilink_style', 'short'),
            'language': output_prefs.get('language', 'zh-CN'),
            'preferred_depth': analysis_prefs.get('preferred_depth', 'deep'),
            'enable_counterfactual': analysis_prefs.get('enable_counterfactual', True),
            'enable_cross_matrix': analysis_prefs.get('enable_cross_matrix', True),
            'min_sources': analysis_prefs.get('min_sources', 3),
        }

    def build_context(self, input_text: str) -> dict:
        """构建完整的记忆上下文"""
        # 提取关键词
        keywords = self.extract_keywords(input_text)
        print(f"[memory_reader] 提取到 {len(keywords)} 个关键词: "
              f"{keywords[:10]}{'...' if len(keywords) > 10 else ''}",
              file=sys.stderr)

        # 匹配历史主题
        matched_topics = self.match_topics(keywords)
        print(f"[memory_reader] 匹配到 {len(matched_topics)} 个历史主题", file=sys.stderr)

        # 推荐框架
        recommended_frameworks = self.recommend_frameworks()
        print(f"[memory_reader] 推荐 {len(recommended_frameworks)} 个分析框架", file=sys.stderr)

        # 来源可靠性
        reliable_sources = self.get_reliable_sources()
        print(f"[memory_reader] 加载 {len(reliable_sources)} 个来源记录", file=sys.stderr)

        # 活跃模式
        active_patterns = self.get_active_patterns()
        print(f"[memory_reader] 找到 {len(active_patterns)} 个活跃模式", file=sys.stderr)

        # 最近会话
        recent_sessions = self.get_recent_sessions()
        print(f"[memory_reader] 加载最近 {len(recent_sessions)} 条会话", file=sys.stderr)

        # 用户偏好
        user_preferences = self.get_user_preferences()

        return {
            'matched_topics': matched_topics,
            'recommended_frameworks': recommended_frameworks,
            'reliable_sources': reliable_sources,
            'active_patterns': active_patterns,
            'recent_sessions': recent_sessions,
            'user_preferences': user_preferences,
        }


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='战略分析记忆上下文读取器 - 从持久化记忆中匹配与当前分析主题相关的上下文'
    )
    parser.add_argument(
        'input_topic',
        help='输入主题（字符串）或包含分析描述的文件路径'
    )
    parser.add_argument(
        'output_file',
        help='输出文件路径（如 memory-context.json）'
    )
    parser.add_argument(
        '--memory-dir',
        default=None,
        help='记忆目录路径（默认: 脚本所在目录的 ../memory/）'
    )
    parser.add_argument(
        '--max-recent-sessions',
        type=int,
        default=5,
        help='最近会话数量（默认: 5）'
    )
    parser.add_argument(
        '--analysis-type',
        choices=['phenomenon', 'industry', 'enterprise', 'trend', 'comparison', 'exploratory'],
        default=None,
        help='分析类型（用于框架推荐和主题匹配）'
    )
    return parser.parse_args()


def main():
    """命令行入口"""
    args = parse_args()

    output_file = Path(args.output_file)

    # 确定记忆目录
    if args.memory_dir:
        memory_dir = Path(args.memory_dir).expanduser()
    else:
        memory_dir = Path(__file__).resolve().parent.parent / 'memory'

    # 确定输入文本
    input_path = Path(args.input_topic)
    if input_path.exists() and input_path.is_file():
        with open(input_path, 'r', encoding='utf-8') as f:
            input_text = f.read()
        print(f"[memory_reader] 从文件读取输入: {input_path} ({len(input_text)} 字符)", file=sys.stderr)
    else:
        input_text = args.input_topic
        print(f"[memory_reader] 使用字符串输入: {input_text[:100]}", file=sys.stderr)

    if not memory_dir.exists():
        print(f"[memory_reader] 警告: 记忆目录不存在: {memory_dir}", file=sys.stderr)
        context = {
            'matched_topics': {},
            'recommended_frameworks': [],
            'reliable_sources': {},
            'active_patterns': [],
            'recent_sessions': [],
            'user_preferences': {
                'default_mode': 'standard',
                'preferred_format': 'obsidian_v3',
                'wikilink_style': 'short',
                'language': 'zh-CN',
                'preferred_depth': 'deep',
                'enable_counterfactual': True,
                'enable_cross_matrix': True,
                'min_sources': 3,
            },
        }
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
        print(f"[memory_reader] 空上下文已保存到: {output_file}", file=sys.stderr)
        sys.exit(0)

    print(f"[memory_reader] 记忆目录: {memory_dir}", file=sys.stderr)

    # 构建上下文
    reader = MemoryReader(
        memory_dir=memory_dir,
        max_recent_sessions=args.max_recent_sessions,
        analysis_type=args.analysis_type,
    )
    reader.load_memory()
    context = reader.build_context(input_text)

    # 保存输出
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    print(f"[memory_reader] 记忆上下文已保存到: {output_file}", file=sys.stderr)

    # 输出摘要
    total_matched = len(context['matched_topics'])
    print(f"[memory_reader] 总匹配: {total_matched} 个主题, "
          f"{len(context['recommended_frameworks'])} 个推荐框架",
          file=sys.stderr)


if __name__ == '__main__':
    main()
