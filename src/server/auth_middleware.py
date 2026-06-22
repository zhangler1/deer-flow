# SPDX-License-Identifier: MIT

"""
guwpToken 用户认证中间件

从请求 Cookie 中提取 guwpToken，调用内网 queryUserInfo API 解析用户信息，
注入到 request.state 中，供后续路由处理函数使用。

- Token 无效或接口失败时返回 anonymous 用户，不阻断主流程
- 使用 LRU + TTL 缓存避免每次请求都调用认证接口
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ─── 用户信息数据模型 ───


@dataclass
class UserInfo:
    """从 queryUserInfo 接口解析的用户信息"""
    user_code: str = "anonymous"
    user_name: str = "匿名用户"
    branch_id: Optional[int] = None
    login_name: str = ""
    device: str = ""
    is_authenticated: bool = False


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


# ─── 认证 API 调用 ───

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
        if not result or not result.get("userCode"):
            logger.warning(
                f"[AUTH] queryUserInfo 返回无效结果（无 userCode）| "
                f"token={token_preview} | result={result} | full_response={data}"
            )
            return UserInfo()

        user_info = UserInfo(
            user_code=str(result.get("userCode", "")),
            user_name=result.get("userName", ""),
            branch_id=result.get("branchId"),
            login_name=result.get("loginName", ""),
            device=result.get("device", ""),
            is_authenticated=True,
        )
        logger.info(
            f"[AUTH] queryUserInfo 成功 | token={token_preview} | "
            f"user_code={user_info.user_code} | user_name={user_info.user_name} | "
            f"branch_id={user_info.branch_id} | login_name={user_info.login_name}"
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
    """从 Cookie 中提取 guwpToken 并解析用户信息注入到 request.state"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 从 Cookie 中获取 guwpToken
        token = request.cookies.get("guwpToken", "")

        # 记录所有请求的认证入口日志（仅 API 请求，跳过静态资源）
        path = request.url.path
        if path.startswith("/api"):
            cookies_keys = list(request.cookies.keys())
            logger.info(
                f"[AUTH] 请求进入 | path={path} | method={request.method} | "
                f"has_guwpToken={bool(token)} | token_len={len(token) if token else 0} | "
                f"cookie_keys={cookies_keys}"
            )

        if token:
            # 先查缓存
            user_info = _get_cached_user(token)
            if user_info is None:
                logger.info(f"[AUTH] 缓存未命中，将调用远程接口 | path={path}")
                # 缓存未命中，调用 API
                user_info = await _query_user_info(token)
                _set_cached_user(token, user_info)
            else:
                logger.info(
                    f"[AUTH] 缓存命中 | path={path} | "
                    f"user_code={user_info.user_code} | user_name={user_info.user_name}"
                )
        else:
            logger.info(
                f"[AUTH] 未携带 guwpToken，使用匿名用户 | path={path} | "
                f"cookie_keys={list(request.cookies.keys())}"
            )
            user_info = UserInfo()

        # 注入到 request.state
        request.state.user_info = user_info
        request.state.guwp_token = token

        response = await call_next(request)
        return response
