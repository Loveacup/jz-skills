# iii 安装 · macOS 实录（2026-06-24）

> cc-tmux 轨2（iii Hub）预研的安装验证记录。M4 Mac mini · Apple Silicon。

## 安装方式

### 推荐：直接下载 binary（绕过 API rate limit）

```bash
# install 脚本需要 GitHub API token，无 token 时 60/hr 限额不够
# 直接下载 release binary 更可靠
V=0.19.7
curl -fsSL "https://github.com/iii-hq/iii/releases/download/iii/v${V}/iii-aarch64-apple-darwin.tar.gz" -o /tmp/iii.tar.gz
tar xzf /tmp/iii.tar.gz -C /tmp/iii-extract
cp /tmp/iii-extract/iii ~/.local/bin/iii
chmod +x ~/.local/bin/iii
```

### 备选：install 脚本（需要 GITHUB_TOKEN）

```bash
# 先导出 token，否则 API rate limit
export GITHUB_TOKEN=$(gh auth token)
curl -fsSL https://install.iii.dev/iii/main/install.sh | sh
```

## macOS 兼容性

- Apple Silicon arm64 是一等公民，release 有原生 binary
- worker microVM 在 macOS 走 **HVF**（Hypervisor.framework），不需要 /dev/kvm（Linux-only）
- 首次 worker 启动需拉 Docker 镜像（~196MB），后续缓存复用（1s 启动）
- M4 Mac mini 无任何拦路虎

## 踩坑

1. `iii project init` 可能报 "iii is not installed"——手动创建 config.yaml 即可，不走模板脚手架
2. 自定义 worker 的 `npm install` 若在首次创建时失败（缺 dev script 等），删除 `~/.iii/managed/<worker>/` 强制重建
3. `iii trigger` 不带 namespace 前缀，直接用 function 名

## 验证

```bash
~/.local/bin/iii --version          # 期望 0.19.7+
cd /tmp/quickstart
~/.local/bin/iii --config config.yaml &
~/.local/bin/iii worker add ./workers/caller-worker
~/.local/bin/iii trigger 'math::add_two_numbers' 'a=3' 'b=7'
# → {"c": 10, "success": "..."}
```
