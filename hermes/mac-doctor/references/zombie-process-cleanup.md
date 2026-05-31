# 僵尸进程检测与清理

macOS 上行之有效的僵尸进程清理方法。

## 检测

```bash
ps aux | grep defunct | grep -v grep
```

或统计数量：
```bash
ps aux | grep -c defunct
```

## 原理

僵尸进程（状态 `Z`）已终止但父进程未调用 `wait()` 回收。**`kill -9` 无法清除僵尸**——它们已经死了。

清理路径：**杀掉父进程，让 launchd (PID 1) 接管孤儿僵尸并自动回收。**

## 步骤

### 1. 找到僵尸的父进程

```bash
# 对每个僵尸 PID 查父进程
ps -p <zombie_pid> -o pid,ppid,stat,comm
```

### 2. 确认父进程是否存活

```bash
ps -p <ppid> -o pid,stat,comm
```

- 状态 `S`/`R` → 父进程还活着，可以杀
- 状态 `Z` → 父进程也是僵尸，已被 launchd 接管（通常会自动回收）
- 不存在 → 父进程已退出，僵尸等待 launchd 回收

### 3. 杀掉父进程

```bash
kill <ppid>
```

父进程一死，其僵尸子进程自动归 launchd，launchd 调用 `wait()` 回收。

### 4. 验证

```bash
ps aux | grep defunct | grep -v grep
# 空输出 = 清理成功
```

## 真实案例 (2026-06-01)

系统健康看门狗检测到 5 个僵尸进程：
- 4 个来自 `Raycast Helper (Extensions)` (PPID 11724)，状态 `S`（存活）
- 1 个 root 僵尸（PPID 49861，已消失）

**操作：** `kill 11724` → 4 个 Raycast 僵尸立即被 launchd 回收。root 僵尸因权限不足未处理（单个无害）。Raycast 自动重启 Helper，功能不受影响。

## 常见僵尸来源

| 来源 | PPID | 处理 |
|------|------|------|
| Raycast Helper (Extensions) | 随机 | `kill <ppid>`，Raycast 自动重建 |
| 短期子进程（brew/script） | 常已退出 | 等 launchd 回收，无需处理 |
| root 进程 | root | 需 `sudo`，单个无害可不处理 |
| Docker/VM 子进程 | daemon | 杀 daemon 后果严重——评估后决定 |

## 预防

僵尸进程通常来自 bug：父进程未正确处理 `SIGCHLD` 或未调用 `waitpid()`。无法从外部预防，只能定期检测清理。建议在系统健康看门狗里加入 `ps aux | grep defunct` 检测项。
