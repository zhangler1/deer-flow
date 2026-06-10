# Mock 搜索服务 - 主入口文件
#
# 采用 FastAPI routers 模式组织代码:
#   - routers/bocom_router.py          -> bocomsearch（内网知识库）
#   - routers/online_router.py         -> online_search（互联网搜索）
#   - routers/searchknowledge_router.py -> searchknowledge_standard（段落级知识检索）
#   - routers/user_router.py           -> queryUserInfo（用户信息查询）
#
# 启动方式：
#   uvicorn mock_search_api:app --host 0.0.0.0 --port 8010 --reload

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import bocom_router, online_router, searchknowledge_router, user_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

app = FastAPI(title="Mock Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 注册路由
# ============================================================
# 方式1：直接注册各个子路由（推荐）
app.include_router(bocom_router.router)
app.include_router(online_router.router)
app.include_router(searchknowledge_router.router)
app.include_router(user_router.router)

# 方式2：通过主路由器统一注册（可选）
# from routers import router as search_router
# app.include_router(search_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock_search_api", "port": 8010}


if __name__ == "__main__":
    import uvicorn
    print("[Mock Search API 启动]")
    print("  路由模块:")
    print("    - bocom_router.py          -> bocomsearch（内网知识库，5条）")
    print("    - online_router.py         -> online_search（互联网新闻，10条）")
    print("    - searchknowledge_router.py -> searchknowledge_standard（段落级知识检索，10条）")
    print("    - user_router.py           -> queryUserInfo（用户信息查询）")
    print("  接口路径:")
    print("    POST /ELLM.ELLM-OFFICE.V-1.0/querySources.do (bocomsearch)")
    print("    POST /ELLM.ELLM-OFFICE.V-1.0/querySources.do (online_search)")
    print("    POST /EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do")
    print("    POST /ELLM.ELLM-OMSERVICE.V-1.0/queryUserInfo.do")
    print("    GET  /health")
    uvicorn.run("mock_search_api:app", host="0.0.0.0", port=8010, reload=True)
