#!/usr/bin/env python3
"""
增强日志使用示例和说明

这个文件展示了如何使用新的增强日志系统来跟踪工程中每一步检索、思考和节点跳转。
"""

import asyncio
import logging
from src.workflow import run_agent_workflow_async
from src.utils.enhanced_logger import get_enhanced_logger, setup_enhanced_logging

def main():
    """主函数，演示增强日志功能"""
    
    print("=" * 60)
    print("DeerFlow 增强日志系统演示")
    print("=" * 60)
    
    # 设置增强日志
    setup_enhanced_logging(level=logging.INFO, enable_colors=True)
    
    # 获取日志实例
    demo_logger = get_enhanced_logger('demo')
    
    print("\n📋 增强日志功能特性:")
    print("  🎨 彩色输出 - 前面部分使用绿色，后面部分使用紫色")
    print("  🔄 节点执行跟踪 - 记录每个节点的进入、执行和退出")
    print("  🔧 工具调用记录 - 详细记录工具使用过程和结果")
    print("  🔍 搜索过程跟踪 - 记录每次搜索的查询和结果")
    print("  🧠 LLM思考过程 - 记录AI思考的详细过程")
    print("  🔀 节点跳转日志 - 跟踪工作流程中的决策和跳转")
    print("  📊 工作流程摘要 - 提供执行统计和性能指标")
    
    print("\n🎯 日志标记说明:")
    print("  🚀 WORKFLOW_START - 工作流开始")
    print("  🔄 NODE_ENTRY - 节点进入")
    print("  ✅ NODE_EXIT - 节点退出")
    print("  🔀 NODE_TRANSITION - 节点跳转")
    print("  🔧 TOOL_START/END - 工具调用")
    print("  🔍 SEARCH - 搜索过程")
    print("  🧠 LLM_THINKING - AI思考")
    print("  📋 PLAN_GENERATION - 计划生成")
    print("  🚀 STEP_EXECUTION - 步骤执行")
    print("  📚 RETRIEVAL - 检索过程")
    print("  📊 WORKFLOW_SUMMARY - 工作流摘要")
    print("  🏁 WORKFLOW_COMPLETE - 工作流完成")
    print("  ❌ *_ERROR - 各种错误")
    
    print("\n📖 使用方法:")
    print("1. 调试模式运行:")
    print("   python debug.py")
    print("   python main.py --debug \"你的问题\"")
    
    print("\n2. 正常模式运行:")
    print("   python main.py \"你的问题\"")
    
    print("\n3. 服务器模式查看日志:")
    print("   python server.py --log-level debug")
    
    print("\n🔧 配置说明:")
    print("• 彩色输出：遵循用户偏好，前面使用绿色，后面使用紫色")
    print("• 日志级别：INFO显示主要流程，DEBUG显示详细信息")
    print("• 性能监控：自动计算和记录各步骤的执行时间")
    print("• 会话跟踪：每次执行都有唯一的会话ID")
    
    print("\n💡 示例运行：")
    
    # 演示基本日志功能
    demo_logger.logger.info("🎪 演示开始 - 这是一个增强日志的示例")
    demo_logger.log_search_process("示例查询", "演示搜索", 5)
    demo_logger.log_llm_thinking("演示AI", 1000, 500, 2.5)
    demo_logger.log_workflow_summary(10.5, ["coordinator", "planner", "researcher"], ["search", "crawl"])
    
    print("\n🚀 现在运行一个真实的工作流程示例:")
    
    # 运行一个简单的工作流程示例
    async def run_demo():
        try:
            result = await run_agent_workflow_async(
                user_input="什么是人工智能？请简要介绍。",
                debug=True,  # 启用详细日志
                max_plan_iterations=1,
                max_step_num=2
            )
            print("\n✨ 演示完成！请查看上面的彩色日志输出。")
        except Exception as e:
            print(f"\n❌ 演示过程中出现错误: {e}")
    
    # 运行异步示例
    asyncio.run(run_demo())
    
    print("\n" + "=" * 60)
    print("增强日志系统已成功集成到DeerFlow中！")
    print("现在你可以跟踪每一步检索、思考和节点跳转的详细过程。")
    print("=" * 60)

if __name__ == "__main__":
    main()