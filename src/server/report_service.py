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
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger

# 北京时区 (UTC+8)
_BEIJING_TZ = timezone(timedelta(hours=8))


async def handle_report_completed(
    thread_id: str,
    report_content: str,
    title: str,
    login_name: str,
    user_name: str,
    user_code: str = "",
    branch_id: Optional[int] = None,
    linked_org_name: str = "",
    duration_ms: int = 0,
    report_type: str = "research",
    template_type: str = "academic",   # 用户选择的写作风格（模板类型）
    status: str = "completed",
    start_timestamp: Optional[float] = None,
    end_timestamp: Optional[float] = None,
    researcher_chars: int = 0,
    reporter_chars: int = 0,
    planner_chars: int = 0,
):
    """报告生成完成后的异步处理

    上传到 MinIO + 保存元数据 + 写入统计日志。
    该函数不会抛出异常，错误仅记录日志。

    Args:
        thread_id: 对话线程 ID
        report_content: 报告 Markdown 内容
        title: 报告标题
        login_name: 登录名（用户唯一标识）
        user_name: 用户姓名
        user_code: 工号（仅数据保存，不参与校验）
        branch_id: 分行ID
        linked_org_name: 行政机构名称
        duration_ms: 生成耗时（毫秒）
        report_type: 报告类型
        template_type: 用户选择的写作风格（模板类型）
        status: 报告状态（completed/cancelled/failed）
        start_timestamp: 报告生成起始时间戳 (Unix timestamp)
        end_timestamp: 报告生成结束时间戳 (Unix timestamp)
        researcher_chars: researcher 节点总输出字符数
        reporter_chars: reporter 节点总输出字符数
        planner_chars: planner 节点总输出字符数
    """
    # 打印起始时间和结束时间（北京时间）
    start_time_str = (
        datetime.fromtimestamp(start_timestamp, tz=_BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        if start_timestamp else "unknown"
    )
    end_time_str = (
        datetime.fromtimestamp(end_timestamp, tz=_BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        if end_timestamp else "unknown"
    )
    logger.info(
        f"[REPORT_SERVICE] 报告保存开始 | thread_id={thread_id} | status={status} | "
        f"起始时间(CST)={start_time_str} | 结束时间(CST)={end_time_str} | "
        f"耗时={duration_ms}ms | login_name={login_name} | title={title[:50]}"
    )
    report_url = None
    object_name = None
    file_size = None

    try:
        # 1. 上传到 MinIO（仅当有内容时）
        if report_content.strip():
            report_url, object_name, file_size = await _upload_to_minio(
                thread_id, report_content, report_type, title
            )
        else:
            logger.info(
                f"[REPORT_SERVICE] 报告内容为空，跳过 MinIO 上传 | thread_id={thread_id} | status={status}"
            )
    except Exception as e:
        logger.error(f"[REPORT_SERVICE] MinIO 上传失败 | thread_id={thread_id} | {e}")

    try:
        # 2. 保存元数据到 PostgreSQL
        from src.storage import report_repository
        from src.storage.models import ReportRecord

        # 计算估算 token 数（2.5 字符 ≈ 1 token，适用于中英文混合场景）
        _total_chars = (planner_chars or 0) + (researcher_chars or 0) + (reporter_chars or 0)
        _estimated_tokens = int(_total_chars / 2.5) if _total_chars > 0 else 0

        record = ReportRecord(
            thread_id=thread_id,
            user_code=user_code,
            user_name=user_name,
            branch_id=branch_id,
            login_name=login_name,
            linked_org_name=linked_org_name,
            title=title,
            duration_ms=duration_ms,
            report_url=report_url,
            object_name=object_name,
            file_size=file_size,
            report_type=report_type,
            template_type=template_type,
            status=status,
            researcher_chars=researcher_chars,
            reporter_chars=reporter_chars,
            estimated_tokens=_estimated_tokens,
        )
        report_id = await report_repository.save_report(record)
        logger.info(
            f"[REPORT_SERVICE] 报告元数据已保存 | thread_id={thread_id} | "
            f"report_id={report_id} | login_name={login_name} | title={title[:50]}"
        )
    except Exception as e:
        logger.error(
            f"[REPORT_SERVICE] 元数据保存失败 | thread_id={thread_id} | login_name={login_name} | {e}"
        )

    try:
        # 3. 写入 JSONL 统计日志
        from src.utils.statistics_logger import log_report_generated

        log_report_generated(
            thread_id=thread_id,
            login_name=login_name,
            user_name=user_name,
            title=title,
            duration_ms=duration_ms,
            report_type=report_type,
            report_url=report_url,
            file_size=file_size,
        )
    except Exception as e:
        logger.error(
            f"[REPORT_SERVICE] 统计日志写入失败 | thread_id={thread_id} | login_name={login_name} | {e}"
        )


async def _upload_to_minio(
    thread_id: str, content: str, report_type: str, title: str = ""
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """上传报告内容到 MinIO

    Returns:
        (report_url, object_name, file_size) 或 (None, None, None) 如果上传失败
    """
    import os

    # 检查是否配置了 MinIO
    if not os.getenv("MINIO_ENDPOINT"):
        logger.info(f"[REPORT_SERVICE] MINIO_ENDPOINT 未配置，跳过上传 | thread_id={thread_id}")
        return None, None, None

    from src.storage.minio_client import upload_report

    file_bytes = content.encode("utf-8")
    file_size = len(file_bytes)

    # 构建对象路径: reports/{year}/{month}/{day}/{thread_id}_{report_type}.md
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
        f"object={object_name} | url={report_url} | size={file_size} | title={title[:50]}"
    )
    return report_url, object_name, file_size


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
