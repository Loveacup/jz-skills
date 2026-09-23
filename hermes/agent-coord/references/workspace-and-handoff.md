# 工作区、所有权与交接

> 本文收录通道无关的所有权与交接原则；具体 Git/worktree/工作区操作以所选通道 skill 与项目现行约定为准。本层不建锁服务、不镜像状态。

## 四类所有权：分别记载，权限不隐式合并

| 所有权 | 负责什么 |
|---|---|
| **workspace owner** | 工作区的登记、创建、保留与删除 |
| **execution owner** | 本轮 worker/尝试的进程执行与生命周期 |
| **Git writer / 集成 owner** | index/分支/提交与 repo 共享面（refs/config/hooks/remotes）操作 |
| **document owner** | 需求锚点与阶段结果的回写 |

四者可由同一主体兼任，但**权限不自动合并**——允许改文件不自动允许 stage/commit/merge/push/delete；execution owner 身份不附带 workspace 删除权。

**关键推论（所有权分离场景）**：一个通道（如 Orca）创建并管理的 worktree，可以交给另一通道经批准的 worker 使用；但该**执行者不得私删该目录**、不得自行 `git worktree remove`、不得改动管理方元数据——**清理归 workspace owner**，按其获批的原生路径收尾。反向同样成立：任一通道的 worker/terminal 释放动作，不授权删除由其他主体创建或托管的工作区，也不证明该任务的外部子进程已全部停止。

## 工作区选择梯度（按最小需要选择）

1. **普通 folder**：文档或非 Git 项目直接用文件夹，不强行 git init。
2. **共享只读**：同基线只读分析可共享；但并发写会导致证据漂移，需固定提交或受控快照。
3. **复用现有 checkout**：小范围单写复用即可，不为每个 worker 新建工作区。
4. **独立 worktree**：并行实现、候选方案或不同基线时才创建。

同树分文件并行是**例外**：须证明写集合（含 lockfile、构建产物）不冲突且唯一 Git writer；无法证明就隔离或串行。

核对身份时查规范路径、symlink、宿主、repo/common-dir、base SHA、实际 branch、共享目录/依赖/hooks/端口——**不同路径字符串不构成隔离证明**。linked worktree 共享对象库、常规 refs、config 与 hooks，不是安全沙箱。

## Git 执行合同要点

- **绑定精确对象**：每个写任务绑定精确 worktree、基线 SHA、允许路径、文件 writer、Git writer、结果版本、集成目标；动作逐项授权（建仓/分支/worktree、编辑、stage、commit、merge、push、发布、删除分别批）。
- **单 Git writer**：同一 worktree 的 stage/commit/切分支不得并发；repo 级共享面由集成 owner 串行管理；不得通过别的 worktree 改不归自己的分支或仓库配置。
- **只读预检**：写前在精确路径查 status、HEAD、cached/unstaged diff、untracked、worktree 清单。Git 查询证明版本与变化，**不证明谁在写**；writer 事实须查通道与执行宿主。
- **保护用户成果**：保留用户预置改动；**不自动 stash/reset/clean**，不用全量 add 吞并未知内容。
- **集成后重验**：集成 owner 核对来源/目标版本、审核、策略与授权后串行集成；无冲突不代表正确，最终目标版本上重跑验收。merge --no-commit 不是只读预演；dirty merge 的 abort 不保证复原。
- **未提交成果保全**：保全 diff、必要 untracked 内容及 hash；HEAD 不代表全部被测代码。
- **删除前核对**：无活跃 writer、变化与未合入 commit 已保全、身份正确、删除获批。clean 不等于已合并；worktree lock 不防编辑，不是 writer 锁；worker release 不等于 worktree 删除；禁自动 force 清理。

## 验证证据的最小留存

- 声称 RED→GREEN 且测试未删减时，在 RED 时保存测试完整副本或哈希，并与 GREEN 版本对照；仅 import 失败日志不证明测试当时已经齐全。
- 保护对象在派工前记录准确路径、HEAD/ref、index/dirty 状态、内容哈希；终态相同不能反向证明全部历史操作合规。
- 请求与拒绝保留原生 message ID、reply ID 和回执，不能只留 worker 转述；协调者补记须标明来源，不伪装原生收据。
- Dispatch 生存区间交叠只证明尝试同时存在；声称真实执行并行需要带时间的执行事件，否则明确不作该声明。

## 交接约定：文件承载成果，消息传递变化

- 先形成可读产物与必要校验（落盘、核 hash），再发送「归属/版本＋产物引用＋摘要＋证据＋缺口」；不贴全量日志、不反复转述聊天。
- 引用路径必须对消费者可访问；跨宿主须明确传输机制与完整性验证。不默认公开分享产物，不传递秘密。
- **关键交付后不悄悄覆盖旧版本**；新结果用新版本路径替代。
- **四件事实分别留证，不互相替代**：①消息接受（入队/ack）②文件存在（产物落盘）③worker 完成（原生终态）④业务验收（Hermes 独立核对）。消息 ack 只是 inbox 处理确认；worker 完成只是交接。
- 不是每条短消息都要 hash；持久合同、关键产物和跨会话交接才用。
- 需求修订须说明旧版→新版、变化、受影响任务与新验收；以消费确认为准，入队/已读不等于已按新要求工作。旧版完成可保留原生 succeeded，业务结果记 stale/待重验。
