# HTTP_PROXY 干扰外部 API 诊断经验

## 现象

Exa API search 在 Hermes 内正常（Wrr 插件走 Hermes Python），但 CLI 子进程（`wrr-cli.py doctor`、pytest 直调）下 `httpx.ConnectTimeout`。

curl 直接测 `api.exa.ai` 返回 200，但 Python `httpx` 挂起。

## 根因

`HTTP_PROXY=127.0.0.1:6152`（Surge/Clash 代理）被子进程继承。
- curl 走系统代理配置，能正常穿透
- httpx 尝试通过 `127.0.0.1:6152` 代理连接 `api.exa.ai`，TLS 握手在代理层超时

## 诊断方法

```bash
# 1. 确认代理是否存在
echo "HTTP_PROXY=$HTTP_PROXY"
echo "HTTPS_PROXY=$HTTPS_PROXY"

# 2. 对比：清代理后是否恢复
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
curl -s https://api.exa.ai/health          # 不含代理
curl -x http://127.0.0.1:6152 https://api.exa.ai/health  # 含代理

# 3. 确认是 httpx 特有的，还是所有 HTTP 客户端都受影响
unset HTTP_PROXY HTTPS_PROXY
python3 -c "import httpx; print(httpx.get('https://api.exa.ai/health').status_code)"
```

## 影响范围

- 受影响的引擎：Exa、Tavily、任何走 httpx 的外部 API
- 不受影响的：本地引擎（qmd/Obsidian/supermemory/session）、SearXNG（本地 127.0.0.1）

## 修复方案

### 方案 A：全局关闭代理（治本）

Surge/Clash 白名单 `api.exa.ai`，或在 Hermes/cron 环境中 `unset HTTP_PROXY`。

### 方案 B：引擎层防御（治标）

在 `exa.py` / `tavily.py` 的 `search()` 中，调用前清代理环境变量：

```python
import os
_proxy_keys = [k for k in os.environ if 'proxy' in k.lower()]
_saved = {k: os.environ.pop(k) for k in _proxy_keys}
try:
    # ... httpx call ...
finally:
    os.environ.update(_saved)
```

当前未实施方案 B（保持代码简单，依赖环境配置）。
