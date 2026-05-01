#!/bin/bash
# ============================================================================
# PostgreSQL Checkpoint 快速启动和验证脚本
# ============================================================================

set -e

echo "=========================================="
echo "  DeerFlow PostgreSQL Checkpoint 配置"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 检查 Docker 是否运行
echo -e "${YELLOW}[1/5] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 环境正常${NC}"
echo ""

# 2. 检查配置文件
echo -e "${YELLOW}[2/5] 检查配置文件...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env 文件不存在${NC}"
    exit 1
fi

if grep -q "LANGGRAPH_CHECKPOINT_SAVER=true" .env; then
    echo -e "${GREEN}✅ LANGGRAPH_CHECKPOINT_SAVER 已启用${NC}"
else
    echo -e "${RED}❌ LANGGRAPH_CHECKPOINT_SAVER 未启用，请检查 .env 文件${NC}"
    exit 1
fi

if grep -q "LANGGRAPH_CHECKPOINT_DB_URL=postgresql://" .env; then
    echo -e "${GREEN}✅ PostgreSQL 连接字符串已配置${NC}"
else
    echo -e "${RED}❌ PostgreSQL 连接字符串未配置，请检查 .env 文件${NC}"
    exit 1
fi
echo ""

# 3. 启动 PostgreSQL 服务
echo -e "${YELLOW}[3/5] 启动 PostgreSQL 服务...${NC}"
docker-compose up -d postgres

echo "等待 PostgreSQL 启动..."
sleep 5

# 4. 验证 PostgreSQL 连接
echo -e "${YELLOW}[4/5] 验证 PostgreSQL 连接...${NC}"
if docker exec deer-flow-postgres pg_isready -U deerflow &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL 连接成功${NC}"
else
    echo -e "${RED}❌ PostgreSQL 连接失败${NC}"
    echo "查看日志："
    docker logs deer-flow-postgres
    exit 1
fi
echo ""

# 5. 验证数据库和表结构
echo -e "${YELLOW}[5/5] 验证数据库和表结构...${NC}"

# 检查数据库
if docker exec deer-flow-postgres psql -U deerflow -d deerflow_checkpoint -c "SELECT 1" &> /dev/null; then
    echo -e "${GREEN}✅ 数据库 deerflow_checkpoint 存在${NC}"
else
    echo -e "${RED}❌ 数据库 deerflow_checkpoint 不存在${NC}"
    exit 1
fi

# 检查表（需要等待 backend 启动后自动创建）
echo "检查表结构（需要启动 backend 服务后自动创建）..."
echo ""

echo "=========================================="
echo -e "${GREEN}✅ PostgreSQL 配置完成！${NC}"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 启动所有服务："
echo "   docker-compose up -d"
echo ""
echo "2. 查看 PostgreSQL 日志："
echo "   docker logs -f deer-flow-postgres"
echo ""
echo "3. 验证 checkpoint 功能："
echo "   # 第一次请求"
echo "   curl -X POST http://localhost:8000/api/chat/stream \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"messages\": [{\"role\": \"user\", \"content\": \"生成AI报告\"}], \"thread_id\": \"test-001\"}'"
echo ""
echo "   # 第二次请求（关联上下文）"
echo "   curl -X POST http://localhost:8000/api/chat/stream \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"messages\": [{\"role\": \"user\", \"content\": \"基于上次报告补充数据\"}], \"thread_id\": \"test-001\"}'"
echo ""
echo "4. 查询 checkpoint 数据："
echo "   docker exec -it deer-flow-postgres psql -U deerflow -d deerflow_checkpoint"
echo "   \\dt  # 查看所有表"
echo "   SELECT * FROM checkpoints LIMIT 10;  # 查看 checkpoint 数据"
echo ""
echo "=========================================="
