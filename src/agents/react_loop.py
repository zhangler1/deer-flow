# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
ReactLoop - 可控的 ReAct 循环引擎

替代 langgraph.prebuilt.create_react_agent，提供：
1. 中间件链机制（before_loop / before_model / after_model / after_tool / after_loop）
2. 硬限制（max_iterations 达到后强制总结）
3. 与现有 agent.ainvoke(input, config) 接口完全兼容

所有控制逻辑（循环检测、软提示、上下文压缩）均通过中间件实现。
ReactLoop 本身只是纯粹的循环引擎 + 回调机制。
"""

import logging
import time
from typing import Any, Callable, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agents.middleware import ReactMiddleware

logger = logging.getLogger(__name__)


class ReactLoop:
    """可控的 ReAct Agent 循环引擎
    
    ReactLoop 只负责：
    1. LLM 调用循环
    2. 工具执行
    3. 中间件链调度
    4. 硬上限保护 + 强制总结
    
    所有控制逻辑（循环检测、软提示、压缩）通过中间件实现。
    on_before_model / on_after_model 为轻量级回调机制（逃生舱）。
    
    Usage:
        agent = ReactLoop(
            model=chat_model,
            tools=tools,
            prompt=prompt_fn,
            middlewares=[LoopDetectionMiddleware(), ...],
            max_iterations=8,
        )
        result = await agent.ainvoke(input={"messages": [...]}, config={...})
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        tools: list,
        prompt: Optional[Callable] = None,
        *,
        max_iterations: int = 8,
        middlewares: Optional[list[ReactMiddleware]] = None,
        on_before_model: Optional[Callable] = None,
        on_after_model: Optional[Callable] = None,
    ):
        """
        Args:
            model: LLM 模型实例（BaseChatModel）
            tools: 工具列表
            prompt: 可选的 prompt 函数，接收 state dict，返回消息列表作为前缀
            max_iterations: 最大迭代次数（硬上限）
            middlewares: 中间件列表，按顺序执行
            on_before_model: 轻量级回调 fn(messages, iteration, context) -> messages|None
            on_after_model: 轻量级回调 fn(response, iteration, context) -> bool|None
        """
        # bind_tools 让 LLM 知道有哪些工具可用
        self.model = model.bind_tools(tools) if tools else model
        self.raw_model = model  # 保留未绑定工具的模型（用于最终总结）
        self.tools = {t.name: t for t in tools}
        self.tool_list = tools
        self.prompt = prompt
        
        # 控制参数
        self.max_iterations = max_iterations
        
        # 中间件链
        self.middlewares: list[ReactMiddleware] = middlewares or []
        
        # 轻量级回调（逃生舱，不想写中间件时用）
        self.on_before_model = on_before_model
        self.on_after_model = on_after_model
    
    async def ainvoke(self, input: dict, config: dict = None) -> dict:
        """异步执行 ReAct 循环
        
        与 create_react_agent 返回的 CompiledGraph.ainvoke 接口兼容:
            input: {"messages": [...]}
            config: {"recursion_limit": N}  (会被忽略，使用自身的 max_iterations)
            
        Returns:
            {"messages": [...所有消息...]}
        """
        messages = list(input.get("messages", []))
        
        # 应用 prompt（如果有）
        if self.prompt and callable(self.prompt):
            try:
                prompt_messages = self.prompt(input)
                if prompt_messages and isinstance(prompt_messages, list):
                    messages = prompt_messages + messages
            except Exception as e:
                logger.warning(f"⚠️ prompt 函数执行失败: {e}")
        
        context = {
            "tool_calls_count": 0,
            "iterations": 0,
            "start_time": time.time(),
            "max_iterations": self.max_iterations,
        }
        
        forced_final = False  # 标记是否需要强制最终总结
        
        # === 中间件: before_loop ===
        messages = await self._run_middleware_before_loop(messages, context)
        
        for iteration in range(self.max_iterations):
            context["iterations"] = iteration
            
            # === 中间件: before_model ===
            messages = await self._run_middleware_before_model(messages, iteration, context)
            # === 轻量级回调: on_before_model ===
            messages = self._call_on_before_model(messages, iteration, context)
            
            # === LLM 调用 ===
            try:
                response: AIMessage = await self.model.ainvoke(messages)
            except Exception as e:
                logger.error(f"❌ ReactLoop LLM 调用失败 (第{iteration+1}轮): {e}")
                raise
            
            messages.append(response)
            
            # 没有 tool_calls → 自然结束
            if not response.tool_calls:
                logger.info(f"✅ ReactLoop 自然结束 | 第 {iteration+1} 轮 | LLM 未请求工具调用")
                break
            
            # === 中间件: after_model ===
            middleware_stop = await self._run_middleware_after_model(response, messages, iteration, context)
            # === 轻量级回调: on_after_model ===
            callback_stop = self._call_on_after_model(response, iteration, context)
            
            if middleware_stop or callback_stop:
                logger.warning(f"🛑 ReactLoop 强制停止 | 第 {iteration+1} 轮 | middleware={middleware_stop}, callback={callback_stop}")
                forced_final = True
                break
            
            # === 执行工具 ===
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                
                context["tool_calls_count"] += 1
                
                if tool_name in self.tools:
                    try:
                        result = await self.tools[tool_name].ainvoke(tool_args)
                    except Exception as e:
                        logger.warning(f"⚠️ 工具 {tool_name} 执行异常: {e}")
                        result = f"工具执行错误: {type(e).__name__}: {str(e)[:300]}"
                else:
                    logger.warning(f"⚠️ 未知工具: {tool_name}")
                    result = f"错误: 未知工具 '{tool_name}'，可用工具: {list(self.tools.keys())}"
                
                tool_msg = ToolMessage(
                    content=str(result) if result else "工具执行完成（无返回内容）",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
                messages.append(tool_msg)
                tool_results.append(tool_msg)
            
            # === 中间件: after_tool ===
            messages = await self._run_middleware_after_tool(messages, tool_results, iteration, context)
            
        else:
            # for-else: 达到 max_iterations 但未 break
            logger.warning(
                f"⚠️ ReactLoop 达到最大迭代 {self.max_iterations} 次 | "
                f"总工具调用: {context['tool_calls_count']}"
            )
            forced_final = True
        
        # === 强制最终总结（如果被强制停止或达到上限） ===
        if forced_final:
            messages = await self._force_final_answer(messages, context)
        
        # === 中间件: after_loop ===
        messages = await self._run_middleware_after_loop(messages, context)
        
        elapsed = time.time() - context["start_time"]
        logger.info(
            f"📊 ReactLoop 完成 | 迭代: {context['iterations']+1}/{self.max_iterations} | "
            f"工具调用: {context['tool_calls_count']} | 耗时: {elapsed:.2f}s | "
            f"中间件: {[m.name for m in self.middlewares]}"
        )
        
        return {"messages": messages}
    
    def invoke(self, input: dict, config: dict = None) -> dict:
        """同步执行（兼容同步调用场景）"""
        import asyncio
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 已在事件循环中（如 Jupyter 或嵌套调用），创建新线程执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self.ainvoke(input, config))
                return future.result()
        else:
            return asyncio.run(self.ainvoke(input, config))
    
    # ============================================================
    # 中间件链执行方法
    # ============================================================
    
    async def _run_middleware_before_loop(self, messages: list, context: dict) -> list:
        """执行所有中间件的 before_loop 钩子"""
        for mw in self.middlewares:
            try:
                messages = await mw.before_loop(messages, context)
            except Exception as e:
                logger.warning(f"⚠️ 中间件 {mw.name}.before_loop 异常: {e}")
        return messages
    
    async def _run_middleware_before_model(self, messages: list, iteration: int, context: dict) -> list:
        """执行所有中间件的 before_model 钩子"""
        for mw in self.middlewares:
            try:
                messages = await mw.before_model(messages, iteration, context)
            except Exception as e:
                logger.warning(f"⚠️ 中间件 {mw.name}.before_model 异常 (第{iteration+1}轮): {e}")
        return messages
    
    async def _run_middleware_after_model(
        self, response: AIMessage, messages: list, iteration: int, context: dict
    ) -> bool:
        """执行所有中间件的 after_model 钩子，任一返回 True 则强制停止"""
        for mw in self.middlewares:
            try:
                should_stop = await mw.after_model(response, messages, iteration, context)
                if should_stop:
                    logger.info(f"🛑 中间件 {mw.name}.after_model 要求停止 (第{iteration+1}轮)")
                    return True
            except Exception as e:
                logger.warning(f"⚠️ 中间件 {mw.name}.after_model 异常 (第{iteration+1}轮): {e}")
        return False
    
    async def _run_middleware_after_tool(
        self, messages: list, tool_results: list, iteration: int, context: dict
    ) -> list:
        """执行所有中间件的 after_tool 钩子"""
        for mw in self.middlewares:
            try:
                messages = await mw.after_tool(messages, tool_results, iteration, context)
            except Exception as e:
                logger.warning(f"⚠️ 中间件 {mw.name}.after_tool 异常 (第{iteration+1}轮): {e}")
        return messages
    
    async def _run_middleware_after_loop(self, messages: list, context: dict) -> list:
        """执行所有中间件的 after_loop 钩子"""
        for mw in self.middlewares:
            try:
                messages = await mw.after_loop(messages, context)
            except Exception as e:
                logger.warning(f"⚠️ 中间件 {mw.name}.after_loop 异常: {e}")
        return messages
    
    # ============================================================
    # 轻量级回调（逃生舱）
    # ============================================================
    
    def _call_on_before_model(self, messages: list, iteration: int, context: dict) -> list:
        """调用 on_before_model 回调（如果有）"""
        if self.on_before_model:
            try:
                result = self.on_before_model(messages, iteration, context)
                if result is not None:
                    messages = result
            except Exception as e:
                logger.warning(f"⚠️ on_before_model 回调异常: {e}")
        return messages
    
    def _call_on_after_model(self, response: AIMessage, iteration: int, context: dict) -> bool:
        """调用 on_after_model 回调（如果有），返回 True 表示要求停止"""
        if self.on_after_model:
            try:
                result = self.on_after_model(response, iteration, context)
                if result:
                    return True
            except Exception as e:
                logger.warning(f"⚠️ on_after_model 回调异常: {e}")
        return False
    
    async def _force_final_answer(self, messages: list, context: dict) -> list:
        """强制 LLM 输出最终答案（不带工具绑定）
        
        当达到上限或检测到循环时，使用不绑定工具的模型
        强制 LLM 只能输出文本答案。
        """
        messages.append(HumanMessage(
            content=(
                "⚠️ 系统指令：你已达到工具调用上限或检测到重复调用。"
                "请立即停止所有工具调用，直接基于你已经收集到的所有信息，"
                "输出完整、结构化的最终研究结果。"
                "不要再尝试调用任何工具。"
            ),
            name="system",
        ))
        
        try:
            # 使用不绑定工具的模型，确保 LLM 只能输出文本
            final_response = await self.raw_model.ainvoke(messages)
            messages.append(final_response)
            logger.info(f"✅ ReactLoop 强制总结完成 | 响应长度: {len(final_response.content or '')}")
        except Exception as e:
            logger.error(f"❌ ReactLoop 强制总结失败: {e}")
            # 兜底：构造一个最小响应
            messages.append(AIMessage(
                content=f"⚠️ 由于工具调用达到上限且总结失败，请参考前述工具返回的信息。错误: {str(e)[:100]}"
            ))
        
        return messages
    
    # ============================================================
    # 属性
    # ============================================================
    
    @property
    def name(self) -> str:
        """兼容属性：某些地方可能检查 agent.name"""
        return "react_loop"
    
    def __repr__(self) -> str:
        return (
            f"ReactLoop(model={getattr(self.model, 'model_name', '?')}, "
            f"tools={list(self.tools.keys())}, "
            f"max_iterations={self.max_iterations})"
        )
