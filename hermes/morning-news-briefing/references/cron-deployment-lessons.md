# Cron 部署与 Skill 加载教训

日期 2026-06-03 · 关联：morning-news-briefing v4.0

## 两道门挡住 Skill 加载

CC agent team 深入 Hermes 源码（`agent/skill_utils.py`, `tools/skills_tool.py`）21 分钟调查结论：

### 门一：SKILL.md frontmatter `platforms` 字段

**位置**：`agent/skill_utils.py:128-169` (`skill_matches_platform`)
**生成点**：`tools/skills_tool.py:1054-1062` (`unsupported` 状态)

`platforms: [macos, linux]` 的值看似正确，但 readiness 检查可能将其与"投递平台"(cron/telegram) 而非 OS(darwin) 比对，导致恒不匹配 → `readiness_status: "unsupported"`。

**修复**：确认 `platforms` 字段值为 `[macos, linux]` 且 readiness 按 OS 比对。必要时补 `cron, telegram`。

### 门二：Gateway 进程缓存

即使 SKILL.md 修好了、文件在正确位置，gateway 进程启动时会冻结：
- `SKILLS_DIR` 常量（`skills_tool.py:90`）
- `_EXTERNAL_DIRS_CACHE`（external_dirs 缓存）

如果 SKILL.md 在 gateway 启动后才修好，内存里仍是旧状态 → 继续报错。

**修复**：部署 skill 后重启 gateway 清缓存。

### 部署后验证步骤

```bash
# 1. 部署 skill
cp -r .../morning-news-briefing ~/.hermes/profiles/cron-worker/skills/

# 2. 更新 external_dirs（如需要）
#    config.yaml: skills.external_dirs 包含 ~/.hermes/profiles/cron-worker/skills

# 3. 重启 gateway 清缓存
pkill -f "hermes-agent-gateway" && sleep 3
# gateway wrapper 会自动重拉

# 4. 验证加载
#    在 cron-worker 进程内调 skill_view("morning-news-briefing")
#    确认返回 success 且 readiness_status 不为 unsupported
```

### 教训

- **部署 skill 后必须重启 gateway** — 缓存不刷新 = 永远看不到
- **不要假设 `platforms: [macos, linux]` 够用** — readiness 语义可能不同于预期
- **cron job 带病成功是真实风险** — `last_status: ok` 不代表 skill 加载了
