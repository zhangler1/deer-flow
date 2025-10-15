# 日志级别配置说明

## 概述

本项目支持通过环境变量统一配置日志级别，控制终端输出的详细程度。

## 环境变量配置

### LOG_LEVEL

设置全局日志级别，控制哪些日志信息会被输出到终端。

**支持的值:**
- `DEBUG` - 最详细的日志信息，包括所有调试信息
- `INFO` - 一般信息（默认级别）
- `WARNING` - 警告信息
- `ERROR` - 错误信息
- `CRITICAL` - 严重错误信息

**默认值:** `INFO`

### 设置方法

#### 方法1: 在 .env 文件中设置

```bash
# .env
LOG_LEVEL=DEBUG
```

#### 方法2: 在命令行中设置

```bash
# Linux/Mac
export LOG_LEVEL=DEBUG
python main.py

# Windows
set LOG_LEVEL=DEBUG
python main.py

# 或者一行命令
LOG_LEVEL=DEBUG python main.py
```

#### 方法3: 在 Docker 中设置

```yaml
# docker-compose.yml
services:
  deer-flow:
    environment:
      - LOG_LEVEL=DEBUG
```

## 日志级别说明

### DEBUG 级别
输出所有日志信息，包括：
- 检索结果摘要（查询关键词、结果数量）
- **检索结果详情**（每条结果的标题和内容前40字）
- 节点执行信息
- 工具调用详情
- LLM思考过程

**适用场景:**
- 开发调试
- 问题诊断
- 详细了解系统运行过程

**示例输出:**
```
[本地检索摘要] 关键词: 'F1赛车制造' | 返回结果数: 3 条
[结果详情] 共3条结果:
  1. 标题: F1赛车制造流程
     内容: F1赛车作为超级赛车已经不仅仅是作为车了，而是一件工程学的艺术品...
  2. 标题: 赛车材料选择
     内容: 碳纤维和铝合金是F1赛车的主要材料，具有轻量化和高强度的特点...
```

### INFO 级别（默认）
输出关键信息，包括：
- 检索结果摘要（查询关键词、结果数量）
- 节点执行信息
- 工具调用开始/结束
- LLM调用信息

**不包括:**
- 检索结果详情

**适用场景:**
- 生产环境
- 一般使用
- 需要了解系统运行状态但不需要太多细节

**示例输出:**
```
[本地检索摘要] 关键词: 'F1赛车制造' | 返回结果数: 3 条
[网络检索摘要] 查询: 'F1赛车制造' | 返回结果数: 5 条
```

### WARNING 级别
仅输出警告和错误信息。

**适用场景:**
- 关注异常情况
- 最小化日志输出

### ERROR 级别
仅输出错误和严重错误信息。

**适用场景:**
- 仅关注错误
- 生产环境错误监控

## 代码实现说明

### 核心函数

项目在 `src/utils/enhanced_logger.py` 中提供了统一的日志级别判断函数：

```python
from src.utils.enhanced_logger import console_print, should_log
import logging

# 方法1: 使用 console_print（推荐）
console_print("这是一条INFO级别的日志", level=logging.INFO)
console_print("这是一条DEBUG级别的日志", level=logging.DEBUG)

# 方法2: 手动判断
if should_log(logging.DEBUG):
    print("这是一条DEBUG级别的日志")
```

### 在工具中使用

检索工具已经集成了日志级别判断：

```python
# src/tools/retriever.py
from src.utils.enhanced_logger import console_print

# INFO级别 - 始终显示摘要
console_print(
    f"[本地检索摘要] 关键词: '{keywords}' | 返回结果数: {len(documents)} 条",
    level=logging.INFO
)

# DEBUG级别 - 仅在DEBUG模式下显示详情
console_print(
    f"[结果详情] 共{len(documents)}条结果:",
    level=logging.DEBUG
)
```

## 最佳实践

1. **开发环境**: 使用 `DEBUG` 级别，便于调试和问题定位
2. **测试环境**: 使用 `INFO` 级别，了解系统运行状态
3. **生产环境**: 使用 `INFO` 或 `WARNING` 级别，减少日志输出
4. **问题排查**: 临时设置为 `DEBUG` 级别，排查完成后恢复

## 颜色输出

日志输出遵循用户偏好的颜色方案：
- 🟢 **绿色**: 标题、主要信息（前面部分）
- 🟣 **紫色**: 内容、详情（后面部分）

该配色方案在所有日志级别下保持一致。

## 注意事项

1. 修改 `LOG_LEVEL` 环境变量后需要重启应用才能生效
2. `DEBUG` 级别会输出大量信息，可能影响性能，不建议在生产环境使用
3. 日志级别只影响终端的 `print` 输出，不影响日志文件（如果配置了）
4. 所有检索相关的详细输出（标题+内容前40字）都属于 `DEBUG` 级别

## 相关文件

- `src/utils/enhanced_logger.py` - 日志工具核心实现
- `src/tools/retriever.py` - 本地检索工具（已集成日志级别）
- `src/tools/custom_search.py` - 网络检索工具（已集成日志级别）
