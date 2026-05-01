# Mock 搜索服务镜像
# 用于外网开发时替代内网 bocomsearch / online_search / 行业研报 / 新闻 接口
#
# 构建：  docker build -t deer-flow-mock-search:latest ./middlewares/search
# 运行：  docker compose -f docker-compose.yml -f docker-compose.mock.yml up

FROM python:3.12-slim

WORKDIR /app

# 设置 pip 源加速（如果在外网可选注释）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 关键：强制 Python 无缓冲输出，否则 docker logs 看不到 uvicorn 日志
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# 先装依赖，利用 Docker 层缓存
# 注意：uvicorn[standard] 自带 watchfiles/httptools/websockets，--reload 必需
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.116.1" \
    "uvicorn[standard]>=0.35.0" \
    "watchfiles>=0.21.0" \
    "python-multipart>=0.0.6" \
    "pydantic>=2.11.9"

# 拷贝 Mock 代码（实际部署时会被 volume 覆盖，便于热更新）
COPY . /app

# 4 个 Mock 服务端口
EXPOSE 8010 8011 8012 8013

# 健康检查（仅看 8010 主搜索接口）
# start_period 给 30s，让 4 个 uvicorn 子进程都起来
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=30s \
    CMD python -c "import urllib.request,sys;\
urllib.request.urlopen('http://localhost:8010/health',timeout=3);sys.exit(0)" || exit 1

# 使用统一启动器拉起 4 个服务
CMD ["python", "main.py"]
