# 实用模型选型指南 · 测试方法论

> 当用户说"不需要专业的测试方式，只需要知道什么模型该用在哪些功能上"时的产出模式。
> 2026-06-02 基于 SURGExZR H200 全栈测试经验总结。

## 核心原则

1. **去掉极限测试** — 用户不需要吞吐/并发/长上下文 benchmark。只需知道"能做什么，不能做什么"。
2. **实测 + 公开评测** — 每个结论必须有本机 curl 实测 + 网上 benchmark 交叉验证。
3. **写清楚四件事**：该不该用 → 怎么调 → 有什么坑 → 和谁配合。
4. **问题要分级**：🔴 阻断（不能用）· 🟡 需适配（能用但要改代码）· 🔵 体验（能用但别扭）。

## 关键 Pitfall: 专用模型需要正确的 Prompt

**2026-06-02 案例**：Hunyuan-MT-Chimera-7B 被误判为"不是翻译器"。

- **❌ 错误的测试**：`curl ... -d '{"model":"Hunyuan-MT-Chimera-7B","messages":[{"role":"user","content":"Hello, I'd like a coffee"}]}'` → 模型当 chatbot 聊天
- **✅ 正确的测试**：`"Translate the following English to Chinese. Only output the translation.\n\nHello, I'd like a coffee."` → "你好，我想点一杯咖啡。"
- **教训**：专用模型（翻译、牙科影像、代码审查等）需要领域特定的 prompt 格式。不要因为第一次裸测失败就下结论——先尝试正确的 prompt 再判断。

## 文档结构模板

```
## ⚡ 30 秒速查（一张表：做什么 → 用什么 → 不要用什么 → 坑）
## 🤖 逐个模型：实测矩阵 + 公开评测 + curl 示例 + ✅适合/❌不适合
## 🔧 辅助服务：status + curl + 集成方案
## 📋 问题记录（🔴 阻断 · 🟡 需适配 · 🔵 体验）
## 🎯 场景化推荐配置（Chat / 翻译 / 语音 / 图文检索 / 牙科诊断）
```

## 实用集成模式

- **语音流水线**：pyannote(分离) → ASR(转文字) → Qwen3.5/gemma(理解) → CosyVoice(转语音)
- **图文检索**：CLIP embed/text → 768d 归一化向量 → CLIP embed/image → cosine 相似度 top-K
- **翻译**：Hunyuan-MT 做主力（WMT 30/31 第一），gemma-4 做备选，Qwen3.5 不要用于翻译（偶尔空返回）
- **牙科**：CLIP 预检 → DentVLM 诊断（不要用通用模型替代——差 19.6%）
