"""Mock Search API - queryUserInfo 用户信息查询路由"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ELLM.ELLM-OMSERVICE.V-1.0/queryUserInfo.do")
async def query_user_info(request: Request):
    """用户信息查询 mock 接口。

    通过 guwpToken 获取当前登录用户信息。
    请求格式：application/json
    """
    try:
        body = await request.json()
        req_body = body.get("REQ_BODY", {})
        param = req_body.get("param", {})
        guwp_token = param.get("guwpToken", "") or request.headers.get("guwp-token", "")

        logger.info("[queryUserInfo] guwpToken=%s", guwp_token[:8] + "..." if len(guwp_token) > 8 else guwp_token)

        response_data = {
            "RSP_BODY": {
                "result": {
                    "guwpToken": guwp_token or "mock_guwp_token_default",
                    "guipToken": None,
                    "jrtAuthCode": None,
                    "okicToken": None,
                    "okicType": None,
                    "httpHeaders": None,
                    "branchId": 1000000003,
                    "loginName": "zhangl_1116",
                    "userCode": "985860",
                    "userName": "张乐",
                    "euifUserId": 5000000001,
                    "device": "PC",
                    "roles": None,
                    "uniqueId": None,
                    "logined": True,
                    "userId": None,
                    "uuid": None,
                    "locale": None,
                    "state": None,
                    "cifId": None,
                    "name": None,
                    "attributes": {},
                },
                "param": None,
            },
            "RSP_HEAD": {
                "TRAN_SUCCESS": "1",
                "TRACE_NO": "mock-omservice-queryUserInfo-001",
                "TRACE_ID": "mock.1.00.queryUserInfo",
                "PROCESS_STATUS_CODE": "N",
                "BIZ_TRACE_NO": None,
            },
        }
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error("[queryUserInfo] 处理请求异常: %s", e)
        return JSONResponse(
            content={
                "RSP_BODY": {"result": None, "param": None},
                "RSP_HEAD": {
                    "TRAN_SUCCESS": "0",
                    "TRACE_NO": "mock-omservice-error",
                    "TRACE_ID": "mock.1.00.error",
                    "PROCESS_STATUS_CODE": "E",
                    "BIZ_TRACE_NO": None,
                },
            },
            status_code=500,
        )
