# cc-send.sh --context 必须是文件路径

## 症状

```bash
cc-send.sh --session <s> --context "inline text here"
# ⚠️ No context file or message provided.
```

## 根因

`cc-send.sh` 的 `--context` 参数**只接受文件路径**（`.md` / `.txt`），不接受内联文本。脚本内部用 `cat` 读取文件内容。

## 正确用法

```bash
# 1. 先写临时文件
write_file /tmp/task.md "任务内容..."

# 2. 发文件路径
cc-send.sh --session <s> --context /tmp/task.md
```

不等价于 `--message`（不存在的 flag）——每次发送任务都必须先写文件，再传路径。
