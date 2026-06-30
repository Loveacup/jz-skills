# cc-start.sh 不支持 --agent-team flag

## 症状

```bash
cc-start.sh --agent-team ...
# Unknown arg: --agent-team
```

## 根因

`cc-start.sh` 没有 `--agent-team` flag。agent team 模式通过 `--task` 中的自然语言指令触发——CC 自己决定是否 spawn 子 agent。

## 正确用法

```bash
cc-start.sh --target <name> --topic <name> --effort high \
  --task "agent team 模式并行研究三个领域..."
```

`--effort high|xhigh|max` + 在 `--task` 中明确写 "agent team 模式" 即可。
