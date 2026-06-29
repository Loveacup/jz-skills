# CC 任务结构策略：新建 vs 修改

## 发现

在 bilibili-video-analyzer Phase 2 委派中观察到系统性差异：

| 任务类型 | CC 表现 | 耗时 |
|----------|---------|------|
| 新建独立脚本 | 快速、准确、一气呵成 | ~3-5min/文件 |
| 修改现有脚本 | 过度分析、反复研究上下文、容易触发 Pitfall #53 | 15min+ |

Phase 2 的 3 个新建文件（`fetch_youtube_comments.py`, `fact_check_wrr.py`, `video_analysis_engine.py`）均在 5 分钟内高质量完成。2 个修改任务（`fetch_all.py` 中加 `detect_youtube_url()`、更新 `SKILL.md`）导致 CC 在「研究 90 个视频的简介→发现仅 2 个含 YouTube 链接→继续深挖原因」的分析循环中卡死 15 分钟。

## 根因

- **新建文件**：CC 看到的是干净画布，直接按 spec 写代码，无需要理解的现有逻辑
- **修改文件**：CC 需要「理解现有代码→评估改动影响→找插入点→保持向后兼容」，每步都可能触发分析循环
  - 尤其当现有代码规模大（fetch_all.py 近 200 行含子进程编排），CC 会试图理解全部逻辑再改

## 对策（三级）

### 1. 拆分 session（推荐）
把新建和修改分成两个独立 session：
```
Session A: 新建 a.py, b.py, c.py  ← 快速完成
Session B: 修改现有 x.py, y.md     ← 单独处理，指令更具体
```

### 2. 给修改任务提供代码片段
不写「在 fetch_all.py 中增加 YouTube 检测」，而是：
```
在 fetch_all.py 的 process_step 循环之后，插入以下函数：
def detect_youtube_url(text): ...
然后在上层调用它。
```
—— 把「理解+设计+实现」压缩为「按位置插入代码」。

### 3. 中断后给单行指令
当 CC 已在分析循环中（`almost done thinking with high effort`）：
```
C-c → sleep 2 → "只做 X，直接写。" → Enter
```
不要给新的大段 prompt——会触发新一轮分析。

## 案例

### ❌ 导致过度思考的指令
> "更新 fetch_all.py，增加搬运检测：从 B站视频信息中提取 description，正则检测 YouTube URL，检测到时自动调用 fetch_youtube_comments.py..."

### ✅ 避免过度思考的指令
> "在 fetch_all.py 第 130 行后插入 detect_youtube_url(url) 函数，正则匹配 youtube.com/watch 和 youtu.be。完成后写 /tmp/done.txt。"

## 适用场景

- 任何需要 CC 修改 100+ 行现有文件的任务
- 尤其当「修改」涉及理解现有架构（子进程编排、协议解析、错误处理链）
- 新建文件无此问题，可放心批量委派
