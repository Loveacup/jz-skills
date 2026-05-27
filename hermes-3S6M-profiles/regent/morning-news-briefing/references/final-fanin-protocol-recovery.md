# 早新闻 final-fanin protocol_violation 恢复模式

## 触发场景

早新闻三路检索任务（中国 / 美国国际 / 市场科技）均已 `done`，但最终汇编卡 `final-fanin` 出现：

- `protocol_violation: worker exited cleanly (rc=0) without calling kanban_complete or kanban_block`
- 或状态 `blocked/crashed`，workspace 无最终 artifact
- 下游 audit / delivery 卡因父任务未 done 卡在 `todo`

## 正确处置

1. **不要把三路检索摘要当最终简报交付。** 三路检索只是原料。
2. **检查三路父任务 workspace 是否已有 artifact**，通常路径形如：
   - `~/.hermes/kanban/workspaces/<cn_task>/morning-news-cn-YYYYMMDD.md`
   - `~/.hermes/kanban/workspaces/<us_task>/morning-news-us-intl-YYYYMMDD.md`
   - `~/.hermes/kanban/workspaces/<market_task>/morning-news-YYYYMMDD.md`
3. **创建精准返工 final-fanin 卡**，不要重搜全量新闻：
   - assignee 优先 `jiangzuojian`（实测对已知 artifact 的合并/格式修复稳定）
   - body 明确列出三份 artifact 绝对路径
   - 明令：不得新增搜索、不得编造来源；只读三份 artifact 去重合并
   - 明令：必须写出 `final-morning-news-YYYYMMDD.md` 并 `kanban_complete`；失败须 `kanban_block`，不可直接退出
4. **为返工卡重建下游链**：`repair-fanin → audit-repair → delivery-repair`。不要让新链依赖旧 blocked fanin。
5. **若 audit approve 且给出最终 artifact path，父皇要求“直接文字发给我”时，可由监国读取已批准 artifact 并原样粘贴交付**；这不是重新汇编/分析，只是交付。不得改写内容。

## 验收口径

- audit 通过但列出观察项时，若 reviewer 明确“不阻却交付”，可交付，同时在主频道不展开审计细节，避免拖沓。
- 若 audit 指出具体条目缺源/假 URL/年份错误，必须创建精准修复卡，只修被阻断条目，不全量重做。

## 反模式

- ❌ 重跑三路检索，浪费时间并引入新差异
- ❌ 等旧 blocked final-fanin 自愈
- ❌ 将旧 blocked fanin 作为新修复链父任务，导致新链永远不 promoted
- ❌ 在主频道只报“done/path”，不按父皇要求直接发送全文
