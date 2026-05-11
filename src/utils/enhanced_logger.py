# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
增强的日志模块，提供彩色输出和详细的日志记录功能
支持工程中每一步检索、思考和节点跳转的详细跟踪
"""

import logging
import time
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from contextlib import contextmanager


# 从环境变量读取日志级别配置
def get_log_level_from_env() -> int:
    """
    从环境变量获取日志级别
    支持的值: DEBUG, INFO, WARNING, ERROR, CRITICAL
    默认: INFO
    """
    level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(level_str, logging.INFO)


# 全局日志级别
CURRENT_LOG_LEVEL = get_log_level_from_env()


def should_use_colors(enable_colors: bool = True) -> bool:
    """判定控制台日志是否应使用 ANSI 彩色。

    优先级：
    1. 环境变量 NO_COLOR 存在（任意值）或 LOG_COLORS 在 {0,false,no,off} 中 → 强制关闭
    2. LOG_COLORS 在 {1,true,yes,on} 中 → 强制开启
    3. stdout 不是 TTY（被重定向/管道/docker logs 采集）→ 关闭
    4. 其余情况使用传入的 enable_colors 参数
    """
    # NO_COLOR 是行业标准（https://no-color.org/）
    if os.getenv("NO_COLOR") is not None:
        return False

    log_colors = os.getenv("LOG_COLORS", "").strip().lower()
    if log_colors in ("0", "false", "no", "off"):
        return False
    if log_colors in ("1", "true", "yes", "on"):
        return True

    # 非 TTY 环境（重定向或 docker/nohup 采集）自动关闭彩色
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False

    return enable_colors


def should_log(level: int = logging.INFO) -> bool:
    """
    判断是否应该输出日志
    
    Args:
        level: 日志级别 (logging.DEBUG, logging.INFO等)
        
    Returns:
        bool: 如果当前日志级别允许输出，返回True
    """
    return level >= CURRENT_LOG_LEVEL


def console_print(message: str, level: int = logging.INFO):
    """
    带日志级别判断的控制台打印函数
    
    Args:
        message: 要打印的消息
        level: 日志级别
    """
    if should_log(level):
        print(message)


class ColoredFormatter(logging.Formatter):
    """彩色日志格式器，根据用户偏好设置颜色"""
    
    # ANSI色彩代码
    COLORS = {
        'DEBUG': '\033[96m',      # 青色
        'INFO': '\033[92m',       # 绿色 (前面部分)
        'WARNING': '\033[93m',    # 黄色
        'ERROR': '\033[91m',      # 红色
        'CRITICAL': '\033[95m',   # 紫色
        'PURPLE': '\033[35m',     # 紫色 (后面部分)
        'RESET': '\033[0m',       # 重置
        'BOLD': '\033[1m',        # 粗体
    }
    
    def format(self, record):
        # 根据用户偏好：前面部分使用绿色，后面部分使用紫色
        log_color = self.COLORS.get(record.levelname, self.COLORS['INFO'])
        purple_color = self.COLORS['PURPLE']
        reset_color = self.COLORS['RESET']
        bold = self.COLORS['BOLD']
        
        # 格式化时间戳 (绿色)
        timestamp = self.formatTime(record, self.datefmt)
        
        # 格式化日志级别 (绿色)
        level = f"{log_color}[{record.levelname}]{reset_color}"
        
        # 格式化模块名 (绿色)
        module = f"{log_color}{record.name}{reset_color}"
        
        # 格式化消息 (紫色)
        message = f"{purple_color}{record.getMessage()}{reset_color}"
        
        return f"{log_color}{timestamp}{reset_color} {level} {module} {purple_color}|{reset_color} {message}"


class EnhancedLogger:
    """增强的日志记录器，专门用于跟踪工作流程"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.session_id = None
        self.workflow_context = {}
        self.file_handler = None
        
    def setup_enhanced_logging(self, level=logging.INFO, enable_colors=True, log_file=None):
        """设置增强日志
        
        Args:
            level: 日志级别
            enable_colors: 是否启用彩色输出（仅控制台）
            log_file: 日志文件路径，如果为None则不输出到文件
        """
        # 设置控制台输出
        console_handler = logging.StreamHandler()

        use_colors = should_use_colors(enable_colors)
        if use_colors:
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 设置文件输出（如果指定了日志文件）
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # 创建文件处理器
            self.file_handler = logging.FileHandler(
                log_file, 
                mode='a',  # 追加模式
                encoding='utf-8'
            )
            
            # 文件输出使用无颜色格式
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.file_handler.setFormatter(file_formatter)
            self.logger.addHandler(self.file_handler)
            
        self.logger.setLevel(level)
        
        # 禁止日志向父logger传播，避免重复输出
        self.logger.propagate = False
        
    def set_session_context(self, session_id: str, user_query: str):
        """设置会话上下文"""
        self.session_id = session_id
        self.workflow_context = {
            'session_id': session_id,
            'user_query': user_query,
            'start_time': time.time()
        }
        
    def log_node_entry(self, node_name: str, state: Union[Dict[str, Any], object]):
        """记录节点进入"""
        self.logger.info(f"🔄 NODE_ENTRY | {node_name} | 开始执行节点")
        if self.logger.isEnabledFor(logging.DEBUG):
            if hasattr(state, '__dict__'):
                state_dict = state.__dict__
            elif isinstance(state, dict):
                state_dict = state
            else:
                state_dict = {'state': str(state)}
            self.logger.debug(f"🔄 NODE_STATE | {node_name} | 输入状态: {self._format_state(state_dict)}")
            
    def log_node_exit(self, node_name: str, result: Any, duration: float):
        """记录节点退出"""
        self.logger.info(f"✅ NODE_EXIT | {node_name} | 节点执行完成 | 耗时: {duration:.2f}s")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"✅ NODE_RESULT | {node_name} | 输出结果: {self._format_result(result)}")
            
    def log_node_transition(self, from_node: str, to_node: str, reason: str = ""):
        """记录节点跳转"""
        reason_text = f" | 原因: {reason}" if reason else ""
        self.logger.info(f"🔀 NODE_TRANSITION | {from_node} → {to_node}{reason_text}")
        
    def log_tool_call_start(self, tool_name: str, parameters: Dict[str, Any]):
        """记录工具调用开始"""
        self.logger.info(f"🔧 TOOL_START | {tool_name} | 开始调用工具")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"🔧 TOOL_PARAMS | {tool_name} | 参数: {self._format_params(parameters)}")
            
    def log_tool_call_end(self, tool_name: str, result: Any, duration: float):
        """记录工具调用结束"""
        self.logger.info(f"🔧 TOOL_END | {tool_name} | 工具调用完成 | 耗时: {duration:.2f}s")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"🔧 TOOL_RESULT | {tool_name} | 结果: {self._format_result(result)}")
            
    def log_search_process(self, query: str, search_type: str, results_count: int = 0):
        """记录搜索过程"""
        self.logger.info(f"🔍 SEARCH | {search_type} | 查询: '{query}' | 结果数: {results_count}")
        
    def log_llm_thinking(self, agent_name: str, prompt_length: int, response_length: int, duration: float):
        """记录LLM思考过程"""
        self.logger.info(f"🧠 LLM_THINKING | {agent_name} | 提示长度: {prompt_length} | 响应长度: {response_length} | 耗时: {duration:.2f}s")
        
    def log_plan_generation(self, plan_iteration: int, plan_title: str, steps_count: int):
        """记录计划生成"""
        self.logger.info(f"📋 PLAN_GENERATION | 迭代: {plan_iteration} | 标题: '{plan_title}' | 步骤数: {steps_count}")
        
    def log_step_execution(self, step_number: int, step_title: str, step_type: str, agent_name: str):
        """记录步骤执行"""
        self.logger.info(f"🚀 STEP_EXECUTION | 步骤{step_number}: {step_title} | 类型: {step_type} | 执行者: {agent_name}")
        
    def log_retrieval_process(self, resource_count: int, query: str, retrieved_docs: int):
        """记录检索过程"""
        self.logger.info(f"📚 RETRIEVAL | 资源数: {resource_count} | 查询: '{query}' | 检索到文档: {retrieved_docs}")
        
    def log_workflow_summary(self, total_duration: float, nodes_executed: List[str], tools_used: List[str]):
        """记录工作流程摘要"""
        self.logger.info(f"📊 WORKFLOW_SUMMARY | 总耗时: {total_duration:.2f}s | 执行节点: {len(nodes_executed)} | 使用工具: {len(tools_used)}")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"📊 NODES_EXECUTED: {', '.join(nodes_executed)}")
            self.logger.debug(f"📊 TOOLS_USED: {', '.join(tools_used)}")
            
    def _format_state(self, state: Dict[str, Any]) -> str:
        """格式化状态信息"""
        if not state:
            return "空状态"
        
        # 只显示关键字段，避免日志过长
        key_fields = ['research_topic', 'locale', 'current_plan', 'messages']
        formatted = {}
        
        for key in key_fields:
            if key in state:
                if key == 'messages':
                    formatted[key] = f"消息数量: {len(state[key])}"
                elif key == 'current_plan' and hasattr(state[key], 'title'):
                    formatted[key] = f"计划: {state[key].title}"
                else:
                    formatted[key] = str(state[key])[:100] + "..." if len(str(state[key])) > 100 else state[key]
                    
        return json.dumps(formatted, ensure_ascii=False, indent=2)
        
    def _format_result(self, result: Any) -> str:
        """格式化结果信息"""
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)[:500] + "..." if len(str(result)) > 500 else json.dumps(result, ensure_ascii=False, indent=2)
        elif isinstance(result, str):
            return result[:200] + "..." if len(result) > 200 else result
        else:
            return str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
            
    def _format_params(self, params: Dict[str, Any]) -> str:
        """格式化参数信息"""
        return json.dumps(params, ensure_ascii=False, indent=2)[:300] + "..." if len(str(params)) > 300 else json.dumps(params, ensure_ascii=False, indent=2)


# 全局日志记录器实例
_enhanced_loggers = {}

def get_enhanced_logger(name: str) -> EnhancedLogger:
    """获取增强日志记录器实例"""
    if name not in _enhanced_loggers:
        _enhanced_loggers[name] = EnhancedLogger(name)
    return _enhanced_loggers[name]


def setup_enhanced_logging(level=logging.INFO, enable_colors=True, log_file=None):
    """全局设置增强日志
    
    Args:
        level: 日志级别
        enable_colors: 是否启用彩色输出（仅控制台）
        log_file: 日志文件路径，如果为None则不输出到文件
                 可以从环境变量LOG_FILE读取
    """
    # 如果没有指定log_file，尝试从环境变量读取
    if log_file is None:
        log_file = os.getenv('LOG_FILE')
    
    for logger in _enhanced_loggers.values():
        logger.setup_enhanced_logging(level, enable_colors, log_file)


@contextmanager
def log_execution_time(logger: EnhancedLogger, operation_name: str):
    """上下文管理器，用于记录执行时间"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.logger.debug(f"⏱️ TIMING | {operation_name} | 耗时: {duration:.2f}s")


def log_node_execution(node_name: str):
    """装饰器，用于记录节点执行"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_enhanced_logger(f"node.{node_name}")
            
            # 记录节点进入
            state = args[0] if args else {}
            logger.log_node_entry(node_name, state)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_node_exit(node_name, result, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.logger.error(f"❌ NODE_ERROR | {node_name} | 节点执行失败: {str(e)} | 耗时: {duration:.2f}s")
                raise
                
        return wrapper
    return decorator


def log_tool_execution(tool_name: str):
    """装饰器，用于记录工具执行"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_enhanced_logger(f"tool.{tool_name}")
            
            # 提取参数
            parameters = {}
            if args:
                parameters['args'] = args
            if kwargs:
                parameters['kwargs'] = kwargs
                
            logger.log_tool_call_start(tool_name, parameters)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_tool_call_end(tool_name, result, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.logger.error(f"❌ TOOL_ERROR | {tool_name} | 工具执行失败: {str(e)} | 耗时: {duration:.2f}s")
                raise
                
        return wrapper
    return decorator