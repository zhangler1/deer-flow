# Mock Search API

这是一个简单的mock服务，用于模拟搜索API的响应。该服务基于FastAPI框架实现，提供与原始API相同的接口和固定的响应内容。

## 功能特点
- 提供与原始搜索API相同的接口路径
- 返回固定的mock数据（基于response.json）
- 支持跨域请求
- 包含健康检查端点

## 使用方法

### 1. 安装依赖

```bash
pip install fastapi uvicorn
```

### 2. 启动服务

有两种方式启动服务：

#### 方式一：直接运行Python脚本

```bash
python mock_search_api.py
```

#### 方式二：使用启动脚本（推荐）

```bash
chmod +x start_mock.sh
./start_mock.sh
```

服务将在 `http://0.0.0.0:8000` 启动。

### 3. 访问API

接口地址：
- 查询接口：`http://localhost:8000/ELLM.ELLM-OFFICE.V-1.0/querySources.do`
- 健康检查：`http://localhost:8000/health`

### 4. 修改请求脚本

要使用这个mock服务，您需要修改 `request.sh` 文件中的URL，将其指向本地服务：

```bash
# 将原来的URL
--url http://12.244.66.225/ELLM.ELLM-OFFICE.V-1.0/querySources.do \

# 修改为
--url http://localhost:8000/ELLM.ELLM-OFFICE.V-1.0/querySources.do \
```

## 自定义响应内容

如果需要修改mock响应内容，可以编辑 `mock_search_api.py` 文件中的 `MOCK_RESPONSE` 变量。

## 注意事项
- 这个mock服务是独立的，不需要与项目中的其他服务集成
- 服务默认监听在所有网络接口的8000端口
- 如果8000端口已被占用，可以修改 `mock_search_api.py` 文件中的端口号