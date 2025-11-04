#!/bin/bash
# DeerFlow 4种路径智能路由系统 - curl 测试脚本

# 终端颜色（绿色+紫色配色）
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

API_BASE_URL="http://localhost:8000"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DeerFlow 4种路径智能路由系统测试${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 测试1: 直接回答路径
echo -e "${PURPLE}【测试 1/4】直接回答路径 - 通用常识${NC}"
echo -e "${GREEN}查询: 什么是汽车？${NC}"
echo -e "${GREEN}期望路径: direct_answer${NC}"
echo ""

curl -X POST "$API_BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "什么是汽车？"
      }
    ],
    "thread_id": "test_direct_answer",
    "max_plan_iterations": 1,
    "max_step_num": 2,
    "max_search_results": 3,
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }' 2>&1 | head -50

echo -e "\n${GREEN}================================${NC}\n"
sleep 2

# 测试2: 简单检索路径（主流）
echo -e "${PURPLE}【测试 2/4】简单检索路径 - 银行业务（主流）${NC}"
echo -e "${GREEN}查询: 信用卡如何申请？${NC}"
echo -e "${GREEN}期望路径: simple_search${NC}"
echo ""

curl -X POST "$API_BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "信用卡如何申请？"
      }
    ],
    "thread_id": "test_simple_search",
    "max_plan_iterations": 1,
    "max_step_num": 2,
    "max_search_results": 3,
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }' 2>&1 | head -50

echo -e "\n${GREEN}================================${NC}\n"
sleep 2

# 测试3: 深度研究路径
echo -e "${PURPLE}【测试 3/4】深度研究路径 - 复杂分析${NC}"
echo -e "${GREEN}查询: 分析金融科技对传统银行的影响${NC}"
echo -e "${GREEN}期望路径: deep_research${NC}"
echo ""

curl -X POST "$API_BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "分析金融科技对传统银行的影响趋势"
      }
    ],
    "thread_id": "test_deep_research",
    "max_plan_iterations": 1,
    "max_step_num": 2,
    "max_search_results": 3,
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }' 2>&1 | head -50

echo -e "\n${GREEN}================================${NC}\n"
sleep 2

# 测试4: 领域知识路径
echo -e "${PURPLE}【测试 4/4】领域知识路径 - 专业知识${NC}"
echo -e "${GREEN}查询: SWIFT报文MT103字段说明${NC}"
echo -e "${GREEN}期望路径: domain_knowledge${NC}"
echo ""

curl -X POST "$API_BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "SWIFT报文MT103的字段详细说明"
      }
    ],
    "thread_id": "test_domain_knowledge",
    "max_plan_iterations": 1,
    "max_step_num": 2,
    "max_search_results": 3,
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }' 2>&1 | head -50

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}测试完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${PURPLE}提示：${NC}"
echo -e "${GREEN}1. 查看服务端日志以获取详细的路由决策信息${NC}"
echo -e "${GREEN}2. 路由路径关键字段：routing_path, langgraph_node${NC}"
echo -e "${GREEN}3. 4种路径：direct_answer, simple_search, deep_research, domain_knowledge${NC}"
echo ""
