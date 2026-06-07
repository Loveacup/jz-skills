# jz-skills Git Commit Scanning for Auto-Diary

## Purpose

The auto-diary's `collect_data.py` currently only scans Obsidian vault (`~/Documents/Obsidian/AlexCai/`) for knowledge base changes using `find -newermt`. But the user's primary knowledge work product is the **jz-skills git repo** (`~/code/jz-skills/`), which contains 60+ skill definitions, deployment scripts, and documentation. These commits are entirely invisible to the diary.

## Scanning Approach

```python
def scan_jz_skills_git(date_str: str) -> list[dict]:
    """Scan jz-skills git log for commits on the target date."""
    import subprocess, json
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    tz = ZoneInfo("Asia/Shanghai")
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    repo = "~/code/jz-skills"
    
    # Get all commits on target date
    r = subprocess.run(
        ["git", "-C", repo, "log",
         f"--after={date_str}T00:00:00+08:00",
         f"--before={date_str}T23:59:59+08:00",
         "--format=%H|%ad|%s",
         "--date=short"],
        capture_output=True, text=True, timeout=10
    )
    
    commits = []
    for line in r.stdout.strip().split("\n"):
        if not line: continue
        parts = line.split("|", 2)
        if len(parts) < 3: continue
        hsh, date, subject = parts
        
        # Get file stats
        r2 = subprocess.run(
            ["git", "-C", repo, "show", "--stat", "--format=", hsh],
            capture_output=True, text=True, timeout=10
        )
        # Parse "X files changed, Y insertions(+), Z deletions(-)"
        stats_line = r2.stdout.strip().split("\n")[-1] if r2.stdout.strip() else ""
        
        # Get file list
        r3 = subprocess.run(
            ["git", "-C", repo, "diff-tree", "--no-commit-id", "--name-only", "-r", hsh],
            capture_output=True, text=True, timeout=10
        )
        files = [f for f in r3.stdout.strip().split("\n") if f]
        
        commits.append({
            "hash": hsh[:7],
            "date": date,
            "subject": subject,
            "stats": stats_line,
            "files": files[:50],  # Cap at 50
            "total_files": len(files)
        })
    
    return commits
```

## Diary Format for Git Commits

In the diary's `📚 知识库更新` section, git commits should be presented as:

```markdown
### 🏛️ jz-skills — {N} Git Commits

#### 1. 🔍 `feat(dingtalk): v1.3.0 图片下载+OCR全链路` (8 files, +746/-57)
→ 关联：💻 CC alexcai + dingtalk-img-reverse

- **skill/SKILL.md** — 描述
- **references/doc.md** — 描述
```

## Cross-Reference with AI Sessions

Match commits to AI sessions by keyword overlap:
- Commit subject mentions "dingtalk" → link to CC dingtalk reverse sessions
- Commit subject mentions "topic" → link to Topic testing sessions
- Commit subject mentions "auto-diary" → link to diary cron
- Commit subject mentions "claude-code" → link to CC observer sessions

## Integration Point

Add to `collect_data.py` → `collect_diary_data()`:
```python
"jz_skills_commits": scan_jz_skills_git(date_str)
```

And update diary format to include this field in the knowledge base section.

## Limitations

- Git commits may appear on different dates than the actual work (if committed next morning)
- Only scans the default branch; feature branches not tracked
- File lists capped at 50 per commit to avoid token blow-up
- Requires git to be available and the repo to exist at the hardcoded path
