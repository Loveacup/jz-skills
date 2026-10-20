# P2-D1 LLM Writer Harness 三方协作记录

**日期**：2026-07-01  
**参与方**：Codex（planning-only）→ CC（cc-tmux 实现）→ OMP（独立审计，2 轮）→ Hermes（协调/验收/修复）

## 任务
在 `video_analysis_engine.py` 实现插拔式 LLM writer harness：
- `WriterProvider = Callable[[str, str], str]`
- `WriterEvidenceCandidate` / `WriterSectionContext` / `WriterResult` dataclasses
- `WRITER_PROMPTS["3"/"4"/"7"]` 中文 prompt 模板
- `validate_section()` 确定性验证器
- `write_llm_section()` 带重试
- `tests/test_writer_harness.py`（5 RED 测试）

## LLM 选型决策
- **DeepSeek V4 Pro** — 质量优先 + 可插拔（`WriterProvider` 是 callable 注入，不硬编码）
- 项目运行在 Hermes 内部时，默认 provider 复用 Hermes 的 DeepSeek V4 Pro
- 独立运行时注入 DeepSeek API wrapper

## 发现与修复

### Bug #1：`ev['index']` 字段不存在（CC 陷阱）
CC 在 `build_typed_writer_section_contexts` 中直接 `ev['index']`，但 `EvidenceCandidate` dataclass 无此字段。测试通过因为 mock 注入了 `index`，生产数据会炸。
**修复**：`enumerate(sec.get('evidence', []), start=1)` + `index=idx`。

### Bug #2：导入路径不一致（OMP 首轮 blocker）
`test_writer_harness.py` 用了 `from scripts.video_analysis_engine import ...`，全项目其余 7 个测试文件用 `from video_analysis_engine import ...`（PYTHONPATH=scripts 标准）。
**修复**：改为 `from video_analysis_engine import ...`。

### OMP 审计
- **第一轮**：blocker — 导入路径不一致
- **第二轮**：pass — 7/7 criterion 通过，16 条 evidence

## 测试结果
- 5 个新测试 ✅
- 71 个全量（含既有 66）✅
- 零回归

## 代码位置
- `scripts/video_analysis_engine.py`: lines 973–1242（追加在 `_demo` 之前）
- `tests/test_writer_harness.py`: 145 行，新建

## 下一步
P2-D2：实现 §3 Key Insights writer，接入 DeepSeek V4 Pro
