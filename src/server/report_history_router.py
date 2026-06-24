# SPDX-License-Identifier: MIT

"""
用户历史报告 API 路由

提供当前登录用户查看自己历史报告列表、获取报告正文内容、
基于历史报告继续对话等接口。所有接口均以 login_name 做数据隔离。
"""

import asyncio
import json
import logging
import time
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
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


class ReportChatRequest(BaseModel):
    """基于历史报告的直连 LLM 流式对话请求"""
    message: str
    history: Optional[List[dict]] = None  # 历史对话消息（role/content 格式）
    reporter_model: Optional[str] = None  # 可选指定 reporter 模型


class UpdateReportRequest(BaseModel):
    """更新报告内容请求"""
    content: str


class UpdateReportResponse(BaseModel):
    """更新报告内容响应"""
    success: bool
    object_name: str
    file_size: int


# ─── 辅助函数 ───


def _get_current_login_name(request: Request) -> str:
    """从 auth 中间件注入的 request.state 中提取当前用户登录名"""
    user_info = getattr(request.state, "user_info", None)
    if user_info is None or not user_info.is_authenticated:
        raise HTTPException(status_code=401, detail="未登录或认证已过期")
    return user_info.login_name


async def _read_report_content(report_id: UUID, login_name: str) -> tuple[str, str, Optional[str]]:
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

    if record.login_name != login_name:
        logger.warning(
            f"[REPORT_HISTORY] 越权访问尝试 | report_id={report_id} | "
            f"owner={record.login_name} | requester={login_name}"
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
    """获取当前用户的报告列表（强制 login_name 隔离，支持标题搜索）"""
    login_name = _get_current_login_name(request)

    items, total = await report_repository.get_reports_paginated(
        page=page,
        page_size=page_size,
        login_name=login_name,
        status=status,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
    )
    return ReportListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


# ─── 辅助函数：报告 ID 解析（兼容 UUID 和 thread_id） ───


async def _resolve_report_record(identifier: str, login_name: str) -> "report_repository.ReportRecord":
    """将报告标识解析为报告记录。

    identifier 可以是：
      - 数据库 UUID（标准格式，来自 Dashboard 历史报告列表）
      - thread_id（来自深度研究流程的前端 THREAD_ID）

    Raises:
        HTTPException 400: 无效标识符
        HTTPException 404: 报告不存在
        HTTPException 403: 无权访问
    """
    record = None

    # 优先尝试 UUID 解析
    try:
        uid = UUID(identifier)
        record = await report_repository.get_report_by_id(uid)
    except ValueError:
        pass  # 不是 UUID，继续尝试 thread_id

    # 回退：按 thread_id 查询
    if record is None:
        record = await report_repository.get_report_by_thread_id(identifier, login_name)

    if record is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    if record.login_name != login_name:
        logger.warning(
            f"[REPORT_HISTORY] 越权访问尝试 | identifier={identifier} | "
            f"owner={record.login_name} | requester={login_name}"
        )
        raise HTTPException(status_code=403, detail="无权访问此报告")

    return record


# ─── API 接口（报告内容/继续对话） ───


@router.get("/{report_id}/content", response_model=ReportContentResponse)
async def get_report_content(report_id: str, request: Request):
    """获取报告 Markdown 正文内容（含权限校验）"""
    login_name = _get_current_login_name(request)

    try:
        uid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    content, title, report_url = await _read_report_content(uid, login_name)

    logger.info(
        f"[REPORT_HISTORY] 读取报告内容 | report_id={report_id} | "
        f"login_name={login_name} | title={title[:50]} | content_len={len(content)}"
    )
    return ReportContentResponse(
        content=content, title=title, report_url=report_url
    )


@router.post("/{report_id}/continue", response_model=ContinueReportResponse)
async def continue_report(report_id: str, request: Request):
    """基于历史报告发起新对话（返回报告内容供前端注入上下文）"""
    login_name = _get_current_login_name(request)

    try:
        uid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    content, title, _ = await _read_report_content(uid, login_name)

    logger.info(
        f"[REPORT_HISTORY] 继续对话 | report_id={report_id} | "
        f"login_name={login_name} | title={title[:50]}"
    )
    return ContinueReportResponse(
        report_content=content, title=title
    )


@router.put("/{report_id}", response_model=UpdateReportResponse)
async def update_report(report_id: str, request: Request, body: UpdateReportRequest):
    """更新报告内容（覆盖写入 MinIO + 更新数据库 file_size）

    report_id 支持 UUID 或 thread_id。
    """
    login_name = _get_current_login_name(request)
    record = await _resolve_report_record(report_id, login_name)

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
    await report_repository.update_report_file_size(record.id, file_size)

    logger.info(
        f"[REPORT_HISTORY] 报告已更新 | report_id={report_id} | "
        f"login_name={login_name} | object_name={object_name} | file_size={file_size}"
    )
    return UpdateReportResponse(
        success=True, object_name=object_name, file_size=file_size
    )


@router.post("/{report_id}/chat")
async def report_chat(report_id: str, request: Request, body: ReportChatRequest):
    """基于历史报告的直连 LLM 流式对话

    绕过完整研究图（coordinator/planner/researcher），
    直接调用 reporter 模型，将报告内容作为上下文回答用户提问。
    返回 SSE 流式响应（格式与 /api/chat/stream 保持一致）。

    report_id 支持 UUID 或 thread_id。
    """
    login_name = _get_current_login_name(request)
    record = await _resolve_report_record(report_id, login_name)

    # 读取报告内容（record.id 是数据库 UUID，直接读取 MinIO）
    report_content, title, _ = await _read_report_content(record.id, login_name)

    logger.info(
        f"[REPORT_CHAT] 发起直连对话 | report_id={report_id} | "
        f"login_name={login_name} | title={title[:50]} | message={body.message[:80]}"
    )

    thread_id = str(uuid.uuid4())
    msg_id = str(uuid.uuid4())

    async def event_generator():
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        from src.config.agents import AGENT_LLM_MAP
        from src.llms.llm import get_llm_by_type

        # 构建系统提示：报告内容作为上下文
        system_prompt = (
            f"你是“交心深度研究”助手。用户正在基于以下历史报告继续提问。"
            f"请仅基于报告内容回答用户的问题，不要引入额外搜索或研究。"
            f"如果报告中未包含相关信息，请如实告知。\n\n"
            f"# 报告标题：{title}\n\n"
            f"# 报告全文\n{report_content}"
        )

        # 构建消息列表
        messages = [SystemMessage(content=system_prompt)]

        # 历史对话（如果有）
        if body.history:
            for h in body.history[-10:]:  # 最多保留最近 10 条
                role = h.get("role", "user")
                content = h.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # 当前用户消息
        messages.append(HumanMessage(content=body.message))

        # 获取 reporter LLM
        reporter_model_key = body.reporter_model or None
        llm = get_llm_by_type(
            AGENT_LLM_MAP["reporter"],
            reporter_model_key=reporter_model_key,
        )

        start_time = time.time()
        full_content = ""

        try:
            async for chunk in llm.astream(messages):
                content = getattr(chunk, "content", "")
                if content:
                    full_content += content
                    event_data = {
                        "id": msg_id,
                        "thread_id": thread_id,
                        "agent": "reporter",
                        "role": "assistant",
                        "content": content,
                    }
                    yield f"event: message_chunk\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            # 发送结束事件
            end_data = {
                "id": msg_id,
                "thread_id": thread_id,
                "agent": "reporter",
                "role": "assistant",
                "finish_reason": "stop",
            }
            yield f"event: message_chunk\ndata: {json.dumps(end_data, ensure_ascii=False)}\n\n"

            logger.info(
                f"[REPORT_CHAT] 对话完成 | report_id={report_id} | "
                f"耗时={time.time() - start_time:.2f}s | 回复长度={len(full_content)}"
            )
        except Exception as e:
            logger.error(f"[REPORT_CHAT] LLM 调用失败 | report_id={report_id} | error={e}")
            error_data = {"thread_id": thread_id, "error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
