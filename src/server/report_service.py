# SPDX-License-Identifier: MIT

"""
报告生成完成处理服务

在报告生成完成后（reporter 节点输出）：
1. 上传报告到 MinIO
2. 保存元数据到 PostgreSQL
3. 写入 JSONL 统计日志

作为独立服务模块，供 app.py 在流式事件中调用。
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


async def handle_report_completed(
    thread_id: str,
    report_content: str,
    title: str,
    user_code: str,
    user_name: str,
    branch_id: Optional[int] = None,
    login_name: str = "",
    duration_ms: int = 0,
    report_type: str = "research",
):
    """报告生成完成后的异步处理

    上传到 MinIO + 保存元数据 + 写入统计日志。
    该函数不会抛出异常，错误仅记录日志。

    Args:
        thread_id: 对话线程 ID
        report_content: 报告 Markdown 内容
        title: 报告标题
        user_code: 用户工号
        user_name: 用户姓名
        branch_id: 分行 ID
        login_name: 登录名
        duration_ms: 生成耗时（毫秒）
        report_type: 报告类型
    """
    report_url = None
    file_size = None

    try:
        # 1. 上传到 MinIO
        report_url, file_size = await _upload_to_minio(
            thread_id, report_content, report_type
        )
    except Exception as e:
        logger.error(f"[REPORT_SERVICE] MinIO 上传失败 | thread_id={thread_id} | {e}")

    try:
        # 2. 保存元数据到 PostgreSQL
        from src.storage import report_repository
        from src.storage.models import ReportRecord

        record = ReportRecord(
            thread_id=thread_id,
            user_code=user_code,
            user_name=user_name,
            branch_id=branch_id,
            login_name=login_name,
            title=title,
            duration_ms=duration_ms,
            report_url=report_url,
            file_size=file_size,
            report_type=report_type,
            status="completed",
        )
        report_id = await report_repository.save_report(record)
        logger.info(
            f"[REPORT_SERVICE] 报告元数据已保存 | thread_id={thread_id} | "
            f"report_id={report_id} | user={user_code}"
        )
    except Exception as e:
        logger.error(
            f"[REPORT_SERVICE] 元数据保存失败 | thread_id={thread_id} | {e}"
        )

    try:
        # 3. 写入 JSONL 统计日志
        from src.utils.statistics_logger import log_report_generated

        log_report_generated(
            thread_id=thread_id,
            user_code=user_code,
            user_name=user_name,
            title=title,
            duration_ms=duration_ms,
            report_type=report_type,
            report_url=report_url,
            file_size=file_size,
        )
    except Exception as e:
        logger.error(
            f"[REPORT_SERVICE] 统计日志写入失败 | thread_id={thread_id} | {e}"
        )


async def _upload_to_minio(
    thread_id: str, content: str, report_type: str
) -> tuple[Optional[str], Optional[int]]:
    """上传报告内容到 MinIO

    Returns:
        (report_url, file_size) 或 (None, None) 如果上传失败
    """
    import os

    # 检查是否配置了 MinIO
    if not os.getenv("MINIO_ENDPOINT"):
        logger.info("[REPORT_SERVICE] MINIO_ENDPOINT 未配置，跳过上传")
        return None, None

    from src.storage.minio_client import upload_report

    file_bytes = content.encode("utf-8")
    file_size = len(file_bytes)

    # 构建对象路径: reports/{year}/{month}/{day}/{thread_id}.md
    now = datetime.now()
    object_name = (
        f"reports/{now.year}/{now.month:02d}/{now.day:02d}/"
        f"{thread_id}_{report_type}.md"
    )

    # MinIO 客户端是同步的，放到线程池执行
    loop = asyncio.get_event_loop()
    report_url = await loop.run_in_executor(
        None, upload_report, file_bytes, object_name, "text/markdown"
    )

    logger.info(
        f"[REPORT_SERVICE] MinIO 上传成功 | thread_id={thread_id} | "
        f"url={report_url} | size={file_size}"
    )
    return report_url, file_size


def extract_report_title(content: str) -> str:
    """从报告 Markdown 内容中提取标题

    查找第一个 # 开头的行作为标题，否则取前 50 字。
    """
    if not content:
        return "未命名报告"

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()[:100]

    # Fallback: 取前 50 字
    return content[:50].replace("\n", " ").strip() or "未命名报告"
