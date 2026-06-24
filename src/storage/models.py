# SPDX-License-Identifier: MIT

"""
报告存储数据模型

定义报告元数据的 Pydantic 模型，用于 API 响应和数据库交互。
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportRecord(BaseModel):
    """报告元数据记录"""
    id: Optional[UUID] = None
    thread_id: Optional[str] = None
    user_code: str
    user_name: Optional[str] = None
    branch_id: Optional[int] = None
    login_name: Optional[str] = None
    linked_org_name: Optional[str] = None
    title: str
    duration_ms: Optional[int] = None
    report_url: Optional[str] = None
    object_name: Optional[str] = None  # MinIO 对象路径，用于直接读取报告正文
    file_size: Optional[int] = None
    report_type: str = "research"
    status: str = "completed"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DailyStat(BaseModel):
    """每日统计数据"""
    date: str  # YYYY-MM-DD
    count: int
    total_duration_ms: Optional[int] = None
    avg_duration_ms: Optional[int] = None


class DashboardSummary(BaseModel):
    """看板汇总数据"""
    total_reports: int = 0
    today_reports: int = 0
    month_reports: int = 0  # 本月报告数
    mau: int = 0  # 月活用户：近30天内生成过报告的去重用户数
    dau: int = 0  # 日活用户：今日生成过报告的去重用户数
    avg_duration_ms: int = 0


class ReportListResponse(BaseModel):
    """报告列表分页响应"""
    items: list[ReportRecord] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
