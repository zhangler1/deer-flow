# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
ReactLoop - 可控的 ReAct 循环实现

替代 langgraph.prebuilt.create_react_agent，提供：
1. 每轮循环前/后的钩子拦截
2. 循环检测（重复 tool_calls 哈希）
3. 软提示停止（注入消息让 LLM 主动停止）
4. 硬限制（max_iterations 达到后强制总结）
5. 与现有 agent.ainvoke(input, config) 接口完全兼容
"""

import hashlib
import logging
import time
from typing import Any, Callable, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

logger = logging.getLogger(__name__)


class ReactLoop:
    """可控的 ReAct Agent 循环
    
    用法:
        agent = ReactLoop(
            model=chat_model,
            tools=tools,
            prompt=prompt_fn,
            max_iterations=5,
            warn_at=3,
        )
        result = await agent.ainvoke(input={"messages": [...]}, config={...})
    
    控制机制:
        - max_iterations: 硬上限，达到后强制让 LLM 总结
        - warn_at: 软警告，达到后注入提示消息
        - 循环检测: 相同 tool_calls 组合重复 N 次后强制停止
        - on_before_model: 自定义钩子，每轮 LLM 调用前执行
        - on_after_model: 自定义钩子，每轮 LLM 调用后执行
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        tools: list,
        prompt: Optional[Callable] = None,
        *,
        max_iterations: int = 8,
        warn_at: int = 5,
        loop_detect_threshold: int = 3,
        on_before_model: Optional[Callable] = None,
        on_after_model: Optional[Callable] = None,
    ):
        """
        Args:
            model: LLM 模型实例（BaseChatModel）
            tools: 工具列表
            prompt: 可选的 prompt 函数，接收 state dict，返回消息列表作为前缀
            max_iterations: 最大迭代次数（硬上限）
            warn_at: 第几轮开始注入停止警告
            loop_detect_threshold: 相同 tool_calls 重复多少次判定为循环
            on_before_model: 自定义钩子 fn(messages, iteration, context) -> messages
            on_after_model: 自定义钩子 fn(response, iteration, context) -> bool (True=强制停止)
        """
        # bind_tools 让 LLM 知道有哪些工具可用
        self.model = model.bind_tools(tools) if tools else model
        self.raw_model = model  # 保留未绑定工具的模型（用于最终总结）
        self.tools = {t.name: t for t in tools}
        self.tool_list = tools
        self.prompt = prompt
        
        # 控制参数
        self.max_iterations = max_iterations
        self.warn_at = warn_at
        self.loop_detect_threshold = loop_detect_threshold
        
        # 自定义钩子
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
        
        # 循环检测状态
        tool_call_hashes: list[str] = []
        context = {
            "tool_calls_count": 0,
            "iterations": 0,
            "start_time": time.time(),
        }
        
        forced_final = False  # 标记是否需要强制最终总结
        
        for iteration in range(self.max_iterations):
            context["iterations"] = iteration
            
            # === 钩子1: 循环前 - 软提示 + 自定义逻辑 ===
            messages = self._before_model(messages, iteration, context)
            
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
            
            # === 钩子2: 循环后 - 循环检测 + 自定义逻辑 ===
            should_stop = self._after_model(response, iteration, context, tool_call_hashes)
            
            if should_stop:
                logger.warning(f"🛑 ReactLoop 强制停止 | 第 {iteration+1} 轮 | 原因: 循环检测或自定义钩子")
                forced_final = True
                break
            
            # === 执行工具 ===
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
                
                messages.append(ToolMessage(
                    content=str(result) if result else "工具执行完成（无返回内容）",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
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
        
        elapsed = time.time() - context["start_time"]
        logger.info(
            f"📊 ReactLoop 完成 | 迭代: {context['iterations']+1}/{self.max_iterations} | "
            f"工具调用: {context['tool_calls_count']} | 耗时: {elapsed:.2f}s"
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
    # 内置钩子实现
    # ============================================================
    
    def _before_model(self, messages: list, iteration: int, context: dict) -> list:
        """每轮 LLM 调用前执行
        
        内置行为:
        - 接近上限时注入软停止提示
        
        可通过 on_before_model 扩展
        """
        # 软提示：接近上限时警告 LLM
        if iteration >= self.warn_at:
            remaining = self.max_iterations - iteration
            messages.append(HumanMessage(
                content=(
                    f"⚠️ 系统提示：你已经进行了 {iteration} 轮工具调用（共计 {context['tool_calls_count']} 次工具使用），"
                    f"剩余 {remaining} 轮机会。"
                    f"请尽快基于已收集的信息总结结果，停止继续搜索。"
                    f"如果信息已经足够，请直接输出最终答案。"
                ),
                name="system",
            ))
            logger.info(f"💡 ReactLoop 软提示已注入 | 第 {iteration+1} 轮 | 剩余 {remaining} 轮")
        
        # 调用自定义钩子
        if self.on_before_model:
            try:
                result = self.on_before_model(messages, iteration, context)
                if result is not None:
                    messages = result
            except Exception as e:
                logger.warning(f"⚠️ on_before_model 钩子异常: {e}")
        
        return messages
    
    def _after_model(
        self, response: AIMessage, iteration: int, context: dict, hash_history: list
    ) -> bool:
        """每轮 LLM 响应后执行
        
        内置行为:
        - 循环检测（相同 tool_calls 哈希重复 N 次）
        
        Returns:
            True = 强制停止, False = 继续
        """
        # === 循环检测 ===
        if response.tool_calls:
            # 计算当前轮 tool_calls 的哈希（顺序无关）
            call_signature = self._hash_tool_calls(response.tool_calls)
            hash_history.append(call_signature)
            
            # 检查最近 N 次是否有重复
            recent_window = hash_history[-(self.loop_detect_threshold + 2):]
            repeat_count = recent_window.count(call_signature)
            
            if repeat_count >= self.loop_detect_threshold:
                logger.warning(
                    f"🔄 ReactLoop 循环检测触发 | 第 {iteration+1} 轮 | "
                    f"相同工具调用组合重复 {repeat_count} 次 | "
                    f"工具: {[tc['name'] for tc in response.tool_calls]}"
                )
                return True
        
        # 调用自定义钩子
        if self.on_after_model:
            try:
                result = self.on_after_model(response, iteration, context)
                if result:
                    return True
            except Exception as e:
                logger.warning(f"⚠️ on_after_model 钩子异常: {e}")
        
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
    # 工具方法
    # ============================================================
    
    @staticmethod
    def _hash_tool_calls(tool_calls: list) -> str:
        """生成 tool_calls 的顺序无关哈希
        
        相同的工具+参数组合，无论顺序如何，都会生成相同哈希。
        """
        # 提取 (name, sorted_args_str) 的列表
        signatures = []
        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})
            # 对 args 排序序列化，确保顺序无关
            args_str = str(sorted(args.items())) if isinstance(args, dict) else str(args)
            signatures.append(f"{name}:{args_str}")
        
        # 排序后拼接，确保顺序无关
        combined = "|".join(sorted(signatures))
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
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
