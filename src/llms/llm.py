# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import time
from pathlib import Path
from typing import Any, Dict, get_args, Union

import httpx  # type: ignore
from langchain_core.language_models import BaseChatModel  # type: ignore
from langchain_deepseek import ChatDeepSeek  # type: ignore
from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
from langchain_openai import AzureChatOpenAI, ChatOpenAI  # type: ignore
from typing import get_args

from src.config import load_yaml_config
from src.config.agents import LLMType
from src.llms.providers.dashscope import ChatDashscope
from src.utils.enhanced_logger import get_enhanced_logger
from src.utils.text_utils import get_messages_context_stats


class EnhancedLLMWrapper:
    """增弾LLM包装器，用于记录思考过程"""

    def __init__(self, llm: BaseChatModel, llm_type: str):
        self.llm = llm
        self.llm_type = llm_type
        self.enhanced_logger = get_enhanced_logger(f'llm.{llm_type}')

    def invoke(self, messages, **kwargs):
        """记录并执行LLM调用，带有自动重试机制"""
        import asyncio
        from httpx import RemoteProtocolError, ConnectError, TimeoutException  # type: ignore

        max_retries = 2  # 最大重试次数
        retry_delay = 2.0  # 重试延迟（秒）

        for attempt in range(max_retries + 1):
            start_time = time.time()
            char_len, token_est = get_messages_context_stats(messages)

            if attempt == 0:
                self.enhanced_logger.logger.info(f"🤖 LLM_INVOKE | {self.llm_type} | 开始思考 | 上下文长度: chars={char_len} | tokens≈{token_est}")
            else:
                self.enhanced_logger.logger.warning(f"🔄 LLM_RETRY | {self.llm_type} | 第 {attempt} 次重试 | 上下文长度: chars={char_len} | tokens≈{token_est}")

            try:
                result = self.llm.invoke(messages, **kwargs)
                duration = time.time() - start_time
                response_length = len(str(result.content)) if hasattr(result, 'content') else 0

                self.enhanced_logger.log_llm_thinking(self.llm_type, char_len, response_length, duration)

                # 记录有关思考过程的额外信息
                if hasattr(result, 'response_metadata'):
                    usage = result.response_metadata.get('usage', {})
                    if usage:
                        self.enhanced_logger.logger.debug(f"🤖 LLM_USAGE | {self.llm_type} | token使用: {usage}")

                return result

            except (RemoteProtocolError, ConnectError, TimeoutException) as e:
                duration = time.time() - start_time
                is_last_attempt = (attempt == max_retries)

                if is_last_attempt:
                    self.enhanced_logger.logger.error(
                        f"❌ LLM_INVOKE_ERROR | {self.llm_type} | 网络错误（已达最大重试次数）: {str(e)} | 耗时: {duration:.2f}s"
                    )
                    raise
                else:
                    self.enhanced_logger.logger.warning(
                        f"⚠️  LLM_NETWORK_ERROR | {self.llm_type} | 网络错误，将在 {retry_delay}s 后重试: {str(e)}"
                    )
                    time.sleep(retry_delay * (attempt + 1))  # 指数退避

            except Exception as e:
                duration = time.time() - start_time
                self.enhanced_logger.logger.error(f"❌ LLM_INVOKE_ERROR | {self.llm_type} | 思考失败: {str(e)} | 耗时: {duration:.2f}s")
                raise
            
    def stream(self, messages, **kwargs):
        """记录并执行流式LLM调用，带有自动重试机制"""
        from httpx import RemoteProtocolError, ConnectError, TimeoutException  # type: ignore

        max_retries = 2  # 最大重试次数
        retry_delay = 2.0  # 重试延迟（秒）

        for attempt in range(max_retries + 1):
            start_time = time.time()
            char_len, token_est = get_messages_context_stats(messages)


            try:
                stream = self.llm.stream(messages, **kwargs)
                chunks_count = 0
                total_content_length = 0

                for chunk in stream:
                    chunks_count += 1
                    if hasattr(chunk, 'content') and chunk.content:
                        total_content_length += len(str(chunk.content))
                    yield chunk

                duration = time.time() - start_time
                return  # 成功完成，退出重试循环

            except (RemoteProtocolError, ConnectError, TimeoutException) as e:
                duration = time.time() - start_time
                is_last_attempt = (attempt == max_retries)

                if is_last_attempt:
                    self.enhanced_logger.logger.error(
                        f"❌ LLM_STREAM_ERROR | {self.llm_type} | 网络错误（已达最大重试次数）: {str(e)} | 耗时: {duration:.2f}s"
                    )
                    raise
                else:
                    self.enhanced_logger.logger.warning(
                        f"⚠️  LLM_STREAM_NETWORK_ERROR | {self.llm_type} | 网络错误，将在 {retry_delay}s 后重试: {str(e)}"
                    )
                    time.sleep(retry_delay * (attempt + 1))  # 指数退避

            except Exception as e:
                duration = time.time() - start_time
                self.enhanced_logger.logger.error(f"❌ LLM_STREAM_ERROR | {self.llm_type} | 流式思考失败: {str(e)} | 耗时: {duration:.2f}s")
                raise
            
    def with_structured_output(self, *args, **kwargs):
        """包装结构化输出方法"""
        structured_llm = self.llm.with_structured_output(*args, **kwargs)
        return EnhancedStructuredLLMWrapper(structured_llm, self.llm_type, self.enhanced_logger)
        
    def bind_tools(self, *args, **kwargs):
        """包装工具绑定方法"""
        tool_bound_llm = self.llm.bind_tools(*args, **kwargs)
        return EnhancedToolBoundLLMWrapper(tool_bound_llm, self.llm_type, self.enhanced_logger)
        
    def _calculate_prompt_length(self, messages):
        """计算提示长度"""
        if isinstance(messages, list):
            return sum(len(str(msg)) for msg in messages)
        else:
            return len(str(messages))
            
    def __getattr__(self, name):
        """委托其他属性到原始LLM"""
        return getattr(self.llm, name)


class EnhancedStructuredLLMWrapper:
    """增强结构化LLM包装器"""
    
    def __init__(self, structured_llm, llm_type: str, enhanced_logger):
        self.structured_llm = structured_llm
        self.llm_type = llm_type
        self.enhanced_logger = enhanced_logger
        
    def invoke(self, messages, **kwargs):
        start_time = time.time()
        char_len, token_est = get_messages_context_stats(messages)
        
        self.enhanced_logger.logger.info(f"🤖 LLM_STRUCTURED | {self.llm_type} | 开始结构化思考 | 上下文长度: chars={char_len} | tokens≈{token_est}")
        
        try:
            result = self.structured_llm.invoke(messages, **kwargs)
            duration = time.time() - start_time
            
            # 计算结构化输出的大小
            result_size = len(str(result)) if result else 0
            
            self.enhanced_logger.logger.info(f"🤖 LLM_STRUCTURED_COMPLETE | {self.llm_type} | 结构化思考完成 | 输出大小: {result_size} | 耗时: {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.enhanced_logger.logger.error(f"❌ LLM_STRUCTURED_ERROR | {self.llm_type} | 结构化思考失败: {str(e)} | 耗时: {duration:.2f}s")
            raise
            
    def _calculate_prompt_length(self, messages):
        if isinstance(messages, list):
            return sum(len(str(msg)) for msg in messages)
        else:
            return len(str(messages))
            
    def __getattr__(self, name):
        return getattr(self.structured_llm, name)


class EnhancedToolBoundLLMWrapper:
    """增强工具绑定LLM包装器"""
    
    def __init__(self, tool_bound_llm, llm_type: str, enhanced_logger):
        self.tool_bound_llm = tool_bound_llm
        self.llm_type = llm_type
        self.enhanced_logger = enhanced_logger
        
    def invoke(self, messages, **kwargs):
        start_time = time.time()
        char_len, token_est = get_messages_context_stats(messages)
        
        
        try:
            result = self.tool_bound_llm.invoke(messages, **kwargs)
            duration = time.time() - start_time
            
            # 检查是否有工具调用
            tool_calls = getattr(result, 'tool_calls', [])
            tool_count = len(tool_calls) if tool_calls else 0
            
            
            
            if tool_calls:
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get('name', '未知工具')
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.enhanced_logger.logger.error(f"❌ LLM_TOOLS_ERROR | {self.llm_type} | 工具思考失败: {str(e)} | 耗时: {duration:.2f}s")
            raise
            
    def _calculate_prompt_length(self, messages):
        if isinstance(messages, list):
            return sum(len(str(msg)) for msg in messages)
        else:
            return len(str(messages))
            
    def __getattr__(self, name):
        return getattr(self.tool_bound_llm, name)

# Cache for LLM instances
_llm_cache: dict[LLMType, BaseChatModel] = {}
enhanced_logger = get_enhanced_logger('llms.llm')


def _get_config_file_path() -> str:
    """Get the path to the configuration file.

    Switchable by the ``LLM_NETWORK`` environment variable:
      - ``external`` (default): use ``conf.yaml`` (e.g. DeepSeek/OpenAI)
      - ``internal``:          use ``conf.internal.yaml`` (e.g. BOCOM ELLM)

    If ``LLM_NETWORK=internal`` is set but ``conf.internal.yaml`` does not
    exist, a warning is logged and the loader falls back to ``conf.yaml``
    so the process can still start.
    """
    root = Path(__file__).parent.parent.parent
    network = os.getenv("LLM_NETWORK", "external").lower()
    if network == "internal":
        internal = root / "conf.internal.yaml"
        if internal.exists():
            return str(internal.resolve())
        enhanced_logger.logger.warning(
            "LLM_NETWORK=internal but conf.internal.yaml not found, "
            "falling back to conf.yaml"
        )
    return str((root / "conf.yaml").resolve())


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
        "code": "CODE_MODEL",
        "reporter_llm": "REPORTER_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value
    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """Create LLM instance using configuration."""
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    if not config_key:
        raise ValueError(f"Unknown LLM type: {llm_type}")

    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM configuration for {llm_type}: {llm_conf}")

    # Get configuration from environment variables
    env_conf = _get_env_llm_conf(llm_type)

    # Merge configurations, with environment variables taking precedence
    merged_conf = {**llm_conf, **env_conf}

    if not merged_conf:
        raise ValueError(f"No configuration found for LLM type: {llm_type}")

    # Add max_retries to handle rate limit errors
    if "max_retries" not in merged_conf:
        merged_conf["max_retries"] = 3

    # Configure timeout for long-running LLM calls
    # Set a longer timeout for streaming responses (15 minutes)
    if "timeout" not in merged_conf:
        merged_conf["timeout"] = 900.0  # 15 minutes in seconds

    # Handle SSL verification settings
    verify_ssl = merged_conf.pop("verify_ssl", True)

    # Create custom HTTP client if SSL verification is disabled
    if not verify_ssl:
        # Configure timeout for httpx clients
        timeout_config = httpx.Timeout(
            connect=60.0,  # Connection timeout
            read=900.0,    # Read timeout (15 minutes for streaming)
            write=60.0,    # Write timeout
            pool=60.0      # Connection pool timeout
        )
        http_client = httpx.Client(verify=False, timeout=timeout_config)
        http_async_client = httpx.AsyncClient(verify=False, timeout=timeout_config)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client
    else:
        # Also configure timeout when SSL verification is enabled
        timeout_config = httpx.Timeout(
            connect=60.0,
            read=900.0,    # 15 minutes for streaming
            write=60.0,
            pool=60.0
        )
        http_client = httpx.Client(timeout=timeout_config)
        http_async_client = httpx.AsyncClient(timeout=timeout_config)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client

    # Check platform-specific routing based on configuration
    platform = merged_conf.get("platform", "").lower()

    # --- BOCOM ELLM (internal) dispatch ---
    if platform == "ellm":
        from src.llms.providers.ellm import EllmChatModel
        # ELLM uses its own httpx client + "api-key" header; remove
        # OpenAI-style http clients and the platform marker before init.
        merged_conf.pop("http_client", None)
        merged_conf.pop("http_async_client", None)
        merged_conf.pop("platform", None)
        return EllmChatModel(**merged_conf)

    is_google_aistudio = platform == "google_aistudio" or platform == "google-aistudio"

    if is_google_aistudio:
        # Handle Google AI Studio specific configuration
        gemini_conf = merged_conf.copy()

        # Map common keys to Google AI Studio specific keys
        if "api_key" in gemini_conf:
            gemini_conf["google_api_key"] = gemini_conf.pop("api_key")

        # Remove base_url and platform since Google AI Studio doesn't use them
        gemini_conf.pop("base_url", None)
        gemini_conf.pop("platform", None)

        # Remove unsupported parameters for Google AI Studio
        gemini_conf.pop("http_client", None)
        gemini_conf.pop("http_async_client", None)

        return ChatGoogleGenerativeAI(**gemini_conf)

    if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureChatOpenAI(**merged_conf)

    # Check if base_url is dashscope endpoint
    if "base_url" in merged_conf and "dashscope." in merged_conf["base_url"]:
        if llm_type == "reasoning":
            merged_conf["extra_body"] = {
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False}
            }
        else:
            merged_conf["extra_body"] = {
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False}
            }
        return ChatDashscope(**merged_conf)

    if llm_type == "reasoning":
        merged_conf["api_base"] = merged_conf.pop("base_url", None)
        return ChatDeepSeek(**merged_conf)
    else:
        return ChatOpenAI(**merged_conf)


def get_llm_by_type(llm_type: LLMType) -> Union[BaseChatModel, 'EnhancedLLMWrapper']:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    start_time = time.time()
    
    try:
        if llm_type in _llm_cache:
            duration = time.time() - start_time
            return _llm_cache[llm_type]

        conf = load_yaml_config(_get_config_file_path())
        llm = _create_llm_use_conf(llm_type, conf)
        _llm_cache[llm_type] = llm
        
        # 包装LLM以添加日志功能
        wrapped_llm = EnhancedLLMWrapper(llm, llm_type)
        
        duration = time.time() - start_time
        return wrapped_llm
        
    except Exception as e:
        duration = time.time() - start_time
        enhanced_logger.logger.error(f"❌ LLM_ERROR | {llm_type} | LLM初始化失败: {str(e)} | 耗时: {duration:.2f}s")
        raise


def get_configured_llm_models() -> dict[str, list[str]]:
    """
    Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.
    """
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()

        configured_models: dict[str, list[str]] = {}

        for llm_type in get_args(LLMType):
            # Get configuration from YAML file
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}

            # Get configuration from environment variables
            env_conf = _get_env_llm_conf(llm_type)

            # Merge configurations, with environment variables taking precedence
            merged_conf = {**yaml_conf, **env_conf}

            # Check if model is configured
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)

        return configured_models

    except Exception as e:
        # Log error and return empty dict to avoid breaking the application
        print(f"Warning: Failed to load LLM configuration: {e}")
        return {}


# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")
