"""测试 requirements.py 元数据与实际引擎的一致性。"""
from wrr.requirements import ENGINE_REQUIREMENTS, get_all_env_keys, get_all_commands
from wrr.registry import get_registry


def test_all_registered_engines_have_requirements():
    """所有注册引擎必须在 ENGINE_REQUIREMENTS 中声明。"""
    registry = get_registry()
    registered_names = set(registry.names())
    declared_names = set(ENGINE_REQUIREMENTS.keys())

    # 检查遗漏
    missing = registered_names - declared_names
    assert not missing, f"以下引擎已注册但未在 ENGINE_REQUIREMENTS 声明: {missing}"

    # 检查多余
    extra = declared_names - registered_names
    assert not extra, f"以下引擎在 ENGINE_REQUIREMENTS 声明但未注册: {extra}"


def test_engine_tier_matches_implementation():
    """ENGINE_REQUIREMENTS 中的 tier 必须与引擎实现一致。"""
    registry = get_registry()
    for engine_name, requirements in ENGINE_REQUIREMENTS.items():
        engine = registry.get(engine_name)
        assert engine is not None, f"{engine_name} 未注册"

        declared_tier = requirements["tier"]
        actual_tier = engine.tier

        assert declared_tier == actual_tier, (
            f"{engine_name}: requirements.py 声明 tier={declared_tier}, "
            f"但实现为 tier={actual_tier}"
        )


def test_get_all_env_keys():
    """get_all_env_keys() 返回去重排序的环境变量列表。"""
    keys = get_all_env_keys()
    assert isinstance(keys, list)
    assert len(keys) > 0
    assert keys == sorted(set(keys))  # 去重且排序
    assert "EXA_API_KEY" in keys
    assert "GITHUB_TOKEN" in keys
    assert "SEARXNG_URL" in keys


def test_get_all_commands():
    """get_all_commands() 返回去重排序的命令列表。"""
    commands = get_all_commands()
    assert isinstance(commands, list)
    assert "opencli" in commands
    assert commands == sorted(set(commands))


def test_brave_env_any_structure():
    """Brave 应使用 env_any 声明双别名支持。"""
    brave_req = ENGINE_REQUIREMENTS.get("brave")
    assert brave_req is not None
    assert "env_any" in brave_req
    assert "BRAVE_API_KEY" in brave_req["env_any"]
    assert "BRAVE_SEARCH_API_KEY" in brave_req["env_any"]


def test_env_example_contains_required_keys():
    """验证 .env.example 包含所有必需环境变量（含注释行）。"""
    import os
    env_example_path = os.path.join(
        os.path.dirname(__file__), "..", "..", ".env.example"
    )

    # 读取 .env.example
    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取所有 KEY= 行（包括注释的，因为备用 key 可能注释掉）
    declared_keys = set()
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # 去掉开头的 # 号
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        if "=" in line:
            key = line.split("=")[0].strip()
            declared_keys.add(key)

    # 必需 keys（从 ENGINE_REQUIREMENTS 提取）
    required_keys = get_all_env_keys()

    # 验证每个必需 key 都在 .env.example 中（含注释）
    for key in required_keys:
        assert key in declared_keys, (
            f"环境变量 {key} 在 ENGINE_REQUIREMENTS 中声明，"
            f"但 .env.example 中未找到（含注释行）"
        )


def test_env_example_no_real_secrets():
    """验证 .env.example 不包含真实密钥（仅占位符）。"""
    import os
    env_example_path = os.path.join(
        os.path.dirname(__file__), "..", "..", ".env.example"
    )

    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 占位符模式
    safe_patterns = [
        "your_",
        "http://127.0.0.1",
        "http://localhost",
        "False",
        "True",
        "/path/to/",
    ]

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        value = value.strip()

        # 跳过空值或注释掉的行
        if not value or value.startswith("#"):
            continue

        # 值必须是占位符
        is_safe = any(pattern in value for pattern in safe_patterns)
        assert is_safe, (
            f".env.example 中 {key}={value} 疑似包含真实密钥，"
            f"应使用占位符（如 'your_{key.lower()}_here'）"
        )
