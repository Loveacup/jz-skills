# WRR v4.0 测试策略

## 测试层级

| 层级 | 命令 | 目标 |
|------|------|------|
| 单元测试 | `pytest tests/unit/` | 覆盖率 > 80% |
| 集成测试 | `pytest tests/integration/` | 需要 API key |
| E2E 测试 | `pytest tests/e2e/` | Hermes 插件加载 |

## 当前覆盖率

**93%** (目标 80%)

## 运行测试

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试（需要 EXA_API_KEY）
pytest tests/integration/ -v

# 覆盖率检查
pytest tests/unit/ --cov=wrr --cov-report=term-missing
```
