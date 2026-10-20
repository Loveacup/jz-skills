# P2-D2–D5 LLM Writer 接入与 Coherence Gate 三方记录（2026-07-01）

## 背景

P2-D1 已建立 `WriterProvider = Callable[[str, str], str]`、typed writer context、`WriterResult`、`WRITER_PROMPTS` 与 `validate_section()`。本轮继续把真正 writer 接入报告渲染：§3/§4/§7 走可插拔 LLM provider，§5 保持确定性金句 writer，并新增跨节一致性检查器。

用户明确偏好：**质量优先**；LLM provider 必须可插拔；默认优先云端 DeepSeek V4 Pro（能力足够，关键是 harness）。

## 关键架构决策

1. **Provider 可插拔，不绑定模型**
   - 项目内部只认 `WriterProvider = Callable[[system_prompt, user_prompt], str]`。
   - DeepSeek / Hermes CLI / OMP / mock provider 都只是 callable。
   - 不把具体模型写死进 writer harness；DeepSeek provider 是一个实现，不是框架边界。

2. **§3/§4/§7 分节 LLM writer，§5 保持 deterministic**
   - §3 Key Insights、§4 Deep Dive、§7 Value Assessment 需要综合判断，适合 LLM。
   - §5 Highlights 只需从 `quote_candidate` 证据渲染 blockquote，继续确定性实现。
   - `render_markdown(report, provider=None)` 默认仍保持旧行为；只有传入 provider 才启用 LLM writer。

3. **失败不可静默**
   - LLM writer 验证失败或异常都必须 fallback 到骨架，但必须 `warnings.warn(...)`。
   - OMP 抓到的 blocker：validation failure 路径原先 fallback 但无 warning；已修复 §3/§4/§7 三处。

4. **Coherence checker 不调用 LLM**
   - 新增 `check_report_coherence(markdown)`，只做确定性检查。
   - 这是 D6 真实 LLM 集成前的机械闸口，不让 LLM 自评。

## 落地 API

### DeepSeek provider

`deepseek_writer_provider(system, user)`：
- 纯标准库：`json` + `urllib.request` / `urllib.error`
- `DEEPSEEK_API_KEY` 缺失 → `ValueError`
- HTTP / 网络失败 → `RuntimeError`
- `model='deepseek-chat'`, `temperature=0.3`, `max_tokens=4096`

### render 接线

`render_markdown(report, provider=None)` → `_render_plan_skeleton(..., provider)` → `_emit_section_skeleton(..., report, provider)`。

§3/§4/§7 分支模式一致：

```python
if provider and report:
    ctx = section context for sid
    result = write_llm_section(ctx, provider, retries=2)
    if result.validation_passed:
        emit LLM section
        return
    warnings.warn("validation failed ... fallback")
except Exception as e:
    warnings.warn("LLM writer failed ... fallback")

emit original skeleton fallback
```

### Cross-section coherence checker

新增：

```python
@dataclass
class ReportCoherenceIssue:
    severity: str      # nit | concern | blocker
    code: str
    message: str
    section_id: Optional[str] = None

@dataclass
class ReportCoherenceResult:
    passed: bool
    issues: List[ReportCoherenceIssue]

check_report_coherence(markdown: str) -> ReportCoherenceResult
```

确定性规则：
1. `section_order`：`## 0.`–`## 8.` 单调递增；倒序 blocker；缺 §0/§8 concern。
2. `skeleton_residue`：残留 `Skeleton` / `_骨架占位` → concern。
3. `duplicate_paragraph`：长度 ≥30 的相同正文段落重复 ≥2 次 → concern。
4. `bad_evidence_citation`：`[E]` / `[Ex]` 等非法引用 → concern。
5. `empty_llm_section`：§3/§4/§7 标题存在但正文 <20 字 → blocker。

## 测试与审计证据

Hermes runtime evidence：

```text
PYTHONPATH=scripts python -m pytest tests/test_writer_integration.py tests/test_report_coherence.py -q
13 passed, 3 expected warnings

PYTHONPATH=scripts python -m pytest tests/ -q --ignore=tests/test_asr_config.py
84 passed, 3 expected warnings
```

OMP 审计路径：
- 第一轮 D3-D5 审计：`concern`，缺 runtime evidence 文件锚点。
- 补 `/tmp/p2d3-d5-runtime-evidence.txt` 后复审：`blocker`，发现 validation failure fallback 无 warning。
- 修复 §3/§4/§7 validation failure warning 后复审：`pass`，8 条 evidence，accepted。

## Pitfalls / Future Rules

- **不要把 fallback 写成 `except: pass` 或 validation-fail 静默降级。** 内容不丢不等于可审计；必须 warning。
- **OMP 要求“真实命令输出锚点”。** 如果 OMP 返回 `concern: missing runtime evidence`，不要争辩；生成 `/tmp/<task>-runtime-evidence.txt`，包含 `git status`、targeted tests、full suite stdout/exit code，再重派。
- **不要让 coherence checker 调 LLM。** 它是机械闸口，不是风格评审器。
- **D6 真实 LLM 集成前必须有 provider key 或可委托 CLI provider。** 当前 `DEEPSEEK_API_KEY` 缺失时，不要假装跑过真实 DeepSeek；只能做 mock 集成或实现 Hermes/CLI provider。