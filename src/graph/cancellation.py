# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
客户端取消信号全局注册表

通过 thread_id 索引 asyncio.Event，避免通过 LangGraph config 传递对象引用导致丢失。
每个 chat/stream 请求在入口注册一个 Event，节点执行时按 thread_id 查询。
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_cancel_events: Dict[str, asyncio.Event] = {}


def register(thread_id: str) -> asyncio.Event:
    """注册或刷新一个 thread_id 对应的取消事件。

    同一 thread_id 再次调用会创建新 Event 并覆盖旧值（支持 interrupt-resume 场景）。
    """
    event = asyncio.Event()
    _cancel_events[thread_id] = event
    logger.debug(f"[CANCEL_REGISTRY] 注册 cancel_event | thread_id={thread_id}")
    return event


def get(thread_id: str) -> Optional[asyncio.Event]:
    """按 thread_id 获取对应的取消事件。不存在则返回 None。"""
    return _cancel_events.get(thread_id)


def unregister(thread_id: str) -> None:
    """清理指定 thread_id 的取消事件。"""
    if _cancel_events.pop(thread_id, None) is not None:
        logger.debug(f"[CANCEL_REGISTRY] 注销 cancel_event | thread_id={thread_id}")


def get_from_config(config) -> Optional[asyncio.Event]:
    """从 RunnableConfig 中提取取消事件。

    优先按 thread_id 查全局注册表，退化到 config.configurable.cancel_event。
    统一封装，节点内一行调用即可。
    """
    if not isinstance(config, dict):
        return None
    configurable = config.get("configurable", {}) or {}
    tid = configurable.get("thread_id")
    if tid:
        ev = _cancel_events.get(tid)
        if ev is not None:
            return ev
    return configurable.get("cancel_event")
