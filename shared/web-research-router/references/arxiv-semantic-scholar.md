# arXiv + Semantic Scholar 操作手册（academic mode）

> WRR `academic` mode 的论文检索操作细节。lane 策略（何时用哪个源、引用纪律）见 `academic-lane.md`；本文是「怎么调」。免 key、仅 curl + stdlib。
> 配套脚本：`scripts/search_arxiv.py`（XML 解析 + 干净输出，无第三方依赖）。

## 🚨 红线

| 借口 | 为什么错 |
|---|---|
| "重试一下，arXiv 大概只是抽风" | arXiv 限流凶（~1 req/3s），重试只会更糟。**改用 Semantic Scholar** 兜底 |
| "在 arXiv 上 = 同行评审过了" | arXiv 是预印本服务器，单独标注 venue / 评审状态 |
| "引最新版就行" | 版本可能差异很大，引你**实际读的那个版本**（如 v2 不是 v7） |
| "10 条够了" | SOTA / survey 可能要 50-100 条，用 `start` 分页 |

## arXiv API（Atom XML，curl 无 key）

```bash
# 基础搜索
curl -s "https://export.arxiv.org/api/query?search_query=all:GRPO+reinforcement+learning&max_results=5"

# 取特定论文（按 ID，可多个逗号分隔）
curl -s "https://export.arxiv.org/api/query?id_list=2402.03300,2401.12345"

# 最新 cs.AI（按提交日降序）
curl -s "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10"
```

**推荐用脚本**（XML 解析 + 干净输出）：

```bash
python scripts/search_arxiv.py "GRPO reinforcement learning"
python scripts/search_arxiv.py "transformer attention" --max 10 --sort date
python scripts/search_arxiv.py --author "Yann LeCun" --max 5
python scripts/search_arxiv.py --category cs.AI --sort date
python scripts/search_arxiv.py --id 2402.03300
```

### 查询语法

| 前缀 | 搜索域 | 例 |
|---|---|---|
| `all:` | 全字段 | `all:transformer+attention` |
| `ti:` | 标题 | `ti:large+language+models` |
| `au:` | 作者 | `au:vaswani` |
| `abs:` | 摘要 | `abs:reinforcement+learning` |
| `cat:` | 分类 | `cat:cs.AI` |
| `co:` | 评论 | `co:accepted+NeurIPS` |

布尔：`+`=AND（默认）· `+OR+` · `+ANDNOT+` · 精确短语 `ti:"chain+of+thought"`。
排序：`sortBy`=`relevance`/`lastUpdatedDate`/`submittedDate`，`sortOrder`=`ascending`/`descending`，`start`=偏移，`max_results`（默认 10，max 30000）。

### 常用分类

`cs.AI` 人工智能 · `cs.CL` NLP · `cs.CV` 视觉 · `cs.LG` 机器学习 · `cs.CR` 密码/安全 · `stat.ML` 统计机器学习 · `math.OC` 优化控制 · `physics.comp-ph` 计算物理。全表：https://arxiv.org/category_taxonomy

### 读论文内容

```
web_extract(urls=["https://arxiv.org/abs/2402.03300"])   # 摘要页（快，元数据+摘要）
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])    # 全文 PDF → markdown
```
本地 PDF 处理见 `ocr-and-documents` skill。

### BibTeX 生成

{% raw %}
```bash
curl -s "https://export.arxiv.org/api/query?id_list=1706.03762" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
root = ET.parse(sys.stdin).getroot()
entry = root.find('a:entry', ns)
if entry is None: sys.exit('Paper not found')
title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
authors = ' and '.join(a.find('a:name', ns).text for a in entry.findall('a:author', ns))
year = entry.find('a:published', ns).text[:4]
raw_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
cat = entry.find('arxiv:primary_category', ns)
primary = cat.get('term') if cat is not None else 'cs.LG'
last_name = entry.find('a:author', ns).find('a:name', ns).text.split()[-1]
print(f'@article{{{last_name}{year}_{raw_id.replace(\".\", \"\")},')
print(f'  title     = {{{title}}},')
print(f'  author    = {{{authors}}},')
print(f'  year      = {{{year}}},')
print(f'  eprint    = {{{raw_id}}},')
print(f'  archivePrefix = {{arXiv}},')
print(f'  primaryClass  = {{{primary}}},')
print(f'  url       = {{https://arxiv.org/abs/{raw_id}}}')
print('}')
"
```
{% endraw %}

## Semantic Scholar API（引用 / 相关 / 作者 — arXiv 没有的）

arXiv 不提供引用数据和推荐。Semantic Scholar 免 key（1 req/s，带 key 100/s），返回 JSON。

```bash
# 论文详情 + 引用数（按 arXiv ID）
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,referenceCount,influentialCitationCount,year,abstract" | python3 -m json.tool

# 谁引用了它
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,authors,year,citationCount&limit=10" | python3 -m json.tool

# 它引用了什么
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/references?fields=title,authors,year,citationCount&limit=10" | python3 -m json.tool

# 搜索（替代 arXiv 搜索，返回 JSON，含 externalIds 里的 arXiv ID）
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=GRPO+reinforcement+learning&limit=5&fields=title,authors,year,citationCount,externalIds" | python3 -m json.tool

# 推荐
curl -s -X POST "https://api.semanticscholar.org/recommendations/v1/papers/" \
  -H "Content-Type: application/json" \
  -d '{"positivePaperIds": ["arXiv:2402.03300"], "negativePaperIds": []}' | python3 -m json.tool

# 作者画像
curl -s "https://api.semanticscholar.org/graph/v1/author/search?query=Yann+LeCun&fields=name,hIndex,citationCount,paperCount" | python3 -m json.tool
```

可用字段：`title` `authors` `year` `abstract` `citationCount` `referenceCount` `influentialCitationCount` `isOpenAccess` `openAccessPdf` `fieldsOfStudy` `publicationVenue` `externalIds`（含 arXiv ID / DOI）。

## 完整工作流

1. **发现**：`search_arxiv.py "topic" --sort date --max 10` —— arXiv 429 则改 Semantic Scholar 搜索（同主题，JSON，含 arXiv ID）
2. **评估影响力**：Semantic Scholar `?fields=citationCount,influentialCitationCount`
3. **读摘要**：`web_extract(["https://arxiv.org/abs/ID"])`
4. **读全文**：`web_extract(["https://arxiv.org/pdf/ID"])`
5. **找相关工作**：Semantic Scholar `/references?limit=20`
6. **拿推荐**：POST recommendations
7. **追踪作者**：Semantic Scholar `/author/search`

## Rate limit + 降级

| API | 速率 | Auth |
|---|---|---|
| arXiv | ~1 req / 3s | 无 |
| Semantic Scholar | 1 req / s | 无（带 key 100/s） |

arXiv 对突发凶狠 429——**收到 429 不要立即重试**：① 切 Semantic Scholar 搜索（JSON，覆盖大多数 AI/ML/CS）；② 要 arXiv 专属新结果则等 ≥5s 重试一次；③ CS/AI/ML 主题 Semantic Scholar 单独通常够发现阶段，事后交叉 arXiv ID。（GRPO academic-lane 实测：arXiv 首 curl 即 429，Semantic Scholar 秒返 188k，Exa 补原文 PDF。）

## 引用纪律（与 academic-lane.md 一致）

- arXiv ID：旧格式 `hep-th/0601001` vs 新 `2402.03300`；PDF `arxiv.org/pdf/{id}`、摘要 `arxiv.org/abs/{id}`、HTML（如有）`arxiv.org/html/{id}`。
- **版本**：`abs/1706.03762` 永远指最新；`abs/1706.03762v1` 指特定不可变版本。生成引用时保留你实际读的版本后缀，防 citation drift。API 的 `<id>` 字段返回带版本 URL。
- **撤稿**：论文可能被撤回——`<summary>` 含 "withdrawn"/"retracted" 时元数据可能不全，当作有效论文前先看 summary。
- **引用数当相对信号**：Semantic Scholar / OpenAlex / Google Scholar 计数各异，用于"数量级对比"而非精确指标，正式文献计量交叉 OpenAlex。

## ✅ 返回结果前自检

- [ ] 守了 arXiv 限流（≥3s/请求）？
- [ ] arXiv 上的标了 "preprint" 而非 "peer-reviewed"？
- [ ] 保留了实际读的版本后缀？
- [ ] 看了 summary 排除撤稿/撤回？
- [ ] SOTA / first-paper 主张交叉了 Semantic Scholar？
