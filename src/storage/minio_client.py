# SPDX-License-Identifier: MIT

"""
MinIO 对象存储客户端

封装 MinIO S3 兼容 API，用于上传、下载和管理报告文件。
配置通过环境变量读取：MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_BUCKET
"""

import io
import logging
import os
from datetime import timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# ─── 配置 ───

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deer-flow-reports")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

# ─── 客户端单例 ───

_client: Optional[Minio] = None


def _get_client() -> Minio:
    """获取 MinIO 客户端单例"""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        # 确保 bucket 存在
        _ensure_bucket()
    return _client


def _ensure_bucket():
    """确保存储桶存在，不存在则创建"""
    client = _client
    if client is None:
        return
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info(f"MinIO bucket '{MINIO_BUCKET}' 已创建")
        else:
            logger.info(f"MinIO bucket '{MINIO_BUCKET}' 已存在")
    except S3Error as e:
        logger.error(f"MinIO bucket 检查/创建失败: {e}")
        raise


# ─── 公开 API ───

def upload_report(
    file_bytes: bytes,
    object_name: str,
    content_type: str = "text/markdown",
) -> str:
    """上传报告文件到 MinIO

    Args:
        file_bytes: 文件内容字节
        object_name: 对象存储路径/文件名（如 "reports/2025/06/08/uuid.md"）
        content_type: 文件 MIME 类型

    Returns:
        文件的访问 URL
    """
    client = _get_client()
    file_size = len(file_bytes)

    try:
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=io.BytesIO(file_bytes),
            length=file_size,
            content_type=content_type,
        )
        logger.info(
            f"✅ MinIO 上传成功 | object={object_name} | size={file_size} bytes"
        )
        # 返回永久访问 URL（由 nginx 代理或直接访问）
        url = _build_object_url(object_name)
        return url
    except S3Error as e:
        logger.error(f"MinIO 上传失败 | object={object_name} | error={e}")
        raise


def get_report_url(object_name: str, expires: int = 7200) -> str:
    """生成预签名 URL（临时访问）

    Args:
        object_name: 对象路径
        expires: URL 有效期（秒），默认 2 小时

    Returns:
        预签名访问 URL
    """
    client = _get_client()
    try:
        url = client.presigned_get_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(seconds=expires),
        )
        return url
    except S3Error as e:
        logger.error(f"MinIO 生成预签名URL失败 | object={object_name} | error={e}")
        raise


def get_object_bytes(object_name: str) -> bytes:
    """下载对象内容

    Args:
        object_name: 对象路径

    Returns:
        文件字节内容
    """
    client = _get_client()
    try:
        response = client.get_object(MINIO_BUCKET, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        logger.error(f"MinIO 下载失败 | object={object_name} | error={e}")
        raise


def _build_object_url(object_name: str) -> str:
    """构建对象的永久访问 URL

    根据是否有 MINIO_PUBLIC_URL 环境变量决定 URL 格式：
    - 有 MINIO_PUBLIC_URL: 使用 nginx 代理地址
    - 无: 使用 endpoint 直接拼接
    """
    public_url = os.getenv("MINIO_PUBLIC_URL", "")
    if public_url:
        return f"{public_url.rstrip('/')}/{MINIO_BUCKET}/{object_name}"

    scheme = "https" if MINIO_SECURE else "http"
    return f"{scheme}://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
