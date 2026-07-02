import textwrap

import verify_publishable_report


def _good_report():
    return textwrap.dedent(
        """
        # B站笔记_优质样例

        ## 0. 元信息与来源

        | 字段 | 值 |
        |---|---|
        | 视频 | 示例 |
        | 数据源 | transcript / comments / danmaku |

        ## 1. 逻辑链：从问题到机制

        | 步骤 | 证据 | 推论 |
        |---|---|---|
        | 1 | 主持人提出核心问题 | 明确讨论对象 |
        | 2 | 嘉宾解释机制 | 建立因果关系 |
        | 3 | 回到行业影响 | 形成行动判断 |

        ```mermaid
        flowchart TD
          A[问题] --> B[机制]
          B --> C[影响]
        ```

        ## 2. 弹幕信号

        - 弹幕样本较少，仅作为氛围信号，不作为结论依据。

        ## 2.5 评论区信号

        - 评论区样本较少，主要用于补充观众问题，而不是替代事实判断。

        ## 3. 核心洞察

        ### 💡 洞察 1：主题命中
        这是一段足够长的洞察正文，用来说明报告已经把视频核心问题转化为可复查的判断，并且没有依赖原始转录堆砌。
        ### 💡 洞察 2：机制解释
        这是一段足够长的洞察正文，用来说明报告已经把角色、场景和因果关系组织起来，方便读者复用。
        ### 💡 洞察 3：行动价值
        这是一段足够长的洞察正文，用来说明报告能够落到后续研究、知识卡片或决策问题上。

        ## 4. 内容深度拆解

        ### 模块 1：问题定义
        这是一段模块正文，解释视频的核心问题、背景、角色和冲突。
        ### 模块 2：机制拆解
        这是一段模块正文，解释内容中出现的机制链条、转折点和风险。
        ### 模块 3：后续影响
        这是一段模块正文，解释它如何进入知识库并形成后续主题研究。

        ## 5. 高光片段

        > "一个短句高光。" — [00:10](https://example.com?t=10)

        解读：这句话短而可定位。

        > "第二个短句高光。" — [01:20](https://example.com?t=80)

        解读：这句话能支撑主题。

        ## 6. 知识图谱

        - [[虚拟偶像]] → [[人格资产]] → [[信任机制]]

        ## 7. 批判与行动

        ### 独特价值
        - 它把问题转化成可复查框架。
        - 它保留了对证据边界的提醒。
        - 它能进入后续主题研究。

        ### 局限与偏见
        - 样本有限，需要更多外部资料。
        - 评论不能替代事实核查。

        ### 可行动项
        1. 建立 claim 清单。
        2. 补充外部资料。
        3. 抽取概念卡片。

        ## 8. Source Appendix

        | source | status |
        |---|---|
        | transcript | available |
        """
    ).strip()


def test_publishable_gate_passes_structured_human_readable_report():
    results, passed = verify_publishable_report.evaluate(_good_report())

    assert passed is True
    assert all(item["pass"] for item in results.values())


def test_publishable_gate_rejects_skeleton_placeholders():
    md = _good_report().replace("- [[虚拟偶像]] → [[人格资产]] → [[信任机制]]", "_骨架占位：暂无证据候选。_")

    results, passed = verify_publishable_report.evaluate(md)

    assert passed is False
    assert results["P0_NO_SKELETON"]["pass"] is False


def test_publishable_gate_rejects_long_transcript_dump_lines():
    long_line = "这是原始转录" * 200
    md = _good_report().replace("这是一段足够长的洞察正文，用来说明报告已经把视频核心问题转化为可复查的判断，并且没有依赖原始转录堆砌。", long_line)

    results, passed = verify_publishable_report.evaluate(md)

    assert passed is False
    assert results["P0_NO_LONG_LINES"]["pass"] is False


def test_publishable_gate_rejects_overlong_highlight_quotes():
    long_quote = "这是一条过长的高光引用" * 80
    md = _good_report().replace("> \"一个短句高光。\" — [00:10](https://example.com?t=10)", f"> \"{long_quote}\" — [00:10](https://example.com?t=10)")

    results, passed = verify_publishable_report.evaluate(md)

    assert passed is False
    assert results["P1_SHORT_HIGHLIGHTS"]["pass"] is False


def test_publishable_gate_rejects_logic_chain_that_is_only_blockquotes():
    bad_logic = textwrap.dedent(
        """
        ## 1. 逻辑链：从问题到机制

        > 这是一整段原始转录，它没有被整理成表格、时间线或 mermaid 逻辑链。
        > 这仍然只是原始转录。
        """
    ).strip()
    md = _good_report().replace(
        _good_report()[_good_report().find("## 1."):_good_report().find("## 2.")].strip(),
        bad_logic,
    )

    results, passed = verify_publishable_report.evaluate(md)

    assert passed is False
    assert results["P1_LOGIC_CHAIN_STRUCTURED"]["pass"] is False
