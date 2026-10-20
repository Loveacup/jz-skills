# 合并报告生成技巧 (Merged Report Tips)

## G4 模块诊断脚本

当 `verify_report.py` 报 G4 `min X words` 但不知道哪个模块不足时，用以下脚本精确定位：

```python
import re

def word_count(text):
    cjk = len(re.findall(r'[一-鿿]', text))
    ascii_words = len(re.findall(r'[A-Za-z0-9]+', text))
    return cjk + ascii_words

def strip_markup(line):
    stripped = line.strip()
    if stripped.startswith('```'):
        return ''
    stripped = re.sub(r'^([#>\\-\\*\\s]|\\[ \\]|\\[x\\])+', '', stripped)
    stripped = stripped.replace('|', ' ')
    stripped = re.sub(r'[*_`]', ' ', stripped)
    return stripped

with open('报告.md') as f:
    lines = f.readlines()

# Find §4
start = end = None
for i, ln in enumerate(lines):
    if re.match(r'^##\s+4\.', ln):
        start = i
    elif start is not None and re.match(r'^##\s', ln):
        end = i
        break

section = lines[start:end]
h3 = re.compile(r'^###\s')
subs = []
cur_head, cur_body = None, []
for ln in section:
    if h3.match(ln):
        if cur_head is not None:
            subs.append((cur_head, cur_body))
        cur_head, cur_body = ln, []
    elif cur_head is not None:
        cur_body.append(ln)
if cur_head is not None:
    subs.append((cur_head, cur_body))

module_filter = re.compile(r'###\s*模块\s*\d')
for h, body in subs:
    if module_filter.search(h):
        total = sum(word_count(strip_markup(ln)) for ln in body)
        print(f"{h.strip()}: {total} words")
```

使用：`python3 diagnose.py` → 找出词数最低的模块 → 精准扩充该模块。

## §1 流程图压缩策略

合并报告含多个视频的独立 flowchart，G1 限制 ≤100 行。压缩策略：

1. **合并相似步骤**：将 2-3 个连续步骤合并为一个节点（如"暗器开局 + 猴王 Boss → 暗器·猴王"）
2. **去除分支细节**：单视频流程图中去掉条件分支（`{资源偏科?}`），保留主线
3. **简化节点标签**：每个节点 ≤15 字，用简称（"配燃决+混元桩" 而非 "配燃决·3玄机格 + 一字混元桩·护体转栏条"）
4. **目标**：每个流程图 ≤6 节点，4 视频 + 1 关系图 = 5 个 flowchart ≈ 35 行 mermaid + 5 行间隔 = 40 行，留给表格 60 行

## 多视频并行 fetch_all + 转录

4 集以内可全部并行启动：
- `fetch_all.py` × N：互不依赖，后台并行
- `mlx_transcribe.py` × N：mlx-whisper 可并行（每个 ~60s），互不干扰
- 注意：`fetch_all.py` 内 `fetch_subtitle_auto.py` 会尝试 yt-dlp（可能 412），如全部失败走 playurl API 旁路
- 旁路步骤（playurl → curl 下载 → ffmpeg 转 WAV）也可在 `execute_code` 中并行处理

## 评论 JSON 结构

`fetch_comments.py` 输出格式：
```json
{
  "bvid": "BV...",
  "total_count": 64,
  "hot_comments": [...]   // ← 关键字是 hot_comments，不是 comments 或 replies
}
```
