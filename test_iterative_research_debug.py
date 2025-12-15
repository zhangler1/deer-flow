#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迭代研究节点调试测试脚本

使用方法：
    python test_iterative_research_debug.py

功能：
    - 强制跳过智能分类，直接路由到 iterative_research_node
    - 测试迭代研究节点的完整功能
    - 查看详细的执行日志
"""

import asyncio
import logging
from langchain_core.messages import HumanMessage
from src.graph.builder import build_graph
from src.config.configuration import get_recursion_limit
from src.utils.enhanced_logger import setup_enhanced_logging, get_enhanced_logger

# 设置日志
setup_enhanced_logging(level=logging.INFO, enable_colors=True)
logger = get_enhanced_logger("test.iterative_research")

# 测试查询
TEST_QUERIES = [
    "详细解释一下量子计算的工作原理",
    "深入分析人工智能在金融领域的应用",
    "全面介绍区块链技术的底层机制",
]


async def test_iterative_research_node(query: str, max_iterations: int = 3):
    """
    测试迭代研究节点
    
    Args:
        query: 测试查询
        max_iterations: 最大迭代次数
    """
    logger.logger.info(f"\n{'='*80}")
    logger.logger.info(f"🧪 开始测试迭代研究节点")
    logger.logger.info(f"📝 查询: {query}")
    logger.logger.info(f"🔢 最大迭代次数: {max_iterations}")
    logger.logger.info(f"{'='*80}\n")
    
    # 构建工作流
    graph = build_graph()
    
    # 准备输入（关键：设置 force_routing_path）
    workflow_input = {
        "messages": [HumanMessage(content=query)],
        "research_topic": query,
        "plan_iterations": 0,
        "final_report": "",
        "current_plan": None,
        "observations": [],
        "iteration_count": 0,
        "iteration_history": [],
        # 🐛 调试模式：强制路由到迭代研究节点
        "force_routing_path": "iterative_research",
    }
    
    # 配置
    workflow_config = {
        "configurable": {
            "max_iteration": max_iterations,
            "max_search_results": 3,
            "search_engine": "custom_search",
        },
        "recursion_limit": get_recursion_limit(),
    }
    
    try:
        logger.logger.info("🚀 开始执行工作流...")
        
        # 执行工作流
        final_state = await graph.ainvoke(workflow_input, workflow_config)
        
        logger.logger.info(f"\n{'='*80}")
        logger.logger.info("✅ 工作流执行完成")
        logger.logger.info(f"{'='*80}\n")
        
        # 输出结果
        logger.logger.info("📊 执行结果:")
        logger.logger.info(f"  - 路由路径: {final_state.get('routing_path', 'unknown')}")
        logger.logger.info(f"  - 迭代次数: {final_state.get('iteration_count', 0)}")
        logger.logger.info(f"  - 最终报告长度: {len(final_state.get('final_report', ''))} 字符")
        
        # 输出迭代历史
        iteration_history = final_state.get('iteration_history', [])
        if iteration_history:
            logger.logger.info(f"\n📜 迭代历史 ({len(iteration_history)} 轮):")
            for i, hist in enumerate(iteration_history, 1):
                logger.logger.info(f"  第 {i} 轮:")
                logger.logger.info(f"    - 查询: {hist.get('query', 'N/A')[:50]}...")
                logger.logger.info(f"    - 回答长度: {len(hist.get('answer', ''))} 字符")
        
        # 输出最终报告
        final_report = final_state.get('final_report', '')
        if final_report:
            logger.logger.info(f"\n📄 最终报告:")
            logger.logger.info(f"{'='*80}")
            logger.logger.info(final_report)
            logger.logger.info(f"{'='*80}\n")
        
        return final_state
        
    except Exception as e:
        logger.logger.error(f"❌ 测试失败: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    logger.logger.info("""
╔════════════════════════════════════════════════════════════════╗
║        迭代研究节点调试测试脚本                                  ║
║                                                                ║
║  功能：                                                         ║
║    - 强制跳过智能分类，直接路由到 iterative_research_node      ║
║    - 测试迭代研究节点的完整功能                                 ║
║    - 查看详细的执行日志                                         ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # 选择测试查询
    print("\n可用的测试查询:")
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"  {i}. {query}")
    
    try:
        choice = input(f"\n请选择测试查询 (1-{len(TEST_QUERIES)}) 或输入自定义查询: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(TEST_QUERIES):
            query = TEST_QUERIES[int(choice) - 1]
        else:
            query = choice if choice else TEST_QUERIES[0]
        
        max_iterations = input("请输入最大迭代次数 (默认 3): ").strip()
        max_iterations = int(max_iterations) if max_iterations.isdigit() else 3
        
        # 执行测试
        await test_iterative_research_node(query, max_iterations)
        
        logger.logger.info("\n✅ 测试完成！")
        
    except KeyboardInterrupt:
        logger.logger.info("\n⚠️ 测试被用户中断")
    except Exception as e:
        logger.logger.error(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
