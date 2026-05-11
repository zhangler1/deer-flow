# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Server script for running the DeerFlow API.
"""
import os
import asyncio
import argparse
import logging
import signal
import sys
import warnings

# 屏蔽 langchain_tavily 中 TavilyResearch 的 pydantic 字段遮蔽告警
# （output_schema / stream 会覆盖 BaseTool 同名属性，属已知且无害的告警）
warnings.filterwarnings(
    "ignore",
    message=r'Field name "(output_schema|stream)" in "TavilyResearch" shadows an attribute in parent "BaseTool"',
    category=UserWarning,
)

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# ── ELLM 链路调试开关 ──
# 设置环境变量 ELLM_LOG_DEBUG=1 （或 true / yes）可将 ELLM 相关模块的日志活动
# （API key 获取 / 后台刷新 / header 注入）单独切到 DEBUG 级别，
# 其他模块保持 INFO，便于排查内网鉴权问题而不注入替换日志。
if os.getenv("ELLM_LOG_DEBUG", "").lower() in ("1", "true", "yes"):
    logging.getLogger("src.llms.providers.ellm").setLevel(logging.DEBUG)
    logging.getLogger("src.llms.providers.ellm_apikey_manager").setLevel(logging.DEBUG)
    logger.info("ELLM_LOG_DEBUG enabled: src.llms.providers.ellm[_apikey_manager] -> DEBUG")

# To ensure compatibility with Windows event loop issues when using Uvicorn and Asyncio Checkpointer,
# This is necessary because some libraries expect a selector-based event loop.
# This is a workaround for issues with Uvicorn and Watchdog on Windows.
# See:
# Since Python 3.8 the default on Windows is the Proactor event loop,
# which lacks add_reader/add_writer and can break libraries that expect selector-based I/O (e.g., some Uvicorn/Watchdog/stdio integrations).
# For compatibility, this forces the selector loop.
if os.name == "nt":
    logger.info("Setting Windows event loop policy for asyncio")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    logger.info("Received shutdown signal. Starting graceful shutdown...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the DeerFlow API server")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (default: True except on Windows)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind the server to (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    # Determine reload setting
    reload = False
    if args.reload:
        reload = True

    try:
        logger.info(f"Starting DeerFlow API server on {args.host}:{args.port}")
        uvicorn.run(
            "src.server:app",
            host=args.host,
            port=args.port,
            reload=reload,
            log_level=args.log_level,
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
