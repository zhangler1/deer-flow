# SPDX-License-Identifier: MIT

"""
数据看板 API 路由

提供报告统计、列表查询、用户信息等看板相关接口。
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.storage import report_repository
from src.storage.models import (
    DailyStat,
    DashboardSummary,
    ReportListResponse,
    ReportRecord,
    TemplateStat,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ─── 权限依赖 ───

async def require_admin(request: Request):
    """FastAPI 依赖：验证当前用户是管理员，否则返回 403"""
    user_info = getattr(request.state, "user_info", None)
    if not user_info or not user_info.is_authenticated:
        raise HTTPException(status_code=401, detail="未登录或认证已过期")
    if not await report_repository.is_user_admin(user_info.login_name):
        raise HTTPException(status_code=403, detail="无管理员权限")
    return user_info


@router.get("/stats/daily", response_model=list[DailyStat])
async def get_daily_stats(
    start_date: Optional[str] = Query(
        None, description="起始日期 (YYYY-MM-DD)，默认近 30 天"
    ),
    end_date: Optional[str] = Query(
        None, description="结束日期 (YYYY-MM-DD)，默认今天"
    ),
    _=Depends(require_admin),
):
    """按日期范围返回每日报告数量统计（仅管理员）"""
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()

    stats = await report_repository.get_daily_statistics(start_date, end_date)
    return stats


@router.get("/stats/summary", response_model=DashboardSummary)
async def get_summary(_=Depends(require_admin)):
    """总报告数、总用户数、平均耗时等汇总（仅管理员）"""
    summary = await report_repository.get_summary()
    return summary


@router.get("/stats/template", response_model=list[TemplateStat])
async def get_template_stats(_=Depends(require_admin)):
    """各模板类型已生成报告份数统计（仅管理员）"""
    return await report_repository.get_template_type_stats()


@router.get("/reports", response_model=ReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    login_name: Optional[str] = Query(None, description="按登录名筛选"),
    user_name: Optional[str] = Query(None, description="按姓名模糊筛选"),
    status: Optional[str] = Query(None, description="按状态筛选（completed/cancelled/failed）"),
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    _=Depends(require_admin),
):
    """分页查询报告列表（仅管理员，支持按用户、姓名、日期、状态筛选）"""
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
async def get_report_detail(report_id: str, _=Depends(require_admin)):
    """获取报告详情（仅管理员）"""
    from uuid import UUID

    try:
        uid = UUID(report_id)
    except ValueError:
        return None
    record = await report_repository.get_report_by_id(uid)
    return record


@router.get("/user/me")
async def get_current_user(request: Request):
    """获取当前用户信息（含 is_admin 权限标志）"""
    user_info = getattr(request.state, "user_info", None)
    if user_info is None:
        return {
            "user_code": "",
            "user_name": "匿名用户",
            "is_authenticated": False,
            "is_admin": False,
        }
    is_admin = (
        await report_repository.is_user_admin(user_info.login_name)
        if user_info.is_authenticated
        else False
    )
    return {
        "user_code": user_info.user_code,
        "user_name": user_info.user_name,
        "branch_id": user_info.branch_id,
        "login_name": user_info.login_name,
        "device": user_info.device,
        "is_authenticated": user_info.is_authenticated,
        "source": getattr(user_info, "source", ""),
        "is_admin": is_admin,
    }


# ─── 管理员管理（仅管理员） ───

class AddAdminRequest(BaseModel):
    login_name: str


@router.get("/admins")
async def list_admins(_=Depends(require_admin)):
    """列出所有管理员（仅管理员）"""
    return await report_repository.list_admins()


@router.post("/admins")
async def add_admin(body: AddAdminRequest, _=Depends(require_admin)):
    """新增管理员（仅管理员）"""
    login_name = body.login_name.strip()
    if not login_name:
        raise HTTPException(status_code=400, detail="login_name 不能为空")
    await report_repository.add_admin(login_name)
    return {"success": True, "login_name": login_name}
