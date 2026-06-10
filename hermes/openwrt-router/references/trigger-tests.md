# Trigger Tests

## Should trigger

1. "连接一下本地 OpenWrt 路由" — OpenWrt SSH/LuCI operation.
2. "看看 <internal IP redacted> 的 iStoreOS 状态" — iStoreOS is OpenWrt-derived.
3. "查一下路由器 DHCP 租约" — OpenWrt DHCP diagnostics.
4. "帮我看 LuCI 为什么打不开" — LuCI/OpenWrt web UI troubleshooting.
5. "给 OpenWrt 装 luci-app-xxx" — opkg package operation.
6. "改一下 OpenWrt 的无线 SSID" — UCI wireless config change.
7. "查 OpenWrt 防火墙规则" — firewall diagnostics.
8. "OpenWrt dropbear 公钥登录失败" — SSH/dropbear troubleshooting; also load `ssh-setup`.
9. "iStoreOS 插件安装失败" — package/LuCI diagnostics.
10. "备份 OpenWrt 配置再改网络" — backup + UCI change protocol.
11. "帮我给 OpenWrt 执行 opkg upgrade 全部包" — trigger, then refuse blanket upgrade and offer named-package/sysupgrade-safe alternative.
12. "帮我 sysupgrade iStoreOS" — trigger high-risk firmware checklist; require explicit authorization before flashing.
13. "OpenWrt LuCI 443 打不开" — trigger LuCI/uHTTPd/rpcd triage.

## Should not trigger

1. "UniFi 控制器登录不了" — use UniFi skills unless OpenWrt is involved.
2. "macOS SSH key 怎么生成" — use `ssh-setup` only.
3. "Docker 里装 OpenWrt 镜像" — container/devops task, not router ops.
4. "查某个 OpenWrt GitHub 项目源码" — use GitHub/web-research skills first.
5. "家里网络慢但路由器不是 OpenWrt" — generic network diagnostics or vendor-specific skill.
6. "写一篇 OpenWrt 介绍文章" — content writing/research, not operations.
7. "配置 UniFi AP SSID" — UniFi skill.
8. "购买什么路由器刷 OpenWrt" — shopping/research mode first.
9. "Surge 规则不生效 / 代理节点延迟高" — Surge proxy layer; use `surge-gateway`.
10. "Surge DNS fake-IP 异常" — Surge DNS/cache layer; use `surge-gateway` unless OpenWrt DNSMasq is explicitly involved.
11. "不知道什么品牌路由器，帮我改配置" — ambiguous; identify vendor non-invasively first, do not run OpenWrt commands until verified.
