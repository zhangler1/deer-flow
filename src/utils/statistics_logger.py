# SPDX-License-Identifier: MIT

"""
统计埋点日志

采用独立的结构化 JSONL 日志文件（每行一个 JSON），与应用日志分离。
- 按天 rotate
- 保留 90 天
- 包含 event、timestamp、thread_id、user_code、user_name 等字段
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

logger = logging.getLogger(__name__)

# ─── 配置 ───

STATISTICS_LOG_DIR = os.getenv("STATISTICS_LOG_DIR", "logs/statistics")
STATISTICS_LOG_RETENTION_DAYS = int(os.getenv("STATISTICS_LOG_RETENTION_DAYS", "90"))

# ─── JSONL Logger 初始化 ───

_stats_logger: Optional[logging.Logger] = None


def _get_stats_logger() -> logging.Logger:
    """获取统计埋点专用 logger（懒初始化）"""
    global _stats_logger
    if _stats_logger is not None:
        return _stats_logger

    # 确保日志目录存在
    os.makedirs(STATISTICS_LOG_DIR, exist_ok=True)

    log_file = os.path.join(STATISTICS_LOG_DIR, "statistics.jsonl")

    _stats_logger = logging.getLogger("deer-flow.statistics")
    _stats_logger.setLevel(logging.INFO)
    _stats_logger.propagate = False  # 不传播到根 logger

    # TimedRotatingFileHandler: 按天切割，保留 N 天
    handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=STATISTICS_LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"
    # 只输出原始消息内容（JSONL 格式）
    handler.setFormatter(logging.Formatter("%(message)s"))
    _stats_logger.addHandler(handler)

    logger.info(
        f"统计埋点日志已初始化 | dir={STATISTICS_LOG_DIR} | "
        f"retention={STATISTICS_LOG_RETENTION_DAYS} days"
    )
    return _stats_logger


# ─── 公开 API ───

def log_report_generated(
    thread_id: str,
    user_code: str,
    user_name: str,
    title: str,
    duration_ms: int,
    report_type: str = "research",
    report_url: Optional[str] = None,
    file_size: Optional[int] = None,
):
    """记录报告生成事件

    Args:
        thread_id: 对话线程 ID
        user_code: 用户工号
        user_name: 用户姓名
        title: 报告标题
        duration_ms: 生成耗时（毫秒）
        report_type: 报告类型
        report_url: MinIO 文件地址
        file_size: 文件大小（字节）
    """
    event = {
        "event": "report_generated",
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "user_code": user_code,
        "user_name": user_name,
        "title": title,
        "duration_ms": duration_ms,
        "report_type": report_type,
        "report_url": report_url,
        "file_size": file_size,
    }

    stats_logger = _get_stats_logger()
    stats_logger.info(json.dumps(event, ensure_ascii=False))


def log_user_login(user_code: str, user_name: str, device: str = ""):
    """记录用户登录事件"""
    event = {
        "event": "user_login",
        "timestamp": datetime.now().isoformat(),
        "user_code": user_code,
        "user_name": user_name,
        "device": device,
    }

    stats_logger = _get_stats_logger()
    stats_logger.info(json.dumps(event, ensure_ascii=False))


def log_research_started(
    thread_id: str,
    user_code: str,
    user_name: str,
    query: str,
    report_type: str = "research",
):
    """记录研究开始事件"""
    event = {
        "event": "research_started",
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "user_code": user_code,
        "user_name": user_name,
        "query": query[:200],  # 截断过长的查询
        "report_type": report_type,
    }

    stats_logger = _get_stats_logger()
    stats_logger.info(json.dumps(event, ensure_ascii=False))
