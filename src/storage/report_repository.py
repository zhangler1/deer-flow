# SPDX-License-Identifier: MIT

"""
报告元数据持久化仓库

使用 PostgreSQL 存储报告元数据，复用 LangGraph checkpoint 的连接池配置。
提供 CRUD + 统计查询接口。
"""

import logging
import os
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from src.storage.models import DailyStat, DashboardSummary, ReportRecord

logger = logging.getLogger(__name__)

# ─── 连接池 ───

_pool: Optional[AsyncConnectionPool] = None


async def _get_pool() -> AsyncConnectionPool:
    """获取或创建 PostgreSQL 连接池"""
    global _pool
    if _pool is None:
        db_url = os.getenv("LANGGRAPH_CHECKPOINT_DB_URL", "")
        if not db_url:
            raise RuntimeError(
                "未配置数据库连接：请设置环境变量 LANGGRAPH_CHECKPOINT_DB_URL"
            )
        _pool = AsyncConnectionPool(conninfo=db_url, min_size=2, max_size=10)
        await _pool.open()
        logger.info("PostgreSQL 报告元数据连接池已创建")
    return _pool


async def ensure_table():
    """确保 reports 表存在（幂等创建）"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                thread_id     VARCHAR(64),
                user_code     VARCHAR(32) NOT NULL,
                user_name     VARCHAR(64),
                branch_id     BIGINT,
                login_name    VARCHAR(64),
                title         VARCHAR(512) NOT NULL,
                duration_ms   BIGINT,
                report_url    VARCHAR(1024),
                file_size     BIGINT,
                report_type   VARCHAR(32) DEFAULT 'research',
                status        VARCHAR(16) DEFAULT 'completed',
                created_at    TIMESTAMP DEFAULT NOW(),
                updated_at    TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_reports_user_code ON reports(user_code);
            CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
            CREATE INDEX IF NOT EXISTS idx_reports_thread_id ON reports(thread_id);
        """)
        await conn.commit()
    logger.info("reports 表已确认存在")


# ─── CRUD ───

async def save_report(report: ReportRecord) -> UUID:
    """保存报告元数据，返回记录 ID"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO reports (thread_id, user_code, user_name, branch_id, login_name,
                                     title, duration_ms, report_url, file_size, report_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    report.thread_id,
                    report.user_code,
                    report.user_name,
                    report.branch_id,
                    report.login_name,
                    report.title,
                    report.duration_ms,
                    report.report_url,
                    report.file_size,
                    report.report_type,
                    report.status,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
            report_id = row[0]
            logger.info(f"✅ 报告元数据已保存 | id={report_id} | title={report.title[:50]}")
            return report_id


async def get_report_by_id(report_id: UUID) -> Optional[ReportRecord]:
    """根据 ID 获取报告详情"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reports WHERE id = %s", (str(report_id),)
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return _row_to_record(row, cur.description)


async def get_reports_by_user(
    user_code: str, page: int = 1, page_size: int = 20
) -> tuple[List[ReportRecord], int]:
    """分页查询用户的报告列表

    Returns:
        (报告列表, 总数)
    """
    pool = await _get_pool()
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 总数
            await cur.execute(
                "SELECT COUNT(*) FROM reports WHERE user_code = %s",
                (user_code,),
            )
            total = (await cur.fetchone())[0]

            # 分页数据
            await cur.execute(
                """
                SELECT * FROM reports WHERE user_code = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_code, page_size, offset),
            )
            rows = await cur.fetchall()
            records = [_row_to_record(row, cur.description) for row in rows]
            return records, total


async def get_reports_paginated(
    page: int = 1,
    page_size: int = 20,
    user_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> tuple[List[ReportRecord], int]:
    """分页查询报告列表（支持按用户、日期筛选）

    Returns:
        (报告列表, 总数)
    """
    pool = await _get_pool()
    offset = (page - 1) * page_size

    # 构建 WHERE 条件
    conditions = []
    params = []
    if user_code:
        conditions.append("user_code = %s")
        params.append(user_code)
    if start_date:
        conditions.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("created_at < %s::date + interval '1 day'")
        params.append(end_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 总数
            await cur.execute(
                f"SELECT COUNT(*) FROM reports WHERE {where_clause}",
                params,
            )
            total = (await cur.fetchone())[0]

            # 分页数据
            await cur.execute(
                f"""
                SELECT * FROM reports WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [page_size, offset],
            )
            rows = await cur.fetchall()
            records = [_row_to_record(row, cur.description) for row in rows]
            return records, total


async def get_daily_statistics(
    start_date: str, end_date: str
) -> List[DailyStat]:
    """按天统计报告生成数量

    Args:
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        每日统计列表
    """
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    DATE(created_at) as report_date,
                    COUNT(*) as count,
                    SUM(duration_ms) as total_duration_ms,
                    AVG(duration_ms)::BIGINT as avg_duration_ms
                FROM reports
                WHERE created_at >= %s AND created_at < %s::date + interval '1 day'
                GROUP BY DATE(created_at)
                ORDER BY report_date
                """,
                (start_date, end_date),
            )
            rows = await cur.fetchall()
            return [
                DailyStat(
                    date=str(row[0]),
                    count=row[1],
                    total_duration_ms=row[2],
                    avg_duration_ms=row[3],
                )
                for row in rows
            ]


async def get_summary() -> DashboardSummary:
    """获取看板汇总数据"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 总报告数
            await cur.execute("SELECT COUNT(*) FROM reports")
            total_reports = (await cur.fetchone())[0]

            # 今日报告数
            await cur.execute(
                "SELECT COUNT(*) FROM reports WHERE DATE(created_at) = CURRENT_DATE"
            )
            today_reports = (await cur.fetchone())[0]

            # 总用户数
            await cur.execute("SELECT COUNT(DISTINCT user_code) FROM reports")
            total_users = (await cur.fetchone())[0]

            # 平均耗时
            await cur.execute(
                "SELECT COALESCE(AVG(duration_ms)::BIGINT, 0) FROM reports WHERE duration_ms IS NOT NULL"
            )
            avg_duration_ms = (await cur.fetchone())[0]

            return DashboardSummary(
                total_reports=total_reports,
                today_reports=today_reports,
                total_users=total_users,
                avg_duration_ms=avg_duration_ms,
            )


# ─── 辅助函数 ───

def _row_to_record(row, description) -> ReportRecord:
    """将数据库行转换为 ReportRecord"""
    columns = [col.name for col in description]
    data = dict(zip(columns, row))
    return ReportRecord(**data)
