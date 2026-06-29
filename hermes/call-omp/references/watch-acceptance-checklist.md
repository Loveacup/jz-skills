# --watch 验收清单 · call-omp v0.5.0

> 逐条 true/false，全 true 后方可 accept。

## 核心行为

| # | 验收条件 | 状态 |
|:---:|------|:---:|
| W1 | `--watch --interval N` 按 N 秒轮询 | ✅ |
| W2 | 进度变化时输出 `📡 #SEQ [距上次 Xs] raw XB/Y行` | ✅ |
| W3 | `--notify-on-change` 下进度不变时沉默 | ✅ |
| W4 | 完成时自动调 monitor 校验 + 输出裁决报告 | ✅ |
| W5 | ACP 通道 + `--watch` → exit 3 + 报错 | ✅ |

## 超时

| # | 验收条件 | 状态 |
|:---:|------|:---:|
| W6 | `--timeout N` 到达后自动 kill + rejected（exit 20） | ✅ |
| W7 | 未指定 `--timeout` 时默认 = `run.max_time + 60s` | ✅ |
| W8 | 超时时输出 `⏰ 超时 · Xs/Ys` | ✅ |
| W9 | 超时 kill 幂等（重复 kill 不报错） | ✅ |

## 干预

| # | 验收条件 | 状态 |
|:---:|------|:---:|
| W10 | 每轮输出 `干预: kill <pid>` | ✅ |
| W11 | 外部 kill pid 后 watch 检测到进程退出 → 正常完成 | ✅ |

## 输出格式

| # | 验收条件 | 状态 |
|:---:|------|:---:|
| W12 | 包裹 `===📡 BEGIN/END===` 中继标记 | ✅ |
| W13 | 输出 JSON 末行（phase/severity/evidence_count） | ✅ |
| W14 | 距上次时长准确（非距开始时长） | ✅ |

## 边界

| # | 验收条件 | 状态 |
|:---:|------|:---:|
| W15 | raw 文件不存在时 watch 不崩溃 | ✅ |
| W16 | INTERVAL 非正整数 → exit 3 | ✅ |
| W17 | state 文件缺失 → exit 3 | ✅ |
