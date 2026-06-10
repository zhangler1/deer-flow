"""Mock Search API - 搜索路由模块"""

from fastapi import APIRouter

from . import bocom_router, online_router, searchknowledge_router, user_router

# 创建主路由器
router = APIRouter()

# 注册所有子路由
router.include_router(bocom_router.router)
router.include_router(online_router.router)
router.include_router(searchknowledge_router.router)
router.include_router(user_router.router)

__all__ = ["router"]
