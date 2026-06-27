# Surge DNS 审查清单

## 审查顺序

1. **定位配置文件** — Alex 有两套：`mine.conf` (本地) 和 `Naixi_Trojan.conf` (iCloud 同步)。先确认审查哪个。
2. **跑只读诊断** — `environment` + `test-network` + `dump active` + `dump summary`
3. **逐项检查 DNS 参数**

## DNS 参数检查表

| 参数 | 正确值 | 常见问题 |
|------|--------|---------|
| `dns-server` | `114.114.114.114, 223.5.5.5` 或 `119.29.29.29, 223.5.5.5` | ❌ 混了 `8.8.8.8`（国内慢/污染）；❌ 混了 `system`（不确定） |
| `encrypted-dns-server` | `https://223.5.5.5/dns-query`（阿里 DoH）或 `https://dns.alidns.com/dns-query` | ❌ 用海外 DoH 但没配 `encrypted-dns-follow-outbound-mode` |
| `encrypted-dns-follow-outbound-mode` | `true` | ❌ 缺失——DoH 请求不走代理，海外 DoH 直连超时。Surge v5+ 参数名（旧名 `doh-follow-outbound-mode`） |
| `hijack-dns` | `8.8.8.8:53, 8.8.4.4:53`（网管模式） | 🟢 网关劫持下游 Google DNS 查询 |
| `udp-policy-not-supported-behaviour` | `direct` | ❌ `reject`——UDP 静默丢包 |

## Host 区检查

| 检查项 | 说明 |
|--------|------|
| 机场域名 | 必须用普通 DNS 解析（`server:223.5.5.5`），防 DoH → 代理 → DNS 死循环 |
| 国内域名 | 用 `DOMAIN-SET:China_Domain.txt` → 阿里 DoH |
| 残留规则 | 清理 `cloudflare-dns.com = server:1.1.1.1` 等旧 DoH 残留 |
| DoH 域名自身 | `dns.alidns.com = server:223.5.5.5`（用普通 DNS 解析 DoH 域名本身） |

### DOMAIN-SET + 加密 DNS 路由（Surge v5+ 正确写法）

来源：manual.nssurge.com/dns/local-dns-mapping.html § Referencing Rule Sets

```ini
[General]
encrypted-dns-server = https://dns.google/dns-query, https://cloudflare-dns.com/dns-query
encrypted-dns-follow-outbound-mode = true

[Host]
# 国内域名走国内 DoH（防止泄露 + 提速）
DOMAIN-SET:https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/china_domains.txt = server:https://dns.alidns.com/dns-query
# DoH 域名自身用普通 DNS 解析（防死循环）
dns.alidns.com = server:223.5.5.5
```

> `DOMAIN-SET:` 必须在 `[Host]` 段中使用，不能直接写在 `encrypted-dns-server` 行里。`domain-set:` 是小写且在 GUI 中显示不同——配置文件里用大写 `DOMAIN-SET:`。

## 视频教程参考（不良人 thinkbox）

视频教程推荐的 DNS 方案：
1. `dns-server` 用 system 即可（只解析 DoH 域名 + 测网络）
2. `encrypted-dns-server` 用海外 DoH（Google/Cloudflare）
3. `encrypted-dns-follow-outbound-mode = true`（核心——让 DoH 走代理。Surge v5+ 参数名，旧名 `doh-follow-outbound-mode`）
4. Host 区：机场域名用普通 DNS 解析；国内域名走 `DOMAIN-SET` → 国内 DoH
5. 可选 `auto-fallback-dns` 做兜底

Alex 实际用的是阿里 DoH（`https://223.5.5.5/dns-query`），不走海外 DoH。这是合理的简化——阿里 DoH 直连可用，无需代理，DNS 不会泄露到海外但阿里可见查询内容。

## 🚨 DoH 切换陷阱（2026-06-02 教训）

**绝不直接改 `encrypted-dns-server` 切换海外 DoH 而不验证可达性。**

### 失败案例：Cloudflare DoH

将 `encrypted-dns-server` 从 `https://223.5.5.5/dns-query` 切成 `https://cloudflare-dns.com/dns-query` 后 DNS 全断。原因：

1. **Bootstrap DNS 解析 `cloudflare-dns.com`** — Host 区里 `server:223.5.5.5` 解析 CF 域名可能返回被 GFW 污染的 IP
2. **代理节点不通 CF DoH** — 即使 `encrypted-dns-follow-outbound-mode = true`，日本节点访问 `cloudflare-dns.com:443` 不一定通
3. **视频教程用的是 Google DoH** — `dns.google`，不是 Cloudflare。不同海外 DoH 在国内代理环境下的可达性完全不同

### 切换前的验证步骤

```bash
# 1. 确认 DoH 域名能正常解析
nslookup cloudflare-dns.com 223.5.5.5

# 2. 从代理节点测试 DoH 连通性（需要当前走代理的终端）
curl --doh-url https://cloudflare-dns.com/dns-query https://www.google.com -o /dev/null -w "%{http_code}"

# 3. 更新 Host 区（bootstrap 用国内 DNS）
# cloudflare-dns.com = server:223.5.5.5

# 4. 改完立即 reload 并验证
surge-cli reload && surge-cli dump dns | head -5
```

### 原则

- 阿里 DoH 对防 DNS 污染足够——加密已阻止 ISP 窥探 DNS 内容
- 换海外 DoH 的隐私收益（隐藏 DNS 提供商国籍）不大，但可靠性风险不小
- **用户明确要求"真的了解了再改别硬改"**——涉及 DNS 的改动必须先验证、再动手
