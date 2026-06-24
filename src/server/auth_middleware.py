# SPDX-License-Identifier: MIT

"""
用户认证中间件

认证优先级：
1. 优先从请求头 X-User-Info 解析前端传入的完整用户信息（JSON 格式，URL 编码）
2. 失败时降级：从 Cookie 提取 guwpToken，调用内网 queryUserInfo API 解析用户信息

- 认证失败时返回 anonymous 用户，不阻断主流程
- 使用 LRU + TTL 缓存避免每次请求都调用认证接口
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ─── 用户信息数据模型 ───


@dataclass
class UserInfo:
    """用户信息数据模型

    来源优先级：
    1. 前端通过 X-User-Info 请求头直接传入（来自 GuipAPI globalInfo）
    2. 后端通过 guwpToken Cookie → queryUserInfo 内网接口解析

    认证判据以 loginName 是否存在为准，login_name 作为用户唯一标识。
    user_code（工号）仅作数据保存，不参与查询和校验。
    """
    user_code: str = ""  # 工号，仅数据保存
    user_name: str = "匿名用户"
    branch_id: Optional[int] = None
    login_name: str = ""
    linked_org_name: str = ""
    device: str = ""
    is_authenticated: bool = False
    source: str = ""  # "header" | "api" | "anonymous"


# ─── 缓存实现（LRU + TTL） ───

_user_cache: dict[str, tuple[UserInfo, float]] = {}
_CACHE_MAX_SIZE = 200
_CACHE_TTL = int(os.getenv("USER_INFO_CACHE_TTL", "300"))  # 默认 5 分钟


def _get_cached_user(token: str) -> Optional[UserInfo]:
    """从缓存获取用户信息，过期则返回 None"""
    entry = _user_cache.get(token)
    if entry is None:
        return None
    user_info, cached_at = entry
    if time.time() - cached_at > _CACHE_TTL:
        _user_cache.pop(token, None)
        return None
    return user_info


def _set_cached_user(token: str, user_info: UserInfo):
    """写入缓存，超过容量时淘汰最旧条目"""
    if len(_user_cache) >= _CACHE_MAX_SIZE:
        # 淘汰最早写入的条目
        oldest_key = next(iter(_user_cache))
        _user_cache.pop(oldest_key, None)
    _user_cache[token] = (user_info, time.time())


# ─── 从请求头解析用户信息（前端直传） ───


def _parse_user_info_from_header(request: Request) -> Optional[UserInfo]:
    """从 X-User-Info 请求头解析前端直传的用户信息。

    前端将 GuipAPI globalInfo().userInfo 序列化为 JSON 并 URL 编码后放入此头。
    解析失败或 loginName 为空时返回 None，调用方应降级到 cookie → API 流程。
    """
    raw = request.headers.get("x-user-info", "")
    if not raw:
        return None

    try:
        decoded = unquote(raw)
        data = json.loads(decoded)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[AUTH] X-User-Info 请求头解析失败: {type(e).__name__}: {e}")
        return None

    if not isinstance(data, dict):
        logger.warning(f"[AUTH] X-User-Info 格式异常，期望 dict，实际: {type(data).__name__}")
        return None

    # 以 loginName 作为用户身份唯一标识（与 queryUserInfo 接口逻辑一致）
    _login_name = data.get("loginName", "") or ""
    if not _login_name:
        logger.info("[AUTH] X-User-Info 中 loginName 为空，将降级到 cookie → API 流程")
        return None

    # branchId 可能为字符串，统一转 int
    _branch_id = data.get("branchId") or data.get("bbosBranchCode")
    if isinstance(_branch_id, str):
        try:
            _branch_id = int(_branch_id)
        except (ValueError, TypeError):
            _branch_id = None

    user_info = UserInfo(
        user_code=str(data.get("userCode", "") or ""),
        user_name=data.get("userName", ""),
        branch_id=_branch_id,
        login_name=_login_name,
        linked_org_name=data.get("linkedOrgName", ""),
        device=data.get("device", ""),
        is_authenticated=True,
        source="header",
    )
    logger.info(
        f"[AUTH] X-User-Info 解析成功 | "
        f"login_name={user_info.login_name} | user_code={user_info.user_code} | user_name={user_info.user_name} | "
        f"branch_id={user_info.branch_id} | linked_org_name={user_info.linked_org_name}"
    )
    return user_info


# ─── 认证 API 调用（降级方案） ───

USER_INFO_API_URL = os.getenv(
    "USER_INFO_API_URL",
    "http://eaip-chn-slb-7006.bocomm.com/ELLM.ELLM-OMSERVICE.V-1.0/queryUserInfo.do"
)


async def _query_user_info(token: str) -> UserInfo:
    """调用内网 queryUserInfo 接口，解析用户信息。

    失败时返回 anonymous 用户，不抛出异常。
    """
    token_preview = (token[:8] + "...") if token and len(token) > 8 else token

    logger.info(
        f"[AUTH] queryUserInfo 开始调用 | token={token_preview} | "
        f"api_url={USER_INFO_API_URL} | token_len={len(token) if token else 0}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            req_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "guwp-token": token,
                "jumpCloud-Env": "BASE",
            }
            req_body = {
                "REQ_BODY": {
                    "param": {
                        "guwpToken": token
                    }
                }
            }
            logger.debug(
                f"[AUTH] 请求详情 | headers={req_headers} | body={req_body}"
            )
            resp = await client.post(
                USER_INFO_API_URL,
                headers=req_headers,
                json=req_body,
            )
            logger.info(
                f"[AUTH] queryUserInfo 响应状态 | status={resp.status_code} | "
                f"content_type={resp.headers.get('content-type', 'N/A')} | "
                f"body_preview={resp.text[:300] if resp.text else 'empty'}"
            )
            resp.raise_for_status()
            data = resp.json()

        logger.info(f"[AUTH] 解析响应体 | data_keys={list(data.keys())} | data={data}")

        result = data.get("RSP_BODY", {}).get("result", {})
        # 以 loginName 作为用户身份唯一标识（而非工号 userCode）
        _login_name = result.get("loginName", "") if result else ""
        if not _login_name:
            logger.warning(
                f"[AUTH] queryUserInfo 返回无效结果（无 loginName）| "
                f"token={token_preview} | result={result} | full_response={data}"
            )
            return UserInfo()

        user_info = UserInfo(
            user_code=str(result.get("userCode", "") or ""),
            user_name=result.get("userName", ""),
            branch_id=result.get("branchId"),
            login_name=_login_name,
            linked_org_name=result.get("linkedOrgName", ""),
            device=result.get("device", ""),
            is_authenticated=True,
            source="api",
        )
        logger.info(
            f"[AUTH] queryUserInfo 成功 | token={token_preview} | "
            f"login_name={user_info.login_name} | user_code={user_info.user_code} | user_name={user_info.user_name} | "
            f"branch_id={user_info.branch_id} | "
            f"linked_org_name={user_info.linked_org_name}"
        )
        return user_info

    except httpx.HTTPStatusError as e:
        logger.warning(
            f"[AUTH] queryUserInfo HTTP错误 | token={token_preview} | "
            f"status={e.response.status_code} | response_body={e.response.text[:300] if e.response.text else 'empty'} | "
            f"detail={str(e)[:200]}"
        )
    except httpx.RequestError as e:
        logger.warning(
            f"[AUTH] queryUserInfo 网络错误（接口不可达） | token={token_preview} | "
            f"api_url={USER_INFO_API_URL} | {type(e).__name__}: {str(e)[:300]}"
        )
    except Exception as e:
        logger.warning(
            f"[AUTH] queryUserInfo 未知错误 | token={token_preview} | {type(e).__name__}: {str(e)[:300]}"
        )

    return UserInfo()


# ─── FastAPI 中间件 ───

class GuwpTokenAuthMiddleware(BaseHTTPMiddleware):
    """用户认证中间件

    认证优先级：
    1. X-User-Info 请求头（前端直传 GuipAPI globalInfo 的完整 userinfo）
    2. Cookie guwpToken → 内网 queryUserInfo API（降级方案）
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # ─── 优先级 1：从 X-User-Info 请求头解析前端直传的用户信息 ───
        user_info = _parse_user_info_from_header(request)

        if user_info is not None:
            logger.info(
                f"[AUTH] 使用前端直传用户信息 | path={path} | "
                f"login_name={user_info.login_name} | source={user_info.source}"
            )
        else:
            # ─── 优先级 2：降级到 cookie → queryUserInfo API ───
            token = request.cookies.get("guwpToken", "")

            if path.startswith("/api"):
                cookies_keys = list(request.cookies.keys())
                logger.info(
                    f"[AUTH] 降级到 cookie 认证 | path={path} | method={request.method} | "
                    f"has_guwpToken={bool(token)} | token_len={len(token) if token else 0} | "
                    f"cookie_keys={cookies_keys}"
                )

            if token:
                # 先查缓存
                user_info = _get_cached_user(token)
                if user_info is None:
                    logger.info(f"[AUTH] 缓存未命中，将调用远程接口 | path={path}")
                    user_info = await _query_user_info(token)
                    _set_cached_user(token, user_info)
                else:
                    logger.info(
                        f"[AUTH] 缓存命中 | path={path} | "
                        f"login_name={user_info.login_name} | user_name={user_info.user_name}"
                    )
            else:
                logger.info(
                    f"[AUTH] 未携带 guwpToken 且无 X-User-Info，使用匿名用户 | path={path} | "
                    f"cookie_keys={list(request.cookies.keys())}"
                )
                user_info = UserInfo()

        # 注入到 request.state
        request.state.user_info = user_info
        request.state.guwp_token = request.cookies.get("guwpToken", "")

        response = await call_next(request)
        return response
