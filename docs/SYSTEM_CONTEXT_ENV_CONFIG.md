# system_context 环境变量配置说明

## 📋 改动概述

将 `system_context`（系统背景上下文）从硬编码改为**从环境变量读取**，提升配置灵活性。

---

## ✅ 已完成的修改

### 1️⃣ **环境变量配置文件**

#### `.env.example` (示例配置)
```bash
# System Context (optional)
# Provides background context for all queries, used in prompt templates
# Example: SYSTEM_CONTEXT="问题关于交通银行"
SYSTEM_CONTEXT=
```

#### `.env` (实际配置)
```bash
# 系统背景上下文（可选）
# 为所有查询提供背景上下文，在 Prompt 模板中使用
# 示例：问题关于交通银行、技术支持场景、客服对话等
SYSTEM_CONTEXT=
```

### 2️⃣ **代码修改**

**文件：** [`src/server/app.py`](file:///home/llm/zhangle/deer-flow/src/server/app.py)

#### 修改点1：`/api/chat/stream` 接口

**修改前：**
```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # ...
    return StreamingResponse(
        _astream_workflow_generator(
            # ...
            system_context="",  # 硬编码为空字符串
        ),
        media_type="text/event-stream",
    )
```

**修改后：**
```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # ...
    # 从环境变量读取系统背景上下文
    system_context = get_str_env("SYSTEM_CONTEXT", "")
    
    return StreamingResponse(
        _astream_workflow_generator(
            # ...
            system_context=system_context,  # 从环境变量读取
        ),
        media_type="text/event-stream",
    )
```

#### 修改点2：`/api/research/simple/stream` 接口

**修改前：**
```python
async for event in _astream_workflow_generator(
    # ...
    system_context="",  # 硬编码为空字符串
):
    yield event
```

**修改后：**
```python
async for event in _astream_workflow_generator(
    # ...
    system_context=get_str_env("SYSTEM_CONTEXT", ""),  # 从环境变量读取
):
    yield event
```

---

## 🎯 使用方式

### **方式1：通过 .env 文件配置**

编辑项目根目录的 [`.env`](file:///home/llm/zhangle/deer-flow/.env) 文件：

```bash
# 设置系统背景上下文
SYSTEM_CONTEXT=问题关于交通银行
```

**重启服务后生效：**
```bash
# 停止服务
Ctrl+C

# 重新启动
python -m src.server.app
```

---

### **方式2：通过环境变量临时设置**

```bash
# Linux/Mac
export SYSTEM_CONTEXT="问题关于交通银行"
python -m src.server.app

# Windows
set SYSTEM_CONTEXT=问题关于交通银行
python -m src.server.app
```

---

### **方式3：Docker 环境**

在 `docker-compose.yml` 中添加环境变量：

```yaml
services:
  backend:
    environment:
      - SYSTEM_CONTEXT=问题关于交通银行
```

---

## 📊 配置示例

### **示例1：银行客服场景**
```bash
SYSTEM_CONTEXT=问题关于交通银行，请结合银行业务知识回答
```

### **示例2：技术支持场景**
```bash
SYSTEM_CONTEXT=这是技术支持对话，请提供详细的技术解决方案
```

### **示例3：医疗咨询场景**
```bash
SYSTEM_CONTEXT=医疗健康咨询场景，请基于医学知识提供建议
```

### **示例4：留空（默认）**
```bash
SYSTEM_CONTEXT=
```
或直接不设置该环境变量。

---

## 🔍 日志输出

### **配置为空时**
```bash
SYSTEM_CONTEXT=
```

**日志：** 不输出（因为值为空，`if system_context:` 条件不满足）

---

### **配置非空时**
```bash
SYSTEM_CONTEXT=问题关于交通银行
```

**日志：** （DEBUG 级别）
```log
2025-11-05 15:30:00,123 - deer-flow.api - DEBUG - 
🏛️ SYSTEM_CONTEXT | 系统背景已配置: 问题关于交通银行 | 将通过State传递给工作流节点
```

**注意：** 日志级别为 `DEBUG`，需要设置 `LOG_LEVEL=DEBUG` 才能看到。

---

## 📝 配置验证

### **检查当前配置**

```bash
# Linux/Mac
echo $SYSTEM_CONTEXT

# Windows
echo %SYSTEM_CONTEXT%

# Python 脚本
python -c "from src.config.loader import get_str_env; print(get_str_env('SYSTEM_CONTEXT', ''))"
```

### **测试配置是否生效**

1. **设置环境变量：**
   ```bash
   # .env 文件
   SYSTEM_CONTEXT=测试背景上下文
   LOG_LEVEL=DEBUG  # 启用DEBUG日志
   ```

2. **启动服务：**
   ```bash
   python -m src.server.app
   ```

3. **发送测试请求：**
   ```bash
   curl -X POST http://localhost:8000/api/chat/stream \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [{"role": "user", "content": "测试问题"}]
     }'
   ```

4. **查看日志输出：**
   ```log
   DEBUG - 🏛️ SYSTEM_CONTEXT | 系统背景已配置: 测试背景上下文
   ```

---

## ⚙️ 技术细节

### **读取函数**

使用 [`get_str_env()`](file:///home/llm/zhangle/deer-flow/src/config/loader.py) 函数读取环境变量：

```python
from src.config.loader import get_str_env

# 读取 SYSTEM_CONTEXT 环境变量，默认值为空字符串
system_context = get_str_env("SYSTEM_CONTEXT", "")
```

### **数据流向**

```
.env 文件或环境变量
  ↓
get_str_env("SYSTEM_CONTEXT", "")
  ↓
chat_stream() 或 _full_workflow_sse_generator()
  ↓
_astream_workflow_generator(system_context=...)
  ↓
workflow_input["system_context"] (传递到 State)
  ↓
workflow_config["configurable"]["system_context"] (传递到 Configuration)
  ↓
各节点可通过 State.system_context 访问
  ↓
在 Prompt Template 中使用（需要在模板中添加 {{ system_context }}）
```

---

## 🚨 注意事项

### **1. Prompt 模板未使用**

⚠️ **当前状态：** `system_context` 虽然传递到了各节点，但 **Prompt 模板中没有使用**。

**验证：**
```bash
grep -r "system_context" src/prompts/ --include="*.md"
# 结果：0 matches
```

**如需使用，需在 Prompt 模板中添加：**

```markdown
# src/prompts/coordinator.md

{% if system_context %}
## 系统背景上下文
{{ system_context }}
{% endif %}

# ... 其他 Prompt 内容 ...
```

### **2. 重启服务生效**

修改 `.env` 文件后，**必须重启服务**才能生效：

```bash
# 停止服务
Ctrl+C

# 重新启动
python -m src.server.app
```

### **3. 日志级别**

`system_context` 的日志是 `DEBUG` 级别，需要设置：

```bash
LOG_LEVEL=DEBUG
```

才能在日志中看到。

---

## 🎨 优势对比

| 方式 | 修改前（硬编码） | 修改后（环境变量） |
|------|------------------|-------------------|
| **配置方式** | 修改代码 | 修改 .env 文件 |
| **灵活性** | ❌ 低 | ✅ 高 |
| **重启需求** | ❌ 需要重新部署 | ✅ 只需重启服务 |
| **多环境支持** | ❌ 困难 | ✅ 简单（不同 .env） |
| **安全性** | ⚠️ 代码中可见 | ✅ .env 可加入 .gitignore |
| **维护成本** | ❌ 高 | ✅ 低 |

---

## 📚 相关文档

- [`.env.example`](file:///home/llm/zhangle/deer-flow/.env.example) - 环境变量示例
- [`.env`](file:///home/llm/zhangle/deer-flow/.env) - 实际配置文件
- [`src/config/loader.py`](file:///home/llm/zhangle/deer-flow/src/config/loader.py) - 配置加载器
- [`docs/SYSTEM_CONTEXT_CLEANUP.md`](file:///home/llm/zhangle/deer-flow/docs/SYSTEM_CONTEXT_CLEANUP.md) - 清理分析文档

---

## ✅ 验证清单

- [x] `.env.example` 已添加 `SYSTEM_CONTEXT` 配置项
- [x] `.env` 已添加 `SYSTEM_CONTEXT` 配置项和中文说明
- [x] `/api/chat/stream` 接口改为从环境变量读取
- [x] `/api/research/simple/stream` 接口改为从环境变量读取
- [x] 日志级别改为 `DEBUG`（减少噪音）
- [x] 创建配置说明文档

---

## 🎯 后续建议

### **短期（可选）**

如果需要在 Prompt 中使用 `system_context`，在相关 Prompt 模板中添加：

```markdown
{% if system_context %}
## 系统背景
{{ system_context }}
{% endif %}
```

涉及文件：
- `src/prompts/coordinator.md`
- `src/prompts/planner.md`
- `src/prompts/researcher.md`
- `src/prompts/reporter.md`

### **长期（可选）**

如果确认不需要这个功能，可以参考 [`docs/SYSTEM_CONTEXT_CLEANUP.md`](file:///home/llm/zhangle/deer-flow/docs/SYSTEM_CONTEXT_CLEANUP.md) 完全移除相关代码。

---

## 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| 1.0 | 2025-11-05 | 将 system_context 从硬编码改为环境变量配置 |

---

**总结：** 现在你可以通过修改 `.env` 文件来灵活配置系统背景上下文，无需修改代码！🎉
