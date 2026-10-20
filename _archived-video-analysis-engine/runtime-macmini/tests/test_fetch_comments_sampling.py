#!/usr/bin/env python3
"""
测试 fetch_comments.py 的分页、分层采样和高赞回复功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import unittest
from unittest.mock import patch, MagicMock
from fetch_comments import (
    fetch_comments_multi_page,
    fetch_comment_replies,
    process_comments_from_raw_list,
)


class TestCommentsSampling(unittest.TestCase):
    """测试评论采样扩量功能"""

    def _mock_reply(self, rpid, content, like=10, rcount=0):
        """生成 mock 评论数据"""
        return {
            "rpid": rpid,
            "member": {
                "mid": 12345,
                "uname": f"用户{rpid}",
                "avatar": "http://avatar.url",
                "level_info": {"current_level": 6},
                "vip": {"status": 0}
            },
            "content": {"message": content},
            "ctime": 1640000000 + rpid,
            "like": like,
            "rcount": rcount,
            "is_top": False,
            "is_up": False
        }

    @patch('fetch_comments.fetch_comments')
    def test_multi_page_hot_comments(self, mock_fetch):
        """测试分页拉取热门评论"""
        # Mock 返回3页，每页20条
        mock_fetch.side_effect = [
            # 第1页
            {
                "code": 0,
                "data": {
                    "page": {"count": 60, "acount": 150},
                    "replies": [self._mock_reply(i, f"热门评论{i}", like=100-i) for i in range(20)]
                }
            },
            # 第2页
            {
                "code": 0,
                "data": {
                    "replies": [self._mock_reply(i+20, f"热门评论{i+20}", like=80-i) for i in range(20)]
                }
            },
            # 第3页
            {
                "code": 0,
                "data": {
                    "replies": [self._mock_reply(i+40, f"热门评论{i+40}", like=60-i) for i in range(20)]
                }
            },
        ]

        # 请求50条，应该分3页拉取
        comments, total, acount = fetch_comments_multi_page(12345, sort=2, target_count=50, sessdata=None)

        self.assertEqual(len(comments), 50)
        self.assertEqual(total, 60)
        self.assertEqual(acount, 150)
        self.assertEqual(mock_fetch.call_count, 3)

    @patch('fetch_comments.fetch_comments')
    def test_multi_page_stops_at_end(self, mock_fetch):
        """测试分页在评论用尽时停止"""
        mock_fetch.side_effect = [
            {
                "code": 0,
                "data": {
                    "page": {"count": 25, "acount": 50},
                    "replies": [self._mock_reply(i, f"评论{i}") for i in range(20)]
                }
            },
            {
                "code": 0,
                "data": {
                    "replies": [self._mock_reply(i+20, f"评论{i+20}") for i in range(5)]
                }
            },
        ]

        # 请求100条，但只有25条
        comments, total, _ = fetch_comments_multi_page(12345, sort=2, target_count=100, sessdata=None)

        self.assertEqual(len(comments), 25)
        self.assertEqual(total, 25)
        self.assertEqual(mock_fetch.call_count, 2)

    @patch('fetch_comments.fetch_comments')
    def test_multi_page_handles_failure(self, mock_fetch):
        """测试分页遇到失败时 graceful 返回已有数据"""
        mock_fetch.side_effect = [
            {
                "code": 0,
                "data": {
                    "page": {"count": 60, "acount": 150},
                    "replies": [self._mock_reply(i, f"评论{i}") for i in range(20)]
                }
            },
            {"code": -400, "message": "请求错误"},
        ]

        # 第2页失败，应返回第1页的20条
        comments, total, _ = fetch_comments_multi_page(12345, sort=2, target_count=50, sessdata=None)

        self.assertEqual(len(comments), 20)
        self.assertEqual(total, 60)

    @patch('fetch_comments.requests.get')
    def test_fetch_comment_replies(self, mock_get):
        """测试获取高赞回复（楼中楼）"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "replies": [
                    {
                        "rpid": 5001,
                        "member": {"mid": 999, "uname": "回复者1"},
                        "content": {"message": "这是一条回复"},
                        "like": 10,
                        "ctime": 1640001000
                    },
                    {
                        "rpid": 5002,
                        "member": {"mid": 888, "uname": "回复者2"},
                        "content": {"message": "这是另一条回复"},
                        "like": 5,
                        "ctime": 1640002000
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        replies = fetch_comment_replies(oid=12345, root_rpid=100, sessdata=None, ps=10)

        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["rpid"], 5001)
        self.assertEqual(replies[0]["content"], "这是一条回复")
        self.assertEqual(replies[1]["user"]["name"], "回复者2")

    @patch('fetch_comments.requests.get')
    def test_fetch_comment_replies_failure(self, mock_get):
        """测试楼中楼获取失败时返回空列表"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -400, "message": "请求错误"}
        mock_get.return_value = mock_response

        replies = fetch_comment_replies(oid=12345, root_rpid=100, sessdata=None)

        self.assertEqual(replies, [])

    @patch('fetch_comments.requests.get')
    def test_fetch_comment_replies_network_error(self, mock_get):
        """测试楼中楼网络错误时返回空列表"""
        mock_get.side_effect = Exception("Network timeout")

        replies = fetch_comment_replies(oid=12345, root_rpid=100, sessdata=None)

        self.assertEqual(replies, [])

    def test_process_comments_from_raw_list(self):
        """测试从原始列表处理评论"""
        raw_replies = [
            self._mock_reply(1, "第一条评论", like=100, rcount=5),
            self._mock_reply(2, "第二条评论", like=50, rcount=0),
        ]

        comments = process_comments_from_raw_list(raw_replies)

        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]["rpid"], 1)
        self.assertEqual(comments[0]["content"], "第一条评论")
        self.assertEqual(comments[0]["like"], 100)
        self.assertEqual(comments[0]["rcount"], 5)
        self.assertEqual(comments[1]["rpid"], 2)

    def test_process_comments_with_limit(self):
        """测试处理评论时限制数量"""
        raw_replies = [self._mock_reply(i, f"评论{i}") for i in range(50)]

        comments = process_comments_from_raw_list(raw_replies, top_n=10)

        self.assertEqual(len(comments), 10)
        self.assertEqual(comments[0]["rpid"], 0)
        self.assertEqual(comments[9]["rpid"], 9)

    @patch('fetch_comments.fetch_comments')
    def test_merged_deduplication(self, mock_fetch):
        """测试热门+时间序合并去重逻辑（通过原始列表模拟）"""
        # 模拟热门评论: rpid 1-20
        hot_replies = [self._mock_reply(i, f"热门{i}", like=100-i) for i in range(1, 21)]
        # 模拟时间序评论: rpid 15-34（其中15-20重复，共6条）
        recent_replies = [self._mock_reply(i, f"最新{i}", like=10) for i in range(15, 35)]

        hot_comments = process_comments_from_raw_list(hot_replies)
        recent_comments = process_comments_from_raw_list(recent_replies)

        # 合并去重
        seen_rpids = set()
        merged = []
        for c in hot_comments + recent_comments:
            if c["rpid"] not in seen_rpids:
                seen_rpids.add(c["rpid"])
                merged.append(c)

        # 热门20条(1-20) + 时间序20条(15-34)，其中15-20重复 = 34条去重后
        self.assertEqual(len(merged), 34)
        self.assertEqual(len(seen_rpids), 34)


if __name__ == '__main__':
    unittest.main()
