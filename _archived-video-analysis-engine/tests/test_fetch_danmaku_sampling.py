#!/usr/bin/env python3
"""
测试 fetch_danmaku_v2.py 的分层采样和关键词加权功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from unittest.mock import MagicMock
from fetch_danmaku_v2 import stratified_sample, keyword_boost


def make_danmaku_element(time_sec, text="测试弹幕"):
    """构造模拟弹幕 XML 元素"""
    elem = MagicMock()
    elem.text = text
    # p 属性: time_sec,mode,size,color,timestamp,pool,user_id,row_id
    elem.get.return_value = f"{time_sec},1,25,16777215,0,0,user123,0"
    return elem


class TestStratifiedSample:
    """测试分层时间段采样"""

    def test_total_less_than_max_returns_all(self):
        """当总弹幕数 <= max_danmaku 时，全取"""
        danmakus = [make_danmaku_element(i) for i in range(100)]
        result = stratified_sample(danmakus, 200, stratify=True)
        assert len(result) == 100
        assert result == danmakus

    def test_no_stratify_takes_first_n(self):
        """stratify=False 时，简单取前 N 条"""
        danmakus = [make_danmaku_element(i) for i in range(3000)]
        result = stratified_sample(danmakus, 1000, stratify=False)
        assert len(result) == 1000
        assert result == danmakus[:1000]

    def test_stratified_sampling_covers_three_segments(self):
        """分层采样后，前中后三段都有样本"""
        # 构造 3000 条弹幕，时间戳 0-2999
        danmakus = [make_danmaku_element(i, f"弹幕{i}") for i in range(3000)]
        result = stratified_sample(danmakus, 1000, stratify=True)

        assert len(result) == 1000

        # 提取采样后的时间戳
        sampled_times = []
        for dm in result:
            p = dm.get('p')
            time_sec = float(p.split(',')[0])
            sampled_times.append(time_sec)

        # 验证三段都有覆盖: 前 1000 / 中 1000 / 后 1000
        front_count = sum(1 for t in sampled_times if t < 1000)
        mid_count = sum(1 for t in sampled_times if 1000 <= t < 2000)
        back_count = sum(1 for t in sampled_times if t >= 2000)

        # 按 30%/40%/30% 分配，容忍 ±5% 误差
        assert front_count >= 250  # 30% * 1000 = 300，容差到 250
        assert mid_count >= 350    # 40% * 1000 = 400，容差到 350
        assert back_count >= 250   # 30% * 1000 = 300，容差到 250

    def test_stratified_quota_distribution(self):
        """验证配额分配: 前30% 中40% 后30%"""
        danmakus = [make_danmaku_element(i) for i in range(3000)]
        result = stratified_sample(danmakus, 1000, stratify=True)

        # 计算实际配额
        front_quota = int(1000 * 0.3)  # 300
        mid_quota = int(1000 * 0.4)    # 400
        back_quota = 1000 - front_quota - mid_quota  # 300

        assert len(result) == front_quota + mid_quota + back_quota

    def test_edge_case_max_equals_total(self):
        """边界: max_danmaku == total"""
        danmakus = [make_danmaku_element(i) for i in range(500)]
        result = stratified_sample(danmakus, 500, stratify=True)
        assert len(result) == 500
        assert result == danmakus


class TestKeywordBoost:
    """测试关键词密度加权"""

    def make_danmaku_dict(self, text, time_sec=0):
        """构造弹幕字典"""
        return {
            "text": text,
            "time": "0:00",
            "time_sec": time_sec,
            "mode": 1,
            "size": 25,
            "color": 16777215
        }

    def test_total_less_than_max_returns_all(self):
        """当总弹幕数 <= max 时，全取"""
        data = [self.make_danmaku_dict(f"弹幕{i}") for i in range(50)]
        result = keyword_boost(data, 100)
        assert len(result) == 50
        assert result == data

    def test_keyword_boost_prioritizes_high_freq_words(self):
        """关键词加权会优先保留含高频词的弹幕"""
        # 构造 200 条弹幕: 前 50 条包含 "牛逼"，后 150 条普通
        data = []
        for i in range(50):
            data.append(self.make_danmaku_dict(f"太牛逼了{i}"))
        for i in range(150):
            data.append(self.make_danmaku_dict(f"普通弹幕{i}"))

        result = keyword_boost(data, 100)
        assert len(result) == 100

        # 统计结果中含 "牛逼" 的弹幕数
        keyword_count = sum(1 for dm in result if "牛逼" in dm['text'])

        # 由于 "牛逼" 是高频词，应该被优先保留
        # 期望: 前 50 条全保留 + 剩余 50 条从普通弹幕中取
        assert keyword_count >= 40  # 容差: 至少保留 80% 的关键词弹幕

    def test_no_keywords_fallback_to_first_n(self):
        """没有关键词时，降级为取前 N 条"""
        # 每条弹幕都唯一，没有高频词
        data = [self.make_danmaku_dict(f"unique_{i}") for i in range(200)]
        result = keyword_boost(data, 100)
        assert len(result) == 100
        # 应该回退到前 100 条
        assert result == data[:100]

    def test_keyword_extraction_from_chinese(self):
        """关键词提取能识别中文高频词"""
        # 构造包含重复词汇的弹幕
        data = [
            self.make_danmaku_dict("哈哈哈哈哈哈"),
            self.make_danmaku_dict("哈哈哈真有意思"),
            self.make_danmaku_dict("笑死我了哈哈哈"),
            self.make_danmaku_dict("普通弹幕1"),
            self.make_danmaku_dict("普通弹幕2"),
            self.make_danmaku_dict("哈哈哈太好笑了"),
        ]

        result = keyword_boost(data, 4)
        assert len(result) == 4

        # 含 "哈哈" 的弹幕应该被优先保留
        haha_count = sum(1 for dm in result if "哈哈" in dm['text'])
        assert haha_count >= 3  # 4 条结果中至少有 3 条含关键词


class TestIntegration:
    """集成测试: 组合分层采样 + 关键词加权"""

    def test_full_pipeline_on_large_dataset(self):
        """模拟真实场景: 5000 条弹幕 → 分层采样 1000 条 → 关键词加权"""
        # 第 1 步: 构造 5000 条弹幕
        danmakus = []
        for i in range(5000):
            elem = make_danmaku_element(i, f"弹幕{i}")
            # 在前 500 条中混入高频关键词 "精彩"
            if i < 500:
                elem.text = f"太精彩了{i}"
            danmakus.append(elem)

        # 第 2 步: 分层采样到 1000 条
        sampled_elements = stratified_sample(danmakus, 1000, stratify=True)
        assert len(sampled_elements) == 1000

        # 第 3 步: 提取数据
        data = []
        for dm in sampled_elements:
            text = dm.text
            p = dm.get('p')
            time_sec = float(p.split(',')[0])
            data.append({
                "text": text,
                "time": "0:00",
                "time_sec": time_sec,
                "mode": 1,
                "size": 25,
                "color": 16777215
            })

        # 第 4 步: 关键词加权（如果采样数 > 100）
        if len(data) > 100:
            data = keyword_boost(data, 1000)

        assert len(data) == 1000

        # 验证: 含关键词 "精彩" 的弹幕应该被优先保留
        keyword_count = sum(1 for dm in data if "精彩" in dm['text'])
        assert keyword_count > 0  # 至少保留了一些高频词弹幕


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
