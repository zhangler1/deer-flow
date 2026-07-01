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
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger

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
        # 通过连接字符串 options 设置会话时区为 Asia/Shanghai
        separator = "&" if "?" in db_url else "?"
        db_url_with_tz = f"{db_url}{separator}options=-c%20timezone%3DAsia/Shanghai"
        _pool = AsyncConnectionPool(
            conninfo=db_url_with_tz,
            min_size=2,
            max_size=20,
        )
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
                user_code     VARCHAR(32),                            -- 工号，仅数据保存，不参与查询
                user_name     VARCHAR(64),
                branch_id     BIGINT,
                login_name    VARCHAR(64) NOT NULL,                   -- 登录名（数据隔离主键）
                linked_org_name VARCHAR(128),
                title         VARCHAR(512) NOT NULL,
                duration_ms   BIGINT,
                report_url    VARCHAR(1024),
                object_name   VARCHAR(512),
                file_size     BIGINT,
                report_type   VARCHAR(32) DEFAULT 'research',
                status        VARCHAR(16) DEFAULT 'completed',
                created_at    TIMESTAMP DEFAULT NOW(),
                updated_at    TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_reports_login_name ON reports(login_name);
            CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
            CREATE INDEX IF NOT EXISTS idx_reports_thread_id ON reports(thread_id);
        """)
        # 幂等新增 object_name 列（兼容已存在的表）
        await conn.execute("""
            ALTER TABLE reports
            ADD COLUMN IF NOT EXISTS object_name VARCHAR(512);
            CREATE INDEX IF NOT EXISTS idx_reports_object_name ON reports(object_name);
        """)
        # 幂等新增 linked_org_name 列
        await conn.execute("""
            ALTER TABLE reports
            ADD COLUMN IF NOT EXISTS linked_org_name VARCHAR(128);
        """)
        # 幂等补充 login_name 索引
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_login_name ON reports(login_name);
        """)
        # 幂等创建角色权限表（管理员看板）
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id          SERIAL PRIMARY KEY,
                name        VARCHAR(32) NOT NULL UNIQUE,
                description VARCHAR(128)
            );
            CREATE TABLE IF NOT EXISTS user_roles (
                id          SERIAL PRIMARY KEY,
                login_name  VARCHAR(64) NOT NULL,
                role_name   VARCHAR(32) NOT NULL REFERENCES roles(name),
                created_at  TIMESTAMP DEFAULT NOW(),
                UNIQUE(login_name, role_name)
            );
        """)
        # 预置管理员角色（幂等）
        await conn.execute("""
            INSERT INTO roles (name, description)
            VALUES ('admin', '系统管理员')
            ON CONFLICT DO NOTHING;
        """)
        await conn.commit()
    logger.info("reports 表已确认存在（含 object_name 字段）")


# ─── 权限查询 ───

async def is_user_admin(login_name: str) -> bool:
    """查询用户是否拥有 admin 角色"""
    try:
        pool = await _get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM user_roles WHERE login_name = %s AND role_name = 'admin' LIMIT 1",
                    (login_name,),
                )
                return (await cur.fetchone()) is not None
    except Exception as e:
        logger.warning(f"查询管理员角色失败 | login_name={login_name} | {e}")
        return False


# ─── CRUD ───

async def save_report(report: ReportRecord) -> UUID:
    """保存报告元数据，返回记录 ID"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO reports (thread_id, user_code, user_name, branch_id, login_name, linked_org_name,
                                     title, duration_ms, report_url, object_name, file_size, report_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    report.thread_id,
                    report.user_code,
                    report.user_name,
                    report.branch_id,
                    report.login_name,
                    report.linked_org_name,
                    report.title,
                    report.duration_ms,
                    report.report_url,
                    report.object_name,
                    report.file_size,
                    report.report_type,
                    report.status,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
            report_id = row[0]
            logger.info(f"报告元数据已保存 | id={report_id} | thread_id={report.thread_id} | title={report.title[:50]} | login_name={report.login_name}")
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


async def get_report_by_thread_id(thread_id: str, login_name: str) -> Optional[ReportRecord]:
    """根据 thread_id 获取最新一条已完成报告的详情（含权限校验）"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reports WHERE thread_id = %s AND login_name = %s "
                "AND status = 'completed' ORDER BY created_at DESC LIMIT 1",
                (thread_id, login_name),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return _row_to_record(row, cur.description)


async def update_report_file_size(report_id: UUID, file_size: int) -> None:
    """更新报告文件大小"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE reports SET file_size = %s, updated_at = NOW() WHERE id = %s",
                (file_size, str(report_id)),
            )
            await conn.commit()
            logger.info(f"报告文件大小已更新 | id={report_id} | file_size={file_size}")


async def get_reports_by_user(
    login_name: str, page: int = 1, page_size: int = 20
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
                "SELECT COUNT(*) FROM reports WHERE login_name = %s",
                (login_name,),
            )
            total = (await cur.fetchone())[0]

            # 分页数据
            await cur.execute(
                """
                SELECT * FROM reports WHERE login_name = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (login_name, page_size, offset),
            )
            rows = await cur.fetchall()
            records = [_row_to_record(row, cur.description) for row in rows]
            return records, total


async def get_reports_paginated(
    page: int = 1,
    page_size: int = 20,
    login_name: Optional[str] = None,
    user_name: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
) -> tuple[List[ReportRecord], int]:
    """分页查询报告列表（支持按用户、姓名、日期、状态、标题关键词筛选）

    Returns:
        (报告列表, 总数)
    """
    pool = await _get_pool()
    offset = (page - 1) * page_size

    # 构建 WHERE 条件
    conditions = []
    params = []
    if login_name:
        conditions.append("login_name = %s")
        params.append(login_name)
    if user_name:
        conditions.append("user_name ILIKE %s")
        params.append(f"%{user_name}%")
    if status:
        conditions.append("status = %s")
        params.append(status)
    if start_date:
        conditions.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("created_at < %s::date + interval '1 day'")
        params.append(end_date)
    if keyword:
        conditions.append("title ILIKE %s")
        params.append(f"%{keyword}%")

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
    """获取看板汇总数据（仅统计已完成的报告）"""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 总报告数（仅已完成）
            await cur.execute("SELECT COUNT(*) FROM reports WHERE status = 'completed'")
            total_reports = (await cur.fetchone())[0]

            # 今日报告数（仅已完成）
            await cur.execute(
                "SELECT COUNT(*) FROM reports WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed'"
            )
            today_reports = (await cur.fetchone())[0]

            # 本月报告数（仅已完成）
            await cur.execute(
                "SELECT COUNT(*) FROM reports WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE) AND status = 'completed'"
            )
            month_reports = (await cur.fetchone())[0]

            # 月活用户（近 30 天内生成过报告的去重用户数）
            await cur.execute(
                "SELECT COUNT(DISTINCT login_name) FROM reports WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'"
            )
            mau = (await cur.fetchone())[0]

            # 日活用户（今日生成过报告的去重用户数）
            await cur.execute(
                "SELECT COUNT(DISTINCT login_name) FROM reports WHERE DATE(created_at) = CURRENT_DATE"
            )
            dau = (await cur.fetchone())[0]

            # 平均耗时（仅已完成的报告）
            await cur.execute(
                "SELECT COALESCE(AVG(duration_ms)::BIGINT, 0) FROM reports WHERE duration_ms IS NOT NULL AND status = 'completed'"
            )
            avg_duration_ms = (await cur.fetchone())[0]

            return DashboardSummary(
                total_reports=total_reports,
                today_reports=today_reports,
                month_reports=month_reports,
                mau=mau,
                dau=dau,
                avg_duration_ms=avg_duration_ms,
            )


# ─── 平均耗时查询 ───

async def get_avg_duration_ms() -> int:
    """获取已完成报告的平均耗时（毫秒），用于前端进度估算。

    Returns:
        平均耗时（毫秒），无数据时返回 0
    """
    try:
        pool = await _get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COALESCE(AVG(duration_ms)::BIGINT, 0) "
                    "FROM reports "
                    "WHERE duration_ms IS NOT NULL AND status = 'completed'"
                )
                row = await cur.fetchone()
                return int(row[0]) if row else 0
    except Exception as e:
        logger.warning(f"获取平均耗时失败（数据库可能未配置）: {e}")
        return 0


# ─── 辅助函数 ───

def _row_to_record(row, description) -> ReportRecord:
    """将数据库行转换为 ReportRecord"""
    columns = [col.name for col in description]
    data = dict(zip(columns, row))
    return ReportRecord(**data)
