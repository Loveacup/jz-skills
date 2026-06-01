# 日记清理/合并判定细则

用于用户要求“整理日记、清理空日记、合并短日记”时，补充 `auto-diary` 的工作流 C。

## 目标

不是只按文件名或月份移动文件，而是逐篇读取 `YYYY-MM-DD.md` 正文，按有效信息量处理：

- 空/模板日记：备份后删除。
- 内容少但有信息：按月份合并到碎片日记文件，备份后删除原文件。
- 正常日记：保留原文件。

## 空/模板日记特征

若正文只包含以下内容，通常视为无有效信息：

- 天气、心情占位
- `(待补充)`、`请补充`、`明天计划`
- `当日无日历事件`、`今日知识库无更新`
- `无 AI 对话记录`、`无会话记录`、`无活跃记录`
- `清晰提示工作流` 三个问题本身
- auto-diary 页脚
- 空待办、空上午/下午/晚上段落

## 内容少但有信息的日记

短文本但出现以下任一类真实信息时，不直接丢弃：

- 个人生活事件，例如吃饭、旅行、聊天、运动、家庭事件
- 工作事项或项目线索
- 日历事项，尤其医疗、出行、课程、会议
- 知识库新增/修改条目，若能说明当天活动
- 待办事项或临时笔记中真实条目
- 关系/情绪/想法记录

处理方式：合并到 `归档/YYYY-MM/碎片日记合并-YYYY-MM.md`；当前月可放在日记根目录。每个条目保留：日期、原路径、有效内容 bullet。

## 安全流程

1. 先复制候选原文到 `~/.hermes/backups/obsidian-diary-cleanup-YYYYMMDD_HHMMSS/`。
2. 再写入/更新月度碎片合并文件。
3. 确认合并文件存在且包含原路径后，删除原始短日记/空日记。
4. 生成 `日记清理报告-YYYYMMDD.md`，记录数量、备份路径、删除列表、合并列表。
5. 如使用 qmd，运行 `qmd update` 刷新索引；不要自动运行 `qmd embed`，除非用户明确要求。

## 建议阈值

可用“有效内容字符数”辅助分类，但不要只靠文件大小：

- 0 有效字符：空/模板
- 少量有效字符：短日记，合并
- 有完整叙事、多个事件或较多 AI/日历/知识库记录：正常日记，保留

关键是保留真实信息，清掉模板噪声。

## 2026-05-25 实战补充：dataless 文件 + qmd fallback

### 为什么需要 qmd fallback

macOS iCloud/Obsidian Sync 会产生 `dataless` 占位文件，`cat`/`open()` 报 `Resource deadlock avoided`。文件大小显示正常，但正文不可读。此时不能按文件大小判定内容多少，必须先拿到正文。

### 判定流程（含 fallback）

```python
import os, sqlite3

def classify_diary(file_path, qmd_collection="alexcai-vault"):
    """读取日记正文并分类。优先直接读，失败时用 qmd fallback。"""
    content = None
    source = "direct"

    # 1. 尝试直接读取
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        if "Resource deadlock" in str(e):
            # 2. qmd fallback
            date = os.path.basename(file_path).replace(".md", "")
            qmd_path = f"{qmd_collection}/50-Self/01-日记/{date}.md"
            db = sqlite3.connect("~/.cache/qmd/index.sqlite")
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT c.doc FROM documents d JOIN content c ON d.hash = c.hash WHERE d.path = ?",
                (qmd_path,)
            ).fetchone()
            if row:
                content = row["doc"]
                source = "qmd"
            db.close()

    if content is None:
        return {"category": "unknown", "source": "failed", "length": 0}

    # 3. 判定
    stripped = content.strip()
    # 空/模板特征检测...
    is_empty = all(marker in stripped for marker in [
        "当日无日历事件", "今日知识库无更新", "无 AI 对话记录"
    ]) and "(待补充)" in stripped

    if is_empty:
        return {"category": "empty_template", "source": source, "length": len(stripped)}
    elif len(stripped) < 500:
        return {"category": "short", "source": source, "length": len(stripped)}
    else:
        return {"category": "normal", "source": source, "length": len(stripped)}
```

### 批量扫描脚本模式

```python
import os, glob, sqlite3

def scan_diary_dir(diary_dir, qmd_collection="alexcai-vault"):
    """扫描日记目录，返回分类结果。"""
    results = {"empty": [], "short": [], "normal": [], "unknown": []}
    db = sqlite3.connect("~/.cache/qmd/index.sqlite")
    db.row_factory = sqlite3.Row

    for f in sorted(glob.glob(os.path.join(diary_dir, "*.md"))):
        basename = os.path.basename(f)
        if not basename.startswith("20") or not basename[4] == "-":
            continue  # 跳过非日期文件

        content = None
        source = "direct"
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            date = basename.replace(".md", "")
            qmd_path = f"{qmd_collection}/50-Self/01-日记/{date}.md"
            row = db.execute(
                "SELECT c.doc FROM documents d JOIN content c ON d.hash = c.hash WHERE d.path = ?",
                (qmd_path,)
            ).fetchone()
            if row:
                content = row["doc"]
                source = "qmd"

        if content is None:
            results["unknown"].append({"file": f, "source": "failed"})
            continue

        stripped = content.strip()
        is_empty = (
            "当日无日历事件" in stripped and
            "今日知识库无更新" in stripped and
            "无 AI 对话记录" in stripped
        )

        if is_empty:
            results["empty"].append({"file": f, "source": source, "length": len(stripped)})
        elif len(stripped) < 500:
            results["short"].append({"file": f, "source": source, "length": len(stripped)})
        else:
            results["normal"].append({"file": f, "source": source, "length": len(stripped)})

    db.close()
    return results
```

### 关键教训

- **不要按文件大小判定**：dataless 文件大小显示正常，但内容不可读。
- **qmd 是只读 fallback**：用 qmd 做内容判定和备份，但写入/删除仍操作真实文件。
- **路径映射**：qmd 用 `01-日记`，实际路径是 `01_日记`。
- **安全边界**：qmd 未索引的文件保持不动，不要强行删除。
- **备份报告**：清理报告必须注明哪些文件用了 qmd fallback。

## 2026-06-02 补充：零数据日合并与低密度日处理

### 场景

回溯重写历史日记时，发现早期多日完全没有 Hermes 数据（系统未上线），仅有少量 CC /usage 查询。如果保留 13 份独立日记，每份都是 800 字符的模板填充分——这是噪声，不是日记。

用户反馈："全0日就清理，低密度合并"。

### 判定标准

| 分类 | 条件 | 处理 |
|------|------|------|
| **全零日** | Hermes=0, CC=0, vault=0, cal=0 | 不创建独立日记 |
| **低密度日** | Hermes=0, CC≥1（仅 /usage 等无意义查询）, vault=0, cal=0 | 合并入时期笔记 |
| **有内容日** | Hermes≥1 或 CC 有实质工作 | 独立日记 |

### 合并格式

多日合并为 `YYYY-MM-DD~DD_主题.md`，如 `2026-05-01~13_前Hermes时期.md`。内容包含：
- 概览表格（每日期 + 天气 + CC 会话数 + 主要活动）
- 时期总结段落
- 页脚标注"此笔记合并了 N 天低密度数据，自 XX 日起转为每日独立日记"

### 与现有清理规则的关系

此规则适用于**回溯重写**场景（用户要求重写整个月份）。日常 cron 运行时正常生成每日日记，不触发合并——因为日常 cron 只生成当天，不存在多日批量问题。
