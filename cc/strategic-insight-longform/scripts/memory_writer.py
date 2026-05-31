#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战略分析记忆持久化写入器
在分析完成后更新持久化记忆

功能：
1. 从工作目录读取分析结果（topic-analysis.json, core-insights.md, source-report.md, quality-report.md 等）
2. 更新 topics.json（新增/更新主题、历史洞察、质量评分）
3. 更新 sources.json（新增/更新来源可靠性）
4. 更新 frameworks.json（更新使用次数、质量评分、按类型效果）
5. 追加 sessions.json（新会话记录，FIFO 轮转）
"""

import re
import sys
import json
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class MemoryWriter:
    """战略分析记忆持久化写入器"""

    def __init__(self, workspace_dir: Path, memory_dir: Path):
        self.workspace_dir = workspace_dir
        self.memory_dir = memory_dir
        self.topic_analysis: dict = {}
        self.quality_report: dict = {}
        self.core_insights_text: str = ''
        self.source_report_text: str = ''

    def load_workspace(self):
        """加载工作目录中的分析结果"""
        # 主分析文件（必须存在）
        self.topic_analysis = self._load_json(self.workspace_dir / 'topic-analysis.json')
        if not self.topic_analysis:
            print("[memory_writer] 警告: topic-analysis.json 不存在或为空", file=sys.stderr)

        # 质量报告（可选）
        self.quality_report = self._load_json(self.workspace_dir / 'quality-report.json')
        # 兼容 .md 格式
        if not self.quality_report:
            qr_md = self.workspace_dir / 'quality-report.md'
            if qr_md.exists():
                self.quality_report = self._parse_quality_report_md(qr_md)

        # 核心洞察（可选）
        insights_file = self.workspace_dir / 'core-insights.md'
        if insights_file.exists():
            self.core_insights_text = self._read_text(insights_file)

        # 来源报告（可选）
        source_file = self.workspace_dir / 'source-report.md'
        if source_file.exists():
            self.source_report_text = self._read_text(source_file)

        print(f"[memory_writer] 工作目录加载完成: topic-analysis={'有' if self.topic_analysis else '无'}, "
              f"quality={'有' if self.quality_report else '无'}, "
              f"insights={'有' if self.core_insights_text else '无'}, "
              f"sources={'有' if self.source_report_text else '无'}",
              file=sys.stderr)

    def _load_json(self, filepath: Path) -> dict:
        """安全加载 JSON 文件"""
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[memory_writer] JSON 解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def _load_memory_json(self, filename: str) -> dict:
        """加载记忆文件"""
        filepath = self.memory_dir / filename
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[memory_writer] 记忆文件解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def _read_text(self, filepath: Path) -> str:
        """安全读取文本文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except OSError as e:
            print(f"[memory_writer] 读取失败: {filepath}: {e}", file=sys.stderr)
            return ''

    def _safe_write(self, filepath: Path, data: dict):
        """安全写入（write-then-rename）"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(filepath.parent),
                suffix='.tmp',
                prefix=filepath.stem + '_',
            )
            tmp_file = Path(tmp_path)
            with open(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')
            tmp_file.rename(filepath)
            print(f"[memory_writer] 已更新: {filepath}", file=sys.stderr)
        except OSError as e:
            print(f"[memory_writer] 写入失败: {filepath}: {e}", file=sys.stderr)
            if 'tmp_file' in locals() and tmp_file.exists():
                tmp_file.unlink()

    def _parse_quality_report_md(self, filepath: Path) -> dict:
        """从 quality-report.md 解析质量评分"""
        text = self._read_text(filepath)
        if not text:
            return {}

        result = {}

        # 尝试匹配评分（支持数字和字母等级）
        score_patterns = [
            re.compile(r'(?:总[体分]|overall|综合)[评分]*\s*[:：]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'(?:质量|quality)[评分]*\s*[:：]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d+)?)\s*/\s*(?:5|10|100)', re.IGNORECASE),
        ]
        for pattern in score_patterns:
            m = pattern.search(text)
            if m:
                try:
                    score = float(m.group(1))
                    # 归一化到 0-5
                    if score > 10:
                        score = score / 20  # 100分制 -> 5分制
                    elif score > 5:
                        score = score / 2   # 10分制 -> 5分制
                    result['quality_score'] = round(score, 2)
                    break
                except ValueError:
                    pass

        return result

    def _extract_insights_from_md(self) -> List[str]:
        """从 core-insights.md 提取洞察摘要（## 标题下的首行）"""
        if not self.core_insights_text:
            return []

        insights = []
        lines = self.core_insights_text.split('\n')
        found_heading = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('## '):
                found_heading = True
                continue
            if found_heading and stripped and not stripped.startswith('#'):
                # 去掉 markdown 列表标记
                clean = re.sub(r'^[-*>]\s*', '', stripped).strip()
                if clean and len(clean) >= 5:
                    insights.append(clean[:200])  # 限制长度
                found_heading = False

        return insights[:10]  # 最多 10 条

    def _extract_sources_from_md(self) -> List[dict]:
        """从 source-report.md 提取来源信息"""
        if not self.source_report_text:
            return []

        sources = []
        lines = self.source_report_text.split('\n')

        # 尝试识别来源条目: "- **来源名** (类型): 描述" 或表格行
        source_pattern = re.compile(
            r'[-*]\s*\*\*([^*]+)\*\*\s*(?:\(([^)]*)\))?\s*[:：]?\s*(.*)'
        )
        # 表格行: | 来源名 | 类型 | 可靠性 | ... |
        table_pattern = re.compile(
            r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([ABCD])\s*\|'
        )

        for line in lines:
            stripped = line.strip()

            m = source_pattern.match(stripped)
            if m:
                name = m.group(1).strip()
                source_type = m.group(2).strip() if m.group(2) else ''
                desc = m.group(3).strip()
                if name:
                    sources.append({
                        'name': name,
                        'type': source_type,
                        'description': desc,
                    })
                continue

            m = table_pattern.match(stripped)
            if m:
                name = m.group(1).strip()
                source_type = m.group(2).strip()
                grade = m.group(3).strip()
                if name and name != '来源' and name != '---':
                    sources.append({
                        'name': name,
                        'type': source_type,
                        'grade': grade,
                    })

        return sources

    def update_topics(self):
        """更新 topics.json"""
        topics_file = self._load_memory_json('topics.json')
        if not topics_file:
            topics_file = {'version': '1.0', 'topics': {}}
        topics = topics_file.get('topics', {})

        now_str = datetime.now().strftime('%Y-%m-%d')

        # 从 topic-analysis.json 提取主题信息
        topic_title = self.topic_analysis.get('topic', '')
        analysis_type = self.topic_analysis.get('analysis_type', self.topic_analysis.get('type', ''))
        keywords = self.topic_analysis.get('keywords', [])

        if not topic_title:
            print("[memory_writer] topic-analysis.json 中无 topic 字段，跳过主题更新", file=sys.stderr)
            return

        # 提取洞察
        insights = self._extract_insights_from_md()

        # 获取质量评分
        quality_score = self.quality_report.get('quality_score', 0.0)
        if not quality_score:
            quality_score = self.topic_analysis.get('quality_score', 0.0)

        if topic_title in topics:
            # 更新已有主题
            existing = topics[topic_title]
            existing['analysis_count'] = existing.get('analysis_count', 0) + 1
            existing['last_analyzed'] = now_str

            # 合并关键词
            existing_keywords = set(existing.get('keywords', []))
            existing_keywords.update(keywords)
            existing['keywords'] = sorted(existing_keywords)

            # 追加洞察（保留最近 20 条）
            historical = existing.get('historical_insights', [])
            historical.extend(insights)
            existing['historical_insights'] = historical[-20:]

            # 追加质量评分（保留最近 20 条）
            scores = existing.get('quality_scores', [])
            if quality_score > 0:
                scores.append(quality_score)
            existing['quality_scores'] = scores[-20:]

            # 更新类型（如果之前为空）
            if not existing.get('type') and analysis_type:
                existing['type'] = analysis_type

            print(f"[memory_writer] 更新已有主题: {topic_title} (第 {existing['analysis_count']} 次分析)",
                  file=sys.stderr)
        else:
            # 新增主题
            topics[topic_title] = {
                'type': analysis_type,
                'keywords': keywords,
                'analysis_count': 1,
                'first_analyzed': now_str,
                'last_analyzed': now_str,
                'historical_insights': insights,
                'quality_scores': [quality_score] if quality_score > 0 else [],
                'related_topics': self.topic_analysis.get('related_topics', []),
            }
            print(f"[memory_writer] 新增主题: {topic_title}", file=sys.stderr)

        topics_file['topics'] = topics
        self._safe_write(self.memory_dir / 'topics.json', topics_file)

    def update_sources(self):
        """更新 sources.json"""
        sources_file = self._load_memory_json('sources.json')
        if not sources_file:
            sources_file = {'version': '1.0', 'sources': {}}
        sources = sources_file.get('sources', {})

        now_str = datetime.now().strftime('%Y-%m-%d')

        # 从 source-report.md 提取来源
        extracted_sources = self._extract_sources_from_md()

        # 也从 topic-analysis.json 提取来源
        ta_sources = self.topic_analysis.get('sources', [])
        if isinstance(ta_sources, list):
            for src in ta_sources:
                if isinstance(src, str):
                    extracted_sources.append({'name': src, 'type': '', 'description': ''})
                elif isinstance(src, dict):
                    extracted_sources.append(src)

        if not extracted_sources:
            print("[memory_writer] 未发现来源信息，跳过来源更新", file=sys.stderr)
            return

        new_count = 0
        updated_count = 0

        for src_info in extracted_sources:
            name = src_info.get('name', '')
            if not name or len(name) < 2:
                continue

            if name in sources:
                # 更新已有来源
                existing = sources[name]
                existing['citation_count'] = existing.get('citation_count', 0) + 1
                existing['last_cited'] = now_str

                # 更新可靠性等级（如果提供了新的）
                new_grade = src_info.get('grade', '')
                if new_grade in ('A', 'B', 'C', 'D'):
                    existing['credibility_grade'] = new_grade

                # 合并领域
                new_domains = src_info.get('domains', [])
                if new_domains:
                    existing_domains = set(existing.get('domains', []))
                    existing_domains.update(new_domains)
                    existing['domains'] = sorted(existing_domains)

                updated_count += 1
            else:
                # 新增来源
                source_type = src_info.get('type', 'user_material')
                # 类型规范化
                type_mapping = {
                    '政府': 'government', '官方': 'government',
                    '研究': 'research_institution', '智库': 'research_institution',
                    '咨询': 'consulting', '券商': 'consulting',
                    '媒体': 'media', '新闻': 'media',
                    '学术': 'academic', '高校': 'academic', '大学': 'academic',
                }
                for zh_type, en_type in type_mapping.items():
                    if zh_type in source_type:
                        source_type = en_type
                        break

                sources[name] = {
                    'type': source_type,
                    'credibility_grade': src_info.get('grade', 'C'),
                    'citation_count': 1,
                    'accuracy_rate': 0.0,
                    'domains': src_info.get('domains', []),
                    'first_cited': now_str,
                    'last_cited': now_str,
                    'notes': src_info.get('description', ''),
                }
                new_count += 1

        print(f"[memory_writer] 来源: 新增 {new_count}, 更新 {updated_count}", file=sys.stderr)

        sources_file['sources'] = sources
        self._safe_write(self.memory_dir / 'sources.json', sources_file)

    def update_frameworks(self):
        """更新 frameworks.json"""
        frameworks_file = self._load_memory_json('frameworks.json')
        if not frameworks_file:
            frameworks_file = {'version': '1.0', 'frameworks': {}}
        frameworks = frameworks_file.get('frameworks', {})

        # 从 topic-analysis.json 提取使用的框架
        used_frameworks = self.topic_analysis.get('frameworks_used', [])
        analysis_type = self.topic_analysis.get('analysis_type', self.topic_analysis.get('type', ''))

        # 获取质量评分
        quality_score = self.quality_report.get('quality_score', 0.0)
        if not quality_score:
            quality_score = self.topic_analysis.get('quality_score', 0.0)

        if not used_frameworks:
            print("[memory_writer] 未发现使用的框架，跳过框架更新", file=sys.stderr)
            return

        for fw_id in used_frameworks:
            if fw_id not in frameworks:
                # 未知框架，创建基础记录
                frameworks[fw_id] = {
                    'display_name': fw_id,
                    'usage_count': 0,
                    'avg_quality_score': 0.0,
                    'best_for': [],
                    'effectiveness_by_type': {},
                }

            fw = frameworks[fw_id]
            old_count = fw.get('usage_count', 0)
            old_avg = fw.get('avg_quality_score', 0.0)

            # 更新使用次数
            fw['usage_count'] = old_count + 1

            # 更新平均质量评分（增量平均）
            if quality_score > 0:
                if old_count > 0 and old_avg > 0:
                    fw['avg_quality_score'] = round(
                        (old_avg * old_count + quality_score) / (old_count + 1), 2
                    )
                else:
                    fw['avg_quality_score'] = round(quality_score, 2)

            # 更新按类型效果
            if analysis_type and quality_score > 0:
                effectiveness = fw.get('effectiveness_by_type', {})
                if analysis_type not in effectiveness:
                    effectiveness[analysis_type] = {
                        'count': 0,
                        'avg_score': 0.0,
                    }
                type_eff = effectiveness[analysis_type]
                type_count = type_eff.get('count', 0)
                type_avg = type_eff.get('avg_score', 0.0)

                if type_count > 0 and type_avg > 0:
                    type_eff['avg_score'] = round(
                        (type_avg * type_count + quality_score) / (type_count + 1), 2
                    )
                else:
                    type_eff['avg_score'] = round(quality_score, 2)
                type_eff['count'] = type_count + 1

                effectiveness[analysis_type] = type_eff
                fw['effectiveness_by_type'] = effectiveness

            print(f"[memory_writer] 框架更新: {fw_id} (使用次数: {fw['usage_count']}, "
                  f"平均质量: {fw['avg_quality_score']})", file=sys.stderr)

        frameworks_file['frameworks'] = frameworks
        self._safe_write(self.memory_dir / 'frameworks.json', frameworks_file)

    def append_session(self):
        """追加会话到 sessions.json"""
        sessions_file = self._load_memory_json('sessions.json')
        if not sessions_file:
            sessions_file = {'version': '1.0', 'max_sessions': 50, 'sessions': []}
        sessions = sessions_file.get('sessions', [])
        max_sessions = sessions_file.get('max_sessions', 50)

        now = datetime.now().isoformat(timespec='seconds')

        # 生成新 ID
        max_num = 0
        for s in sessions:
            sid = s.get('id', '')
            if sid.startswith('S') and sid[1:].isdigit():
                max_num = max(max_num, int(sid[1:]))
        new_id = f'S{max_num + 1:03d}'

        # 提取会话信息
        topic = self.topic_analysis.get('topic', '')
        analysis_type = self.topic_analysis.get('analysis_type', self.topic_analysis.get('type', ''))
        mode = self.topic_analysis.get('mode', 'standard')
        frameworks_used = self.topic_analysis.get('frameworks_used', [])
        sources_count = len(self.topic_analysis.get('sources', []))

        # 质量评分
        quality_score = self.quality_report.get('quality_score', 0.0)
        if not quality_score:
            quality_score = self.topic_analysis.get('quality_score', 0.0)

        # 持续时间
        duration = self.topic_analysis.get('duration_minutes', 0)

        # 关键洞察
        key_insights = self._extract_insights_from_md()[:5]

        # 使用的模式
        patterns_applied = self.topic_analysis.get('patterns_applied', [])

        new_session = {
            'id': new_id,
            'timestamp': now,
            'topic': topic,
            'analysis_type': analysis_type,
            'mode': mode,
            'frameworks_used': frameworks_used,
            'sources_count': sources_count,
            'quality_score': quality_score,
            'duration_minutes': duration,
            'key_insights': key_insights,
            'patterns_applied': patterns_applied,
            'analyzed': False,
        }

        sessions.append(new_session)

        # FIFO 轮转
        if len(sessions) > max_sessions:
            removed_count = len(sessions) - max_sessions
            sessions = sessions[-max_sessions:]
            print(f"[memory_writer] 会话记录超过上限 {max_sessions}，已删除最早 {removed_count} 条",
                  file=sys.stderr)

        print(f"[memory_writer] 新增会话: {new_id} (主题: {topic}, 类型: {analysis_type})",
              file=sys.stderr)

        sessions_file['sessions'] = sessions
        self._safe_write(self.memory_dir / 'sessions.json', sessions_file)

    def run(self):
        """执行全部更新"""
        print("[memory_writer] 开始更新记忆...", file=sys.stderr)
        self.load_workspace()

        if not self.topic_analysis:
            print("[memory_writer] topic-analysis.json 为空，跳过记忆更新", file=sys.stderr)
            return

        self.update_topics()
        self.update_sources()
        self.update_frameworks()
        self.append_session()

        print("[memory_writer] 记忆更新完成", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='战略分析记忆持久化写入器 - 将分析结果写入持久化记忆'
    )
    parser.add_argument(
        'workspace_dir',
        help='工作目录路径（包含 topic-analysis.json 等分析结果）'
    )
    parser.add_argument(
        'memory_dir',
        help='记忆目录路径（如 ~/.claude/skills/strategic-insight-longform-v3.0/memory/）'
    )
    return parser.parse_args()


def main():
    """命令行入口"""
    args = parse_args()

    workspace_dir = Path(args.workspace_dir)
    memory_dir = Path(args.memory_dir).expanduser()

    if not workspace_dir.exists():
        print(f"[memory_writer] 错误: 工作目录不存在: {workspace_dir}", file=sys.stderr)
        sys.exit(1)

    if not memory_dir.exists():
        print(f"[memory_writer] 错误: 记忆目录不存在: {memory_dir}", file=sys.stderr)
        sys.exit(1)

    writer = MemoryWriter(workspace_dir, memory_dir)
    writer.run()


if __name__ == '__main__':
    main()
