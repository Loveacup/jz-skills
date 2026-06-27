# CC 驱动的外部项目许可证核查模式

> 2026-06-01 · china-legal-optimized v2.0 吸收方案中验证

当 CC 需要判断对外部项目的吸收合规性时，不要凭印象推断许可证——用 `gh api` 逐仓库实测。

## 核查流程

### Step 1: 确认 gh 认证
```bash
gh auth status
```

### Step 2: 逐仓库拉取真实 LICENSE
```bash
# 单个仓库
gh api repos/{owner}/{repo}/license --jq '.license.spdx_id'

# 批量（5 个仓库并行）
for repo in anthropics/claude-for-legal CSlawyer1985/claude-for-legal-ZH; do
  echo "$repo: $(gh api repos/$repo/license --jq '.license.spdx_id' 2>/dev/null || echo 'NULL')"
done
```

### Step 3: 处理 null（无 LICENSE 文件）
`gh api` 返回 null 时，检查 README 是否有 per-file 许可声明：
```bash
gh api repos/{owner}/{repo}/readme --jq '.content' | base64 -d | grep -iE 'licen|cc-by|mit|apache'
```

### Step 4: 穿透数据集许可
如果吸收项引用了外部数据集（如 CUAD），需单独查数据集的原始许可：
```bash
gh api repos/{dataset-owner}/{dataset-repo}/license --jq '.license.spdx_id'
```

### Step 5: Apache-2.0 attribution 义务
检查仓库是否有 NOTICE 文件（决定 attribution 传递义务）：
```bash
gh api repos/{owner}/{repo}/contents/NOTICE --jq '.name' 2>/dev/null || echo "NO NOTICE"
```

## 许可证相容性速查

| 吸收源许可 | 目标 MIT | 目标 Apache-2.0 |
|-----------|---------|----------------|
| MIT | ✅ 保留版权声明 | ✅ |
| Apache-2.0 | ✅ 保留 LICENSE + 注明改动 | ✅ |
| CC BY 4.0 | ✅ 署名 | ✅ 署名 |
| CC-BY-NC | ❌ 不可商用 | ❌ |
| 无 LICENSE (null) | ❌ 默认保留所有权利 | ❌ |

## 陷阱

- `gh api repos/{repo}` 的 `license` 字段可能是 `null`（GitHub 未检测到 LICENSE 文件），不能假设它有值
- per-skill 许可（如 README 声明）可能不同于仓库级 LICENSE 文件
- 穿透许可：项目自身 MIT 不覆盖其引用的数据集/第三方内容
