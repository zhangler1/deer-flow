# 性能监控工具使用指南

## 📋 概述

`performance_monitor.py` 是一个通用的性能监控工具，提供了**上下文管理器**方式来监控代码块的执行耗时。该工具特别适合用于监控分类模型、LLM推理、数据库查询等操作的性能。

## ✨ 主要特性

1. ✅ **上下文管理器** - 使用 `with` 语句灵活控制监控范围
2. ✅ **耗时监控** - 自动记录操作的执行时间
3. ✅ **阈值告警** - 超过设定阈值时自动发出警告
4. ✅ **嵌套监控** - 支持多层嵌套监控
5. ✅ **性能统计** - 收集并分析多次执行的统计信息
6. ✅ **装饰器支持** - 可作为函数装饰器使用
7. ✅ **彩色日志** - 集成增强日志系统，符合用户颜色偏好（绿色+紫色）
8. ✅ **异步支持** - 支持异步函数监控

## 🚀 快速开始

### 基本使用

```python
from src.utils.performance_monitor import PerformanceMonitor

# 监控代码块执行时间
with PerformanceMonitor("分类模型推理"):
    result = classify_request(query)
```

### 设置耗时阈值

```python
# 超过2秒会发出警告
with PerformanceMonitor("LLM推理", threshold=2.0):
    result = llm.invoke(prompt)
```

### 添加元数据

```python
with PerformanceMonitor(
    "分类器调用",
    metadata={"query_length": len(query), "model": "qwen-plus"}
):
    result = classify(query)
```

### 嵌套监控

```python
with PerformanceMonitor("完整流程"):
    with PerformanceMonitor("预处理"):
        preprocess_data()
    
    with PerformanceMonitor("模型推理"):
        model_inference()
    
    with PerformanceMonitor("后处理"):
        postprocess_result()
```

### 获取执行时间

```python
monitor = PerformanceMonitor("复杂计算")
with monitor:
    complex_calculation()

# 获取不同格式的耗时
print(f"耗时(秒): {monitor.duration:.3f}s")
print(f"耗时(毫秒): {monitor.get_duration_ms():.1f}ms")
print(f"格式化: {monitor.get_duration_formatted()}")
```

## 🎯 在分类器中的实际应用

### 示例：监控 classifier.py 中的分类过程

```python
# 在 src/graph/classifier.py 中使用

from src.utils.performance_monitor import PerformanceMonitor

def classify_request(query: str, department: str = "general") -> RouteDecision:
    """使用LLM对用户请求进行智能分类"""
    
    # 监控整个分类流程
    with PerformanceMonitor("分类器整体流程") as overall_monitor:
        
        # 监控模板渲染
        with PerformanceMonitor("模板渲染", level=logging.DEBUG):
            template = env.get_template("classifier/classifier.md")
            classification_prompt = template.render(query=query)
        
        # 监控LLM推理（关键部分，设置阈值）
        with PerformanceMonitor(
            "LLM推理", 
            threshold=2.0,
            metadata={"query_length": len(query), "model": "qwen-plus"}
        ) as llm_monitor:
            llm = get_llm_by_type("basic")
            response = llm.invoke([{"role": "user", "content": classification_prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
        
        # 监控结果解析
        with PerformanceMonitor("结果解析", level=logging.DEBUG):
            result = _parse_llm_response_to_route_decision(content, query, department)
        
        # 记录关键性能信息
        enhanced_logger.logger.info(
            f"✅ 分类完成 | 总耗时: {overall_monitor.get_duration_formatted()} | "
            f"LLM耗时: {llm_monitor.get_duration_formatted()}"
        )
        
        return result
```

## 📊 性能统计功能

用于收集多次执行的性能统计信息：

```python
from src.utils.performance_monitor import PerformanceStats

# 创建统计收集器
stats = PerformanceStats("分类器性能测试")

# 执行多次测试
for query in test_queries:
    with stats.monitor():
        classify_request(query)

# 打印统计摘要
stats.print_summary()

# 输出示例：
# 📊 PERF_STATS | 分类器性能测试 | 
# 执行次数: 10 | 成功: 10 | 失败: 0 | 
# 平均: 0.523s | 最小: 0.401s | 最大: 0.678s | 
# P50: 0.512s | P95: 0.650s | P99: 0.678s | 
# 总计: 5.230s

# 获取详细统计
print(f"平均耗时: {stats.get_average():.3f}s")
print(f"P95耗时: {stats.get_percentile(95):.3f}s")
```

## 🎨 装饰器用法

```python
from src.utils.performance_monitor import performance_monitor

# 简单装饰器
@performance_monitor(threshold=2.0)
def classify_request(query: str):
    # ... 分类逻辑
    return result

# 包含参数信息的装饰器
@performance_monitor("分类器推理", include_args=True)
def classify(query: str, department: str):
    # ... 分类逻辑
    return result

# 支持异步函数
@performance_monitor("异步分类")
async def async_classify(query: str):
    # ... 异步分类逻辑
    return result
```

## 🔧 API 参考

### PerformanceMonitor 类

```python
PerformanceMonitor(
    operation_name: str,           # 操作名称
    logger_name: str = "performance",  # 日志记录器名称
    level: int = logging.INFO,     # 日志级别
    threshold: Optional[float] = None,  # 耗时阈值（秒）
    auto_log: bool = True,         # 是否自动记录日志
    metadata: Optional[Dict] = None  # 额外元数据
)
```

**方法：**
- `get_duration_ms()` - 获取耗时（毫秒）
- `get_duration_formatted()` - 获取格式化的耗时字符串

### PerformanceStats 类

```python
PerformanceStats(
    name: str,                     # 统计名称
    logger_name: str = "performance.stats"
)
```

**方法：**
- `monitor()` - 监控单次执行（返回上下文管理器）
- `get_count()` - 获取执行次数
- `get_average()` - 获取平均耗时
- `get_min()` / `get_max()` - 获取最小/最大耗时
- `get_percentile(percentile)` - 获取指定百分位的耗时
- `print_summary()` - 打印统计摘要
- `reset()` - 重置统计数据

## 📝 日志输出示例

```
18:30:45 - performance - INFO | ⏱️  PERF_START | 分类模型推理 | 开始监控
18:30:45 - performance - INFO | ⏱️  PERF_END | 分类模型推理 | ✅ 完成 | 耗时: 0.523s

18:31:10 - performance - WARNING | ⏱️  PERF_END | 数据库查询 | ✅ 完成 | 耗时: 1.234s ⚠️ 超过阈值 1.0s

18:31:30 - performance - ERROR | ⏱️  PERF_END | API调用 | ❌ 失败: ValueError | 耗时: 0.156s

18:32:00 - performance.stats - INFO | 📊 PERF_STATS | 分类器性能测试 | 执行次数: 10 | 成功: 10 | 失败: 0 | 平均: 0.523s | 最小: 0.401s | 最大: 0.678s | P50: 0.512s | P95: 0.650s | P99: 0.678s | 总计: 5.230s
```

## 🎯 使用建议

### 1. 何时使用性能监控

- ✅ **LLM推理** - 监控模型推理耗时（建议设置阈值）
- ✅ **数据库操作** - 监控查询和写入性能
- ✅ **外部API调用** - 监控第三方服务响应时间
- ✅ **复杂计算** - 监控耗时较长的算法
- ✅ **工作流节点** - 监控各个节点的执行时间

### 2. 日志级别建议

- `logging.INFO` - 关键操作（如分类器整体流程、LLM推理）
- `logging.DEBUG` - 详细步骤（如预处理、后处理）
- `logging.WARNING` - 自动触发（超过阈值时）
- `logging.ERROR` - 自动触发（发生错误时）

### 3. 阈值设置建议

- **LLM推理**: 2.0 - 3.0 秒
- **数据库查询**: 0.5 - 1.0 秒
- **API调用**: 1.0 - 2.0 秒
- **缓存操作**: 0.1 - 0.2 秒

### 4. 最佳实践

```python
# ✅ 好的做法：监控关键路径
with PerformanceMonitor("分类器", threshold=2.0):
    result = classify(query)

# ✅ 好的做法：嵌套监控定位瓶颈
with PerformanceMonitor("完整流程"):
    with PerformanceMonitor("LLM推理", threshold=2.0):
        llm_result = llm.invoke(prompt)
    with PerformanceMonitor("后处理"):
        final_result = postprocess(llm_result)

# ⚠️ 避免：过度监控影响性能
# 不要在频繁调用的小函数中使用
def small_helper_function():  # 每秒调用1000次
    with PerformanceMonitor("小函数"):  # ❌ 不推荐
        return x + y

# ✅ 推荐：使用统计收集器批量分析
stats = PerformanceStats("小函数批量测试")
for i in range(1000):
    with stats.monitor(auto_log=False):  # 不自动记录每次
        small_helper_function()
stats.print_summary()  # 只打印汇总
```

## 🔗 相关文件

- **核心实现**: [`src/utils/performance_monitor.py`](../src/utils/performance_monitor.py)
- **日志系统**: [`src/utils/enhanced_logger.py`](../src/utils/enhanced_logger.py)
- **使用示例**: [`examples/performance_monitor_usage.py`](../examples/performance_monitor_usage.py)
- **测试脚本**: [`test_performance_monitor.py`](../test_performance_monitor.py)

## 📚 更多示例

查看 [`examples/performance_monitor_usage.py`](../examples/performance_monitor_usage.py) 获取更多详细示例。

---

**创建时间**: 2025-11-10  
**版本**: 1.0.0
