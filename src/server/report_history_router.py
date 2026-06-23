# SPDX-License-Identifier: MIT

"""
用户历史报告 API 路由

提供当前登录用户查看自己历史报告列表、获取报告正文内容、
基于历史报告继续对话等接口。所有接口均以 user_code 做数据隔离。
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from src.storage import report_repository
from src.storage.models import ReportListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["report-history"])


# ─── 响应模型 ───


class ReportContentResponse(BaseModel):
    """报告正文内容响应"""
    content: str
    title: str
    report_url: Optional[str] = None


class ContinueReportResponse(BaseModel):
    """基于历史报告继续对话响应"""
    report_content: str
    title: str


class UpdateReportRequest(BaseModel):
    """更新报告内容请求"""
    content: str


class UpdateReportResponse(BaseModel):
    """更新报告内容响应"""
    success: bool
    object_name: str
    file_size: int


# ─── 辅助函数 ───


def _get_current_user_code(request: Request) -> str:
    """从 auth 中间件注入的 request.state 中提取当前用户工号"""
    user_info = getattr(request.state, "user_info", None)
    if user_info is None or not user_info.is_authenticated:
        raise HTTPException(status_code=401, detail="未登录或认证已过期")
    return user_info.user_code


async def _read_report_content(report_id: UUID, user_code: str) -> tuple[str, str, Optional[str]]:
    """读取报告正文（含权限校验）

    Returns:
        (content, title, report_url)

    Raises:
        HTTPException 404: 报告不存在
        HTTPException 403: 无权访问
        HTTPException 503: MinIO 不可用
    """
    record = await report_repository.get_report_by_id(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    if record.user_code != user_code:
        logger.warning(
            f"[REPORT_HISTORY] 越权访问尝试 | report_id={report_id} | "
            f"owner={record.user_code} | requester={user_code}"
        )
        raise HTTPException(status_code=403, detail="无权访问此报告")

    object_name = record.object_name
    if not object_name:
        raise HTTPException(status_code=404, detail="报告文件路径不存在")

    try:
        from src.storage.minio_client import get_object_bytes

        loop = asyncio.get_event_loop()
        file_bytes = await loop.run_in_executor(None, get_object_bytes, object_name)
        content = file_bytes.decode("utf-8")
    except Exception as e:
        logger.error(
            f"[REPORT_HISTORY] MinIO 读取失败 | report_id={report_id} | "
            f"object_name={object_name} | error={e}"
        )
        raise HTTPException(status_code=503, detail="报告文件读取失败，请稍后重试")

    return content, record.title, record.report_url


# ─── API 接口 ───


@router.get("/my", response_model=ReportListResponse)
async def get_my_reports(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="标题模糊搜索关键词"),
    status: Optional[str] = Query(None, description="状态筛选（completed/cancelled/failed）"),
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    """获取当前用户的报告列表（强制 user_code 隔离，支持标题搜索）"""
    user_code = _get_current_user_code(request)

    items, total = await report_repository.get_reports_paginated(
        page=page,
        page_size=page_size,
        user_code=user_code,
        status=status,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
    )
    return ReportListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{report_id}/content", response_model=ReportContentResponse)
async def get_report_content(report_id: str, request: Request):
    """获取报告 Markdown 正文内容（含权限校验）"""
    user_code = _get_current_user_code(request)

    try:
        uid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    content, title, report_url = await _read_report_content(uid, user_code)

    logger.info(
        f"[REPORT_HISTORY] 读取报告内容 | report_id={report_id} | "
        f"user={user_code} | title={title[:50]} | content_len={len(content)}"
    )
    return ReportContentResponse(
        content=content, title=title, report_url=report_url
    )


@router.post("/{report_id}/continue", response_model=ContinueReportResponse)
async def continue_report(report_id: str, request: Request):
    """基于历史报告发起新对话（返回报告内容供前端注入上下文）"""
    user_code = _get_current_user_code(request)

    try:
        uid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    content, title, _ = await _read_report_content(uid, user_code)

    logger.info(
        f"[REPORT_HISTORY] 继续对话 | report_id={report_id} | "
        f"user={user_code} | title={title[:50]}"
    )
    return ContinueReportResponse(
        report_content=content, title=title
    )


@router.put("/{report_id}", response_model=UpdateReportResponse)
async def update_report(report_id: str, request: Request, body: UpdateReportRequest):
    """更新报告内容（覆盖写入 MinIO + 更新数据库 file_size）"""
    user_code = _get_current_user_code(request)

    try:
        uid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    # 权限校验 + 获取现有记录
    record = await report_repository.get_report_by_id(uid)
    if record is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    if record.user_code != user_code:
        logger.warning(
            f"[REPORT_HISTORY] 越权更新尝试 | report_id={report_id} | "
            f"owner={record.user_code} | requester={user_code}"
        )
        raise HTTPException(status_code=403, detail="无权修改此报告")

    object_name = record.object_name
    if not object_name:
        raise HTTPException(status_code=404, detail="报告文件路径不存在")

    # 覆盖写入 MinIO
    try:
        from src.storage.minio_client import upload_report

        file_bytes = body.content.encode("utf-8")
        file_size = len(file_bytes)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, upload_report, file_bytes, object_name, "text/markdown"
        )
    except Exception as e:
        logger.error(
            f"[REPORT_HISTORY] MinIO 更新失败 | report_id={report_id} | "
            f"object_name={object_name} | error={e}"
        )
        raise HTTPException(status_code=503, detail="报告文件保存失败，请稍后重试")

    # 更新数据库 file_size
    await report_repository.update_report_file_size(uid, file_size)

    logger.info(
        f"[REPORT_HISTORY] 报告已更新 | report_id={report_id} | "
        f"user={user_code} | object_name={object_name} | file_size={file_size}"
    )
    return UpdateReportResponse(
        success=True, object_name=object_name, file_size=file_size
    )
