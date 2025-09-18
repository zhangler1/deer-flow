# 自定义搜索工具测试脚本说明

## 概述

完成了DeerFlow项目的自定义搜索工具测试脚本，包含两个版本：

1. **完整版测试脚本** (`test_custom_search.py`) - 包含全面的测试功能
2. **简化版测试脚本** (`test_custom_search_simple.py`) - 专注于核心功能测试

## 测试脚本功能

### 完整版测试脚本 (`test_custom_search.py`)

#### 主要测试功能：
1. **环境变量配置测试** - 验证所有环境变量的正确加载
2. **API请求格式测试** - 验证请求头和请求体格式
3. **响应解析测试** - 测试API响应的解析逻辑
4. **错误处理测试** - 测试各种异常情况的处理
5. **Mock服务健康检测** - 检查Mock服务的运行状态
6. **搜索集成测试** - 端到端的搜索功能测试

#### 运行模式：
- **基础模式**: `python test_custom_search.py`
- **全面模式**: `python test_custom_search.py --comprehensive`

#### 特色功能：
- 支持颜色输出（遵循用户偏好：绿色+紫色）
- 自动检测Mock服务状态
- 详细的测试结果统计
- 环境变量安全备份和恢复

### 简化版测试脚本 (`test_custom_search_simple.py`)

#### 核心测试：
1. **基本功能测试** - 工具创建和配置验证
2. **Mock服务测试** - 服务连接和API调用
3. **搜索集成测试** - 实际搜索功能验证

#### 运行方式：
```bash
python test_custom_search_simple.py
```

## 测试覆盖范围

### 功能覆盖
- ✅ 工具实例化和配置加载
- ✅ 环境变量处理机制
- ✅ API请求构建和发送
- ✅ 响应解析和数据转换
- ✅ 错误处理和回退机制
- ✅ Mock服务集成测试

### 配置测试
- ✅ API URL 配置
- ✅ Repository 设置
- ✅ Channel ID 配置
- ✅ 用户认证信息
- ✅ 最大结果数限制

### 响应解析验证
- ✅ 成功响应解析
- ✅ content 和 absContent 回退机制
- ✅ 分数排序功能
- ✅ 空结果过滤
- ✅ 额外字段提取（createTime, category等）

## Mock服务更新

更新了 `middlewares/search/mock_search_api.py`：

### 改进内容：
1. **请求格式支持** - 支持标准的JSON请求体
2. **参数提取优化** - 正确解析嵌套的请求结构
3. **日志增强** - 详细记录请求参数和处理过程
4. **错误处理改进** - 更好的异常处理机制

### API端点：
- `POST /ELLM.ELLM-OFFICE.V-1.0/querySources.do` - 搜索接口
- `GET /health` - 健康检查接口

## 测试结果

### 完整版测试结果
```
📊 测试结果汇总
===============================
总测试数: 5
通过数: 5
失败数: 0
通过率: 100.0%

🎉 所有测试都通过了!
```

### 简化版测试结果
```
📊 测试结果汇总
===============================
总测试数: 3
通过数: 3
失败数: 0
通过率: 100.0%

🎉 所有测试都通过了!
```

## 使用指南

### 环境准备
1. 确保项目虚拟环境已激活
2. 安装必要依赖：requests, fastapi, uvicorn

### 运行Mock服务
```bash
cd middlewares/search
python mock_search_api.py
```

### 运行测试
```bash
# 基础测试
python test_custom_search_simple.py

# 完整测试
python test_custom_search.py --comprehensive
```

### 环境变量配置（可选）
```bash
export CUSTOM_SEARCH_API_URL="http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"
export CUSTOM_SEARCH_REPOSITORY="your-repository"
export CUSTOM_SEARCH_CHANNEL_ID="your-channel-id"
export MUWP_USER_NAME="用户名"
# ... 其他配置
```

## 验证的核心功能

1. **搜索工具创建** ✅
2. **配置参数加载** ✅
3. **API请求构建** ✅
4. **HTTP请求发送** ✅
5. **响应数据解析** ✅
6. **结果排序和过滤** ✅
7. **错误处理机制** ✅
8. **Mock服务集成** ✅

## 注意事项

1. Mock服务需要在8010端口运行
2. 测试脚本会自动设置必要的环境变量
3. 错误情况下会返回友好的提示信息
4. 支持同时测试多个查询场景

## 扩展性

测试脚本设计为模块化，易于扩展：
- 可添加新的测试用例
- 支持不同的Mock数据
- 可配置不同的API端点
- 易于集成到CI/CD流程

完成的测试脚本为自定义搜索工具提供了全面的验证，确保功能正确性和稳定性。