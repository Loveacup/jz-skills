# 手机版 PDF 版式八诫 · 验收清单

> 固化自 2026-05-25 两轮返工。工部渲染和御史稽核必须逐条核验。

## 验收清单

| # | 诫条 | 检查方法 | 阻断级别 |
|---|------|----------|----------|
| 1 | 卡内来源 `来源：S01 媒体名 · S02 媒体名` | grep PDF 文本中所有"来源"行，检查是否含 S## | BLOCK |
| 2 | 强哨兵七项全命中：执行摘要/分析/今日总结/核心矛盾/Alex Cai/六部监制/来源清单 | PyMuPDF 抽取全文，逐项 `in text` | BLOCK |
| 3 | 封面含"制作者 Alex Cai" | 检查首页 `get_text()` 含 "Alex Cai" 或 "制作者" | BLOCK |
| 4 | 右边距 ≥16px | `@page { margin: 10px 16px 16px }`；视觉确认卡片右边框不贴页边 | BLOCK |
| 5 | 视觉 PNG 抽检（封面/分析/总结/来源） | 出 4 张截图，视觉确认无过密/孤儿/空白/乱码 | BLOCK |
| 6 | 执行摘要为 bullet（3–5 条） | 检查首页文本中执行摘要区域含 `<li>` 或 bullet 标记 | BLOCK |
| 7 | 分页无标题孤儿 | 视觉检查：无"标题后仅一行正文即断页"或"页面顶部无标题续文" | WARN |
| 8 | 来源清单为 S01–SNN 逐行编号列表 | 末尾页逐行含 S## + 媒体名 + URL，非串联段落 | BLOCK |

## 快速自检脚本

```python
import fitz
doc = fitz.open(pdf_path)
text = "\n".join(p.get_text() for p in doc)

# 诫1: 来源格式
bad_sources = [l for l in text.split('\n') if '来源' in l and '来源：S' not in l and '📡' in l]
assert not bad_sources, f"缺S##前缀来源行: {bad_sources[:3]}"

# 诫2: 七哨兵
for s in ['执行摘要','分析','今日总结','核心矛盾','Alex Cai','六部监制','来源清单']:
    assert s in text, f"缺哨兵: {s}"

# 诫3: 封面制作者
assert '制作者 Alex' in doc[0].get_text(), "封面缺制作者"

# 诫4: 右边距 (通过CSS @page检查，此脚本仅检查无溢出)
assert text.count('\ufffd') == 0, "有U+FFFD替换字符"
```
