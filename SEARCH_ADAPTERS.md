# 检索接口适配器架构设计文档

## 概述

本文档介绍了 DeerFlow 项目中检索接口的适配器架构设计，该架构旨在：

1. **隔离变化** - 不同检索接口的调用方式参数变化不影响上层代码
2. **独立调试** - 可以单独测试接口脚本
3. **快速接入** - 新接口可以快速集成到检索工具中

## 架构设计

### 核心组件

#### 1. search_adapter_base.py - 适配器基础设施
提供适配器的抽象接口、数据模型、基础实现和管理功能。

#### 1. SearchResult (数据类) - search_adapter_base.py
标准化的检索结果数据结构：

```python
@dataclass
class SearchResult:
    title: str           # 标题
    content: str         # 内容
    url: str = ""        # URL
    source: str = ""     # 来源
    score: float = 0.0   # 评分
    doc_id: str = ""     # 文档ID
    repository: str = "" # 仓库
    create_time: Optional[str] = None  # 创建时间
    update_time: Optional[str] = None  # 更新时间
    category: Optional[str] = None     # 分类
    organization: Optional[str] = None # 组织
```

#### 2. SearchAdapter (抽象基类) - search_adapter_base.py
检索接口适配器的抽象基类：

```python
class SearchAdapter(ABC):
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
        
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """执行检索操作"""
        pass
```

#### 3. 内置适配器实现 - search_adapter_base.py

##### MockSearchAdapter
用于测试和调试的Mock适配器：

```python
class MockSearchAdapter(SearchAdapter):
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        # 返回模拟数据
        pass
```

##### CustomSearchAdapter
通用自定义检索适配器：

```python
class CustomSearchAdapter(SearchAdapter):
    def __init__(self, api_url: str, api_key: str = "", **kwargs):
        super().__init__("Custom", api_url=api_url, api_key=api_key, **kwargs)
        
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        # 调用自定义API
        pass
```

## 使用方法

### 1. 独立测试适配器

```bash
# 测试Mock适配器
python test_search_adapters.py mock "测试查询"

# 测试自定义适配器
python test_search_adapters.py custom "F1赛车制造" --config '{"api_url": "http://example.com/search"}'
```

### 2. 在代码中使用适配器

```python
from src.tools.search_adapter_base import get_search_adapter

# 获取适配器实例
adapter = get_search_adapter("mock")
# 或者
adapter = get_search_adapter("custom", api_url="http://example.com/search", api_key="your_key")

# 执行检索
results = adapter.search("F1赛车制造")
for result in results:
    print(f"标题: {result.title}")
    print(f"内容: {result.content[:50]}...")
```

### 3. 注册新的适配器

```python
from src.tools.search_adapter_base import register_search_adapter

class MyCustomAdapter(SearchAdapter):
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        # 实现自定义检索逻辑
        pass

# 注册适配器
register_search_adapter("my_custom", MyCustomAdapter)
```

## 快速接入新接口指南

### 步骤1: 创建适配器类

创建新的适配器类继承自 `SearchAdapter`：

```python
from src.tools.search_adapter_base import SearchAdapter, SearchResult

class NewSearchAdapter(SearchAdapter):
    def __init__(self, api_endpoint: str, **kwargs):
        super().__init__("NewSearch", api_endpoint=api_endpoint, **kwargs)
        self.api_endpoint = api_endpoint
        
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        # 实现具体的检索逻辑
        # 1. 构建请求
        # 2. 发送请求
        # 3. 解析响应
        # 4. 转换为 SearchResult 列表
        # 5. 调用 self._log_search_result(query, results) 记录日志
        pass
```

### 步骤2: 注册适配器

在适配器注册表中注册新适配器：

```python
# 在 search_adapter_base.py 中添加
from .adapters.new_search_adapter import NewSearchAdapter

_SEARCH_ADAPTERS = {
    "mock": MockSearchAdapter,
    "custom": CustomSearchAdapter,
    "new_search": NewSearchAdapter,  # 添加新适配器
}
```

### 步骤3: 测试适配器

```bash
# 测试新适配器
python test_search_adapters.py new_search "测试查询" --config '{"api_endpoint": "http://api.example.com/search"}'
```

## 环境变量配置

### 常用配置

```bash
# 自定义搜索API配置
CUSTOM_SEARCH_API_URL=http://your-api-endpoint.com/search
CUSTOM_SEARCH_API_KEY=your_api_key

# 日志级别配置
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 调试技巧

### 1. 使用不同日志级别

```bash
# 查看详细检索结果
LOG_LEVEL=DEBUG python your_script.py

# 只查看摘要信息
LOG_LEVEL=INFO python your_script.py
```

### 2. 独立测试脚本

使用 `test_search_adapters.py` 脚本可以独立测试任何适配器：

```bash
# 查看可用适配器
python test_search_adapters.py

# 测试特定适配器
python test_search_adapters.py adapter_type "查询词" --config '{"param": "value"}'
```

## 最佳实践

### 1. 错误处理
```python
def search(self, query: str, **kwargs) -> List[SearchResult]:
    try:
        # 检索逻辑
        pass
    except Exception as e:
        logger.error(f"检索错误: {e}")
        return []  # 返回空列表而不是抛出异常
```

### 2. 结果验证
```python
def _convert_item_to_result(self, item: Dict[str, Any]) -> Optional[SearchResult]:
    # 确保必要字段存在
    if not item.get("title") and not item.get("content"):
        return None  # 跳过无效结果
        
    # 创建 SearchResult 实例
    return SearchResult(...)
```

### 3. 日志记录
```python
def search(self, query: str, **kwargs) -> List[SearchResult]:
    results = self._perform_search(query, **kwargs)
    self._log_search_result(query, results)  # 自动记录摘要和详情
    return results
```

## 扩展性

### 支持的检索服务类型

1. **HTTP API** - 通过HTTP请求调用的检索服务
2. **数据库查询** - 直接查询数据库的检索服务
3. **文件系统** - 本地文件检索
4. **第三方SDK** - 使用第三方库的检索服务

### 适配器开发模板

```python
from src.tools.search_adapter_base import SearchAdapter, SearchResult

class TemplateSearchAdapter(SearchAdapter):
    def __init__(self, **kwargs):
        super().__init__("Template", **kwargs)
        # 初始化适配器特定配置
        
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        # 1. 参数处理
        # 2. 执行检索
        # 3. 结果解析
        # 4. 格式转换
        # 5. 日志记录
        # 6. 返回结果
        pass
```

## 故障排除

### 常见问题

1. **检索结果为空**
   - 检查查询词是否正确
   - 验证API连接配置
   - 查看日志了解具体错误

2. **适配器未找到**
   - 确认适配器已正确注册
   - 检查适配器名称拼写

3. **结果格式不正确**
   - 确保 `_convert_item_to_result` 方法正确处理各种字段
   - 验证必须字段（title 或 content）是否存在

### 调试命令

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 测试适配器
python test_search_adapters.py custom "测试查询"
```