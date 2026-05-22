# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
ReactLoop 统一配置（对齐 DeerFlow 2.0 配置架构）

从 conf.yaml 的 REACT_LOOP 段加载所有中间件配置，
使用 Pydantic BaseModel 做类型验证 + 默认值。

架构对齐 2.0：
- 每个中间件有独立的 Config 子模型
- ReactLoopConfig 聚合所有子配置
- 单例模式 + get_react_loop_config() 全局访问
- 支持 conf.yaml 覆盖 + 环境变量覆盖

Usage:
    from src.agents.react_config import get_react_loop_config
    config = get_react_loop_config()
    config.max_iterations          # 8
    config.loop_detection.warn_at  # 5
"""

import logging
import os
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


# ============================================================
# 各中间件配置子模型（Pydantic BaseModel）
# ============================================================

class LoopDetectionConfig(BaseModel):
    """循环检测中间件配置"""
    # loop 级: 哈希检测
    hash_threshold: int = Field(default=3, ge=1, description="相同 tool_calls 组合重复多少次触发强停")
    hash_window_size: int = Field(default=20, ge=1, description="哈希历史窗口大小")
    warn_at: int = Field(default=5, ge=0, description="第几轮开始注入软提示（0=禁用）")
    # session 级: 频率检测
    freq_warn_threshold: int = Field(default=15, ge=1, description="同一工具累计调用多少次警告")
    freq_hard_threshold: int = Field(default=25, ge=1, description="同一工具累计调用多少次强停")
    session_max_tool_calls: int = Field(default=0, ge=0, description="session 总工具调用上限（0=不限制）")
    session_max_iterations: int = Field(default=0, ge=0, description="session 总迭代上限（0=不限制）")

    @model_validator(mode="after")
    def validate_thresholds(self) -> "LoopDetectionConfig":
        if self.freq_hard_threshold < self.freq_warn_threshold:
            raise ValueError("freq_hard_threshold must be >= freq_warn_threshold")
        return self


class SummarizationConfig(BaseModel):
    """上下文摘要中间件配置"""
    enabled: bool = Field(default=True, description="是否启用")
    max_context_tokens: int = Field(default=12000, ge=1000, description="触发全局压缩的 token 阈值（应 < SEARCH_BUDGET.hard_limit）")
    keep_recent_messages: int = Field(default=6, ge=1, description="保留最近 N 条消息不压缩")
    tool_result_max_chars: int = Field(default=3000, ge=100, description="单个工具结果最大字符数")
    compression_mode: str = Field(default="summarize", description="压缩模式: summarize 或 truncate")
    summary_max_chars: int = Field(default=1500, ge=100, description="摘要最大长度")
    token_chars_ratio: float = Field(default=3.0, gt=0, description="token 估算比率（与 SEARCH_BUDGET 保持一致，中英混合 3.0）")


class LLMErrorHandlingConfig(BaseModel):
    """LLM 错误处理中间件配置"""
    max_retries: int = Field(default=3, ge=0, description="最大重试次数（不含首次）")
    base_delay: float = Field(default=1.0, gt=0, description="基础延迟（秒）")
    max_delay: float = Field(default=8.0, gt=0, description="最大延迟（秒）")
    backoff_factor: float = Field(default=2.0, ge=1, description="退避倍数")
    circuit_breaker_threshold: int = Field(default=5, ge=1, description="连续失败多少次后熔断")
    circuit_breaker_recovery_seconds: float = Field(default=30.0, gt=0, description="熔断恢复时间（秒）")


class ToolErrorHandlingConfig(BaseModel):
    """工具错误处理中间件配置"""
    consecutive_error_warn: int = Field(default=3, ge=1, description="连续错误多少次后注入引导提示")
    error_max_chars: int = Field(default=500, ge=50, description="错误消息最大长度")
    add_suggestions: bool = Field(default=True, description="是否在错误消息中添加建议")


class TokenUsageConfig(BaseModel):
    """Token 用量统计中间件配置"""
    enabled: bool = Field(default=True, description="是否启用")


class DynamicContextConfig(BaseModel):
    """动态上下文注入中间件配置"""
    system_hint: str = Field(default="", description="自定义系统提示")


class BudgetEnforcementConfig(BaseModel):
    """搜索预算执行中间件配置（方案 C：原生工具 + 中间件接管预算）"""
    enabled: bool = Field(default=True, description="是否启用预算执行中间件（仅 researcher 类型生效）")
    max_search_calls: int = Field(default=5, ge=1, description="每个 researcher 节点的最大搜索调用次数")
    max_tokens: int = Field(default=10000, ge=1000, description="软预警 token 阈值")
    hard_token_limit: int = Field(default=14000, ge=1000, description="硬 token 上限，达到立即拦截")
    token_chars_ratio: float = Field(default=3.0, gt=0, description="字符数/token 估算比例（与 SEARCH_BUDGET、summarization 保持一致）")
    controlled_tool_names: list[str] = Field(
        default_factory=lambda: [
            "online_search",
            "searchknowledge_standard",
            "financial_summary",
            "product_instance_search",
        ],
        description="受预算控制的原生工具白名单。bocomsearch 因 guwp_token 线程安全保留独立包装器，不在此处",
    )
    attach_warning: bool = Field(default=True, description="是否在每次成功调用后给工具结果附加预算警告")


# ============================================================
# 聚合配置（对齐 2.0 的 AppConfig 模式）
# ============================================================

class ReactLoopConfig(BaseModel):
    """ReactLoop 统一配置

    聚合所有中间件配置，对齐 DeerFlow 2.0 的 AppConfig 设计。
    从 conf.yaml 的 REACT_LOOP 段加载。
    """
    max_iterations: int = Field(default=8, ge=1, description="最大迭代次数（硬上限）")

    loop_detection: LoopDetectionConfig = Field(default_factory=LoopDetectionConfig)
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)
    llm_error_handling: LLMErrorHandlingConfig = Field(default_factory=LLMErrorHandlingConfig)
    tool_error_handling: ToolErrorHandlingConfig = Field(default_factory=ToolErrorHandlingConfig)
    token_usage: TokenUsageConfig = Field(default_factory=TokenUsageConfig)
    dynamic_context: DynamicContextConfig = Field(default_factory=DynamicContextConfig)
    budget_enforcement: BudgetEnforcementConfig = Field(default_factory=BudgetEnforcementConfig)


# ============================================================
# 单例管理（对齐 2.0 的 get_xxx_config 模式）
# ============================================================

_react_loop_config: Optional[ReactLoopConfig] = None


def get_react_loop_config() -> ReactLoopConfig:
    """获取 ReactLoop 配置单例

    首次调用时从 conf.yaml 加载，后续调用返回缓存。
    如果 conf.yaml 中没有 REACT_LOOP 段，返回全默认值。
    """
    global _react_loop_config
    if _react_loop_config is None:
        _react_loop_config = _load_react_loop_config()
    return _react_loop_config


def reload_react_loop_config() -> ReactLoopConfig:
    """强制重新加载配置（用于配置热更新或测试）"""
    global _react_loop_config
    _react_loop_config = _load_react_loop_config()
    return _react_loop_config


def reset_react_loop_config() -> None:
    """重置缓存（用于测试防止单例泄漏）"""
    global _react_loop_config
    _react_loop_config = None


def _load_react_loop_config() -> ReactLoopConfig:
    """从 conf.yaml 加载 REACT_LOOP 配置

    加载优先级：
    1. conf.yaml 中的 REACT_LOOP 段
    2. 环境变量覆盖（兼容旧的 REACT_* 环境变量）
    3. Pydantic 默认值兜底
    """
    config_data = _read_yaml_section()
    config_data = _apply_env_overrides(config_data)

    try:
        config = ReactLoopConfig.model_validate(config_data)
        logger.info(
            f"✅ ReactLoop 配置加载完成 | "
            f"max_iterations={config.max_iterations} | "
            f"loop_detection.warn_at={config.loop_detection.warn_at} | "
            f"llm_error_handling.max_retries={config.llm_error_handling.max_retries}"
        )
        return config
    except Exception as e:
        logger.warning(f"⚠️ ReactLoop 配置验证失败，使用默认值: {e}")
        return ReactLoopConfig()


def _read_yaml_section() -> dict:
    """从 conf.yaml 读取 REACT_LOOP 段"""
    try:
        from src.config import load_yaml_config
        import os as _os
        config_path = _os.path.join(_os.getcwd(), "conf.yaml")
        full_config = load_yaml_config(config_path)
        return full_config.get("REACT_LOOP", {}) or {}
    except Exception as e:
        logger.warning(f"⚠️ 无法从 conf.yaml 加载 REACT_LOOP: {e}")
        return {}


def _apply_env_overrides(data: dict) -> dict:
    """兼容旧的 REACT_* 环境变量，覆盖 YAML 配置

    环境变量优先级高于 YAML，确保向后兼容。
    """
    # 顶层
    _env_override_int(data, "max_iterations", "REACT_MAX_ITERATIONS")

    # loop_detection
    ld = data.setdefault("loop_detection", {})
    _env_override_int(ld, "hash_threshold", "REACT_LOOP_DETECT_THRESHOLD")
    _env_override_int(ld, "warn_at", "REACT_WARN_AT")

    # summarization
    sm = data.setdefault("summarization", {})
    _env_override_int(sm, "max_context_tokens", "REACT_MAX_CONTEXT_TOKENS")
    _env_override_int(sm, "tool_result_max_chars", "REACT_TOOL_RESULT_MAX_CHARS")
    _env_override_str(sm, "compression_mode", "REACT_COMPRESSION_MODE")

    # llm_error_handling
    le = data.setdefault("llm_error_handling", {})
    _env_override_int(le, "max_retries", "REACT_LLM_MAX_RETRIES")
    _env_override_float(le, "base_delay", "REACT_LLM_BASE_DELAY")

    # dynamic_context
    dc = data.setdefault("dynamic_context", {})
    _env_override_str(dc, "system_hint", "REACT_SYSTEM_HINT")

    return data


def _env_override_int(data: dict, key: str, env_name: str) -> None:
    val = os.getenv(env_name)
    if val is not None:
        try:
            data[key] = int(val)
        except ValueError:
            pass


def _env_override_float(data: dict, key: str, env_name: str) -> None:
    val = os.getenv(env_name)
    if val is not None:
        try:
            data[key] = float(val)
        except ValueError:
            pass


def _env_override_str(data: dict, key: str, env_name: str) -> None:
    val = os.getenv(env_name)
    if val is not None:
        data[key] = val
