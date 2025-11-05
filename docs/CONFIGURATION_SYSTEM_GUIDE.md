# 配置系统完整指南

本文档详细介绍 DeerFlow 的配置读取机制、环境变量与配置文件的区别、以及各种配置的使用场景。

## 📋 目录

1. [配置系统架构](#配置系统架构)
2. [配置来源](#配置来源)
3. [环境变量 vs 配置文件](#环境变量-vs-配置文件)
4. [配置读取流程](#配置读取流程)
5. [配置类型详解](#配置类型详解)
6. [优先级规则](#优先级规则)
7. [实际案例分析](#实际案例分析)

---

## 配置系统架构

DeerFlow 采用**多层次配置系统**，从多个来源读取配置，并按优先级合并：

```mermaid
graph TB
    A[应用启动] --> B{配置来源}
    B --> C[环境变量 .env]
    B --> D[YAML配置 conf.yaml]
    B --> E[运行时参数 RunnableConfig]
    
    C --> F[配置加载器]
    D --> F
    E --> F
    
    F --> G[配置合并]
    G --> H[优先级处理]
    H --> I[最终配置]
    
    I --> J[LLM配置]
    I --> K[工作流配置]
    I --> L[数据库配置]
    I --> M[工具配置]
```

---

## 配置来源

### 1. 环境变量（`.env` 文件）

**位置**: `/home/llm/zhangle/deer-flow/.env`

**特点**:
- 优先级最高（会覆盖其他配置）
- 适用于敏感信息（API密钥、数据库密码）
- 适用于环境相关配置（开发/生产环境）
- 支持运行时覆盖（无需重启应用）

**示例内容**:
```bash
# 应用基础配置
DEBUG=True
APP_ENV=development
AGENT_RECURSION_LIMIT=25

# 日志级别
LOG_LEVEL=INFO

# CORS配置
ALLOWED_ORIGINS=http://frontend:3000

# 搜索引擎配置
SEARCH_API=custom_search
CUSTOM_SEARCH_API_URL=http://192.168.0.106:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do
CUSTOM_SEARCH_API_KEY=your_custom_search_api_key
CUSTOM_SEARCH_REPOSITORY=okic-dynamicSearch

# 数据库配置
LANGGRAPH_CHECKPOINT_SAVER=true
LANGGRAPH_CHECKPOINT_DB_URL=mongodb://localhost:27017/

# RAG配置
RAG_PROVIDER=vikingdb_knowledge_base
VIKINGDB_KNOWLEDGE_BASE_API_URL=api.example.com
VIKINGDB_KNOWLEDGE_BASE_API_AK=your_access_key
VIKINGDB_KNOWLEDGE_BASE_API_SK=your_secret_key
VIKINGDB_KNOWLEDGE_BASE_RETRIEVAL_SIZE=10

# LLM配置覆盖（双下划线格式）
BASIC_MODEL__API_KEY=sk-override-key
BASIC_MODEL__BASE_URL=https://api.override.com/v1
BASIC_MODEL__MODEL=gpt-4
```

### 2. YAML配置文件（`conf.yaml`）

**位置**: `/home/llm/zhangle/deer-flow/conf.yaml`

**特点**:
- 适用于结构化配置（嵌套配置）
- 适用于相对稳定的配置（模型设置、默认参数）
- 支持环境变量引用（`$VAR_NAME`）
- 修改后需要重启应用
- 带缓存机制（避免重复读取）

**示例内容**:
```yaml
# LLM模型配置
BASIC_MODEL:
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat 
  api_key: sk-1bdd889cbd3e46a6a454cb4bb322cf60
  verify_ssl: false

REASONING_MODEL:
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat 
  api_key: sk-1bdd889cbd3e46a6a454cb4bb322cf60
  verify_ssl: false

# 搜索引擎配置
SEARCH_ENGINE:
  engine: custom_search
  include_domains:
    - example.com
    - gov.cn
    - edu.cn
  exclude_domains:
    - spam.com

# 自定义搜索配置
CUSTOM_SEARCH:
  repositories:
    aggregation_search:
      name: "聚合搜索"
      repository: "aggregation-search"
      channel_id: "0"
    vector_search:
      name: "向量库"
      repository: "euvd-searchByChannelId"
      channel_id: "0"
  default_repository: "aggregation_search"
```

### 3. 运行时参数（RunnableConfig）

**特点**:
- API请求级别的配置
- 最灵活，每次请求可不同
- 通过 `configurable` 字段传递
- 优先级低于环境变量

**示例**:
```python
workflow_config = {
    "thread_id": thread_id,
    "configurable": {
        "resources": resources,
        "max_plan_iterations": 5,
        "max_step_num": 10,
        "search_engine": "tavily",
        "system_context": "针对金融行业的分析",
    },
    "recursion_limit": 25,
}
```

---

## 环境变量 vs 配置文件

### 对比表格

| 特性 | 环境变量 (.env) | 配置文件 (conf.yaml) |
|------|----------------|---------------------|
| **优先级** | 最高（会覆盖） | 中等（被环境变量覆盖） |
| **适用场景** | 敏感信息、环境相关 | 结构化配置、默认值 |
| **数据结构** | 扁平键值对 | 嵌套结构、数组、对象 |
| **运行时修改** | 支持（部分） | 不支持（需重启） |
| **版本控制** | 通常不提交（.gitignore） | 提交到Git（模板） |
| **安全性** | 高（不暴露） | 低（需脱敏） |
| **可读性** | 中等 | 高（支持注释、结构） |
| **示例** | `DEBUG=True` | `BASIC_MODEL: {api_key: xxx}` |

### 使用建议

#### ✅ 使用环境变量的场景

1. **敏感信息**
   ```bash
   # API密钥、访问令牌
   BASIC_MODEL__API_KEY=sk-secret-key
   VIKINGDB_KNOWLEDGE_BASE_API_AK=access_key
   VIKINGDB_KNOWLEDGE_BASE_API_SK=secret_key
   ```

2. **环境差异配置**
   ```bash
   # 开发环境
   DEBUG=True
   APP_ENV=development
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   
   # 生产环境
   DEBUG=False
   APP_ENV=production
   NEXT_PUBLIC_API_URL=https://api.production.com
   ```

3. **基础设施配置**
   ```bash
   # 数据库连接
   LANGGRAPH_CHECKPOINT_DB_URL=mongodb://localhost:27017/
   
   # 服务地址
   CUSTOM_SEARCH_API_URL=http://192.168.0.106:8010/api
   ```

4. **功能开关**
   ```bash
   ENABLE_MCP_SERVER_CONFIGURATION=false
   ENABLE_PYTHON_REPL=false
   LANGGRAPH_CHECKPOINT_SAVER=true
   ```

#### ✅ 使用配置文件的场景

1. **结构化模型配置**
   ```yaml
   BASIC_MODEL:
     base_url: https://api.deepseek.com/v1
     model: deepseek-chat
     max_retries: 3
     verify_ssl: false
   ```

2. **复杂嵌套配置**
   ```yaml
   CUSTOM_SEARCH:
     repositories:
       aggregation_search:
         name: "聚合搜索"
         repository: "aggregation-search"
         channel_id: "0"
       vector_search:
         name: "向量库"
         repository: "euvd-searchByChannelId"
         channel_id: "0"
     default_repository: "aggregation_search"
   ```

3. **默认值和预设**
   ```yaml
   SEARCH_ENGINE:
     engine: custom_search
     include_domains:
       - example.com
       - gov.cn
     exclude_domains:
       - spam.com
   ```

---

## 配置读取流程

### 1. 环境变量读取

**工具函数**: `src/config/loader.py`

```python
def get_bool_env(name: str, default: bool = False) -> bool:
    """读取布尔型环境变量"""
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

def get_str_env(name: str, default: str = "") -> str:
    """读取字符串型环境变量"""
    val = os.getenv(name)
    return default if val is None else str(val).strip()

def get_int_env(name: str, default: int = 0) -> int:
    """读取整数型环境变量"""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        print(f"Invalid integer value for {name}: {val}. Using default {default}.")
        return default
```

**使用示例**:
```python
from src.config.loader import get_bool_env, get_str_env, get_int_env

# 读取布尔值
checkpoint_enabled = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)

# 读取字符串
db_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "mongodb://localhost:27017/")

# 读取整数
recursion_limit = get_int_env("AGENT_RECURSION_LIMIT", 25)
```

### 2. YAML配置读取

**工具函数**: `src/config/loader.py`

```python
def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """加载并处理YAML配置文件"""
    # 如果文件不存在，返回{}
    if not os.path.exists(file_path):
        return {}

    # 检查缓存中是否已存在配置
    if file_path in _config_cache:
        return _config_cache[file_path]

    # 如果缓存中不存在，则加载并处理配置
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    processed_config = process_dict(config)

    # 将处理后的配置存入缓存
    _config_cache[file_path] = processed_config
    return processed_config
```

**环境变量引用支持**:
```python
def replace_env_vars(value: str) -> str:
    """替换配置值中的环境变量引用"""
    if not isinstance(value, str):
        return value
    if value.startswith("$"):
        env_var = value[1:]
        return os.getenv(env_var, env_var)
    return value
```

**YAML中使用环境变量**:
```yaml
BASIC_MODEL:
  api_key: $OPENAI_API_KEY  # 引用环境变量
  base_url: https://api.openai.com/v1
```

### 3. Configuration类合并

**定义**: `src/config/configuration.py`

```python
@dataclass(kw_only=True)
class Configuration:
    """工作流配置类"""
    
    resources: list[Resource] = field(default_factory=list)
    max_plan_iterations: int = 1
    max_step_num: int = 3
    max_search_results: int = 2
    search_engine: str = "custom_search"
    custom_search_repository: Optional[str] = None
    mcp_settings: dict = None
    report_style: str = ReportStyle.ACADEMIC.value
    enable_deep_thinking: bool = False
    system_context: str = ""

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """从RunnableConfig创建Configuration实例"""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        # 优先级: 环境变量 > RunnableConfig
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
```

**合并逻辑**:
1. 从 `RunnableConfig` 获取基础值
2. 环境变量覆盖同名配置（转大写匹配）
3. 过滤掉None值，保留类默认值

### 4. LLM配置合并

**定义**: `src/llms/llm.py`

```python
def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    从环境变量获取LLM配置
    格式: {LLM_TYPE}_MODEL__{KEY}
    例如: BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix):].lower()
            conf[conf_key] = value
    return conf

def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """创建LLM实例，合并YAML和环境变量配置"""
    # 从YAML获取配置
    llm_conf = conf.get(config_key, {})
    
    # 从环境变量获取配置
    env_conf = _get_env_llm_conf(llm_type)
    
    # 合并配置，环境变量优先级更高
    merged_conf = {**llm_conf, **env_conf}
    
    # 创建LLM实例
    return ChatOpenAI(**merged_conf)
```

**LLM配置优先级**:
```
环境变量 (BASIC_MODEL__api_key) 
    > 
YAML配置 (BASIC_MODEL.api_key)
    >
代码默认值
```

**示例**:
```yaml
# conf.yaml
BASIC_MODEL:
  api_key: sk-yaml-key
  base_url: https://api.yaml.com/v1
  model: gpt-3.5-turbo
```

```bash
# .env
BASIC_MODEL__API_KEY=sk-env-key
BASIC_MODEL__MODEL=gpt-4
```

**最终生效配置**:
```python
{
    "api_key": "sk-env-key",        # 环境变量覆盖
    "base_url": "https://api.yaml.com/v1",  # YAML配置
    "model": "gpt-4"                # 环境变量覆盖
}
```

---

## 配置类型详解

### 1. 应用级配置（环境变量）

**作用域**: 全局，影响整个应用

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEBUG` | bool | False | 调试模式开关 |
| `APP_ENV` | string | production | 应用环境（development/staging/production） |
| `AGENT_RECURSION_LIMIT` | int | 25 | Agent递归深度限制 |
| `LOG_LEVEL` | string | INFO | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `ALLOWED_ORIGINS` | string | * | CORS允许的源 |

**读取示例**:
```python
# src/config/configuration.py
def get_recursion_limit(default: int = 25) -> int:
    """获取递归限制"""
    parsed_limit = get_int_env("AGENT_RECURSION_LIMIT", default)
    if parsed_limit > 0:
        return parsed_limit
    else:
        return default
```

### 2. 数据库配置（环境变量）

**作用域**: 全局，持久化相关

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `LANGGRAPH_CHECKPOINT_SAVER` | bool | false | 是否启用检查点保存 |
| `LANGGRAPH_CHECKPOINT_DB_URL` | string | mongodb://localhost:27017/ | 数据库连接URL |

**支持的数据库**:
- MongoDB: `mongodb://user:pass@host:port/db`
- PostgreSQL: `postgresql://user:pass@host:port/db`

**读取示例**:
```python
# src/server/app.py
checkpoint_saver = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)
checkpoint_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "")

if checkpoint_saver and checkpoint_url.startswith("postgresql://"):
    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        await checkpointer.setup()
        graph.checkpointer = checkpointer
```

### 3. 搜索引擎配置（混合）

**环境变量部分**:
```bash
SEARCH_API=custom_search
CUSTOM_SEARCH_API_URL=http://api.example.com/search
CUSTOM_SEARCH_API_KEY=your_api_key
CUSTOM_SEARCH_REPOSITORY=okic-dynamicSearch
```

**YAML配置部分**:
```yaml
SEARCH_ENGINE:
  engine: custom_search
  include_domains:
    - example.com
  exclude_domains:
    - spam.com

CUSTOM_SEARCH:
  repositories:
    aggregation_search:
      name: "聚合搜索"
      repository: "aggregation-search"
  default_repository: "aggregation_search"
```

**读取示例**:
```python
# src/config/tools.py
SELECTED_SEARCH_ENGINE = os.getenv("SEARCH_API", SearchEngine.CUSTOM_SEARCH.value)
```

### 4. RAG配置（环境变量）

**VikingDB示例**:
```bash
RAG_PROVIDER=vikingdb_knowledge_base
VIKINGDB_KNOWLEDGE_BASE_API_URL=api.example.com
VIKINGDB_KNOWLEDGE_BASE_API_AK=your_access_key
VIKINGDB_KNOWLEDGE_BASE_API_SK=your_secret_key
VIKINGDB_KNOWLEDGE_BASE_RETRIEVAL_SIZE=10
VIKINGDB_KNOWLEDGE_BASE_REGION=cn-north-1
```

**读取示例**:
```python
# src/rag/vikingdb_knowledge_base.py
class VikingDBKnowledgeBase:
    def __init__(self):
        api_url = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_URL")
        if not api_url:
            raise ValueError("VIKINGDB_KNOWLEDGE_BASE_API_URL is not set")
        self.api_url = api_url
        
        self.api_ak = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_AK")
        self.api_sk = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_SK")
        self.retrieval_size = int(os.getenv("VIKINGDB_KNOWLEDGE_BASE_RETRIEVAL_SIZE", "10"))
```

### 5. LLM配置（YAML + 环境变量）

**YAML基础配置**:
```yaml
BASIC_MODEL:
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat
  api_key: sk-default-key
  max_retries: 3
  verify_ssl: false

REASONING_MODEL:
  base_url: https://api.deepseek.com/v1
  model: deepseek-reasoner
  api_key: sk-default-key
```

**环境变量覆盖**:
```bash
# 覆盖BASIC_MODEL配置
BASIC_MODEL__API_KEY=sk-production-key
BASIC_MODEL__BASE_URL=https://api.production.com/v1
BASIC_MODEL__MODEL=gpt-4-turbo

# 覆盖REASONING_MODEL配置
REASONING_MODEL__API_KEY=sk-reasoning-key
REASONING_MODEL__MODEL=deepseek-reasoner-v2
```

**合并后生效配置**:
```python
# BASIC_MODEL最终配置
{
    "base_url": "https://api.production.com/v1",  # 环境变量覆盖
    "model": "gpt-4-turbo",                       # 环境变量覆盖
    "api_key": "sk-production-key",               # 环境变量覆盖
    "max_retries": 3,                             # YAML配置
    "verify_ssl": False                           # YAML配置
}
```

### 6. 工作流配置（运行时参数）

**通过API请求传递**:
```python
# src/server/app.py
workflow_config = {
    "thread_id": thread_id,
    "configurable": {
        "resources": resources,                    # 资源列表
        "max_plan_iterations": max_plan_iterations, # 最大计划迭代次数
        "max_step_num": max_step_num,              # 最大步骤数
        "max_search_results": max_search_results,  # 最大搜索结果数
        "search_engine": search_engine,            # 搜索引擎类型
        "custom_search_repository": custom_search_repository,
        "mcp_settings": mcp_settings,
        "report_style": report_style.value,        # 报告风格
        "enable_deep_thinking": enable_deep_thinking,
        "system_context": system_context,          # 系统背景上下文
    },
    "recursion_limit": get_recursion_limit(),
}
```

**Configuration类读取**:
```python
# src/graph/nodes.py
config = Configuration.from_runnable_config(config)

# 访问配置
max_step_num = config.max_step_num
search_engine = config.search_engine
system_context = config.system_context
```

---

## 优先级规则

### 总体优先级（从高到低）

```
1. 环境变量（.env）
   ↓
2. 运行时参数（RunnableConfig）
   ↓
3. YAML配置（conf.yaml）
   ↓
4. 代码默认值
```

### 详细规则

#### 规则1: 环境变量覆盖一切

```python
# Configuration类合并逻辑
values: dict[str, Any] = {
    f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
    #      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #      环境变量优先，如果不存在才使用configurable
    for f in fields(cls)
    if f.init
}
```

**示例**:
```python
# RunnableConfig传入
configurable = {"max_step_num": 5}

# 环境变量设置
os.environ["MAX_STEP_NUM"] = "10"

# 最终结果
config.max_step_num  # 10 (环境变量覆盖)
```

#### 规则2: LLM配置特殊合并

```python
# YAML配置
llm_conf = {"api_key": "yaml-key", "base_url": "yaml-url"}

# 环境变量配置
env_conf = {"api_key": "env-key", "model": "env-model"}

# 合并结果
merged_conf = {**llm_conf, **env_conf}
# {
#     "api_key": "env-key",      # 环境变量覆盖
#     "base_url": "yaml-url",    # YAML保留
#     "model": "env-model"       # 环境变量新增
# }
```

#### 规则3: 运行时参数覆盖默认值

```python
@dataclass(kw_only=True)
class Configuration:
    max_step_num: int = 3  # 默认值

# 运行时传入
config = Configuration.from_runnable_config({
    "configurable": {"max_step_num": 10}
})
# config.max_step_num == 10
```

### 优先级示例

**场景**: 配置 `max_step_num`

```python
# 1. 代码默认值
class Configuration:
    max_step_num: int = 3  # 默认3

# 2. YAML配置（无此选项）

# 3. 运行时参数
configurable = {"max_step_num": 5}

# 4. 环境变量
os.environ["MAX_STEP_NUM"] = "10"

# 最终结果
config.max_step_num  # 10
```

**优先级链**:
```
环境变量(10) > 运行时参数(5) > YAML(无) > 默认值(3)
最终: 10
```

---

## 实际案例分析

### 案例1: LLM配置的完整合并流程

**文件准备**:

```yaml
# conf.yaml
BASIC_MODEL:
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat
  api_key: sk-yaml-default
  max_retries: 3
  verify_ssl: false
```

```bash
# .env
BASIC_MODEL__API_KEY=sk-production-secret
BASIC_MODEL__MODEL=gpt-4-turbo
```

**代码执行**:
```python
# 1. 加载YAML配置
conf = load_yaml_config("conf.yaml")
llm_conf = conf.get("BASIC_MODEL", {})
# {
#     "base_url": "https://api.deepseek.com/v1",
#     "model": "deepseek-chat",
#     "api_key": "sk-yaml-default",
#     "max_retries": 3,
#     "verify_ssl": False
# }

# 2. 加载环境变量配置
env_conf = _get_env_llm_conf("basic")
# {
#     "api_key": "sk-production-secret",
#     "model": "gpt-4-turbo"
# }

# 3. 合并配置
merged_conf = {**llm_conf, **env_conf}
# {
#     "base_url": "https://api.deepseek.com/v1",  # YAML
#     "model": "gpt-4-turbo",                     # 环境变量覆盖
#     "api_key": "sk-production-secret",          # 环境变量覆盖
#     "max_retries": 3,                           # YAML
#     "verify_ssl": False                         # YAML
# }

# 4. 创建LLM实例
llm = ChatOpenAI(**merged_conf)
```

**最终效果**:
- API密钥使用环境变量（安全）
- 模型使用环境变量（灵活切换）
- base_url、max_retries、verify_ssl使用YAML（稳定配置）

### 案例2: 工作流配置的优先级

**环境变量**:
```bash
MAX_STEP_NUM=15
SEARCH_ENGINE=tavily
```

**API请求**:
```python
POST /api/research/simple/stream
{
    "query": "研究主题",
    "max_step_num": 10,
    "search_engine": "custom_search",
    "system_context": "金融行业背景"
}
```

**配置合并流程**:
```python
# 1. 准备运行时配置
workflow_config = {
    "configurable": {
        "max_step_num": 10,           # API请求
        "search_engine": "custom_search",  # API请求
        "system_context": "金融行业背景",  # API请求
    }
}

# 2. Configuration.from_runnable_config 合并
config = Configuration.from_runnable_config(workflow_config)

# 3. 环境变量覆盖
config.max_step_num      # 15 (环境变量覆盖)
config.search_engine     # "tavily" (环境变量覆盖)
config.system_context    # "金融行业背景" (无环境变量，使用API)
```

**优先级表现**:
| 配置项 | API请求 | 环境变量 | 最终值 | 生效来源 |
|--------|---------|----------|--------|----------|
| max_step_num | 10 | 15 | 15 | 环境变量 |
| search_engine | custom_search | tavily | tavily | 环境变量 |
| system_context | 金融行业背景 | (无) | 金融行业背景 | API请求 |

### 案例3: 数据库配置的条件读取

**环境变量**:
```bash
LANGGRAPH_CHECKPOINT_SAVER=true
LANGGRAPH_CHECKPOINT_DB_URL=postgresql://user:pass@localhost:5432/db
```

**代码逻辑**:
```python
# src/server/app.py
checkpoint_saver = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)
checkpoint_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "")

if checkpoint_saver and checkpoint_url != "":
    if checkpoint_url.startswith("postgresql://"):
        # 使用PostgreSQL
        async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
            graph.checkpointer = checkpointer
            
    elif checkpoint_url.startswith("mongodb://"):
        # 使用MongoDB
        async with AsyncMongoDBSaver.from_conn_string(checkpoint_url) as checkpointer:
            graph.checkpointer = checkpointer
else:
    # 不使用检查点保存
    pass
```

**配置分析**:
- `LANGGRAPH_CHECKPOINT_SAVER`: 功能开关（环境变量）
- `LANGGRAPH_CHECKPOINT_DB_URL`: 连接信息（环境变量，敏感）
- 根据URL前缀自动选择数据库类型（代码逻辑）

### 案例4: RAG配置的必需验证

**环境变量**:
```bash
RAG_PROVIDER=vikingdb_knowledge_base
VIKINGDB_KNOWLEDGE_BASE_API_URL=api.vikingdb.com
VIKINGDB_KNOWLEDGE_BASE_API_AK=your_ak
VIKINGDB_KNOWLEDGE_BASE_API_SK=your_sk
VIKINGDB_KNOWLEDGE_BASE_RETRIEVAL_SIZE=10
```

**代码逻辑**:
```python
# src/rag/vikingdb_knowledge_base.py
class VikingDBKnowledgeBase:
    def __init__(self):
        # 必需参数验证
        api_url = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_URL")
        if not api_url:
            raise ValueError("VIKINGDB_KNOWLEDGE_BASE_API_URL is not set")
        
        api_ak = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_AK")
        if not api_ak:
            raise ValueError("VIKINGDB_KNOWLEDGE_BASE_API_AK is not set")
        
        api_sk = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_SK")
        if not api_sk:
            raise ValueError("VIKINGDB_KNOWLEDGE_BASE_API_SK is not set")
        
        # 可选参数（有默认值）
        retrieval_size = os.getenv("VIKINGDB_KNOWLEDGE_BASE_RETRIEVAL_SIZE")
        self.retrieval_size = int(retrieval_size) if retrieval_size else 10
        
        region = os.getenv("VIKINGDB_KNOWLEDGE_BASE_REGION", "cn-north-1")
        self.region = region
```

**配置特点**:
- 敏感信息（AK/SK）必须通过环境变量
- 必需参数缺失时抛出异常
- 可选参数提供默认值

---

## 最佳实践

### 1. 配置分离原则

```
敏感配置 → 环境变量（不提交）
稳定配置 → YAML文件（提交模板）
动态配置 → 运行时参数（API传递）
```

### 2. 环境变量命名规范

```bash
# 应用级配置：大写+下划线
DEBUG=True
APP_ENV=production

# LLM配置：模型类型__参数名（双下划线）
BASIC_MODEL__API_KEY=sk-xxx
BASIC_MODEL__BASE_URL=https://api.xxx.com/v1

# 功能模块：模块名_配置项
VIKINGDB_KNOWLEDGE_BASE_API_URL=xxx
CUSTOM_SEARCH_API_KEY=xxx
```

### 3. 配置模板管理

**提交到Git**:
- `.env.example` - 环境变量模板（脱敏）
- `conf.yaml` - YAML配置模板（脱敏）

**不提交到Git**:
- `.env` - 实际环境变量（包含密钥）
- `.env.local` - 本地覆盖配置

**.gitignore设置**:
```gitignore
.env
.env.local
.env.*.local
```

### 4. 配置验证

**启动时验证必需配置**:
```python
def validate_config():
    required_env_vars = [
        "BASIC_MODEL__API_KEY",
        "CUSTOM_SEARCH_API_URL",
    ]
    
    missing = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
```

### 5. 配置文档化

**在代码中添加注释**:
```python
@dataclass(kw_only=True)
class Configuration:
    """工作流配置类
    
    环境变量优先级: 环境变量 > RunnableConfig > 默认值
    
    示例:
        # 通过环境变量覆盖
        export MAX_STEP_NUM=10
        
        # 通过RunnableConfig传递
        config = Configuration.from_runnable_config({
            "configurable": {"max_step_num": 5}
        })
    """
    max_step_num: int = 3  # 最大步骤数，可通过MAX_STEP_NUM环境变量覆盖
```

---

## 故障排查

### 问题1: 配置未生效

**症状**: 修改了配置但没有生效

**排查步骤**:
1. 检查配置优先级（环境变量是否覆盖）
2. 检查YAML缓存（重启应用）
3. 检查变量名称（大小写、拼写）
4. 检查配置加载顺序

**解决方案**:
```python
# 清除YAML缓存
from src.config.loader import _config_cache
_config_cache.clear()

# 重新加载配置
conf = load_yaml_config("conf.yaml")
```

### 问题2: 环境变量未读取

**症状**: 设置了环境变量但代码中获取不到

**排查步骤**:
1. 检查`.env`文件是否在正确位置
2. 检查`dotenv`是否加载
3. 检查变量名格式（大小写）
4. 检查运行环境（Docker/本地）

**解决方案**:
```python
# 确保加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 验证环境变量
import os
print(os.getenv("YOUR_VAR_NAME"))
```

### 问题3: LLM配置覆盖失败

**症状**: 环境变量设置了但LLM仍使用YAML配置

**排查步骤**:
1. 检查环境变量格式（双下划线）
2. 检查LLM类型名称（basic/reasoning/vision）
3. 检查参数名称（小写）

**正确格式**:
```bash
# ✅ 正确
BASIC_MODEL__API_KEY=sk-xxx
BASIC_MODEL__BASE_URL=https://xxx

# ❌ 错误
BASIC_MODEL_API_KEY=sk-xxx      # 单下划线
BASIC__MODEL__API_KEY=sk-xxx    # 位置错误
basic_model__api_key=sk-xxx     # 小写
```

---

## 总结

### 配置系统特点

1. **多层次**: 环境变量 + YAML + 运行时参数
2. **优先级明确**: 环境变量 > 运行时参数 > YAML > 默认值
3. **灵活性**: 支持不同场景的配置方式
4. **安全性**: 敏感信息通过环境变量隔离

### 使用建议

| 配置类型 | 推荐方式 | 原因 |
|----------|----------|------|
| API密钥 | 环境变量 | 安全性 |
| 数据库连接 | 环境变量 | 环境差异 |
| 模型配置 | YAML + 环境变量 | 结构化 + 覆盖 |
| 工作流参数 | 运行时参数 | 灵活性 |
| 功能开关 | 环境变量 | 快速切换 |

### 核心原则

1. **敏感配置不入库**: 使用环境变量 + .gitignore
2. **环境隔离**: 开发/测试/生产使用不同`.env`
3. **配置验证**: 启动时检查必需配置
4. **文档同步**: 配置变更同步更新文档
