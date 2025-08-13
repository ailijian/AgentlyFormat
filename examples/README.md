# AgentlyFormat 示例代码

本目录包含了 AgentlyFormat 库的各种使用示例，帮助开发者快速了解和使用库的功能。

## 示例列表

### 1. 差分引擎演示 (`diff_engine_demo.py`)

展示了新的结构化差分引擎的核心功能，包括：

- **基础差分功能**: 演示如何计算两个数据结构之间的最小差分
- **事件合并 (Coalescing)**: 展示如何合并快速连续的事件以提高性能
- **幂等事件**: 演示事件去重和幂等性检查机制
- **流式解析器集成**: 展示差分引擎与流式 JSON 解析器的集成使用
- **智能 vs 保守模式**: 对比不同差分模式的效果

#### 运行示例

```bash
# 从项目根目录运行
python examples/diff_engine_demo.py
```

#### 示例输出

示例会展示以下内容：

1. **基础差分演示**: 显示数据变化过程中的差分计算和事件生成
2. **事件合并演示**: 展示快速连续更新时的事件合并效果
3. **幂等事件演示**: 验证重复数据不会产生重复事件
4. **流式解析集成**: 演示实际的 JSON 流式解析场景
5. **模式对比**: 比较保守模式和智能模式的差异

## 核心概念说明

### 差分引擎 (Diff Engine)

差分引擎是 AgentlyFormat 的核心组件，负责：

- **结构化差分**: 理解 JSON 对象和数组的结构，计算最小编辑距离
- **路径追踪**: 为每个数据路径维护状态，支持精确的变更追踪
- **事件生成**: 将差分结果转换为结构化的流式事件

### 事件合并 (Event Coalescing)

在高频数据更新场景中，事件合并可以：

- **减少事件数量**: 将连续的相同路径更新合并为单个事件
- **提高性能**: 减少事件处理开销
- **保持数据一致性**: 确保最终状态的正确性

### 幂等性 (Idempotency)

幂等性机制确保：

- **去重**: 相同的数据变更不会产生重复事件
- **哈希追踪**: 为每个路径维护内容哈希，精确检测变更
- **性能优化**: 避免不必要的事件处理

### 差分模式

- **智能模式 (SMART)**: 使用高级算法计算最优差分，适合复杂数据结构
- **保守模式 (CONSERVATIVE)**: 使用简单算法，适合大型数据或性能敏感场景

## 配置选项

### DiffMode

```python
from src.agently_format.core.diff_engine import DiffMode

# 智能模式 - 最优差分算法
engine = StructuredDiffEngine(diff_mode=DiffMode.SMART)

# 保守模式 - 简单高效算法
engine = StructuredDiffEngine(diff_mode=DiffMode.CONSERVATIVE)
```

### CoalescingConfig

```python
from src.agently_format.core.diff_engine import CoalescingConfig

config = CoalescingConfig(
    enabled=True,                    # 启用事件合并
    time_window_ms=100,             # 时间窗口（毫秒）
    max_coalesced_events=10,        # 最大合并事件数
    stability_threshold=3           # 稳定性阈值
)
```

### 便捷创建函数

```python
from src.agently_format.core.diff_engine import create_diff_engine

# 使用默认配置
engine = create_diff_engine()

# 自定义配置
engine = create_diff_engine(
    mode="smart",
    coalescing_enabled=True,
    time_window_ms=200
)
```

## 性能考虑

1. **大型数据集**: 对于大型列表或对象，建议使用保守模式
2. **高频更新**: 启用事件合并以减少事件处理开销
3. **内存使用**: 定期调用 `cleanup_old_paths()` 清理过期的路径状态
4. **统计监控**: 使用 `get_stats()` 监控引擎性能

## 故障排除

### 常见问题

1. **事件未生成**: 检查是否启用了事件合并，可能需要调用 `flush_all_coalescing_buffers()`
2. **重复事件**: 确保正确调用了 `update_hash()` 方法
3. **性能问题**: 考虑使用保守模式或调整合并配置

### 调试技巧

```python
# 获取详细统计信息
stats = engine.get_stats()
print(f"统计信息: {stats}")

# 检查路径状态
path_state = engine.get_path_state("some.path")
print(f"路径状态: {path_state}")

# 重置统计信息
engine.reset_stats()
```

## 扩展开发

如果需要扩展差分引擎功能：

1. **自定义差分算法**: 继承 `StructuredDiffEngine` 并重写相关方法
2. **自定义事件类型**: 扩展事件系统以支持新的事件类型
3. **性能优化**: 针对特定数据模式优化差分算法

## 相关文档

- [API 文档](../docs/api.md)
- [架构设计](../docs/architecture.md)
- [性能指南](../docs/performance.md)