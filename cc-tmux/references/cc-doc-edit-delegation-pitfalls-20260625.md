# CC 文档修改委派坑点（AI-MUD 2026-06-25）

## 触发场景

用 cc-tmux 委派 Claude Code 修改 Obsidian/Markdown 多文档，尤其是：

- 先审计报告，再让 CC 按报告改文档；
- 同名/近似项目目录存在多个位置；
- 任务要求长时间运行且用户强烈要求可见进度；
- Hermes 侧已准备 context，但需要确认 CC 真的启动、收到、执行。

## 本次踩坑

1. **context 写好了但没有启动 CC**
   - 现象：`/tmp/cc-*-context.md` 存在，但无 transcript、lock、turn-done、目标文件 mtime 未变。
   - 教训：写 context 不是派活。必须验证 `cc-start.sh` 成功、`cc-send.sh` 返回成功、pane 中 CC 开始读 context。

2. **只看“CC 在读文件”，没看路径**
   - 现象：CC 读到了错误目录 `10_Projects/AI-MUD/`，而正确目录是 `20-Areas/20_技术项目/AI-MUD-世界引擎/`。
   - 教训：文档修改任务必须在首轮抓屏里核对绝对路径；路径不对立即 `C-c`，不要等它继续思考。

3. **xhigh/high 都可能在文档编辑任务上过度思考**
   - 现象：spinner/THINK_TIME 持续增长，但文件 mtime 长时间不变，CC 在“核对状态/思考方案”里空转。
   - 教训：文档批改类任务要强约束“读一次→改一次→写入→报绝对路径”，并用 mtime 独立确认。

4. **Hermes 直接接管写文件可能越权**
   - 现象：用户要求“让 CC 直接修改”，Hermes 因 CC 低效而自己脚本写 7 个文件，用户要求恢复。
   - 教训：当用户明确指定 CC 执行时，Hermes 只能做 orchestration/audit/correction；除非用户批准，不要代替 CC 写目标文件。

## 推荐流程

### 1. 派发前：上下文必须写死路径

Context 必须包含：

```md
唯一工作目录：/absolute/path/to/project/
禁止读取/修改：/absolute/path/to/wrong-or-old-project/
禁止 Glob/Search 去找同名项目；直接使用上述绝对路径。
每改完一个文件，回复：已写入：<绝对路径>
最后总结写入 /tmp/<task-summary>.md
```

### 2. 启动后：三点存活验证

- `cc-start.sh` 输出 session 名；
- `cc-send.sh` 成功；
- `tmux_read`/capture-pane 看到 CC 正在读正确 context。

如果只完成前两项，不算任务已启动。

### 3. 首轮进度：必须核对路径和 mtime

在第一次进度汇报中检查：

```bash
stat -f "%Sm %z %N" -t "%H:%M:%S" /absolute/project/*.md
```

同时看 pane 中 Read/Write 的路径是否属于唯一工作目录。

### 4. 空转判定

如果出现以下组合，先汇报，再按用户偏好决定中断/纠偏：

- THINK_TIME 持续增长超过数分钟；
- 目标文件 mtime 没有变化；
- pane 显示反复“读取/核对/思考”，没有 Edit/Write；
- 或路径不属于唯一工作目录。

### 5. 纠偏文本模板

```md
你刚才读错目录/没有写入。立刻纠偏。

正确目录唯一是：<ABS_PATH>
错误目录：<WRONG_PATH>

要求：
1. 禁止读取/修改错误目录。
2. 不要 Glob 搜同名项目，直接使用绝对路径。
3. 从 <specific_file> 开始改，避免继续卡在前一个文件。
4. 每改完一个文件，报告“已写入：<绝对路径>”。
5. 最后总结写入 /tmp/<summary>.md。
```

## 验收清单

- [ ] 目标文件 mtime/size 确实变化。
- [ ] 禁止修改的文件 mtime 未变。
- [ ] 错误目录 mtime 未变或不存在。
- [ ] 新建文件存在且 size > 0。
- [ ] summary 文件存在。
- [ ] wikilink 检查无缺失。
- [ ] 关键词/清单项命中，不能只信 CC 自报。
