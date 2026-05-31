# L1 硬性规则黑名单

> output-finalizer 在 L1 闸门执行 grep 风格硬扫描。**命中即回炉局部段落**（不全文重写）。
>
> 不分模式——v5.0 所有质检一律全开。命中即扣分 + 回炉，达上限标记低置信度放行。

---

## 一、AI 词黑名单（26 词）

### 中文 AI 套话（14 词）

| 词 | 替代写法建议 |
|---|---|
| 赋能 | 改成具体动作（"帮 X 做了什么"） |
| 抓手 | 改成"切入点"或具体动词 |
| 底层逻辑 | 改成"根本原因"或具体机制 |
| 范式 | 改成"做法"或"模式" |
| 叙事 | 改成"说法"或"故事线" |
| 共识 | 改成"大家都同意 X" |
| 涌现 | 改成"逐渐出现"或"突然冒出来" |
| 复盘 | 改成"回看"或"重新检视" |
| 矩阵化 | 改成具体的表格 / 维度组合 |
| 生态位 | 仅在生态学语境保留；商业语境改成"位置"或"市场空白" |
| 核心要义 | 改成"重点"或直接陈述要点 |
| 至关重要 | 改成"很重要"或说明为什么重要 |
| 全方位 | 删除或具体化为 N 个维度 |
| 多维度 | 改成具体的维度列表 |

### 英文 AI 套话（12 词）

| 词 | 备注 |
|---|---|
| delve | 改成 "look at" / "examine" |
| tapestry | 改成 "mix" / "blend" |
| multifaceted | 改成 "complex" 或列具体面 |
| synergy | 改成 "working together" |
| leverage | 改成 "use" |
| robust | 改成 "strong" / "reliable" |
| comprehensive | 改成 "complete" 或具体范围 |
| seamlessly | 改成 "smoothly" 或删除 |
| pivotal | 改成 "key" |
| navigate | 在非物理语境改成 "handle" / "deal with" |
| underscore | 改成 "highlight" / "stress" |
| in today's landscape | 改成具体时间 / 具体行业 |

**检测方法**：全文 grep 命中数。L1 阈值 = 0（任一命中即触发回炉局部段落）。

---

## 二、教科书开头模式（命中即拒）

以下模式出现在**段落首句**即触发：

| 模式 | 示例 |
|---|---|
| 「在当今...」 | 在当今数字化时代 / 在当今激烈的竞争中 |
| 「随着...的发展」 | 随着 AI 技术的发展 / 随着市场的演进 |
| 「众所周知」 | 众所周知，X 是 Y |
| 「不可否认」 | 不可否认，X 已成为 Y |
| 「值得注意的是」 | 值得注意的是，X 正在 Y |
| 「毋庸置疑」 | 毋庸置疑，X 是 Y 的关键 |
| 「In today's...」 | In today's fast-paced world |
| 「In the era of...」 | In the era of AI |
| 「It is worth noting that...」 | |
| 「It cannot be denied that...」 | |

**检测方法**：每段首句 regex 匹配。L1 阈值 = 0。

---

## 三、禁止标点表

| 模式 | 阈值 | 说明 |
|---|---|---|
| 连续 3+ 段以破折号 `——` 结尾 | 0 | 整段链式破折号 = AI 节奏 |
| 同段内 `——` 紧跟 `——`（中间字符 < 30） | 0 | 双破折号嵌套 |
| 全文 `——` 总数 / 字数 | ≤ 1 / 800 字 | 破折号密度软上限 |
| 段末问号收尾 ≥ 3 连段 | 0 | 连续设问 = AI 节奏 |
| 连续 4+ 段以「...是 X，...是 Y，...是 Z」结尾 | 0 | 三段排比尾巴 |

**检测方法**：段落级 regex + 全文密度统计。

---

## 四、三段式排比

模式：「**不是 X，而是 Y，更是 Z**」「**既...又...还...**」「**既是...也是...更是...**」

| 项 | 阈值 |
|---|---|
| 全文累计出现次数 | ≤ 2 处 |
| 单段出现次数 | ≤ 1 处 |

**检测方法**：regex `(不是|既)[^，。]{2,15}[，；](而是|又)[^，。]{2,15}[，；](更是|还)`

---

## 五、否定式排比

模式：「**不是 X，而是 Y**」（两段式否定式排比）

| 项 | 阈值 |
|---|---|
| 全文累计出现次数 | ≤ 1 处 |

**检测方法**：regex `不是[^，。]{2,20}[，；]而是`（计数全文出现）

---

## 六、检查方法 & verdict 上报

output-finalizer 在 L1 阶段：

1. **加载终稿**：读取 longform-writer 输出的 final-article.md
2. **执行 grep 风格扫描**：按上述 1-5 类逐项检查
3. **统计命中**：每类记录命中次数 + 命中位置（段落编号）
4. **判定 verdict**：

```json
{
  "gate": "L1",
  "pass": false,
  "score": 3.2,
  "subscores": {
    "ai_word_hits": 4,
    "textbook_opening_hits": 1,
    "punctuation_violations": 2,
    "triple_parallel_hits": 3,
    "negative_parallel_hits": 1
  },
  "blocking": [
    "ai_word_hits=4 > 0 (赋能 ×2, 底层逻辑 ×1, 抓手 ×1)",
    "triple_parallel_hits=3 > 2"
  ],
  "next_action": "send_back_to:longform-writer",
  "回炉范围": "段落 5, 段落 12, 段落 18"
}
```

5. **回炉局部段落**：通过 `SendMessage(longform-writer 的 task_id, "局部改写: 段落 5/12/18, 命中原因: ...")`，**不全文重写**
6. **重试上限**：L1 累计回炉 2 次仍 fail → 标记低置信度放行 + 评分 -0.5 + 报告告警

---

## 七、相关 Skill 调用

- L1 仅做硬扫描和回炉指令，**不自动调用任何 Skill**
- L4 软违规时才调用 `Skill(skill="de-slop", args="检测并改写以下文本的AI味：{text}")`

参考：
- [agent-pipeline.md](agent-pipeline.md) §「Stage 6.5 Skill 调用签名」
- de-slop skill（双语 AI 痕迹检测引擎）
- humanizer-zh skill（中文专版，仅作 L4 备选）
