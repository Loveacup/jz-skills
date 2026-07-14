# Evidence-only 代码审计契约

适用：`auditor.independence_level=bundle_only`，审计者只读 evidence bundle、不能或不应自行运行 shell / pytest。

## 包构建前的硬清单

1. **先过 package gate**：包必须是 v2 结构：`task_id`、`mode`、`channel`、`task`、`scope` object、`criterion` array、`threshold.round_limit/reject_limit` numbers、`output={format:"json", evidence_required:true}`、`auditor`。不要沿用扁平旧 schema。
2. **区分 write scope 与 read references**：
   - `scope.allowed_paths`：本次允许改动的文件；
   - `scope.read_only_reference_paths`（或等价字段/证据清单）：判定契约必须读取、但本次不可改的文件，例如 feature flag 的唯一真相源、`pyproject.toml`、红线文件。
   - `changed-files.txt` + 空的 `protected-diff.txt`：证明范围，而非要求审计者自行 `git diff`。
3. **客观运行证据必须原样落盘**：每条 runtime criterion 都要有对应 `*.txt`，内含命令 stdout/stderr 和显式 `__EXIT_CODE__=0`。不要只写“tests passed”的人工摘要。
4. **证据最小但闭环**：带 `diff.patch`、changed/protected diff、改动与参照源码、targeted tests、必要的 full baseline 摘要/输出、CLI smoke 和语义等价脚本输出。不要塞无关全量日志。

## 审计 brief

明确写：

- 只使用 evidence bundle；不调用工具、网络或工作区外源码；
- runtime criterion 的原始命令输出已在 bundle，按该输出裁决，不因无法自行运行 shell 把“不可执行”误判为代码 blocker；
- 返回单一裸 JSON，不要 Markdown：`{severity, summary, evidence, findings}`；`evidence` 必须非空。

## blocker 的裁决顺序

- **证据不足 / scope 不足 blocker**：先 `omp-finish --reject`，补 evidence 或 read-only refs 后再开新 task；不要改代码来“修”证据问题。
- **代码/测试 blocker**：修最小根因、重跑原始命令、更新 evidence 后再审。
- **两轮后仍无合法 verdict，或 raw 快速无界增长**：停止重试，记录 OMP 审计工具失效；Hermes 独立复跑客观命令，并换独立只读审查者（如 Codex read-only）。最终报告必须写“没有 OMP pass”，不能把 fallback 审查改名为 OMP 通过。

## 验收记录的事实层级

分别记录：

1. 当前工作区的代码与测试事实；
2. 审计工具的 verdict / reject / failure；
3. 独立审查者的静态结论；
4. commit / push / release 状态。

本地绿、审计 pass、已提交、已发布是四个不同事实，禁止合并表述。
