# SPDX-License-Identifier: MIT

"""
数据看板 API 路由

提供报告统计、列表查询、用户信息等看板相关接口。
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Request

from src.storage import report_repository
from src.storage.models import (
    DailyStat,
    DashboardSummary,
    ReportListResponse,
    ReportRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats/daily", response_model=list[DailyStat])
async def get_daily_stats(
    start_date: Optional[str] = Query(
        None, description="起始日期 (YYYY-MM-DD)，默认近 30 天"
    ),
    end_date: Optional[str] = Query(
        None, description="结束日期 (YYYY-MM-DD)，默认今天"
    ),
):
    """按日期范围返回每日报告数量统计"""
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()

    stats = await report_repository.get_daily_statistics(start_date, end_date)
    return stats


@router.get("/stats/summary", response_model=DashboardSummary)
async def get_summary():
    """总报告数、总用户数、平均耗时等汇总"""
    summary = await report_repository.get_summary()
    return summary


@router.get("/reports", response_model=ReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    login_name: Optional[str] = Query(None, description="按登录名筛选"),
    user_name: Optional[str] = Query(None, description="按姓名模糊筛选"),
    status: Optional[str] = Query(None, description="按状态筛选（completed/cancelled/failed）"),
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    """分页查询报告列表（支持按用户、姓名、日期、状态筛选）"""
    items, total = await report_repository.get_reports_paginated(
        page=page,
        page_size=page_size,
        login_name=login_name,
        user_name=user_name,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    return ReportListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/reports/{report_id}", response_model=Optional[ReportRecord])
async def get_report_detail(report_id: str):
    """获取报告详情"""
    from uuid import UUID

    try:
        uid = UUID(report_id)
    except ValueError:
        return None
    record = await report_repository.get_report_by_id(uid)
    return record


@router.get("/user/me")
async def get_current_user(request: Request):
    """获取当前用户信息（从认证中间件注入的 request.state 读取）"""
    user_info = getattr(request.state, "user_info", None)
    if user_info is None:
        return {
            "user_code": "",
            "user_name": "匿名用户",
            "is_authenticated": False,
        }
    return {
        "user_code": user_info.user_code,
        "user_name": user_info.user_name,
        "branch_id": user_info.branch_id,
        "login_name": user_info.login_name,
        "device": user_info.device,
        "is_authenticated": user_info.is_authenticated,
        "source": user_info.source,
    }
