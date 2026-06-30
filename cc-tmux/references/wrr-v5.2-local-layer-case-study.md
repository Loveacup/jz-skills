# WRR v5.2 本地搜索层 — STDD 多 Agent 流水线案例

## 背景

WRR v5.1 只有 7 个外网引擎，缺失本地知识库搜索。PI 版 WRR v3.4 的 Step 0 曾有"本地优先"路由规则
（Hindsight→session_search→qmd/Obsidian→CodeGraph），但从未实现为代码引擎。v5.0 重写时删除。

## 流水线（2026-06-29）

| Phase | 角色 | 工具 | 产出 |
|-------|------|------|------|
| P1 评估 | Codex | `codex exec` 632行方案 | 4 本地引擎 + local mode + 融合策略 + 测试计划 |
| P2 执行 | CC agent team | cc-tmux | 17 files, +1445/-6, 4 engines + _local_utils + config/router |
| P3 审计 | OMP | call-omp shell sync | concern → deep 单测缺失 → 补修 |
| P4 验收 | 小黄 | 交叉验证 | 248/248 tests, doctor 11 engines, push + OB |

## 关键决策

1. **Codex 先出方案再启动 CC** — 避免 CC 在无约束下自行设计整个架构
2. **P0 范围克制** — CC 只做 4 引擎 + local mode + doctor + 测试，不做 CLI v5 mode 修复
3. **OMP 用 shell sync** — 避开 async 静默失败坑（100MB+ raw 文件可靠产出）
4. **concern 级 verdict 接受后补修** — 不在审计阶段阻塞，一条 deep 单测事后补

## 文件清单

- 新建：`local_supermemory.py`, `local_qmd.py`, `local_obsidian.py`, `local_session.py`, `_local_utils.py`
- 修改：`config.py`（local mode/weights/dispatch）, `router.py`, `registry.py`, `requirements.py`, `wrr-cli.py`
- 测试：`test_local_*.py` × 4, `test_local_routing.py`, `test_doctor_local_engines.py`（61 新测试）

## 代码规模

+1445/-6 行，248/248 tests，11 引擎（7 外网 + 4 本地）。

## Post-P0 Follow-ups

### P1: classify_intent 关键词扩 + recovery mode

Commit `09e57bd`。修复 4 个误判：

| 查询 | 之前 | 之后 |
|------|------|------|
| 大模型推理优化最新进展 | grounding | research |
| open source vector database projects | grounding | discovery |
| 有没有类似LangChain的框架 | grounding | discovery |
| 找不到已删除的GitHub项目 | discovery | recovery |

新增：RESEARCH +9 词、DISCOVERY +10 词、RECOVERY_KEYWORDS 全新 15 词 + `recovery_triggered()`。18/18 classify 准确。

### P1: Exa auth 修复

Commit `bd3652e`。extract/similar 端点用了 `Authorization: Bearer` 应为 `x-api-key`。3 端点全统一。

### Proxy 干扰诊断（跨引擎）

`HTTP_PROXY=127.0.0.1:6152` 导致 Exa API `ConnectTimeout`。诊断模式：health → ok，deep → timeout，curl 父 shell → 200，unset proxy → 200。详见 `references/proxy-env-api-interference.md`。

### 环境修复

Python 版本漂移（3.11/3.12/3.14）+ 缺 `pyyaml` → `plugin.yaml dependencies` 声明 + 版本号三源统一 `5.2.0`。

## 经验教训

1. **proxy env 泄漏** — key 有效、服务健康、父进程连通，子进程挂。诊断先 `unset HTTP_PROXY`。
2. **classify_intent 关键词** — 中英同义词 + 意图家族全覆盖（research/discovery/recovery）。
3. **版本号三源** — plugin.yaml/code/SKILL.md 对不齐产生虚假诊断报告。
4. **OMP shell sync > async** — 100MB+ raw 文件可靠产出，避开静默失败。
