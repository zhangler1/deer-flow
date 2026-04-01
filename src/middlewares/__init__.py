# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Middleware modules for DeerFlow 1.0"""

from .tool_result_compression import (
    ToolResultCompressionMiddleware,
    invoke_with_tool_compression,
)

__all__ = [
    "ToolResultCompressionMiddleware",
    "invoke_with_tool_compression",
]
