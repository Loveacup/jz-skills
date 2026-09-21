---
name: stdd-danger-push
enabled: true
alwaysApply: true
---

危险操作：commit/push、npm/pnpm/yarn/cargo publish、docker push、deploy、对外发送、安装/升级、运行时配置/repoint、登录/认证/凭据/权限变更等必须取得该具体动作的明确授权，并用 `gates.mjs scanDanger` 或已启用的 hook 留证。Full-auto、yolo 或普通任务授权不隐含这些权限。