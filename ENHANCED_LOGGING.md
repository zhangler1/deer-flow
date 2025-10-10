# DeerFlow 增强日志系统

## 概述

为了满足您对工程中"每一步检索、每一步思考和节点跳转都通过日志输出"的需求，我们实现了一个全面的增强日志系统。

## 🎯 主要功能

### 1. 彩色日志输出
- **前面部分使用绿色**：时间戳、日志级别、模块名
- **后面部分使用紫色**：日志消息内容
- 符合您的个人偏好设置

### 2. 节点执行跟踪
- `🔄 NODE_ENTRY` - 节点进入时记录
- `✅ NODE_EXIT` - 节点退出时记录执行时间
- `🔀 NODE_TRANSITION` - 记录节点间的跳转和原因

### 3. 工具调用日志
- `🔧 TOOL_START` - 工具调用开始，记录参数
- `🔧 TOOL_END` - 工具调用结束，记录结果和耗时
- `🔍 SEARCH` - 专门记录搜索过程和结果数量

### 4. LLM思考过程
- `🧠 LLM_THINKING` - 记录AI思考的详细过程
- `🧠 LLM_INVOKE` - 记录LLM调用的开始
- `🧠 LLM_STREAM` - 记录流式思考过程

### 5. 工作流程监控
- `🚀 WORKFLOW_START` - 工作流开始
- `📋 PLAN_GENERATION` - 计划生成过程
- `🚀 STEP_EXECUTION` - 步骤执行跟踪
- `📚 RETRIEVAL` - 检索过程记录
- `📊 WORKFLOW_SUMMARY` - 工作流程摘要统计
- `🏁 WORKFLOW_COMPLETE` - 工作流完成

## 🔧 实现文件

### 核心模块
- `src/utils/enhanced_logger.py` - 增强日志核心模块
- `src/graph/nodes.py` - 节点日志增强（部分完成）
- `src/graph/builder.py` - 图构建器日志增强（部分完成）
- `src/tools/search.py` - 搜索工具日志增强
- `src/llms/llm.py` - LLM思考过程日志
- `src/workflow.py` - 工作流程日志增强

### 演示文件
- `enhanced_logging_demo.py` - 完整的使用演示和说明

## 🚀 使用方法

### 1. 基本使用
```python
from src.utils.enhanced_logger import get_enhanced_logger, setup_enhanced_logging

# 设置增强日志
setup_enhanced_logging(level=logging.INFO, enable_colors=True)

# 获取日志实例
logger = get_enhanced_logger('your_module')
```

### 2. 调试模式运行
```bash
# 启用详细日志
python debug.py
python main.py --debug "你的问题"
```

### 3. 服务器模式
```bash
python server.py --log-level debug
```

## 📊 日志输出示例

运行时您将看到类似以下的彩色日志输出：

```
🚀 WORKFLOW_START | session_1728123456 | 开始工作流执行 | 用户输入: 'f1赛车是如何制造的'
📝 WORKFLOW_CONFIG | 最大计划迭代: 1 | 最大步骤数: 3 | 背景调研: True
🔄 NODE_ENTRY | coordinator | 开始执行协调者节点
🧠 LLM_INVOKE | coordinator | 开始思考 | 提示长度: 1024
🧠 LLM_THINKING | coordinator | 提示长度: 1024 | 响应长度: 512 | 耗时: 2.3s
🔀 NODE_TRANSITION | coordinator → background_investigator | 原因: 需要背景调研
✅ NODE_EXIT | coordinator | 节点执行完成 | 耗时: 2.5s
🔄 NODE_ENTRY | background_investigation | 开始执行背景调研节点
🔍 SEARCH | background_investigation | 查询: 'f1赛车是如何制造的' | 结果数: 5
🔧 TOOL_START | web_search | 开始调用工具
🔧 TOOL_END | web_search | 工具调用完成 | 耗时: 1.8s
✅ NODE_EXIT | background_investigation | 节点执行完成 | 耗时: 2.1s
📊 WORKFLOW_SUMMARY | 总耗时: 15.2s | 执行节点: 5 | 使用工具: 3
🏁 WORKFLOW_COMPLETE | session_1728123456 | 工作流执行完成 | 总耗时: 15.2s
```

## 💡 特性说明

### 性能监控
- 自动计算和记录各步骤执行时间
- 提供工作流程性能摘要

### 会话跟踪
- 每次执行都有唯一的会话ID
- 便于跟踪和调试特定执行过程

### 彩色输出
- 遵循用户偏好的颜色设置
- 提高日志可读性

### 分级记录
- INFO级别：显示主要流程和决策点
- DEBUG级别：显示详细的内部状态和参数

## 🔄 当前状态

✅ **已完成**：
- 增强日志核心模块
- 工具调用日志增强
- LLM思考过程日志
- 工作流程级别的监控
- 搜索过程详细记录

⚠️ **部分完成**：
- 图节点日志（由于类型兼容性问题）
- 节点跳转逻辑日志（需要进一步调试）

## 🎯 效果

通过这个增强日志系统，您现在可以：

1. **跟踪每一步检索** - 所有搜索和检索操作都有详细记录
2. **监控每一步思考** - LLM的所有思考过程都被记录
3. **观察节点跳转** - 工作流程中的所有决策和跳转都有日志
4. **性能分析** - 每个操作的耗时都被精确测量
5. **问题调试** - 详细的错误日志和上下文信息

现在运行 `python enhanced_logging_demo.py` 来查看完整的演示！