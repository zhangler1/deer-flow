#!/bin/bash

# DeerFlow API 接口测试脚本
# 用于快速测试所有 API 接口

# 颜色定义
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
BASE_URL="${DEERFLOW_URL:-http://localhost:8000}"
OUTPUT_DIR="./api_test_results"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DeerFlow API 接口测试工具${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${PURPLE}服务地址: ${BASE_URL}${NC}"
echo ""

# 函数：打印测试标题
print_test() {
    echo -e "\n${YELLOW}>>> 测试: $1${NC}"
}

# 函数：打印成功
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 函数：打印失败
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 测试菜单
show_menu() {
    echo -e "\n${GREEN}请选择要测试的接口:${NC}"
    echo "1. 核心研究接口"
    echo "   1.1 流式聊天接口 (/api/chat/stream)"
    echo "   1.2 简化流式研究接口 (/api/research/simple/stream)"
    echo "   1.3 OpenAI兼容流式接口 (/api/research/simple/stream/openai)"
    echo ""
    echo "2. 内容生成接口"
    echo "   2.1 PPT生成接口 (/api/ppt/generate)"
    echo "   2.2 提示词增强接口 (/api/prompt/enhance)"
    echo ""
    echo "3. 配置管理接口"
    echo "   3.1 系统配置接口 (/api/config)"
    echo "   3.2 RAG配置接口 (/api/rag/config)"
    echo "   3.3 RAG资源接口 (/api/rag/resources)"
    echo ""
    echo "4. 智能路由测试（4种路径）"
    echo "   4.1 Direct Answer 路径"
    echo "   4.2 Simple Search 路径"
    echo "   4.3 Domain Knowledge 路径"
    echo "   4.4 Deep Research 路径"
    echo ""
    echo "0. 运行所有测试"
    echo "q. 退出"
    echo ""
}

# ============================================
# 核心研究接口测试
# ============================================

test_chat_stream() {
    print_test "流式聊天接口 - /api/chat/stream"
    
    local output="$OUTPUT_DIR/chat_stream.txt"
    
    curl -N -X POST "${BASE_URL}/api/chat/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "什么是人工智能？请简要介绍。"
                }
            ],
            "search_engine": "tavily",
            "max_step_num": 2,
            "auto_accepted_plan": true
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
    else
        print_error "测试失败"
    fi
}

test_simple_stream() {
    print_test "简化流式研究接口 - /api/research/simple/stream"
    
    local output="$OUTPUT_DIR/simple_stream.txt"
    
    curl -N -X POST "${BASE_URL}/api/research/simple/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "2024年人工智能发展趋势"
                }
            ],
            "search_engine": "tavily",
            "max_search_results": 3,
            "auto_accepted_plan": true
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
    else
        print_error "测试失败"
    fi
}

test_openai_stream() {
    print_test "OpenAI兼容流式接口 - /api/research/simple/stream/openai"
    
    local output="$OUTPUT_DIR/openai_stream.txt"
    
    curl -N -X POST "${BASE_URL}/api/research/simple/stream/openai" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "介绍一下区块链技术"
                }
            ],
            "search_engine": "tavily",
            "auto_accepted_plan": true
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
    else
        print_error "测试失败"
    fi
}

# ============================================
# 内容生成接口测试
# ============================================

test_ppt_generate() {
    print_test "PPT生成接口 - /api/ppt/generate"
    
    local output="$OUTPUT_DIR/generated.pptx"
    
    curl -X POST "${BASE_URL}/api/ppt/generate" \
        -H "Content-Type: application/json" \
        -d '{
            "content": "# AI发展趋势报告\n\n## 概述\n人工智能正在快速发展\n\n## 关键技术\n- 深度学习\n- 强化学习\n- 大语言模型\n\n## 应用领域\n- 自然语言处理\n- 计算机视觉\n- 智能推荐"
        }' \
        --output "$output" \
        2>/dev/null
    
    if [ -f "$output" ] && [ -s "$output" ]; then
        print_success "PPT生成成功，保存到: $output"
        ls -lh "$output"
    else
        print_error "PPT生成失败"
    fi
}

test_prompt_enhance() {
    print_test "提示词增强接口 - /api/prompt/enhance"
    
    local output="$OUTPUT_DIR/prompt_enhance.json"
    
    curl -X POST "${BASE_URL}/api/prompt/enhance" \
        -H "Content-Type: application/json" \
        -d '{
            "prompt": "AI 发展",
            "context": "需要写一份学术报告",
            "report_style": "academic"
        }' \
        2>/dev/null | tee "$output" | jq .
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
        echo -e "\n${PURPLE}增强后的提示词:${NC}"
        jq -r '.result' "$output"
    else
        print_error "测试失败"
    fi
}

# ============================================
# 配置管理接口测试
# ============================================

test_config() {
    print_test "系统配置接口 - /api/config"
    
    local output="$OUTPUT_DIR/config.json"
    
    curl -X GET "${BASE_URL}/api/config" \
        -H "Content-Type: application/json" \
        2>/dev/null | tee "$output" | jq .
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
        echo -e "\n${PURPLE}配置摘要:${NC}"
        echo "RAG Provider: $(jq -r '.rag.provider' "$output")"
        echo "Models: $(jq -r '.models | length' "$output") 个"
        echo "Search Repositories: $(jq -r '.custom_search_repositories | length' "$output") 个"
    else
        print_error "测试失败"
    fi
}

test_rag_config() {
    print_test "RAG配置接口 - /api/rag/config"
    
    local output="$OUTPUT_DIR/rag_config.json"
    
    curl -X GET "${BASE_URL}/api/rag/config" \
        -H "Content-Type: application/json" \
        2>/dev/null | tee "$output" | jq .
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
    else
        print_error "测试失败"
    fi
}

test_rag_resources() {
    print_test "RAG资源接口 - /api/rag/resources"
    
    local output="$OUTPUT_DIR/rag_resources.json"
    
    curl -X GET "${BASE_URL}/api/rag/resources" \
        -H "Content-Type: application/json" \
        2>/dev/null | tee "$output" | jq .
    
    if [ -s "$output" ]; then
        print_success "测试完成，结果保存到: $output"
        echo -e "\n${PURPLE}资源数量:${NC} $(jq -r '.resources | length' "$output")"
    else
        print_error "测试失败"
    fi
}

# ============================================
# 智能路由测试（4种路径）
# ============================================

test_direct_answer() {
    print_test "智能路由 - Direct Answer 路径"
    echo -e "${PURPLE}场景: 通用知识问题，不走检索${NC}"
    
    local output="$OUTPUT_DIR/route_direct_answer.txt"
    
    curl -N -X POST "${BASE_URL}/api/chat/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "什么是汽车？"
                }
            ]
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "Direct Answer 路径测试完成"
        echo -e "${PURPLE}预期: 系统应直接回答，不进行搜索${NC}"
    else
        print_error "测试失败"
    fi
}

test_simple_search() {
    print_test "智能路由 - Simple Search 路径"
    echo -e "${PURPLE}场景: 常规业务问题，单次检索${NC}"
    
    local output="$OUTPUT_DIR/route_simple_search.txt"
    
    curl -N -X POST "${BASE_URL}/api/chat/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "信用卡如何申请？"
                }
            ],
            "search_engine": "custom_search"
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "Simple Search 路径测试完成"
        echo -e "${PURPLE}预期: 系统应进行一次搜索后回答${NC}"
    else
        print_error "测试失败"
    fi
}

test_domain_knowledge() {
    print_test "智能路由 - Domain Knowledge 路径"
    echo -e "${PURPLE}场景: 专业领域问题，使用知识库${NC}"
    
    local output="$OUTPUT_DIR/route_domain_knowledge.txt"
    
    curl -N -X POST "${BASE_URL}/api/chat/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "SWIFT报文MT103的字段详细说明"
                }
            ]
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "Domain Knowledge 路径测试完成"
        echo -e "${PURPLE}预期: 系统应使用专业知识库回答${NC}"
    else
        print_error "测试失败"
    fi
}

test_deep_research() {
    print_test "智能路由 - Deep Research 路径"
    echo -e "${PURPLE}场景: 复杂研究任务，完整流程${NC}"
    
    local output="$OUTPUT_DIR/route_deep_research.txt"
    
    curl -N -X POST "${BASE_URL}/api/chat/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {
                    "role": "user",
                    "content": "分析金融科技对传统银行的影响趋势"
                }
            ],
            "max_step_num": 5,
            "auto_accepted_plan": true,
            "enable_background_investigation": true
        }' \
        2>/dev/null | tee "$output"
    
    if [ -s "$output" ]; then
        print_success "Deep Research 路径测试完成"
        echo -e "${PURPLE}预期: 系统应通过coordinator进入深度研究流程${NC}"
    else
        print_error "测试失败"
    fi
}

# ============================================
# 综合测试
# ============================================

run_all_tests() {
    print_test "运行所有接口测试"
    
    echo -e "\n${GREEN}=== 1. 核心研究接口 ===${NC}"
    test_chat_stream
    sleep 2
    test_simple_stream
    sleep 2
    test_openai_stream
    sleep 2
    
    echo -e "\n${GREEN}=== 2. 内容生成接口 ===${NC}"
    test_ppt_generate
    sleep 1
    test_prompt_enhance
    sleep 1
    
    echo -e "\n${GREEN}=== 3. 配置管理接口 ===${NC}"
    test_config
    sleep 1
    test_rag_config
    sleep 1
    test_rag_resources
    sleep 1
    
    echo -e "\n${GREEN}=== 4. 智能路由测试 ===${NC}"
    test_direct_answer
    sleep 2
    test_simple_search
    sleep 2
    test_domain_knowledge
    sleep 2
    test_deep_research
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}所有测试完成！${NC}"
    echo -e "${PURPLE}结果已保存到: $OUTPUT_DIR${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# ============================================
# 主程序
# ============================================

main() {
    # 检查服务是否可用
    if ! curl -s "${BASE_URL}/api/config" > /dev/null 2>&1; then
        print_error "无法连接到 DeerFlow 服务: ${BASE_URL}"
        echo "请确保服务正在运行"
        exit 1
    fi
    
    print_success "DeerFlow 服务连接成功"
    
    # 检查依赖
    if ! command -v jq &> /dev/null; then
        print_error "未安装 jq，某些功能可能无法正常显示"
        echo "安装方法: sudo apt-get install jq"
    fi
    
    # 交互模式
    if [ $# -eq 0 ]; then
        while true; do
            show_menu
            read -p "请输入选项: " choice
            
            case $choice in
                1.1) test_chat_stream ;;
                1.2) test_simple_stream ;;
                1.3) test_openai_stream ;;
                2.1) test_ppt_generate ;;
                2.2) test_prompt_enhance ;;
                3.1) test_config ;;
                3.2) test_rag_config ;;
                3.3) test_rag_resources ;;
                4.1) test_direct_answer ;;
                4.2) test_simple_search ;;
                4.3) test_domain_knowledge ;;
                4.4) test_deep_research ;;
                0) run_all_tests ;;
                q|Q) 
                    echo -e "${GREEN}退出测试工具${NC}"
                    exit 0
                    ;;
                *)
                    print_error "无效选项，请重新选择"
                    ;;
            esac
            
            echo ""
            read -p "按回车键继续..."
        done
    else
        # 命令行模式
        case $1 in
            all) run_all_tests ;;
            chat) test_chat_stream ;;
            simple) test_simple_stream ;;
            openai) test_openai_stream ;;
            ppt) test_ppt_generate ;;
            prompt) test_prompt_enhance ;;
            config) test_config ;;
            rag-config) test_rag_config ;;
            rag-resources) test_rag_resources ;;
            route-direct) test_direct_answer ;;
            route-simple) test_simple_search ;;
            route-domain) test_domain_knowledge ;;
            route-deep) test_deep_research ;;
            *)
                echo "用法: $0 [all|chat|simple|openai|ppt|prompt|config|rag-config|rag-resources|route-direct|route-simple|route-domain|route-deep]"
                echo "或直接运行不带参数进入交互模式"
                exit 1
                ;;
        esac
    fi
}

# 运行主程序
main "$@"
