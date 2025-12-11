#!/bin/bash
# 测试 researcher 智能体工具调用的快速测试脚本

echo "=========================================="
echo "  测试 Researcher 智能体工具调用能力"
echo "=========================================="
echo ""

echo "1️⃣  运行单元测试 - 测试智能体是否正确接收工具"
echo "命令: pytest tests/unit/agents/test_researcher_agent.py -v"
echo ""

echo "2️⃣  运行集成测试 - 测试 researcher_node 工具配置"
echo "命令: pytest tests/integration/test_researcher_node_tools.py -v"
echo ""

echo "3️⃣  测试所有 researcher 相关功能"
echo "命令: pytest -k researcher -v"
echo ""

echo "4️⃣  查看测试覆盖率"
echo "命令: pytest tests/unit/agents/test_researcher_agent.py --cov=src.agents --cov-report=term-missing"
echo ""

echo "=========================================="
echo "选择要运行的测试:"
echo "  1 - 单元测试"
echo "  2 - 集成测试"
echo "  3 - 所有 researcher 测试"
echo "  4 - 查看覆盖率"
echo "  5 - 运行所有测试"
echo "=========================================="

read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo "运行单元测试..."
        uv run pytest tests/unit/agents/test_researcher_agent.py -v
        ;;
    2)
        echo "运行集成测试..."
        uv run pytest tests/integration/test_researcher_node_tools.py -v
        ;;
    3)
        echo "运行所有 researcher 测试..."
        uv run pytest -k researcher -v
        ;;
    4)
        echo "查看覆盖率..."
        uv run pytest tests/unit/agents/test_researcher_agent.py --cov=src.agents --cov-report=term-missing
        ;;
    5)
        echo "运行所有测试..."
        uv run pytest tests/unit/agents/test_researcher_agent.py tests/integration/test_researcher_node_tools.py -v
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
