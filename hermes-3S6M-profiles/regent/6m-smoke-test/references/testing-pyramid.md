# 三省六部五层测试金字塔

> 2026-05-30 全面测试实践中总结的方法论。Ob 方案：`三省六部全面测试方案_20260530.md`

## 五层结构

```
L4  非功能   性能 · 故障 · 安全（低频：大版本/月度/季度）
L3  E2E治理  多场景全链路（中书→门下→尚书→六部→史馆）
L2  集成     A2A+Kanban · 讨论 · 事件桥 · 跨部门调用
L1  组件     每模块独立（A2A Server / Kanban / Discuss / Event Bridge / Skill Resolver / DCI）
L0  基础健康  进程·端口·注册表·Gateway·Supermemory（每次修改后必跑）
```

## L0 基础健康（必过门槛）

在启动任何 L2/L3 治理链之前，L0 必须全绿。任一项失败 → 先修复再测试。

| # | 测试 | 命令 | 期望 |
|:--|------|------|------|
| 1 | 进程+解释器 | `ps aux \| grep server.py \| wc -l` | 15+ |
| 2 | 注册表 | `registry.py` 读端口 | 15 profiles，无重复 |
| 3 | 健康+Agent Card | `hermes-a2a-doctor.sh` | 16/16 healthy |
| 4 | Token | `cat ~/.hermes/.a2a-token` | 43 bytes |
| 5 | A2A 任务 | Python 诊断脚本（见下方） | status=completed |
| 6 | Gateway | `ps aux \| grep 'gateway run'` | ≥3 进程 |
| 7 | Kanban | `sqlite3 kanban.db "SELECT count(*) FROM tasks"` | >0 |
| 8 | Supermemory | `supermemory_search` 工具 | 返回结果 |

### A2A 任务快速诊断脚本

```python
import urllib.request, json, time
token = open('~/.hermes/.a2a-token').read().strip()
data = json.dumps({'id':'l0-check','task':'reply: PONG'}).encode()
req = urllib.request.Request('http://127.0.0.1:8939/a2a/tasks', data=data,
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
r = json.loads(urllib.request.urlopen(req).read())
sid = r['id']
time.sleep(15)
req2 = urllib.request.Request(f'http://127.0.0.1:8939/a2a/tasks/{sid}',
    headers={'Authorization': f'Bearer {token}'})
r2 = json.loads(urllib.request.urlopen(req2).read())
print(f'status={r2["status"]}, error={r2.get("error","none")}')
# 期望：status=completed
# 失败：status=failed, error=Empty message → A2A 任务执行通路断裂
```

## L1 组件测试

每模块独立验证，不进全链路：

- **A2A Server**：Agent Card / 任务提交轮询 / 认证 / HOME sandbox 穿透
- **Kanban**：状态机 5 态全路径：create(ready)→claim(running)→block→unblock→complete→archive
- **Discuss**：ROLEPLAY 2-3 轮 / SYNTHESIZE 单轮
- **Event Bridge**：pre_tool_call → JSONL → daemon → Obsidian + Supermemory
- **Skill Resolver**：M2CL 4 层跨 profile 加载
- **DCI Pipeline**：14 kind 分类 + VoteTally

### Kanban 状态机验证命令

```bash
TID=$(hermes kanban create "l1-lifecycle" --body "test" --assignee tester | grep -o 't_[a-f0-9]*')
hermes kanban claim "$TID"      # ready → running
hermes kanban block "$TID"      # running → blocked
hermes kanban unblock "$TID"    # blocked → ready
hermes kanban complete "$TID"   # ready → done
hermes kanban archive "$TID"    # done → archived
```

## L2 集成测试

跨组件联合：

| 场景 | 链路 | 阻塞条件 |
|:--|------|------|
| A2A→Kanban 派工 | regent → A2A task → shangshu → Kanban | 需 A2A 任务通路正常 |
| 讨论→归档 | ROLEPLAY → 礼部 → 史馆 Ob | 需 discuss.py 正常 |
| 事件桥→Supermemory | tool call → daemon → Supermemory | 需 event bridge daemon 运行 |
| 跨部门 A2A | 兵部→户部→工部 3 跳 | 需 A2A 任务通路正常 |

## L3 E2E 治理场景

除现有健康扫描（S1）外，可扩展：

| # | 场景 | 链路 |
|:--|------|------|
| S1 | 健康扫描 | planner→reviewer→shangshu→budget∥gongbu→protocol→tester→reviewer→archivist |
| S2 | 代码审查 | planner→reviewer→shangshu→engineer→tester→reviewer |
| S3 | 早新闻生成 | planner→shangshu→budget(搜)→protocol(编)→reviewer |
| S4 | 制度修改 | planner→reviewer(封驳≥1)→shangshu→archivist |
| S5 | 故障演练 | planner→shangshu→engineer(bug)→tester(发现)→engineer(修复)→tester(回归) |

## 问题追踪协议

每发现缺陷即登记到 Ob 方案 `§八 问题登记`，含：发现时间、层级、描述、严重度（🔴P0/🟡P1/🟢P2-P3）、状态（🔍排查中/📋待修复/✅已修复）。

测试完成后的「追踪问题到方案」回写步骤：
1. 确认问题在方案中已登记
2. 已修复的标记 ✅ + 修复摘要
3. 已知但未修复的保留 📋
4. 更新方案 `modified` 时间戳
