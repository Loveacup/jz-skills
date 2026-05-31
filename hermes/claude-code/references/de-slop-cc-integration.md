# de-slop — CC Skill Integration

> 来源：[Loveacup/jz-skills](https://github.com/Loveacup/jz-skills/tree/main/shared/de-slop)
> 用途：L4 活人感闸门 — 检测并改写 AI 生成文本中的机器味
> 适用：Claude Code agent team（CC 原生 `Skill()` 调用）

## 安装

```bash
cd /tmp
git clone --depth 1 --filter=blob:none --sparse https://github.com/Loveacup/jz-skills.git jz-skills-tmp
cd jz-skills-tmp && git sparse-checkout set shared/de-slop
cp -r shared/de-slop ~/.claude/skills/de-slop
rm -rf /tmp/jz-skills-tmp
ls ~/.claude/skills/de-slop/SKILL.md  # 验证
```

## CC 调用签名

```
Skill(skill="de-slop", args="检测并改写以下文本的AI味：{text}")
```

或在 L4 质量门 context 中：

```
Skill(skill="de-slop", args="全文AI味检测，输出密度报告+改写建议")
```

## 在 SIL 质量门中的角色

L4 活人感闸门（output-finalizer 第三段）：
- **软违规**（AI 味词汇密度 > 0.3/千字 / 破折号密度 > 1/800 字）：自动调用 de-slop 改写
- **硬违规**（否定排比 > 1 / 三段式 "不是X而是Y更是Z" > 2）：回 longform-writer 重写
- 调用 de-slop 后 output-finalizer 再次检查密度 → 仍不合格则扣分放行（不死锁）

## 相关技能

- Hermes 端：`creative/de-slop` skill（同名但不同运行环境）
- 本 skill 在 Hermes 中用于 Telegram 消息改写
- CC 端：上述安装路径 `~/.claude/skills/de-slop/` 供 CC agent team 使用
