## 场景

整理日记时，Obsidian vault 中的部分 Markdown 文件可能是 macOS/iCloud/Obsidian Sync 的 `dataless` 占位文件。表现为：

- `ls -lO@` 显示 `compressed,dataless`
- Python `open()` 或 `cat` 报：`Resource deadlock avoided`
- 文件名和大小可见，但正文不能直接读取

这种情况下不要按文件大小或文件名清理；必须先拿到正文。

## 安全流程

1. 先尝试触发 Obsidian 同步：
   - `python3 ~/.hermes/skills/auto-diary/scripts/obsidian_sync.py sync <vault>`
   - 等待片刻后重试读取。
2. 如果仍无法读取，用 qmd 索引做只读 fallback：
   - `qmd collection list` 确认 vault collection，例如 `alexcai-vault`。
   - `qmd ls alexcai-vault/50-Self/01-日记 -n 200` 查看 qmd 已索引的日记。
   - `qmd get 'qmd://alexcai-vault/50-Self/01-日记/YYYY-MM-DD.md' -l 200` 抽查正文。
   - 批量处理可读取 qmd sqlite：`~/.cache/qmd/index.sqlite` 中 `documents JOIN content USING(hash)`，字段 `content.doc` 是完整 Markdown 正文。
3. 只处理 qmd 已索引、能取回完整正文、路径映射明确的日期文件。
4. 备份时保存两类信息：
   - qmd 重建正文：`backup/<qmd_path_with_slashes_replaced>.md`
   - 若原文件可复制，再保存 raw copy；复制失败不强行处理。
5. 合并短日记后再删除原件；未索引/不确定的文件保持不动。
6. 清理报告必须注明使用了 qmd fallback，以及哪些文件未动。
7. 整理后运行 `qmd update -c <collection>`，刷新 removed/updated 状态。不要自动跑 `qmd embed`，除非用户明确要求。

## 路径注意

qmd collection 里可能把 Obsidian 路径 `01_日记` 显示成 `01-日记`。删除或写入真实文件时要映射回实际路径，例如：

- qmd：`50-Self/01-日记/2026-05-20.md`
- 实际：`50-Self/01_日记/2026-05-20.md`

## 不要做

- 不要因为 direct read 失败就说文件坏了。
- 不要把 `dataless` 本身记录成永久限制；这是同步/占位状态，不是 Markdown 内容问题。
- 不要删除 qmd 未索引或正文不完整的文件。

## 2026-05-25 实战补充

### 逐日采集替代 weekly 模式

`collect_data.py` 的 `weekly` 子命令尚未实现。手动生成周报时，逐日跑：

```bash
for d in 2026-05-18 2026-05-19 2026-05-20 2026-05-21 2026-05-22 2026-05-23 2026-05-24; do
  echo "=== $d ==="
  python3 ~/.hermes/skills/auto-diary/scripts/collect_data.py diary "$d" 2>/dev/null
  # 或只取 ai_logs 和 calendar_events 做聚合
  python3 ~/.hermes/skills/auto-diary/scripts/collect_data.py diary "$d" 2>/dev/null | jq '{date: .date, ai_logs: .ai_logs, calendar_events: .calendar_events}'
done
```

### 从 qmd 索引批量读取日记正文（Python）

```python
import sqlite3, json

def read_diary_from_qmd(collection, date_str):
    """从 qmd sqlite 读取指定日期的日记正文。"""
    db = sqlite3.connect("~/.cache/qmd/index.sqlite")
    db.row_factory = sqlite3.Row
    # qmd 路径用连字符，实际路径用下划线
    qmd_path = f"{collection}/50-Self/01-日记/{date_str}.md"
    row = db.execute(
        "SELECT c.doc FROM documents d JOIN content c ON d.hash = c.hash WHERE d.path = ?",
        (qmd_path,)
    ).fetchone()
    return row["doc"] if row else None

# 示例：读取一周日记
for d in ["2026-05-18", "2026-05-19", "2026-05-20", "2026-05-21", "2026-05-22", "2026-05-23", "2026-05-24"]:
    doc = read_diary_from_qmd("alexcai-vault", d)
    print(f"{d}: {len(doc) if doc else 'MISSING'} chars")
```

### 周报生成时的数据缺口处理

若某几天日记为空模板（如 5/20-5/23），周报中直接注明“X 天空模板，无实质内容”，不要编造。周报结构参考 `references/weekly-format.md`。

### 清理后索引刷新顺序

1. `qmd update -c alexcai-vault` — 先更新文件列表和 BM25 索引
2. `qmd embed -c alexcai-vault` — 仅在用户要求时更新向量（耗时较长）
3. 检查 `qmd status` 确认 pending 状态
