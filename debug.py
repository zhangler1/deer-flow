#!/usr/bin/env python3
"""节点输入输出调试脚本"""

import logging
from src.workflow import run_agent_workflow_async

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

async def debug_workflow():
    # 测试查询
    query = "f1赛车是如何制造和生产的请搜索资料回答问题"
    
    # 启用调试模式
    result = await run_agent_workflow_async(
        user_input=query,
        debug=True,  # 启用调试
        max_plan_iterations=1,
        max_step_num=3
    )
    
    print(f"最终结果: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_workflow())