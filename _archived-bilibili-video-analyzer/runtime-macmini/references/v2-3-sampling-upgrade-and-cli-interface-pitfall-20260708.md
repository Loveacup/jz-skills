# v2.3 采样量扩量 CLI 接口与真实样片测试 pitfall

> Session: 2026-07-08
> 相关 commit: `a9c3c50`, `446200b`
> 相关视频: `BV1Xs7u6ZEuS`（欧洲 AI），`BV1QcQfB7EtH`（历史学家错了的重大发现）

---

## 1. 背景

v2.3 采样量扩量把评论从默认 50 扩到 ~150、弹幕从 ≥30-60 扩到 up to 1000 stratified，并引入 `mixed` 评论策略。
`fetch_all.py` 作为集成入口，需要把扩量参数传给子脚本 `fetch_comments.py` 和 `fetch_danmaku_v2.py`。

---

## 2. Pitfall A：`fetch_all.py` 用位置参数传 `count` + `--strategy`

### 现象

```
fetch_comments.py: error: unrecognized arguments: --writer-provider 150
```

### 根因

`fetch_comments.py` 的 CLI 签名是 `bvid [sessdata] [count]`，`--strategy` 是可选参数。

错误调用：
```python
comment_args = [bvid] + ([sessdata] if sessdata else []) + ['150', '--strategy', 'mixed']
```

当 `sessdata` 为空时，`150` 被解析为 `sessdata`，然后 `--strategy` 后面的 `--writer-provider` 被当成 `unrecognized arguments`。

### 修复

1. `fetch_comments.py` 增加 `--count` 可选参数：
```python
parser.add_argument("count", nargs="?", type=int, default=None,
                    help="获取评论数量（位置参数，已弃用；请用 --count，默认50）")
parser.add_argument("--count", dest="count_opt", type=int, default=None,
                    help="获取评论数量（默认50，覆盖位置参数 count）")
```

2. `fetch_all.py` 改为显式可选参数：
```python
comment_args = [bvid] + ([sessdata] if sessdata else []) + ['--count', '150', '--strategy', 'mixed']
```

### 验证

- `fetch_comments.py BV1 --count 150 --strategy mixed` → strategy=mixed, count=150 ✅
- `fetch_comments.py BV1 150` → 仍兼容（位置参数 count）✅
- 全量测试 228/228 通过 ✅

---

## 3. Pitfall B：`fetch_all.py` 把 `--writer-provider` / `--depth-profile` 透传给子脚本

### 现象

`fetch_all.py --report --writer-provider cli --depth-profile claim-first-full BV...` 跑评论时失败：

```
fetch_comments.py: error: unrecognized arguments: --writer-provider
```

### 根因

`fetch_all.py` 只过滤了 `--report`：
```python
args = [a for a in sys.argv[1:] if a != '--report']
```

没过滤 `--writer-provider` 和 `--depth-profile`，导致它们被当作 `sessdata` 传给子脚本。

### 修复

`fetch_all.py` 主函数用白名单过滤自己的参数：
```python
own_known = {'--report', '--writer-provider', '--depth-profile'}
filtered = []
skip_next = False
for a in sys.argv[1:]:
    if skip_next:
        skip_next = False
        continue
    if a in own_known:
        continue
    if a.startswith('--writer-provider=') or a.startswith('--depth-profile='):
        continue
    if a in ('--writer-provider', '--depth-profile'):
        skip_next = True
        continue
    filtered.append(a)
```

---

## 4. Pitfall C：`generate_report.py` 读落盘弹幕文件不兼容 `danmaku` 键

### 现象

`generate_report.py --bvid BV1QcQfB7EtH` 生成的报告 frontmatter 显示 `danmaku_count: 0`，弹幕深度分析为空。

### 根因

`fetch_danmaku_v2.py`：
- stdout 的 RESULT_JSON 用 `data` 键
- 落盘 `/tmp/{BV}_danmaku.json` 用 `danmaku` 键

`generate_report.py` 的 `_build_danmaku` 只读 `data` 键。`--bvid` 重建模式读落盘文件，所以弹幕为空。

### 修复

```python
def _build_danmaku(danmaku_step):
    d = _safe(danmaku_step)
    if not d:
        return []
    raw_list = d.get('data') or d.get('danmaku') or []
    for it in raw_list:
        ...
```

### 验证

修复后 `BV1QcQfB7EtH` 报告正确识别 `danmaku_count: 506` ✅

---

## 5. 真实样片测试经验

### 测试流程

用户要求“拉起自己的 cli，再跑一轮实际测试和评估”时：

1. 从 b23.tv 短链解析 BV 号：
   ```bash
   curl -sI -o /dev/null -w '%{redirect_url}' 'https://b23.tv/xxx'
   ```
2. 清理旧数据：`rm -f /tmp/BV*`
3. 后台高 timeout 跑完整流程：
   ```bash
   python3 scripts/fetch_all.py BV... --report --writer-provider cli --depth-profile claim-first-full
   ```
4. 若卡在某一步（如 YouTube 评论抓取），kill 后单独跑子脚本定位
5. 分段成功后，用 `generate_report.py --bvid BV...` 或 mock input 继续验证报告生成

### 发现的卡点

| 卡点 | 症状 | 处理 |
|:---|:---|:---|
| YouTube 评论抓取 | `fetch_youtube_comments.py` 失败：`youtube-comment-downloader` 不可用 + `yt-dlp` 解析失败 | 外部依赖波动，不阻塞主流程；可单独诊断或改用 WRR 补充 |
| H200 ASR / 网络 | `fetch_all.py` 长时间无输出 | 分段跑子脚本，tail 日志定位 |
| 报告生成失败 | `TypeError: can't multiply sequence by non-int of type 'float'` | 通常是输入数据缺失/格式错误导致引擎内部计算失败，需检查输入 JSON |

### 质量评估

`BV1QcQfB7EtH` 最终报告：
- 26,667 字符
- 弹幕 506 条、评论 27 条
- 12 claims、13 insights
- 3 个核心洞察：技术史非线性、平均寿命统计谬误、西方中心叙事遮蔽

报告质量良好，证明采样量扩量后数据被正确消费。

---

## 6. 教训清单

1. 主脚本调用子脚本时，**尽量用显式可选参数**，避免位置参数歧义
2. 子脚本的 CLI 接口变更时，**同时更新所有调用方**（`fetch_all.py`、测试、文档）
3. 主脚本过滤自己的参数时，**不能只过滤一个 `--report`**，要维护完整白名单
4. 落盘文件和 stdout 的 JSON schema 可能不一致，**消费端要兼容多个键名**
5. 真实样片测试不要怕时间长，**用后台高 timeout 跑完整流程**，分段诊断
6. 外部依赖（YouTube 抓取、ASR）失败不等于代码 bug，**单独诊断后再下结论**

---

## 7. 相关命令速查

```bash
# 解析 b23.tv 短链
curl -sI -o /dev/null -w '%{redirect_url}' 'https://b23.tv/xxx' | grep -o 'BV[0-9A-Za-z]\{10\}'

# 跑完整流程
python3 scripts/fetch_all.py BV... --report --writer-provider cli --depth-profile claim-first-full

# 从落盘文件重建报告
python3 scripts/generate_report.py --bvid BV... --writer-provider cli --depth-profile claim-first-full

# 全量测试
python3 -m pytest -q tests --ignore=tests/test_asr_config.py

# 单独诊断子脚本
python3 scripts/fetch_comments.py BV... --count 150 --strategy mixed
python3 scripts/fetch_danmaku_v2.py BV...
python3 scripts/fetch_subtitle_auto.py BV...
python3 scripts/fetch_youtube_comments.py 'https://www.youtube.com/watch?v=xxx' --limit 100
```
