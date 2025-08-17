#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试MemoryManager集成问题的测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from agently_format.core.performance_optimizer import PerformanceOptimizer
    print("✓ PerformanceOptimizer导入成功")
    
    # 创建优化器实例
    optimizer = PerformanceOptimizer(enable_memory_management=True)
    print("✓ PerformanceOptimizer实例创建成功")
    
    # 检查memory_manager属性
    print(f"memory_manager类型: {type(optimizer.memory_manager)}")
    print(f"memory_manager是否为None: {optimizer.memory_manager is None}")
    
    if optimizer.memory_manager:
        print(f"memory_manager有register_cache_object方法: {hasattr(optimizer.memory_manager, 'register_cache_object')}")
        
        # 尝试调用register_cache_object方法
        test_cache = {"key": "value"}
        try:
            optimizer.memory_manager.register_cache_object("test_cache", test_cache)
            print("✓ register_cache_object调用成功")
            
            # 获取内存使用情况
            memory_info = optimizer.memory_manager.get_memory_usage()
            print(f"内存信息: {memory_info}")
            print(f"缓存对象数量: {memory_info.get('cache_objects', 0)}")
            
        except Exception as e:
            print(f"✗ register_cache_object调用失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("✗ memory_manager为None")
        
except Exception as e:
    print(f"✗ 导入或创建失败: {e}")
    import traceback
    traceback.print_exc()