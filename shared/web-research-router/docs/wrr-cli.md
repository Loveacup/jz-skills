# wrr-cli —— Web Research Router 命令行工具

`wrr-cli.py` 是 WRR 的独立命令行入口，直接驱动 `wrr` 包（`router` + `registry` +
`engines`），**不经过 Hermes 运行时 / tool handler**。适合在终端临时检索、写脚本、
跑 CI 冒烟，或在排查引擎问题时绕开 Hermes 单独验证某条 fallback 链。

- 位置：`~/.hermes/plugins/wrr-hermes/wrr-cli.py`
- 依赖：仅 Python 标准库 + `wrr` 自身（含 `httpx`，wrr 已依赖）。无 click/typer。
- Python：3.10+（用到 `str | None` 注解）。

## 快速开始

```bash
cd ~/.hermes/plugins/wrr-hermes
./wrr-cli.py test                       # 冒烟测试三大动作
./wrr-cli.py search "claude opus 4.8" --mode deep --count 5
./wrr-cli.py fetch https://exa.ai --max-chars 2000
./wrr-cli.py similar https://exa.ai
```

脚本已 `chmod +x`，可直接 `./wrr-cli.py`，也可 `python3 wrr-cli.py`。

## 命令

### `search` —— 多引擎 fallback 搜索

```bash
wrr-cli.py search "查询词" [--count 10] [--mode {fast,auto,deep-lite,deep}]
                          [--provider {exa,brave,searxng}]
```

- `--count`：结果数，1..20（默认 10）。
- `--mode`：**仅影响 Exa**（fast/auto/deep-lite/deep）；缺省时按查询自动路由。
- 默认 fallback 顺序：`exa → brave → searxng`。

### `fetch` —— 抓取 URL 正文

```bash
wrr-cli.py fetch "https://..." [--max-chars 5000] [--provider {exa,brave}]
```

- `--max-chars`：正文截断上限，1..50000（默认 5000）。
- 默认 fallback 顺序：`exa → brave`（exa 返回干净正文，brave 为裸抓取兜底）。

### `similar` —— 查找相似页面（仅 Exa）

```bash
wrr-cli.py similar "https://..." [--count 10]
```

- 仅 Exa 支持；指定 `--provider` 为非 exa 时该能力不可用。

### `test` —— 冒烟测试

```bash
wrr-cli.py test [--provider exa]
```

依次验证 `search` / `fetch` / `similar` 能否调通，逐项打印 `✓/✗/—`。
全部通过退出码 `0`，任一失败 `1`。`--provider` 非 exa 时 `similar` 自动跳过（`—`）。

## 通用选项

| 选项 | 说明 |
|------|------|
| `--json` | 输出机器可读 JSON（见下）。 |
| `--provider {exa,brave,searxng}` | 强制单引擎，**禁用 fallback**。 |
| `--env PATH` | 指定 `.env` 路径。 |
| `-q, --quiet` | 不打印 `· 已加载 env` / `● provider=` 等元信息（走 stderr）。 |

## 配置 / .env

引擎所需环境变量：

| 变量 | 用途 | 必需性 |
|------|------|--------|
| `EXA_API_KEY` | Exa 搜索 / 抓取 / findSimilar | Exa 路径必需 |
| `BRAVE_API_KEY`（或 `BRAVE_SEARCH_API_KEY`） | Brave 搜索 | Brave 路径必需 |
| `SEARXNG_URL` | SearXNG 实例地址（如 `http://127.0.0.1:32080`） | SearXNG 路径必需 |

CLI 启动时自动加载 `.env`，优先级：

1. `--env PATH`
2. `$WRR_ENV`
3. `~/.hermes/.env`（默认）

解析器为内置极简实现：支持 `KEY=VALUE` / `export KEY=VALUE`、`#` 注释、空行、
首尾引号；**不覆盖**已存在的真实环境变量。

## 输出格式

**人类可读（默认）**：渲染 Markdown 列表（标题 / URL / 摘要），元信息（已加载
env、实际 provider、是否降级）打到 **stderr**，正文走 stdout —— 可安全重定向。

**`--json`**：稳定结构，便于管道处理。

成功：

```json
{
  "operation": "search",
  "ok": true,
  "provider": "exa",
  "fallback_chain": [{"provider": "exa", "ok": true, "count": 5, "error": null}],
  "result": [{"title": "...", "url": "...", "snippet": "...", "highlights": ["..."]}]
}
```

`fetch` 的 `result` 为单对象 `{"url","text","highlights"}`；`search`/`similar`
为对象数组。

失败：

```json
{"operation": "extract", "ok": false, "error": "all_engines_failed",
 "detail": "All engines failed for extract:\n  - exa: timeout >10.0s\n  - brave: budget exceeded (skipped)"}
```

## 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 运行期失败（所有引擎失败 / WRR 异常） |
| `2` | 参数错误（count / max-chars 越界、URL 非法等） |
| `130` | 用户中断（Ctrl-C） |

## 设计说明 / 已知限制

- **为何走 `router.route()` 而非引擎裸调**：router 已封装 fallback、per-engine
  超时与总预算（`TOTAL_BUDGET_SECONDS=10s`），裸调引擎会丢这些保障。`--provider`
  通过 `route(explicit_provider=...)` 实现单引擎、禁 fallback，等价于"直接调用某引擎"。
- **总预算 10s**：`fetch` 默认链上 Exa 若慢于 10s，会触发
  `exa: timeout` → `brave: budget exceeded (skipped)` 整链失败。这是 router 既有
  策略，非 CLI bug；可改用 `--provider brave` 直抓，或调 `wrr/config.py` 的
  `TOTAL_BUDGET_SECONDS` / `ENGINE_TIMEOUT`。
- **`--provider` 下的"已降级"提示**：显式单引擎时，wrr 的 formatter 仍可能打印
  `⚠️ fallback ... 已降级` 字样（源于其 `degraded_from` 判定），属 wrr formatter
  既有行为，不影响结果正确性。
- 不依赖 wrr 顶层 `__init__` 的再导出（其当前为空），全部从子模块按需导入。
