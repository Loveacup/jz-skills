# Cross-profile governance deployment

Use this when `web-research-router` must become available to the regent / 三省六部 profile system, not just the default assistant.

## Durable lesson

Hermes skills are profile-local. Creating or patching a skill under the default profile (`~/.hermes/skills/...`) does **not** make it available to `regent` or department profiles under `~/.hermes/profiles/<name>/skills/...`.

For governance-critical research rules, deployment has two parts:

1. **Copy the skill directory into each target profile.**
2. **Patch the governance/constitution skill in `regent`** so the system is instructed to load and enforce it.

Without both, the skill exists but will not reliably shape 三省六部 behavior.

## Target profiles used in the 三省六部 system

Typical targets:

- `regent`
- `planner`
- `reviewer`
- `auditor`
- `engineer`
- `hanlinyuan`
- `shangshu`
- `archivist`
- `budget`
- `dispatcher`
- `emergency`
- `jiangzuojian`
- `protocol`
- `registry`
- `security`
- `tester`

Adjust the list by checking `hermes profile list` before acting.

## Deployment pattern

Copy the default profile skill to profile-local skill trees:

```python
from pathlib import Path
import shutil, datetime

src = Path('/Users/alexcai/.hermes/skills/research/web-research-router')
profiles_root = Path('/Users/alexcai/.hermes/profiles')
stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

for prof in sorted(p for p in profiles_root.iterdir() if p.is_dir()):
    dest = prof / 'skills/research/web-research-router'
    if dest.exists():
        backup = prof / f'backups/web-research-router-{stamp}'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dest, backup)
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    script = dest / 'scripts/dedup_rrf.py'
    if script.exists():
        script.chmod(0o755)
```

Then patch `regent`'s constitution skill:

- Add `web-research-router` to `metadata.hermes.related_skills`.
- Add a rule equivalent to:

> 公开资料搜索、项目检索、来源地图、事实核验、竞品/技术/市场研究，必须加载 `web-research-router`；按 `discovery` / `grounding` / `research` / `recovery` / `academic` 标注模式。学术检索走 Academic Lane：arXiv → Semantic Scholar → OpenAlex/Crossref → PubMed；不把 arXiv 当 peer review；citation count 只做信号不做事实；区分官方代码与第三方复现；SOTA/"首篇"声明须交叉验证。多引擎结果必须先 URL 归一化 + dedup/RRF，再产出 source map；重大事实须交叉验证，不得把搜索结果当已证事实。

## Verification

Verify four layers:

1. **Presence:** each profile has `skills/research/web-research-router/SKILL.md`.
2. **References:** each profile has `references/academic-search-github-projects.md` and any other reference files present in the source. Reference files are easy to miss when syncing individually — `copytree` catches them, but manual `cp SKILL.md` does not.
3. **Content parity:** each profile's copy contains key markers — `### \`academic\`` (v2 Academic Lane), `Hindsight` (v2.1 local memory), and `## Academic Lane Policy` (academic policy chapter). A profile missing these is running an outdated version.
4. **Script health:** each profile's `scripts/dedup_rrf.py` passes `py_compile`.
5. **Policy hook:** `regent` constitution contains both `web-research-router` in related skills and the public-search governance rule.

Useful verification shape:

```python
from pathlib import Path
import subprocess, sys

profiles_root = Path('/Users/alexcai/.hermes/profiles')
missing = []
stale = []
compile_fail = []
content_markers = ['### `academic`', 'Hindsight', '## Academic Lane Policy']

for prof in sorted(p for p in profiles_root.iterdir() if p.is_dir()):
    d = prof / 'skills/research/web-research-router'
    skill = d / 'SKILL.md'
    if not skill.exists():
        missing.append(prof.name)
        continue
    c = skill.read_text()
    for marker in content_markers:
        if marker not in c:
            stale.append(f"{prof.name}: missing '{marker}'")
            break
    script = d / 'scripts/dedup_rrf.py'
    r = subprocess.run([sys.executable, '-m', 'py_compile', str(script)], capture_output=True, text=True)
    if r.returncode:
        compile_fail.append((prof.name, r.stderr.strip()))

assert not missing, f"Missing profiles: {missing}"
assert not stale, f"Stale profiles: {stale}"
assert not compile_fail, f"Compile failures: {compile_fail}"
print(f"All {len(list(profiles_root.iterdir()))} profiles verified")
```

If `regent` has a running gateway, restart it after profile-local skill or constitution changes so subsequent sessions load the new policy.