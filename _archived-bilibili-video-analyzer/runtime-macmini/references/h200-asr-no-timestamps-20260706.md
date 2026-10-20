# H200 ASR 无逐句时间戳的处理规范

> 记录时间：2026-07-06
> 触发视频：BV1anMP69ED5（韩红一句“走面儿”，走出了京圈的黄昏）
> 相关参考：`references/h200-asr-vs-bili-asr-20260630.md`、`references/asr-evidence-gates-and-single-note-output-20260630.md`

## 现象

当前默认 ASR 路径 `BILI_ASR_PROVIDER=auto` 优先走 SURGExZR H200 HTTP ASR（`POST /ASR/transcribe`）。H200 对 Bilibili PlayURL 直拉的音频返回的转录文本是**纯文本**或**按大段切分**，没有类似 SRT/ASS 的逐句时间戳。

RESULT_JSON 示例：

```json
{
  "method": "h200-asr",
  "txt_path": "/tmp/BVxxx_subtitle_whisper.txt",
  "parts": 1,
  "trace": [{"step": "whisper", "status": "ok", "reason": "引擎=h200-asr; parts=1/1"}]
}
```

文件内容通常是整段文字，没有 `00:00:05,000 --> 00:00:08,000` 这样的时间戳。

## 影响

1. **§5 高光时刻** 中的 `[mm:ss]` 链接无法精确对应到原视频句子，只能按叙事结构估算。
2. **§1 逻辑链** 的叙事弧线时间栏也只能根据文本顺序大致划分段落。
3. 如果用户后续引用报告中的时间戳去回看原视频，可能有几秒到几十秒的偏差。
4. 需要精确逐句引用的场景（如技术教程、政策逐条解读），H200 ASR 不够用。

## 处理规范

### 1. 数据源声明

在 §0 Meta 和 §8 附录的 Source Appendix 中必须声明：

```markdown
- transcript_available=true
- method: h200-asr
- segments: 1（或很少）
- 时间戳：无逐句时间戳，报告内时间戳按叙事结构估算
```

### 2. 估算时间戳的优先级

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 高 | 弹幕时间 | 弹幕有精确 `time_sec`，若弹幕与视频论点强相关，可用弹幕时间校正 |
| 中 | 文本结构分段 | 按全文比例估算，例如 9 分 34 秒视频，前 1/3 对应 0:00–3:10 |
| 低 | 固定标题/片头 | 0:00 起点可用，但后续不能用线性插值硬套 |

### 3. 报告内表述

不要写精确断言如：

> ❌ “在 2:15 处，UP 主说……”

应写：

> ✅ “约 2:15 处，UP 主提出……” 或 “在视频前半段，UP 主指出……”

并在 §8 附录中明确说明时间戳限制。

### 4. 何时应切换回官方/AI字幕

如果视频类型是以下之一，且时间戳精确性重要，应优先尝试官方/AI字幕：

- 技术教程/操作演示（需要精确到步骤）
- 政策/法律解读（需要精确到条款）
- 长访谈/演讲（需要按分钟精确引用）

方法：

```bash
yt-dlp --cookies-from-browser chrome \
  --write-subs --sub-lang "zh,ai-zh" \
  --skip-download --convert-subs srt \
  -o '/tmp/bv_hermes' '<URL>'
```

详见 `references/h200-asr-vs-bili-asr-20260630.md` 和 Subtitle Extraction 章节。

## 验证清单

- [ ] §0 Meta 是否声明了 H200 ASR 无逐句时间戳？
- [ ] §8 附录的 Source Appendix 是否记录了 `segments` 数量和估算说明？
- [ ] 报告内时间戳是否用了“约”“约莫”“大致”等限定词？
- [ ] 是否用弹幕时间校正了关键节点？
- [ ] 若时间戳精确性重要，是否已尝试官方/AI字幕？
