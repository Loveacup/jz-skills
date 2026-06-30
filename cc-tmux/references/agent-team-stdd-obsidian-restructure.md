# Agent Team STDD Obsidian Restructure Pattern

> ⚠️ 2026-06-29 WRR 实战教训：不要用 agent team 做 OB 重构。CC 的 agent team 模式在复杂任务上极易陷入无限思考（Pitfall #53/56/57 三重叠加）。**推荐模式**：Codex 方案设计 → CC **单 agent** 执行（短指令 + 读文件模式）。详见 `references/wrr-ob-stdd-restructure-case-study.md`。

Use when driving CC via cc-tmux to review and restructure an Obsidian project documentation folder.

## Recommended delegation package

- Use Agent Team + high effort; avoid max for document restructuring unless there is a specific deep-debug need.
- Ask for at least three read-only reviewers before execution:
  - STDD/control-plane reviewer: finds missing Spec/Accept/Verify/residual ledger structure.
  - Architecture consistency reviewer: checks whether terminology and file responsibilities still match the design.
  - Obsidian information architecture reviewer: checks naming, split boundaries, MOC, wikilinks, maintainability.
- Main thread synthesizes findings, then performs the restructure.
- If the user asks for “最终实现建议 / 架构建议 / 路线图回写”, add this as an explicit deliverable in the context, not as an afterthought:
  - map current prototype → final architecture without rewrite;
  - classify requirements by Phase;
  - propose minimal implementable slices;
  - identify data models and Engine/LLM/UI boundaries;
  - list files to update in architecture/roadmap/control-plane docs.

## Two-stage workflow

### 1. Read-only review first

Tell CC to save a plan report before editing, then stop:

- `/tmp/cc-output-<project>-docs-restructure-plan.md`

The plan report should contain:

1. Current doc-pack diagnosis.
2. Issues by severity: blocker / concern / nit.
3. Target structure.
4. Rename / split / merge list.
5. STDD additions: decisions, residuals, accept criteria.
6. Execution sequence with verification after each risky step.
7. Risks and non-goals.
8. Questions with recommended defaults.
9. Implementation architecture + roadmap advice when requested by the user.

Hermes reviews the plan and decides defaults before sending the execution command.

### 2. Execute after Hermes approval

The execution instruction should restate the chosen defaults (for example: rename numbering, whether to add ROADMAP, what to mark as historical). Require CC to save:

- `/tmp/cc-output-<project>-docs-restructure-final.md`

Final report must include changed files, renamed files, new files, STDD updates, roadmap/architecture write-back summary, verification commands + real output, and residual risks.

## Typical successful outputs

- `README_文档地图.md` or equivalent MOC.
- `STDD_项目控制面.md` or equivalent control document.
- Optional but often useful: `ROADMAP_落地路线图.md` or equivalent when the task includes final implementation planning.
- Split overloaded documents into focused files with numbered names.
- Rename misleading documents when the H1/content has evolved.
- Update all wikilinks after renames/splits.
- Write a completion report to `/tmp/cc-output-<task>.md` with agent-team conclusions, before/after structure, changed files, residuals, and verification evidence.

## Directory governance pass

Use this when the user says the Obsidian project folder has become “too many docs / too messy”. Treat it as an STDD directory-governance task, not as another content-expansion task.

- Spec: reduce cognitive load and make the entry path obvious; do not continue expanding design content.
- Accept before editing: root markdown count target, total markdown count preserved, no broken wikilinks, README/MOC updated, control-plane validation updated, no deletion unless explicitly approved.
- Build minimally: keep only the true entry/control docs at the project root (usually README/MOC, STDD/control plane, ROADMAP); move design docs into a few class-level subdirectories such as `00_愿景与参考/`, `10_运行时架构/`, `20_世界与机制/`, `30_UI与表现/`, `40_安全转化与自进化/`, `90_归档/`.
- Prefer move-only cleanup over merging. Only archive/merge a file when duplication is explicit and there is a clear `absorbed_into` target; otherwise leave the content intact.
- After moving files into subdirectories, update validation scripts and examples from `base.glob('*.md')` to `base.rglob('*.md')`; otherwise the check silently ignores moved files.
- Make README state that Obsidian wikilinks resolve by filename, so moving files into folders should not require path-qualified wikilinks as long as filenames remain unique.
- Final user-facing reply should be short: what changed, final tree/counts, link-check result. Put long details in the CC report file, not in Telegram, unless the user asks.

## Second-opinion audit pattern

After CC finishes, Hermes should independently verify. For higher confidence or when the user asks, run a read-only Codex CLI audit as a second opinion:

- Tell Codex explicitly: “Read-only audit only. Do not modify files.”
- Ask it to check current disk state, not CC self-report.
- Ask for concise verdict with evidence paths and blocker/concern/nit classification.
- If Codex finds a small concern, Hermes may patch it directly if it is low-risk and within scope; then re-run link checks.

Do not let Codex become the writer unless the user explicitly asks; here it is an auditor.

## Verification pitfalls

- Do not trust CC's “0 broken links” self-report. Re-run from Hermes.
- Naive `grep` over markdown can falsely detect wikilinks inside fenced code blocks.
- Project-local link checks can falsely classify valid cross-folder Obsidian links as missing.
- Better check: strip fenced code blocks, resolve targets against the whole vault, and separately report cross-directory links.
- After inserting or renaming numbered sections, grep for stale section references such as `§15.3`; update cross-references to the new headings.
- If `cc-finish` reports non-dangerous residual input, never press Enter. Release lock if allowed, keep the session as evidence, and report the residue.

## Example verification logic

```python
from pathlib import Path
import re
vault = Path('/Users/alexcai/Documents/Obsidian/AlexCai')
base = vault / '20-Areas/20_技术项目/<project>'
all_files = {p.stem for p in vault.rglob('*.md')}
project_files = {p.stem for p in base.rglob('*.md')}
missing, external = [], []
for p in base.rglob('*.md'): 
    txt = p.read_text(encoding='utf-8')
    stripped, in_fence = [], False
    for line in txt.splitlines():
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if not in_fence:
            stripped.append(line)
    for target in re.findall(r'\[\[([^\]|#]+)', '\n'.join(stripped)):
        if target not in all_files:
            missing.append((p.name, target))
        elif target not in project_files:
            external.append((p.name, target))
print('missing_in_vault', missing)
print('external_vault_links', external)
```

Pass condition: `missing_in_vault == []`. Cross-folder links are not failures if the target exists in the vault.

## Finish discipline

- Release the cc-tmux lock after turn-done and verification.
- Do not kill the CC session unless the user explicitly asks or the session is known to be disposable and the skill's kill-session rule is satisfied.
- If `cc-finish` reports non-dangerous residual input, never press Enter; report/keep evidence or clean only if safe.
