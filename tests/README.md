# 测试指南

本文档说明如何组织和运行 deer-flow 项目的测试。

## 📁 测试目录结构

```
tests/
├── unit/                       # 单元测试 - 测试单个模块的功能
│   ├── agents/                 # 智能体相关测试
│   │   └── test_researcher_agent.py
│   ├── checkpoint/             # 检查点相关测试
│   ├── config/                 # 配置相关测试
│   ├── crawler/                # 爬虫模块测试
│   ├── graph/                  # 图构建测试
│   ├── llms/                   # LLM 集成测试
│   ├── prompt_enhancer/        # 提示词增强测试
│   ├── rag/                    # RAG 系统测试
│   ├── server/                 # 服务器测试
│   ├── tools/                  # 工具集成测试
│   └── utils/                  # 工具函数测试
├── integration/                # 集成测试 - 测试多个模块协作
│   ├── test_crawler.py
│   ├── test_nodes.py
│   ├── test_researcher_node_tools.py
│   ├── test_template.py
│   └── test_tts.py
├── manual/                     # 手动测试 - 需要人工介入的测试
│   └── test_complete_crawl_system.py
├── performance/                # 性能测试
└── README.md                   # 本文档
```

## 🎯 测试分类

### 1. 单元测试 (Unit Tests)

**位置**: `tests/unit/`

**特点**:
- 测试单个函数、类或模块
- 使用 Mock 隔离外部依赖
- 执行速度快
- 覆盖率高

**示例**:
```python
# tests/unit/agents/test_researcher_agent.py
def test_researcher_agent_receives_tools():
    """测试 researcher 智能体能否接收到工具"""
    tools = [mock_web_search_tool, mock_crawl_tool]
    agent = create_agent("researcher", "researcher", tools, template)
    # 验证工具配置...
```

### 2. 集成测试 (Integration Tests)

**位置**: `tests/integration/`

**特点**:
- 测试多个模块之间的交互
- 可能需要真实的外部服务（如数据库、API）
- 执行时间较长
- 验证端到端流程

**示例**:
```python
# tests/integration/test_researcher_node_tools.py
async def test_researcher_node_configures_web_search_tool():
    """测试 researcher_node 是否配置了 web_search 工具"""
    await researcher_node(state, config)
    # 验证工具配置和执行...
```

### 3. 手动测试 (Manual Tests)

**位置**: `tests/manual/`

**特点**:
- 需要人工交互或检查
- 通常是完整的系统测试
- 提供交互式菜单

**示例**:
```bash
python tests/manual/test_complete_crawl_system.py
```

### 4. 性能测试 (Performance Tests)

**位置**: `tests/performance/`

**特点**:
- 测试系统性能和资源使用
- 基准测试
- 压力测试

## 🚀 运行测试

### 快速开始

```bash
# 运行所有测试
make test

# 或者
pytest tests/

# 或者
uv run pytest tests/
```

### 运行特定层级的测试

```bash
# 只运行单元测试
pytest tests/unit/

# 只运行集成测试
pytest tests/integration/

# 只运行手动测试
pytest tests/manual/

# 只运行性能测试
pytest tests/performance/
```

### 运行特定文件或测试

```bash
# 运行特定文件
pytest tests/unit/agents/test_researcher_agent.py

# 运行特定测试类
pytest tests/unit/agents/test_researcher_agent.py::TestResearcherAgent

# 运行特定测试函数
pytest tests/unit/agents/test_researcher_agent.py::TestResearcherAgent::test_researcher_agent_receives_tools

# 运行名称匹配的测试
pytest -k "researcher"
```

### 使用测试标记 (Markers)

```bash
# 运行异步测试
pytest -m asyncio

# 跳过慢速测试
pytest -m "not slow"

# 只运行单元测试标记
pytest -m unit

# 只运行集成测试标记
pytest -m integration
```

### 生成覆盖率报告

```bash
# 生成终端覆盖率报告
make coverage

# 或者
pytest --cov=src tests/ --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest --cov=src tests/ --cov-report=html

# 打开 HTML 报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 详细输出

```bash
# 显示详细输出
pytest -v

# 显示非常详细的输出
pytest -vv

# 显示标准输出（print 语句）
pytest -s

# 显示失败的测试详细信息
pytest --tb=short

# 显示所有测试摘要
pytest -ra
```

## 📝 测试 Researcher 智能体工具调用

### 单元测试

测试智能体是否正确接收工具：

```bash
# 运行所有 researcher agent 测试
pytest tests/unit/agents/test_researcher_agent.py -v

# 测试工具接收
pytest tests/unit/agents/test_researcher_agent.py::TestResearcherAgent::test_researcher_agent_receives_tools -v

# 测试所有工具（包括本地检索）
pytest tests/unit/agents/test_researcher_agent.py::TestResearcherAgent::test_researcher_agent_with_all_tools -v

# 测试无工具警告
pytest tests/unit/agents/test_researcher_agent.py::TestResearcherAgent::test_researcher_agent_without_tools_warning -v
```

### 集成测试

测试 researcher_node 节点的工具配置：

```bash
# 运行所有 researcher node 工具测试
pytest tests/integration/test_researcher_node_tools.py -v

# 测试 web_search 工具配置
pytest tests/integration/test_researcher_node_tools.py::TestResearcherNodeTools::test_researcher_node_configures_web_search_tool -v

# 测试爬虫工具配置
pytest tests/integration/test_researcher_node_tools.py::TestResearcherNodeTools::test_researcher_node_includes_crawl_tool -v

# 测试本地检索工具
pytest tests/integration/test_researcher_node_tools.py::TestResearcherNodeTools::test_researcher_node_with_local_retriever -v
```

### 查看测试输出

```bash
# 显示详细日志输出
pytest tests/integration/test_researcher_node_tools.py -v -s

# 只显示测试名称
pytest tests/integration/test_researcher_node_tools.py --collect-only
```

## 🔧 测试配置

测试配置在 `pyproject.toml` 中：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=src --cov-report=term-missing"
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::UserWarning",
]
```

## 📊 持续集成 (CI)

项目使用 GitHub Actions 进行 CI/CD（如果配置了）。每次 push 或 PR 都会自动运行测试。

## 💡 最佳实践

### 1. 测试命名规范

- **文件**: `test_<module>.py`
- **类**: `Test<Feature>`
- **函数**: `test_<specific_behavior>`

### 2. 使用 Fixtures

共享测试数据和配置：

```python
@pytest.fixture
def mock_web_search_tool():
    """模拟 web_search 工具"""
    @tool
    def mock_web_search(query: str) -> str:
        return f"搜索结果: {query}"
    return mock_web_search
```

### 3. 使用 Mock 隔离依赖

```python
with patch('src.graph.nodes.get_web_search_tool') as mock_get_search:
    mock_get_search.return_value = mock_tool
    # 测试逻辑...
```

### 4. 异步测试

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 5. 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
])
def test_with_params(input, expected):
    assert process(input) == expected
```

## 🐛 调试测试

### 使用 pdb 调试器

```bash
# 在失败时进入调试器
pytest --pdb

# 在开始时就进入调试器
pytest --trace
```

### 只运行失败的测试

```bash
# 先运行所有测试
pytest

# 只重新运行失败的测试
pytest --lf

# 先运行失败的，再运行其他的
pytest --ff
```

## 📚 相关资源

- [Pytest 官方文档](https://docs.pytest.org/)
- [Pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [Pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock 文档](https://docs.python.org/3/library/unittest.mock.html)

## ❓ 常见问题

### Q: 如何只运行快速测试？

A: 使用 marker：
```bash
pytest -m "not slow"
```

### Q: 如何查看测试覆盖率？

A: 
```bash
make coverage
# 或
pytest --cov=src tests/
```

### Q: 测试失败如何查看详细信息？

A:
```bash
pytest -vv --tb=long
```

### Q: 如何测试特定的智能体或工具？

A: 使用 `-k` 参数进行名称匹配：
```bash
pytest -k "researcher"
pytest -k "web_search"
```

## 📞 获取帮助

如有问题，请：
1. 查看测试日志输出
2. 使用 `-vv` 和 `-s` 获取详细信息
3. 查阅相关测试文件的注释
4. 联系开发团队
