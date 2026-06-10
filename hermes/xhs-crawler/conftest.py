def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: 联网金丝雀，默认跳过（设 XHS_LIVE_TEST=1 才跑）",
    )
