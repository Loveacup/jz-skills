# 部署后验证模式 — Post-Deploy Verification Pattern

> 引用来源：common-pitfalls #9（Agent Team Schema 持久化）、#16（CC Agent Team Schema Unknown）
> 建立时间：2026-06-01

## 适用场景

Worker 产出包含新字段时，storage 层可能静默丢弃（只存预定义列）。每次 agent team 写入新结构化数据后，必须走本验证流程。

---

## 核心验证模式：Python subprocess curl

用 Python 发 POST 写入 → sleep 让存储层异步完成 → GET 读回 → 检查 artifact 含预期字段。

```python
import subprocess
import json
import time

BASE_URL = "http://localhost:8080"  # 替换为实际地址

def verify_artifact_field(task_id: str, expected_field: str, token: str) -> bool:
    """
    POST artifact → sleep → GET → 检查预期字段存在且非空。
    返回 True 表示验证通过。
    """
    # Step 1: 写入 artifact（含新字段）
    payload = {
        "task_id": task_id,
        "artifact": {
            expected_field: "placeholder_value",
            # 其他字段...
        }
    }
    post_result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         f"{BASE_URL}/tasks/{task_id}/artifact",
         "-H", "Content-Type: application/json",
         "-H", "Authorization: " + "Bearer " + token,  # 见下方脱敏陷阱
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    print("POST response:", post_result.stdout)

    # Step 2: 等待存储层异步完成
    time.sleep(2)

    # Step 3: GET 读回
    get_result = subprocess.run(
        ["curl", "-s",
         f"{BASE_URL}/tasks/{task_id}/artifact",
         "-H", "Authorization: " + "Bearer " + token],
        capture_output=True, text=True
    )

    # Step 4: 检查预期字段
    try:
        data = json.loads(get_result.stdout)
        artifact = data.get("artifact", {})
        if expected_field in artifact and artifact[expected_field]:
            print(f"✅ 验证通过：artifact['{expected_field}'] = {artifact[expected_field]}")
            return True
        else:
            print(f"❌ 验证失败：artifact 中无 '{expected_field}'，完整 artifact = {artifact}")
            return False
    except json.JSONDecodeError:
        print(f"❌ GET 响应无法解析：{get_result.stdout}")
        return False
```

---

## 陷阱 1：Token 脱敏破坏字符串

**问题：** Hermes 脱敏替换 `***` 时，可能同时删除 token 前后相邻的字符，导致 Authorization header 格式错误（如 `Bearer***token` 变成 `***`）。

**错误写法（f-string）：**
```python
# 危险：脱敏器可能把 f-string 整体替换，破坏结构
headers = {"Authorization": f"Bearer {token}"}
```

**正确写法（字符串拼接）：**
```python
# 安全：前缀 'Bearer ' 是字面量，不被脱敏；token 部分单独替换
auth_header = "Bearer " + token
headers = {"Authorization": auth_header}

# subprocess curl 场景同理
["-H", "Authorization: " + "Bearer " + token]
```

**Shell 场景：** 避免直接在命令行引用 token 变量，改用 `--header @file`（token 存文件）或通过环境变量 + 管道传入。

---

## 陷阱 2：新字段写入位置

**错误：** 把新字段写到 task 对象顶层（会被 schema 校验拒绝或静默忽略）：
```json
// 错误：新字段在 task 顶层
{"task_id": "...", "status": "done", "my_new_field": "value"}
```

**正确：** 新字段写入 `artifact` dict（整体序列化为 JSON blob 存储，schema 无限制）：
```json
// 正确：新字段在 artifact 内
{"task_id": "...", "status": "done", "artifact": {"my_new_field": "value", "other": "..."}}
```

**代码：**
```python
# 读取现有 artifact，合并新字段，整体写回
existing = get_artifact(task_id)  # dict
existing["my_new_field"] = computed_value
put_artifact(task_id, existing)   # 整体 PUT/PATCH
```

---

## 验证清单

部署后按顺序执行：

- [ ] POST 返回 2xx（非 4xx schema 拒绝）
- [ ] sleep 2s 后 GET 返回的 `artifact` 包含预期字段
- [ ] 预期字段值非空、类型正确
- [ ] token Authorization header 格式为 `Bearer <token>`（首字母大写，空格分隔）
- [ ] 旧有字段未被覆盖（`artifact` 是合并写入，不是全量替换）

---

## 相关条目

- Pitfall #9 — Agent Team Schema 持久化（写入验证）
- Pitfall #12 — Token 脱敏破坏语法（脱敏 `***` 问题）
- Pitfall #16 — CC Agent Team Schema Unknown（见 #9）
