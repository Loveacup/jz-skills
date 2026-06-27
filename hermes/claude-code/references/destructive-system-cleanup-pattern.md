# 四阶段系统清理模式（Archive → CC Pre-Review → Destroy → CC Post-Audit）

用于大规模系统卸载、profile 删除、插件移除等高风险破坏性操作。核心原则：**先封存、再审查、后删除、终审计**——破坏性动作永远在 CC 确认之后。

## 适用场景

- 删除多 profile / plist / 插件 / 数据库等 Hermes 系统组件
- 大规模文件清理（非单文件删除）
- 任何"删完可能回不来"的操作

## 四阶段流程

```
Phase A: Archive + Checksum + Dry-run
  └─ 封存全量快照 → 生成 MANIFEST.sha256 → 生成待删清单

Phase B: CC Shadow-Review（破坏前安全门）
  └─ CC 读封存 + 现场状态 → 逐项交叉核对 → 输出 BLOCKED/PASS

Phase C: Detach + Destroy（仅在 CC PASS 后执行）
  └─ 先脱钩配置 → 重启验证 → 再执行破坏性删除

Phase D: CC Post-Audit（事后核验）
  └─ CC 读现场状态 → 检查残留/误删/降级 → 输出审计报告
```

## Phase A：封存 + 校验 + 干跑

### 封存脚本关键点

```bash
# 封存根目录
ARCHIVE_ROOT=~/.hermes/archives/<name>-$(date +%Y%m%d-%H%M%S)
mkdir -p $ARCHIVE_ROOT/{profiles,launchagents,plugins,db,state}

# rsync 全量复制（保留权限和符号链接）
rsync -a --copy-links ~/.hermes/profiles/<target>/ $ARCHIVE_ROOT/profiles/<target>/

# 保存 plist
cp ~/Library/LaunchAgents/com.hermes.a2a.*.plist $ARCHIVE_ROOT/launchagents/

# 生成 MANIFEST + 待删清单
cd $ARCHIVE_ROOT && find . -type f -exec shasum -a 256 {} \; > MANIFEST.sha256
```

### 关键陷阱

- **Python `shutil.rmtree` 遇 symlink 会抛 OSError**：`shutil.rmtree` 不能直接操作符号链接目录。错误信息：`OSError: Cannot call rmtree on a symbolic link`。**用 shell `rm -rf` 替代**。
- **MANIFEST 自指问题**：MANIFEST.sha256 的第一行通常是对自身的哈希（空文件值 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`），这是良性自指，不影响数据完整性。
- **rsync 窗口期**：大目录 rsync 期间可能有日志文件被写入，导致个别 checksum 不匹配。抽查关键回滚文件即可，不必追求 100% 匹配。
- **Post-Cleanup 残余审计不要用 xhigh + 结构化 checklist**：残余检查本质是「目录存在性验证」，用单条 `ls`/`find` 命令 14s 完成。若用 xhigh + 「逐项 ✅/🔴/⚠️ 判定 + PASS/BLOCKED 判决」格式，会触发无限思考循环（>4min token 冻结）。**策略：先让 CC 做原子存在性检查，确认残余后 Hermes 直接执行删除，不做二次深度审计。**（2026-06-03 系统卸载残余审计实战验证，参见 Pitfall #28）

## Phase B：CC Shadow-Review（破坏前安全门）

### Context 文件模板

```markdown
# <任务名> Shadow-Review

## 背景
<简述要做什么、封存在哪、待删清单在哪>

## 审查清单

### 1. 封存完整性
- 检查封存目录结构是否完整
- 抽查 3-5 个关键文件的 SHA256 与 MANIFEST 是否一致
- 验证封存内容覆盖所有待删项

### 2. 待删清单交叉核对
- 逐项读现场实际文件，对比待删清单
- 检查是否有**保留项被误列入待删清单**
- 检查是否有**该删的遗漏**

### 3. 依赖/引用审计
- 读所有保留 profile 的 config.yaml，检查是否有引用待删 plugin/路径
- 读所有 plist 的 ProgramArguments，检查是否有引用待删路径
- 读 cron job 列表，检查是否有引用待删 profile/plugin

### 4. 脱钩方案审查
- 验证脱钩步骤覆盖所有引用方
- 验证脱钩顺序（先改 config → 重启 → 再删文件）

## 输出要求
- 逐项 ✅/🔴/⚠️
- 判决：PASS（可进入 Phase C）/ BLOCKED（列明阻断项）
- 以 ===CC_REVIEW_DONE=== 结尾

只读，不修改任何文件。
```

### CC 启动参数

```bash
# audit/review 类 → xhigh
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort xhigh
```

### 典型阻断项

- 保留 profile 的 config 仍引用待删 plugin（本次会话 default/cron-worker 引用 3s6m/hermes-a2a）
- 保留 gateway plist 仍引用待删代码仓库路径
- 待删清单遗漏了孤儿 plist

## Phase C：脱钩 + 删除

### 执行顺序（硬约束）

```
1. 编辑保留 profile config → 移除待删 plugin 引用
2. 备份 config 到封存 state/ 目录
3. 重启受影响 gateway（或确认已自动重载）
4. 验证 gateway 正常响应后，才执行删除：
   a. launchctl bootout + 删除 plist
   b. rm -rf profile 目录
   c. rm -rf plugin 目录
   d. mv 退役 DB（改名，非硬删）
5. 验证保留 gateway 进程仍在运行
```

### 退役 DB 命名规范

```bash
suffix=".<name>-retired-$(date +%Y%m%d-%H%M%S)"
mv ~/.hermes/kanban.db ~/.hermes/kanban.db${suffix}
```

### 关键陷阱

- **DB 退役可能被自动撤销**：如果保留了 kanban-gate 插件，Hermes 会在下次 gateway tick 时自动重建 kanban.db（空库）。退役文件中的数据安全，但现场会出现一个降级空库。需明确意图：要么接受空库，要么恢复退役库。
- **gateway plist 可能引用待删路径**：即使 plugin 目录已删，plist 的 `ProgramArguments` 可能仍指向 wrapper 脚本（如 `~/code/hermes-a2a/scripts/gateway-wrapper.sh`）。清理仓库前必须先改 plist。
- **部署副本 vs 代码仓库区分**：删除 profile 下的 `jz-skills/` 数据时，只删部署副本（`~/.hermes/profiles/<name>/home/.hermes/jz-skills/<subdir>/`），**绝不**删代码仓库（`~/code/jz-skills/`）。两者内容相同但职责不同——代码仓库的 `CLAUDE.md` 标注「Don't touch」只约束仓库操作，不适用于已部署副本。删除前先用绝对路径确认目标位置。`hermes-3S6M-profiles/` 等旧三省六部子目录只存在于部署副本中，安全删除。（2026-06-03 系统卸载验证）

## Phase C.5：Post-Cleanup 功能验证（每次清理后强制执行）

**在 CC Post-Audit 之前，先跑功能冒烟**——确保保留的系统组件仍能正常工作。

### 必检清单

```bash
# 1. Gateway 健康（所有保留 profile）
for port in 8417 8460 8461; do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$port/health)
  echo "port $port: $code"
done

# 2. Kanban CRUD 冒烟（创建→列表→归档，验证 DB 未退化）
hermes kanban create "smoke-test" --body "post-cleanup verify" --assignee "planner"
hermes kanban list --status ready --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)), 'ready')"
hermes kanban archive <task_id>

# 3. Profile 清单（确认只保留预期 profile）
ls ~/.hermes/profiles/

# 4. Plugin 清单（确认无残留/孤儿插件）
ls ~/.hermes/plugins/
```

### 冒烟失败处置

- Gateway 非 200 → 检查进程/plist，不要进入 Phase D
- Kanban 创建失败 → DB 可能损坏/退化，检查 `kanban.db` schema
- 意外 profile/plugin 残留 → 查明是否被当前系统引用后再决定删除

## Phase D：CC Post-Audit

### 审计维度

1. 现场残余检查（profiles/plugins/plists）
2. 退役文件审计（改名是否成功、原名是否重现）
3. 保留 agent 健康检查（config/进程/日志）
4. 防止误删验证（关键文件是否完好）
5. Cron job 悬空引用检查
6. 封存完整性抽查（3 个随机文件 SHA256 对比）

### CC 启动参数（同 Phase B）

### 典型发现

- kanban.db 被自动重建（schema 退化）
- gateway plist 仍引用已删仓库路径
- 重复/陈旧 plist 残留
- 退役窗口期的瞬时日志报错（已自愈）

## Phase E：Residual Hunt（深度残余扫描）

> **何时触发：** Phase C 宣称「卸载完毕」后，用户追问「还有没有别的残留？」时。主清理（Phase C）通常只删了目录级别的组件（profiles/plugins/plists），但以下五类残余容易遗漏：
> 1. 已删 profile 引用的 **active cron jobs**
> 2. plugin.yaml 中 **author 字段** 暴露的旧治理体系来源（如「将作监(旧部门)」）
> 3. skill 正文中内嵌的旧体系术语（34 处引用但文件名不含关键词）
> 4. 保留 profile 的 system prompt 中的防御性自述（「不属于旧治理体系」）
> 5. 部署副本中的旧治理数据（`jz-skills/hermes-3S6M-profiles/` vs 代码仓库 `~/code/jz-skills/`）

### 六路扫描法

```bash
# 路 1：关键词全文扫描（旧治理/旧部门名）
grep -rl -iE 'san-sheng-liu-bu|edict|jiangzuojian|hanlinyuan|shangshusheng|shangshu|gongbu|budget|jiangzuojian|hanlinyuan' \
  ~/.hermes/skills/ ~/.hermes/profiles/*/skills/ 2>/dev/null | grep -v archives | sort -u

# 路 2：Config 文件中引用旧 profile 名
grep -rl -E 'shangshu|budget|gongbu|protocol|tester|planner|reviewer|archivist|engineer|auditor|registry|hanlinyuan|jiangzuojian|dispatcher' \
  ~/.hermes/profiles/*/config.yaml 2>/dev/null

# 路 3：Cron jobs 引用已删 profile
hermes cron list 2>&1 | grep -iE 'shangshu|budget|gongbu|protocol|3s6m|三省'

# 路 4：Plugin 元数据暴露来源
head -10 ~/.hermes/plugins/*/plugin.yaml 2>/dev/null | grep -E 'author|description'
# ─ 关键信号：author: 将作监(旧) / description 含「旧治理」「五层校验」→ 旧治理残留

# 路 5：Profile skills 目录直接列表（检查文件名级别）
ls ~/.hermes/profiles/<name>/skills/ | grep -iE '6m|smoke|s6m|a2a|province|constitution|edict'

# 路 6：Hermes-agent 内置 references（治理文档残留）
ls ~/.hermes/skills/autonomous-ai-agents/hermes-agent/references/regent-* \
   ~/.hermes/skills/autonomous-ai-agents/hermes-agent/references/a2a-security* \
   ~/.hermes/skills/autonomous-ai-agents/hermes-agent/references/hindsight-cross* 2>/dev/null
```

### 残余分级处置

| 级别 | 特征 | 处置 |
|------|------|------|
| 🔴 P0 | Active cron job 引用已删 profile，下次 tick 必报错 | **立即删除** cron job |
| 🟡 P1 | 专属旧治理 skill（6m-smoke-test / three-provinces-constitution / a2a-discussion） | **整体删除** skill 目录 |
| 🟢 P2 | Skill references 中引用的旧 doc（regent-3s6m-*.md / edict-integration-pattern.md） | **删除引用文件**，保留 skill 主体 |
| ⚪ P3 | System prompt 中的防御性自述（「不属于旧治理体系」）/ 非专属 skill 中的历史术语 | 低优先级，可择机清理 |

### 关键陷阱

- **文件名不含关键词 ≠ 不是旧治理残留。** `three-provinces-constitution`（治理宪章）文件名无 `3s6m`，但它是整个治理体系的宪章文档。必须通过**内容扫描**（路 1）捕获。
- **plugin.yaml 的 author 字段是铁证。** `kanban-gate` 插件的 author 是「将作监」——即使目录名、描述都不含旧治理关键词，author 字段直接暴露来源。删除后需验证 Kanban 走原生流程仍畅通。
- **Cron job 是唯一会主动报错的残留。** Skill/引用/document 是静态文本不会报错，但引用已删 profile 的 cron job 会在下次 tick 时产生实际错误。P0 优先处理。
- **删除 jz-skills 数据时区分部署副本和代码仓库。** 只删 profile 嵌套 home 下的部署副本 `hermes-3S6M-profiles/`，不删 `~/code/jz-skills/` 仓库。（2026-06-03 系统卸载残余审计实战验证）
