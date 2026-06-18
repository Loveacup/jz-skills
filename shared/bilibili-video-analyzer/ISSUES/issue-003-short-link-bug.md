# Issue #3: B站短链接解析失败

**Date:** 2026-02-05  
**Status:** Open  
**Priority:** Medium  

## 问题描述

当使用 B站短链接 `b23.tv/V6lujNi` 进行视频解析时，脚本错误地解析为另一个视频（BV1ut6YByEZq），而非目标视频（BV1dqffBMEcg）。

### 复现步骤

```bash
cd ~/clawd/skills/bilibili-video-analyzer
python3 scripts/fetch_all.py https://b23.tv/V6lujNi
```

### 预期结果

解析目标视频：BV1dqffBMEcg（OpenClaw 多 Agent 教程）

### 实际结果

错误解析为：BV1ut6YByEZq（网文小说吐槽视频）

## 根因分析

短链接重定向规则：
```
V6lujNi → BV1dqffBMEcg
```

但解析逻辑没有正确跟随重定向，导致获取到错误的 BV 号。

## 建议修复方案

1. **在脚本中增加 curl -sI 检测**
   ```bash
   # 获取短链接重定向后的真实 URL
   LOCATION=$(curl -sI "$input" | grep -i "location:" | awk '{print $2}' | tr -d '\r')
   BV_ID=$(echo "$LOCATION" | grep -oP 'BV[^?]+' | head -1)
   ```

2. **或使用 bilibili API 获取真实 BV 号**
   ```bash
   # B站官方 API
   curl -s "https://api.bilibili.com/x/share?id=b23.tv/V6lujNi"
   ```

3. **增加输入验证**
   - 检测输入是否为短链接格式
   - 验证解析出的 BV 号是否有效

## 临时解决方案

```bash
# 手动获取真实 BV 号
curl -sI https://b23.tv/V6lujNi | grep -i location
# 然后用真实 BV 号调用脚本
python3 scripts/fetch_all.py BV1dqffBMEcg
```

## 相关资源

- **测试链接：** `https://b23.tv/V6lujNi`
- **目标视频：** BV1dqffBMEcg
- **错误视频：** BV1ut6YByEZq

---

*Created by: 小黄*  
*Session: 2026-02-05-1826*
