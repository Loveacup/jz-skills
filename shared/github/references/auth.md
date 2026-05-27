# GitHub Authentication — Detailed Setup

> **Prerequisite:** Run the auth detection block from the main SKILL.md first. This reference covers full setup when `AUTH` resolves to `none`.

## Detection Flow (when user asks to work with GitHub)

```bash
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"
git config --global credential.helper 2>/dev/null || echo "no git credential helper"
```

**Decision:**
1. `gh auth status` shows authenticated → use `gh` for everything
2. `gh` installed but not auth'd → use "gh auth" method below
3. `gh` not installed → use "git-only" method below

---

## Method 1: Git-Only (No gh, No sudo)

### Option A: HTTPS with PAT (Recommended)

**Step 1: Create a token.** Tell user to go to https://github.com/settings/tokens
- "Generate new token (classic)" → name: "hermes-agent"
- Scopes: `repo`, `workflow`, `read:org`
- Expiration: 90 days
- Copy the token — won't be shown again

**Step 2: Configure credential storage:**
```bash
git config --global credential.helper store
# Trigger auth once — git prompts for username + token (paste as password)
git ls-remote https://github.com/<username>/<any-repo>.git
```

Alternative — cache in memory (8 hours):
```bash
git config --global credential.helper 'cache --timeout=28800'
```

Alternative — embed token in remote URL (per-repo):
```bash
git remote set-url origin https://<username>:<token>@github.com/<owner>/<repo>.git
```

**Step 3: Configure identity:**
```bash
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```

**Step 4: Verify:**
```bash
git ls-remote https://github.com/<username>/<any-repo>.git
git config --global user.name && git config --global user.email
```

### Option B: SSH Key

```bash
# Check existing keys
ls -la ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found"

# Generate new key
ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub  # Add to https://github.com/settings/keys

# Test
ssh -T git@github.com

# Auto-rewrite HTTPS → SSH
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

---

## Method 2: gh CLI Authentication

```bash
# Interactive browser login (desktop)
gh auth login  # Select: GitHub.com → HTTPS → browser

# Token-based (headless/SSH)
echo "<TOKEN>" | gh auth login --with-token
gh auth setup-git
gh auth status  # verify
```

---

## API Access Without gh

```bash
export GITHUB_TOKEN="<token>"
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

Extract token from git credentials:
```bash
grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `git push` asks for password | GitHub disabled password auth. Use PAT as password, or switch to SSH |
| `remote: Permission denied` | Token lacks `repo` scope — regenerate |
| `fatal: Authentication failed` | Stale cached credentials → `git credential reject` then re-auth |
| SSH port 22 blocked | Add to `~/.ssh/config`: `Host github.com` with `Port 443` + `Hostname ssh.github.com` |
| Credentials not persisting | Check `git config --global credential.helper` — must be `store` or `cache` |
| Multiple accounts | Use SSH with different keys per host alias in `~/.ssh/config` |
| `gh: command not found` + no sudo | Use git-only Method 1 — no installation needed |
