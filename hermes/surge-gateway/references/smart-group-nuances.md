# Smart Group Nuances

Key takeaways from the [Surge KB Smart Group page](https://kb.nssurge.com/surge-knowledge-base/zh/guidelines/smart-group).

## How Smart Differs from url-test/fallback

| Aspect | url-test/fallback | Smart |
|--------|-------------------|-------|
| Decision timing | Periodic re-test | Real-time dynamic optimization |
| Data collected | Single `test-url` latency | Handshake delay, packet loss, connectivity, RTT (multi-dimensional) |
| Failure handling | Wait for next test cycle | Adaptive retry — switches immediately, upper layer unaware |
| Per-site awareness | No — one result for all sites | Yes — records per-domain latency/connectivity |

## `update-interval` on Smart Groups

- Smart groups do their own internal scheduling for periodic re-tests
- They only re-test a subset of proxies (not all), based on usage patterns
- `update-interval` is LESS impactful on Smart groups than on url-test/fallback
- Setting `update-interval=3600` is harmless but Smart groups already self-manage

## Key Limitations

- **Latency-focused, not bandwidth-aware**: Smart groups optimize for low latency. If a group contains a mix of high-bandwidth and low-bandwidth proxies, it may select the low-latency/low-bandwidth one, hurting downloads. Keep member proxies similar in quality.
- **No sub-group nesting**: Smart groups cannot have other groups as direct sub-strategies. Use `include-other-group` to copy members from another group.
- **No geo-lock awareness**: Smart groups react to connection errors, timeouts, and stalls — they cannot detect region-lock restrictions.
- **Snell `reuse` incompatibility**: When using Snell protocol in a Smart group, the `reuse` mechanism won't work.

## Design Philosophy

> "推荐在 Smart 策略组组中放入的线路品质应比较相近，可再加上少量次等备用线路。不建议往组中放入过多的几乎不可能被使用的策略。"

Translation: Put proxies of similar quality in a Smart group, plus a few fallbacks. Don't stuff it with proxies that will never realistically be used.

## For This User's Config

The user's 8 regional Smart groups (`🇭🇰 香港节点`, `🇯🇵 日本节点`, etc.) all use `include-other-group=✈️ 我的节点` to pull members from the remote node list. This is the correct pattern — the Smart groups contain the actual proxies (not nested groups), and the proxy list is maintained through the `✈️ 我的节点` policy-path.
