# Git push 超时/认证阻塞：GitHub 密码弃用 + gh token 临时绕过（2026-07-08）

## 症状

在 bilibili-video-analyzer v2.3 采样量扩量收尾时，`git push` 反复超时：

```
[Command timed out after 120s/180s]
```

或卡在：

```
fatal: could not read Password for 'https://github.com': Device not configured
```

## 根因

GitHub 已弃用密码认证。macOS keychain 中可能仍保存旧密码，导致 git 使用 keychain 中的凭证与 GitHub 交互，被 401 后反复重试或卡住。

环境上下文：
- `git remote -v` 显示 `origin  git@github.com:Loveacup/jz-skills.git (push)`
- 本地代理 `HTTP_PROXY=127.0.0.1:6152`（Surge/Clash）可能转发 HTTPS 流量
- `curl -sI https://github.com/` 可以通，说明网络本身可达

## 修复步骤

1. 确认 `gh` 已登录且 token 有效：
   ```bash
   gh auth status
   ```

2. 临时将 remote URL 改为 token 认证的 HTTPS：
   ```bash
   cd /Users/alexcai/code/jz-skills
   git remote set-url origin https://$(gh auth token)@github.com/Loveacup/jz-skills.git
   ```

3. 执行 push：
   ```bash
   git push
   ```

4. 成功后立即恢复 SSH URL，避免 token 长期留在 git config：
   ```bash
   git remote set-url origin git@github.com:Loveacup/jz-skills.git
   git remote -v
   ```

## 注意事项

- 不要长期将 token 留在 remote URL 中；push 成功后立即恢复 SSH。
- 如果 `gh` 未登录，需要先 `gh auth login`。
- 如果 SSH 本身有问题（如 `ssh-add -l` 无 keys），则优先修复 SSH agent 或使用 HTTPS token 作为临时方案。
- 仅适用于个人仓库；团队仓库应使用 `gh` 的 credential helper 或配置 `git credential.helper` 为 `gh`。

## 替代方案

也可以配置 git 使用 `gh` 作为 credential helper：

```bash
gh auth setup-git
```

但在某些情况下（keychain 中旧密码仍干扰），可能仍需临时 token URL。

## 相关命令

```bash
gh auth status
gh auth token
git remote -v
git remote set-url origin https://$(gh auth token)@github.com/Loveacup/jz-skills.git
git remote set-url origin git@github.com:Loveacup/jz-skills.git
```
