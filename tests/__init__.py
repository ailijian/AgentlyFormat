"""测试模块

包含所有测试用例和测试工具。
"""

# 测试配置
TEST_CONFIG = {
    "timeout": 30,
    "max_retries": 3,
    "test_data_dir": "test_data",
    "mock_api_port": 8888
}

# 测试标记
TEST_MARKS = {
    "unit": "单元测试",
    "integration": "集成测试",
    "api": "API测试",
    "performance": "性能测试",
    "slow": "慢速测试"
}