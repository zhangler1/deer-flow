# 检索日志增强功能说明

## 📋 概述

为了提高系统的可观测性，特别是在 researcher 执行检索时，系统现在提供详细的日志输出，包括检索过程的开始、结果数量、内容摘要和性能指标。

## 🎯 功能说明

### 问题背景

之前 researcher 在进行网络检索或本地知识库检索时，终端没有明显的输出，导致：
- 不清楚是否正在检索
- 不知道检索到了什么内容
- 难以判断检索是否成功
- 无法评估检索性能

### 解决方案

在三个核心位置添加了详细的日志输出：

1. **通用检索装饰器** ([`src/tools/decorators.py`](file:///home/llm/zhangle/deer-flow/src/tools/decorators.py))
2. **自定义搜索工具** ([`src/tools/custom_search.py`](file:///home/llm/zhangle/deer-flow/src/tools/custom_search.py))
3. **本地检索工具** ([`src/tools/retriever.py`](file:///home/llm/zhangle/deer-flow/src/tools/retriever.py))

## 🔧 技术实现

### 1. 增强的 LoggedToolMixin

位置：[`src/tools/decorators.py`](file:///home/llm/zhangle/deer-flow/src/tools/decorators.py#L43-L134)

所有使用 `create_logged_tool` 创建的搜索工具（Tavily、DuckDuckGo、Brave、ArXiv、Wikipedia）都会自动获得以下日志能力：

```python
# 检索开始
🔍 TOOL_CALL_START | TavilySearch | 开始检索
[开始检索] 工具: TavilySearch | 查询: '量子计算的应用'

# 检索完成
✅ TOOL_CALL_END | TavilySearch | 检索完成 | 耗时: 2.35s | 结果数: 5
[检索完成] 工具: TavilySearch | 返回 5 条结果 | 耗时: 2.35s

# DEBUG 级别的详细结果
[📊 结果详情] 共 5 条结果:
  [1] 量子计算基础介绍
      量子计算是一种利用量子力学原理进行计算的新型计算范式...
  [2] 量子计算的实际应用
      在密码学、药物研发、金融建模等领域具有重要应用...
```

### 2. 自定义搜索日志

位置：[`src/tools/custom_search.py:_run`](file:///home/llm/zhangle/deer-flow/src/tools/custom_search.py#L216-L282)

```python
# 开始检索
🔍 SEARCH_START | custom_search | 开始自定义搜索 | 仓库: 动态搜索 | 查询: 'AI技术发展'
[🔍 开始搜索] 仓库: 动态搜索 | 查询: 'AI技术发展'

# 检索完成
✅ SEARCH_COMPLETE | custom_search | 搜索完成 | 结果数: 8 | 耗时: 1.52s
[✅ 搜索完成] 查询: 'AI技术发展' | 返回 8 条结果 | 耗时: 1.52s

# DEBUG 级别的详细信息
[📊 结果详情] 共 8 条结果:
  1. 文档: 人工智能技术发展报告
     内容: 2024年人工智能技术取得了重大突破，特别是在大语言模型...
     [评分: 0.95 | 来源: internal_docs]
  2. 文档: AI在医疗领域的应用
     内容: 人工智能技术在医疗诊断、药物研发等方面展现出巨大潜力...
     [评分: 0.88 | 来源: research_papers]
```

### 3. 本地知识库检索日志

位置：[`src/tools/retriever.py:_run`](file:///home/llm/zhangle/deer-flow/src/tools/retriever.py#L32-L113)

```python
# 开始检索
📚 RETRIEVAL_START | local_search | 开始本地知识库检索 | 关键词: 'DeerFlow架构' | 资源数: 3
[📚 本地检索] 关键词: 'DeerFlow架构' | 资源数: 3

# 检索完成
✅ RETRIEVAL_COMPLETE | local_search | 本地检索完成 | 结果数: 4 | 耗时: 0.85s
[✅ 检索完成] 关键词: 'DeerFlow架构' | 返回 4 条结果 | 耗时: 0.85s

# DEBUG 级别的详细信息
[📊 结果详情] 共 4 条结果:
  1. 文档: DeerFlow系统架构设计
     内容: DeerFlow采用基于LangGraph的状态机驱动多智能体协作架构...
     [来源: architecture_docs.md]
  2. 文档: 智能体工作流程
     内容: 系统包含协调员、规划员、研究员、编码员、报告员五大核心...
     [来源: workflow_design.md]

# 无结果时
⚠️ RETRIEVAL_EMPTY | local_search | 本地检索无结果 | 耗时: 0.15s
[⚠️  无结果] 未在本地知识库中找到 'DeerFlow架构' 相关内容
```

## 📊 日志级别控制

系统支持通过环境变量控制日志输出的详细程度：

### INFO 级别（默认）
显示：
- ✅ 检索开始/完成提示
- ✅ 结果数量统计
- ✅ 性能指标（耗时）
- ✅ 成功/失败状态

### DEBUG 级别
额外显示：
- ✅ 详细的结果内容预览
- ✅ 每条结果的标题和摘要
- ✅ 评分和来源信息
- ✅ 更多调试细节

### 设置方法

在 `.env` 文件中设置：
```bash
LOG_LEVEL=DEBUG  # 查看详细结果
# 或
LOG_LEVEL=INFO   # 仅查看摘要信息
```

## 🎨 日志输出格式

遵循用户偏好的颜色方案：
- <span style="color: green;">**绿色**</span>：前面部分（工具名、操作类型）
- <span style="color: purple;">**紫色**</span>：后面部分（查询内容、统计数据）
- <span style="color: yellow;">**黄色**</span>：警告信息（无结果）
- <span style="color: red;">**红色**</span>：错误信息

示例：
```
[开始检索] 工具: CustomSearch | 查询: '量子计算'
          ↑绿色部分↑           ↑紫色部分↑
```

## 🚀 使用场景

### 1. 调试研究流程

```bash
# 启动服务时设置 DEBUG 级别
LOG_LEVEL=DEBUG uv run server.py
```

观察输出：
```
🔍 SEARCH_START | custom_search | 开始自定义搜索 | 查询: '人工智能'
[🔍 开始搜索] 仓库: 动态搜索 | 查询: '人工智能'
✅ SEARCH_COMPLETE | custom_search | 搜索完成 | 结果数: 10 | 耗时: 1.23s
[📊 结果详情] 共 10 条结果:
  1. 文档: 人工智能概述
     内容: 人工智能是计算机科学的一个分支，致力于创建能够模拟...
  2. 文档: AI发展历史
     内容: 从1956年达特茅斯会议开始，人工智能经历了多次浪潮...
```

### 2. 性能监控

通过日志中的耗时信息，可以：
- 识别慢查询
- 对比不同搜索引擎的性能
- 优化检索策略

### 3. 结果验证

通过查看详细结果预览，可以：
- 验证检索内容是否相关
- 评估结果质量
- 调整查询关键词

## 📈 性能影响

- **最小化性能开销**：日志输出仅在检测到时才执行
- **智能级别控制**：通过 `should_log()` 函数进行预判
- **高效字符串处理**：预览内容限制在 60-100 字符
- **可选详细输出**：DEBUG 级别仅在需要时开启

## 🔗 相关文件

### 核心实现
- 日志装饰器：[`src/tools/decorators.py`](file:///home/llm/zhangle/deer-flow/src/tools/decorators.py)
- 自定义搜索：[`src/tools/custom_search.py`](file:///home/llm/zhangle/deer-flow/src/tools/custom_search.py)
- 本地检索：[`src/tools/retriever.py`](file:///home/llm/zhangle/deer-flow/src/tools/retriever.py)
- 日志工具：[`src/utils/enhanced_logger.py`](file:///home/llm/zhangle/deer-flow/src/utils/enhanced_logger.py)

### 应用位置
- Researcher 节点：[`src/graph/nodes.py:853-903`](file:///home/llm/zhangle/deer-flow/src/graph/nodes.py#L853-L903)
- 搜索工具初始化：[`src/tools/search.py`](file:///home/llm/zhangle/deer-flow/src/tools/search.py)

## 📌 注意事项

1. **自动应用**：无需手动配置，所有检索工具自动包含日志
2. **颜色支持**：终端需要支持 ANSI 颜色码
3. **日志级别**：生产环境建议使用 INFO，调试时使用 DEBUG
4. **性能监控**：关注耗时超过 5 秒的检索操作

## 🎯 示例输出

### 完整的检索流程日志

```bash
# Researcher 开始执行
🔄 NODE_ENTRY | researcher | 开始执行研究节点
🔍 RESEARCH_INIT | 开始研究步骤: 分析量子计算的应用领域

# 检索工具初始化
🔧 TOOL_READY | 研究工具配置完成 | 工具数: 1 | 包含本地检索: 否

# 智能体开始执行
🤖 AGENT_INVOKE | researcher | 开始智能体执行 | 递归限制: 25

# 检索开始
🔍 TOOL_CALL_START | CustomSearch | 开始检索
[🔍 开始搜索] 仓库: 动态搜索 | 查询: '量子计算应用领域'

# 检索完成
✅ SEARCH_COMPLETE | custom_search | 搜索完成 | 结果数: 8 | 耗时: 1.85s
[✅ 搜索完成] 查询: '量子计算应用领域' | 返回 8 条结果 | 耗时: 1.85s

# 智能体完成
✅ AGENT_COMPLETE | researcher | 智能体执行完成 | 耗时: 12.45s

# 步骤完成
✅ STEP_COMPLETE | researcher | 步骤执行完成: '分析量子计算的应用领域'
✅ NODE_EXIT | researcher | 节点执行完成 | 总耗时: 13.21s
```

---

**最后更新**: 2025-01-22
