---
name: stdd-danger-push
enabled: true
alwaysApply: true
---

危险操作：发布/推送类命令（git push、npm/pnpm/yarn publish、cargo publish、docker push 等）必须经 resolve 或人工确认，并被 gates.mjs danger 记录在案。