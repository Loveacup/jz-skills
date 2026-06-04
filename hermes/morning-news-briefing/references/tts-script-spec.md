# TTS 语音稿规范 (Step 6)

早新闻语音版三段式脚本规范。SKILL.md v4.0 Step 6 的完整定义。

> **v4.0 mandate**：TTS 是 pipeline 步骤，不是可选项。`text_to_speech` 不可达时跳过并标注，但**不得静默省略**（SKILL.md Core Rule #8）。

---

## 一、触发时机

```
audit 通过 (Verifier/Step 5 全 sentinel pass)
   ↓
Step 6: TTS Generation  ← 本规范
   ↓
Step 7: Deliver (PDFs + audio)
```

输入：`morning-news-{date}.md`（已审计通过的 markdown）
输出：`output/morning-news-{date}.mp3`

---

## 二、三段式结构

| 段落 | 来源 | 时长 | 风格 |
|------|------|------|------|
| **① 开场摘要** | 执行摘要 → 口语化改写 | 30-45s | "早上好，今天是…。N 件大事：…" |
| **② 深度分析** | Top 3 分析条目 | 60-90s | 每条压缩为「事件 + 为什么重要」，≤50 字/条 |
| **③ 收尾总结** | 📌 今日总结 | 20-30s | 核心张力 + 一句话前瞻 |

**总时长**：≤5 分钟语音（约 700-900 字中文）。

### 各段约束

- **① 开场**：从执行摘要 3-5 bullet 提炼为 3 个口语化要点。不念 bullet 符号，用顿号/逗号串联。
- **② 分析**：从 🔍 深度分析 5-8 条中**选 Top 3**（影响最大）。每条剥离「前提/推理/结论」标签，融合为一句「事件 + 为什么重要」，≤50 字。不读"前提："这类结构词。
- **③ 收尾**：从 📌 今日总结提取核心张力一句 + 一句前瞻，以"明天见"收束。

---

## 三、脚本模板

```
开场：早上好，今天是 {YYYY} 年 {M} 月 {D} 日，{周几}。今天有 {N} 件大事：{要点1}、{要点2}、{要点3}。

分析：
  下面说三条值得关注的。
  第一，{标题}。{事件 + 为什么重要，≤50字}。
  第二，{标题}。{事件 + 为什么重要，≤50字}。
  第三，{标题}。{事件 + 为什么重要，≤50字}。

收尾：总的来说，{核心张力一句}。{一句前瞻}。我们明天见。
```

> 模板是骨架，不是死板填空。改写时优先**自然口语流畅**，避免书面长句、嵌套从句、英文缩写直读（如 "GDP" → "国内生产总值"或保留但确认 TTS 发音正确）。

---

## 四、口语化改写规则（markdown → 口播稿）

| 书面 | 口语化 | 理由 |
|------|--------|------|
| `📰 今日要闻` 等 emoji 标题 | 删除 | TTS 不念 emoji |
| `[s1]` `[S01]` 源编号 | 删除 | 口播不读引用标记 |
| `前提：…推理：…结论：…` | 融合成一句陈述 | 结构词不口播 |
| `±2%`、`$14B` | "百分之二以内"、"一百四十亿美元" | 符号/缩写口语化 |
| 长破折号从句 | 拆成两个短句 | 口播断句清晰 |
| `一方面…另一方面` | 直接给判断 | anti-hedging：骑墙词不入稿 |
| URL / 链接 | 删除 | 不口播 |
| markdown 加粗 `**x**` | 删除符号保留文字 | 纯文本 |

落盘中间稿：`output/tts-script-{date}.txt`（纯文本，无 markdown）。

---

## 五、生成流程

```
1. 从 morning-news-{date}.md 提取三段内容（执行摘要 / Top3 分析 / 今日总结）
2. 按 §四 规则改写为口语化脚本 → output/tts-script-{date}.txt
3. 调用 Hermes text_to_speech(text=full_script)
4. 保存 output/morning-news-{date}.mp3
5. 质检：试听 30s 片段，确认无吞字/断句异常/数字误读
```

### 工具调用

```
text_to_speech(text=<tts-script-{date}.txt 全文>)
→ 音频流 → 保存 output/morning-news-{date}.mp3
```

---

## 六、质检 (QA)

| 检查项 | 标准 |
|--------|------|
| 总时长 | ≤5 分钟 |
| 试听片段 | 抽 30s（建议开场+一条分析），确认无吞字、断句自然 |
| 数字读音 | 抽查金额/百分比/日期读音正确（"14B" 不读成 "14 B"） |
| emoji/符号残留 | 脚本 txt 中 grep emoji/`[sN]`/markdown 符号 → 应为 0 |
| 文件存在 | `output/morning-news-{date}.mp3` 实际生成且体积 >0 |

---

## 七、Fallback（TTS 不可达）

`text_to_speech` 不可达（CosyVoice down / 无 TTS provider）时：

```
1. Log: "TTS skipped — text_to_speech unavailable"
2. 继续 Step 7 交付，只发两版 PDF
3. 在交付消息中标注："📢 语音版今日跳过（TTS 服务不可达）"
4. 不删除 tts-script-{date}.txt（保留脚本，服务恢复后可补生成）
```

⚠️ **不得静默省略**。交付清单里必须明示语音版状态（生成 / 跳过+原因）。

---

## 八、交付物 (Step 7)

| 产物 | 路径 |
|------|------|
| 口播脚本 | `output/tts-script-{date}.txt` |
| 语音文件 | `output/morning-news-{date}.mp3` |

随 mobile + A4 两版 PDF 一并交付（Kanban 模式经 `kanban_complete(artifacts=[...])`，见 `references/kanban-swarm-workflow.md` §七）。

---

## 验收清单

- [ ] 三段结构齐全（开场 / Top3 分析 / 收尾）？
- [ ] 总时长 ≤5 分钟？
- [ ] 脚本 txt 无 emoji / `[sN]` / markdown 符号残留？
- [ ] 无骑墙词（一方面/另一方面/可能/或许/似乎）？
- [ ] 数字/金额/日期读音抽查通过？
- [ ] `morning-news-{date}.mp3` 存在且体积 >0（或：已标注 fallback 跳过）？
- [ ] 交付消息明示语音版状态？
